import type { ChatRequest } from '#/api/agent/chat';
import type { ChatEndpointConfig } from '#/config/chat-endpoints';
import type {
  ChatMessage,
  InterruptRequest,
  SSEMessage,
  StreamError,
} from '#/views/agent/chat/types/chat';

import { ref } from 'vue';

import { XStream } from 'ant-design-x-vue';

import { sendChatMessage } from '#/api/agent/chat';
import { useAgentChatStore } from '#/store/modules/agent-chat';
import { createTimestampedId } from '#/views/agent/chat/services/id';
import {
  ConnectionStatus,
  isSSEMessage,
  SessionStatus,
} from '#/views/agent/chat/types/chat';
import { parseInterruptOptions } from '#/views/agent/chat/utils/parseInterruptOptions';

function createStreamError(
  message: string,
  code = 'STREAM_ERROR',
): StreamError {
  return {
    code,
    message,
    timestamp: Date.now(),
    isRecoverable: true,
  };
}

function toChatMessage(
  event: SSEMessage,
  type: ChatMessage['type'],
): ChatMessage {
  return {
    id: createTimestampedId(),
    type,
    content: event.content ?? '',
    nodeName: event.node_name,
    timestamp: Date.now(),
    conversationId: event.conversation_id,
  };
}

export function useChatStream() {
  const store = useAgentChatStore();
  const isStreaming = ref(false);
  const error = ref<null | StreamError>(null);

  let timeoutHandle: ReturnType<typeof setTimeout> | undefined;
  let controller: AbortController | null = null;

  function clearStreamTimeout() {
    if (timeoutHandle) {
      clearTimeout(timeoutHandle);
      timeoutHandle = undefined;
    }
  }

  function scheduleTimeout(config: ChatEndpointConfig) {
    clearStreamTimeout();

    // 如果配置的超时时间为undefined，则不设置超时
    if (config.timeoutMs === undefined) {
      return;
    }

    timeoutHandle = setTimeout(() => {
      handleStreamError(createStreamError('Stream timeout', 'STREAM_TIMEOUT'));
      if (controller) {
        controller.abort();
      }
    }, config.timeoutMs);
  }

  function handleStart(message: SSEMessage) {
    if (store.currentSession) {
      if (message.conversation_id) {
        store.currentSession.id = message.conversation_id;
      }
      store.currentSession.updatedAt = Date.now();
      store.currentSession.status = SessionStatus.ACTIVE;
    }

    store.updateStreamState({
      isStreaming: true,
      connectionStatus: ConnectionStatus.STREAMING,
      lastUpdateTime: Date.now(),
    });
  }

  function handleOutput(message: SSEMessage) {
    const chatMessage = toChatMessage(message, 'output');
    store.addMessageToCurrentGroup(chatMessage);
  }

  function handleExecution(message: SSEMessage) {
    const chatMessage = toChatMessage(message, 'execution');
    store.addMessageToCurrentGroup(chatMessage);
  }

  function handleToolCall(message: SSEMessage) {
    const chatMessage = toChatMessage(message, 'tool_call');
    (chatMessage as any).toolPayload = {
      tool_name: (message as any).tool_name,
      arguments: (message as any).arguments,
    };
    store.addMessageToCurrentGroup(chatMessage);
  }

  function handleToolResult(message: SSEMessage) {
    const chatMessage = toChatMessage(message, 'tool_result');
    (chatMessage as any).toolPayload = {
      tool_name: (message as any).tool_name,
      data: (message as any).data,
      error: (message as any).error,
      message: (message as any).message,
    };
    store.addMessageToCurrentGroup(chatMessage);
  }

  function handleInterrupt(message: SSEMessage, currentConfig: ChatEndpointConfig) {
    const options = parseInterruptOptions(message.content ?? '');

    // 🔧 [STAGE_WORKFLOW] 从配置URL解析当前阶段
    let currentStage: string | undefined;
    if (currentConfig.isStageWorkflow && currentConfig.stageBaseUrl) {
      const match = currentConfig.url.match(/\/([^/]+)$/);
      currentStage = match ? match[1] : undefined;
    }

    const interruptRequest: InterruptRequest = {
      id: createTimestampedId(),
      checkpointId: message.checkpoint_id ?? '',
      conversationId: message.conversation_id ?? '',
      content: message.content ?? '',
      options,
      timestamp: Date.now(),
      currentStage, // 🔧 [STAGE_WORKFLOW] 保存从URL解析的阶段
    };
    store.setInterrupt(interruptRequest);
  }

  function handleComplete(message: SSEMessage) {
    // 🔧 [STAGE_WORKFLOW] 修改：从store获取conversation_id和checkpoint_id
    if (message.next) {
      const conversationId = store.currentSession?.id;
      const checkpointId = store.currentSession?.checkpointId;

      if (conversationId && checkpointId) {
        store.setPendingNextStage(
          message.next,
          conversationId,
          checkpointId,
        );
      }
    }

    // 原有逻辑保持不变
    store.updateStreamState({
      isStreaming: false,
      connectionStatus: ConnectionStatus.DISCONNECTED,
      lastUpdateTime: Date.now(),
    });
    clearStreamTimeout();
    isStreaming.value = false;
  }

  function handleStreamError(streamError: StreamError) {
    error.value = streamError;
    store.registerStreamError(streamError);
    isStreaming.value = false;
    clearStreamTimeout();
  }

  async function processStream(
    readable: ReadableStream<Uint8Array>,
    config: ChatEndpointConfig,
  ) {
    const stream = XStream({ readableStream: readable });

    for await (const chunk of stream) {
      scheduleTimeout(config);

      const raw = chunk?.data;
      if (!raw || typeof raw !== 'string') {
        continue;
      }

      let payload: unknown;
      try {
        payload = JSON.parse(raw);
        console.log('[Chat SSE]', (payload as any).type, raw.slice(0, 200));
      } catch {
        handleStreamError(
          createStreamError(
            'Failed to parse stream message',
            'STREAM_PARSE_ERROR',
          ),
        );
        continue;
      }

      if (!isSSEMessage(payload)) {
        continue;
      }

      switch (payload.type) {
        case 'complete': {
          handleComplete(payload);
          break;
        }
        case 'execution_msg': {
          handleExecution(payload);
          break;
        }
        case 'interrupt': {
          handleInterrupt(payload, config); // 🔧 [STAGE_WORKFLOW] 传递config用于解析阶段
          break;
        }
        case 'output_msg': {
          handleOutput(payload);
          break;
        }
        case 'start': {
          handleStart(payload);
          break;
        }
        case 'tool_call': {
          handleToolCall(payload);
          break;
        }
        case 'tool_result': {
          handleToolResult(payload);
          break;
        }
        default: {
          break;
        }
      }
    }
  }

  async function sendMessage(request: ChatRequest, config: ChatEndpointConfig) {
    if (isStreaming.value) {
      controller?.abort();
    }

    controller = new AbortController();
    error.value = null;
    isStreaming.value = true;

    // Check if this is continuing an existing session (interrupt response)
    if (request.conversation_id && request.checkpoint_id) {
      store.continueSession(request.conversation_id, request.checkpoint_id);
    } else if (!store.currentSession) {
      // 只有在没有 session 时才创建新 session
      // 注意：通常在添加用户消息时已经创建了 session
      store.startNewSession({
        userInput: request.message,
      });
    }

    store.updateStreamState({
      isStreaming: true,
      connectionStatus: ConnectionStatus.CONNECTING,
      lastUpdateTime: Date.now(),
      retryCount: 0,
    });

    try {
      console.log('[Chat] Sending request:', request.message.slice(0, 50));
      const response = await sendChatMessage(request, config, {
        signal: controller.signal,
      });

      console.log('[Chat] Response status:', response.status, 'ok:', response.ok, 'body:', !!response.body);

      if (!response.ok) {
        throw createStreamError(
          `Stream request failed (${response.status})`,
          'HTTP_ERROR',
        );
      }

      if (!response.body) {
        throw createStreamError(
          'Stream response missing body',
          'NO_STREAM_BODY',
        );
      }

      store.updateStreamState({
        connectionStatus: ConnectionStatus.CONNECTED,
        lastUpdateTime: Date.now(),
      });

      scheduleTimeout(config);
      await processStream(response.body, config);
    } catch (error_) {
      const streamError =
        error_ instanceof Error
          ? createStreamError(error_.message)
          : createStreamError('Unknown stream error');
      handleStreamError(streamError);
      throw error_;
    } finally {
      clearStreamTimeout();
      isStreaming.value = false;
      controller = null;
    }
  }

  function cancelStream() {
    if (controller) {
      controller.abort();
    }
    handleStreamError(
      createStreamError('Stream cancelled', 'STREAM_CANCELLED'),
    );
  }

  return {
    isStreaming,
    error,
    sendMessage,
    cancelStream,
  };
}
