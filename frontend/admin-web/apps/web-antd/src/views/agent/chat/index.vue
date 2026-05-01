<script setup lang="ts">
import type { ChatRequest } from '#/api/agent/chat';
import type { ChatMessage } from '#/views/agent/chat/types/chat';

import { computed, onUnmounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import { message as messageApi } from 'ant-design-vue';
import { storeToRefs } from 'pinia';

import { $t } from '@vben/locales';
import { getChatEndpointConfig } from '#/config/chat-endpoints';
import { useAgentChatStore } from '#/store/modules/agent-chat';
import ChatContainer from '#/views/agent/chat/components/ChatContainer.vue';
import ChatInput from '#/views/agent/chat/components/ChatInput.vue';
import ExecutionPanel from '#/views/agent/chat/components/ExecutionPanel.vue';
import OutputPanel from '#/views/agent/chat/components/OutputPanel.vue';
import { useChatStream } from '#/views/agent/chat/composables/useChatStream';
import { createTimestampedId } from '#/views/agent/chat/services/id';
import { isRejectOption } from '#/views/agent/chat/utils/parseInterruptOptions';

const route = useRoute();
const chatStore = useAgentChatStore();
const { messageGroups } = storeToRefs(chatStore);

const inputValue = ref('');
const lastSubmittedMessage = ref<null | string>(null);

const chatEndpointConfig = computed(() => getChatEndpointConfig(route.path));
const checkpointId = computed(() => chatStore.currentSession?.checkpointId);

// Reset state when route changes
function resetChatState() {
  inputValue.value = '';
  lastSubmittedMessage.value = null;
  chatStore.resetState();
}

const { isStreaming, error, sendMessage, cancelStream, triggerNextStage } = useChatStream();

const errorMessage = computed(() => error.value?.message ?? '');
const canRetry = computed(
  () => !!error.value && !!lastSubmittedMessage.value && !isStreaming.value,
);

const inputDisabled = computed(() => {
  // Disable during streaming unless user needs to provide command
  if (isStreaming.value && !chatStore.needsUserCommand) {
    return true;
  }
  // Also disable when there's an active interrupt waiting for button click
  if (chatStore.currentInterrupt) {
    return true;
  }
  return false;
});
const inputPlaceholder = computed(() => {
  if (chatStore.needsUserCommand) {
    return $t('agent.chat.provideAlternativeCommand');
  }
  if (chatEndpointConfig.value.supportsFileUpload) {
    return $t('agent.chat.placeholderWithFile');
  }
  return $t('agent.chat.placeholder');
});

const sendChat = async (data: { file_upload?: File[]; message: string }) => {
  const trimmed = data.message.trim();
  if (!trimmed && !data.file_upload) {
    return;
  }

  // 添加用户消息到消息列表
  if (trimmed) {
    const userMessage: ChatMessage = {
      id: createTimestampedId(),
      type: 'user',
      content: trimmed,
      timestamp: Date.now(),
      conversationId: chatStore.currentSession?.id,
    };
    chatStore.addMessageToCurrentGroup(userMessage);
  }

  // Build payload, using pendingContinuation if available
  const payload: ChatRequest = {
    message: trimmed,
    stream: true,
    checkpoint_id:
      chatStore.pendingContinuation?.checkpointId ?? checkpointId.value,
    file_upload: data.file_upload,
  };

  // Add conversation_id if continuing from rejected interrupt
  if (chatStore.pendingContinuation) {
    payload.conversation_id = chatStore.pendingContinuation.conversationId;
  }

  try {
    lastSubmittedMessage.value = trimmed;
    // Clear needsUserCommand flag when user sends new command
    if (chatStore.needsUserCommand) {
      chatStore.setNeedsUserCommand(false);
      chatStore.clearPendingContinuation();
    }
    await sendMessage(payload, chatEndpointConfig.value);
    inputValue.value = '';
  } catch (error_) {
    console.error('[chat] send failed:', error_);
  }
};

const handleSubmit = async (data: { file_upload?: File[]; message: string }) => {
  await sendChat(data);
};

const handleRetry = async () => {
  if (!lastSubmittedMessage.value) {
    return;
  }
  await sendChat({ message: lastSubmittedMessage.value });
};

const handleInterruptSelect = async (value: string) => {
  const interrupt = chatStore.currentInterrupt;
  if (!interrupt) {
    return;
  }

  // Find the selected option
  const selectedOption = interrupt.options.find((opt) => opt.value === value);
  if (!selectedOption) {
    return;
  }

  // Check if this is a reject option
  if (isRejectOption(selectedOption.label)) {
    // Reject: save continuation info, clear interrupt, unlock input, and wait for user command
    chatStore.setPendingContinuation(
      interrupt.conversationId,
      interrupt.checkpointId,
    );
    chatStore.clearInterrupt();
    chatStore.setNeedsUserCommand(true);
    return;
  }

  try {
    chatStore.clearInterrupt();
    chatStore.setNeedsUserCommand(false);
    chatStore.clearPendingContinuation();

    // 🔧 [STAGE_WORKFLOW] 修改：阶段工作流直接触发下一阶段，不再调用当前阶段
    if (chatEndpointConfig.value.isStageWorkflow && chatStore.pendingNextStage) {
      await triggerNextStage(chatEndpointConfig.value);
      return;
    }

    // 非阶段工作流：发送interrupt确认消息
    const payload: ChatRequest = {
      message: value,
      stream: true,
      checkpoint_id: interrupt.checkpointId,
      conversation_id: interrupt.conversationId,
    };

    await sendMessage(payload, chatEndpointConfig.value);
  } catch (error_) {
    console.error('[chat] interrupt feedback failed:', error_);
  }
};

watch(
  error,
  (err) => {
    if (err) {
      messageApi.error(err.message);
      if (lastSubmittedMessage.value) {
        inputValue.value = lastSubmittedMessage.value;
      }
    }
  },
  { immediate: false },
);

// Watch for route changes and reset state
watch(
  () => route.path,
  (newPath, oldPath) => {
    if (newPath !== oldPath) {
      cancelStream();
      resetChatState();
    }
  },
);

onUnmounted(() => {
  cancelStream();
});
</script>

<template>
  <a-spin :spinning="isStreaming" :tip="$t('agent.chat.thinking')" class="chat-spin">
    <ChatContainer>
      <template #output>
        <OutputPanel
          :message-groups="messageGroups"
          :is-streaming="isStreaming"
          @interrupt-select="handleInterruptSelect"
        />
      </template>
      <template #execution>
        <ExecutionPanel
          :message-groups="messageGroups"
          :is-streaming="isStreaming"
        />
      </template>
      <template #input>
        <div class="chat-input-wrapper">
          <ChatInput
            v-model="inputValue"
            :disabled="inputDisabled"
            :loading="isStreaming"
            :placeholder="inputPlaceholder"
            :supports-file-upload="chatEndpointConfig.supportsFileUpload"
            :max-file-size="chatEndpointConfig.maxFileSize"
            :accepted-file-types="chatEndpointConfig.acceptedFileTypes"
            @submit="handleSubmit"
            @cancel="cancelStream"
          />
          <div v-if="errorMessage" class="chat-error">
            {{ errorMessage }}
          </div>
          <div v-if="canRetry" class="chat-retry">
            <a-button type="link" size="small" @click="handleRetry">
              {{ $t('agent.chat.resend') }}
            </a-button>
          </div>
        </div>
      </template>
    </ChatContainer>
  </a-spin>
</template>

<style scoped>
.chat-spin {
  display: flex;
  width: 100%;
  height: 100%;
}

.chat-spin :deep(.ant-spin-container) {
  display: flex;
  flex: 1;
}

.chat-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chat-error {
  font-size: 12px;
  color: var(--ant-color-error-text, #ff4d4f);
}

.chat-retry {
  text-align: right;
}
</style>
