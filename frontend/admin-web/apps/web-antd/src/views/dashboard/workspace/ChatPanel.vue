<script lang="ts" setup>
import type { BubbleListProps, BubbleListRef } from 'ant-design-x-vue';
import type { PlatformModelApiSetting } from '#/api/platform/setting';
import type { ChatMessage } from '#/api/platform/setting';

import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { BubbleList } from 'ant-design-x-vue';
import { Button, Empty, Input, Space, Spin } from 'ant-design-vue';

import { $t } from '@vben/locales';

import { getPlatformModelApiListApi, platformChatStreamApi } from '#/api/platform/setting';
import { useMarkdownRender } from '#/views/agent/chat/composables/useMarkdownRender';
import { useWorkspaceStore } from '#/store/modules/workspace';

const store = useWorkspaceStore();
const router = useRouter();
const { messageRender } = useMarkdownRender();

const chatLoading = ref(false);
const chatInput = ref('');
const modelRows = ref<PlatformModelApiSetting[]>([]);
const listRef = ref<BubbleListRef>();
let abortController: AbortController | null = null;
let currentReader: ReadableStreamDefaultReader<Uint8Array> | null = null;

const primaryModel = computed(() => {
  return (
    modelRows.value.find((item) => item.is_primary) ||
    modelRows.value.find((item) => item.is_active) ||
    null
  );
});

const bubbleItems = computed(() => {
  const session = store.currentSession;
  if (!session) return [];

  const msgs = session.messageGroups.flatMap((g) => g.messages);

  return msgs.map((msg) => ({
    key: msg.id,
    role: msg.role === 'user' ? 'user' : 'ai',
    placement: msg.role === 'user' ? ('end' as const) : ('start' as const),
    content: msg.content,
    messageRender: msg.role === 'assistant' ? messageRender : undefined,
  }));
});

const rolesConfig = computed<BubbleListProps['roles']>(() => ({
  ai: {
    placement: 'start',
    variant: 'filled',
    shape: 'round',
    styles: {
      content: {
        maxWidth: '85%',
        borderRadius: '18px',
        padding: '14px 16px',
        borderTopLeftRadius: '6px',
        background: '#ffffff',
        color: '#20324d',
      },
    },
  },
  user: {
    placement: 'end',
    variant: 'filled',
    shape: 'round',
    styles: {
      content: {
        maxWidth: '85%',
        borderRadius: '18px',
        padding: '14px 16px',
        borderTopRightRadius: '6px',
        background: 'linear-gradient(135deg, #1677ff, #0958d9)',
        color: '#ffffff',
      },
    },
  },
}));

// ---- Model loading ----

async function loadModelSettings() {
  chatLoading.value = true;
  try {
    const data = await getPlatformModelApiListApi();
    modelRows.value = data.items || [];
  } catch (error) {
    console.error('Load platform model settings failed:', error);
  } finally {
    chatLoading.value = false;
  }
}

// ---- Streaming ----

function buildApiMessages(): ChatMessage[] {
  const session = store.currentSession;
  if (!session) return [];
  const apiMessages: ChatMessage[] = [];
  for (const group of session.messageGroups) {
    for (const msg of group.messages) {
      apiMessages.push({ role: msg.role, content: msg.content });
    }
  }
  return apiMessages;
}

async function handleSendMessage() {
  const content = chatInput.value.trim();
  if (!content || store.streaming) return;

  const messageText = content;

  // Fix: clear input immediately + force DOM sync before pushing messages
  chatInput.value = '';
  await nextTick();

  store.ensureSession();

  const userMsgId = `user-${Date.now()}`;
  store.addMessage({
    id: userMsgId,
    role: 'user',
    type: 'text',
    content: messageText,
    timestamp: Date.now(),
  });
  await nextTick();
  listRef.value?.scrollTo({ block: 'end' });

  if (!primaryModel.value) {
    store.addMessage({
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      type: 'text',
      content: $t('workspace.error.noModel'),
      timestamp: Date.now(),
    });
    await nextTick();
    listRef.value?.scrollTo({ block: 'end' });
    return;
  }

  const assistantId = `assistant-${Date.now()}`;
  store.addMessage({
    id: assistantId,
    role: 'assistant',
    type: 'text',
    content: '',
    timestamp: Date.now(),
  });
  await nextTick();
  listRef.value?.scrollTo({ block: 'end' });

  store.setStreaming(true);
  abortController = new AbortController();

  try {
    const apiMessages = buildApiMessages();
    const response = await platformChatStreamApi(
      apiMessages.slice(0, -1),
      abortController.signal,
    );

    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
      updateAssistantContent(assistantId, $t('workspace.error.requestFailed', {
        code: response.status,
        message: errorText || $t('workspace.error.unknown'),
      }));
      return;
    }

    if (!response.body) {
      updateAssistantContent(assistantId, $t('workspace.error.noStreamBody'));
      return;
    }

    const reader = response.body.getReader();
    currentReader = reader;
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        buffer += decoder.decode();
        const finalLine = buffer.trim();
        if (finalLine && finalLine.startsWith('data: ')) {
          const dataStr = finalLine.slice(6);
          if (dataStr !== '[DONE]') {
            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.type === 'output_msg' && parsed.content) {
                appendAssistantContent(assistantId, parsed.content);
              }
            } catch { /* skip */ }
          }
        }
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data: ')) continue;

        const dataStr = trimmed.slice(6);
        if (dataStr === '[DONE]') continue;

        try {
          const parsed = JSON.parse(dataStr);

          if (parsed.type === 'output_msg' && parsed.content) {
            appendAssistantContent(assistantId, parsed.content);
            continue;
          }
          if (parsed.type === 'error') {
            updateAssistantContent(assistantId, parsed.message || $t('workspace.error.unknown'));
            return;
          }
          // tool_call, tool_result, complete: skip for now

          // OpenAI format fallback
          const delta = parsed.choices?.[0]?.delta?.content;
          if (delta) {
            appendAssistantContent(assistantId, delta);
          }
        } catch {
          if (import.meta.env.DEV) {
            console.debug('[ChatPanel] Failed to parse SSE line:', trimmed);
          }
        }
      }
    }
  } catch (error: any) {
    if (error?.name === 'AbortError') {
      const current = getAssistantContent(assistantId);
      if (!current) {
        updateAssistantContent(assistantId, $t('workspace.chat.cancelled'));
      }
    } else {
      console.error('Chat stream error:', error);
      const current = getAssistantContent(assistantId);
      updateAssistantContent(
        assistantId,
        current || $t('workspace.error.streamFailed', {
          message: error?.message || $t('workspace.error.unknown'),
        }),
      );
    }
  } finally {
    store.setStreaming(false);
    abortController = null;
    currentReader = null;
    store.closeCurrentGroup();
    nextTick(() => {
      listRef.value?.scrollTo({ block: 'end' });
    });
  }
}

function getAssistantContent(id: string): string {
  const session = store.currentSession;
  if (!session) return '';
  for (const group of session.messageGroups) {
    const msg = group.messages.find((m) => m.id === id);
    if (msg) return msg.content;
  }
  return '';
}

function updateAssistantContent(id: string, content: string) {
  const session = store.currentSession;
  if (!session) return;
  for (const group of session.messageGroups) {
    const msg = group.messages.find((m) => m.id === id);
    if (msg) {
      msg.content = content;
      session.updatedAt = Date.now();
      return;
    }
  }
}

function appendAssistantContent(id: string, delta: string) {
  const session = store.currentSession;
  if (!session) return;
  for (const group of session.messageGroups) {
    const msg = group.messages.find((m) => m.id === id);
    if (msg) {
      msg.content += delta;
      session.updatedAt = Date.now();
      nextTick(() => {
        listRef.value?.scrollTo({ block: 'end' });
      });
      return;
    }
  }
}

function handleCancelStream() {
  if (abortController) {
    abortController.abort();
  }
}

function handleClearChat() {
  if (store.streaming) {
    handleCancelStream();
  }
  store.clearCurrentSession();
}

function openPlatformSetting() {
  router.push('/platform/setting').catch((error) => {
    console.error('Navigation failed:', error);
  });
}

onMounted(() => {
  void loadModelSettings();
});

onUnmounted(() => {
  if (currentReader) {
    currentReader.cancel().catch(() => {});
  }
  if (abortController) {
    abortController.abort();
  }
});
</script>

<template>
  <div class="chat-panel">
    <Spin :spinning="chatLoading" class="chat-panel__spin">
      <div class="chat-panel__list">
        <Empty
          v-if="!store.currentSession || store.currentSession.messageGroups.length === 0"
          :description="$t('workspace.chat.emptyHint')"
        />
        <BubbleList
          v-else
          ref="listRef"
          :items="bubbleItems"
          :roles="rolesConfig"
          auto-scroll
          style="flex: 1 1 0%; min-height: 0"
        />
      </div>
    </Spin>

    <div class="chat-panel__actions">
      <Button @click="openPlatformSetting">
        {{ $t('workspace.action.platformSetting') }}
      </Button>
      <Button @click="handleClearChat">
        {{ $t('workspace.chat.clear') }}
      </Button>
    </div>

    <div class="chat-panel__input">
      <Input.TextArea
        v-model:value="chatInput"
        :auto-size="{ minRows: 3, maxRows: 6 }"
        :disabled="store.streaming"
        :placeholder="$t('workspace.chat.placeholder')"
        @press-enter.prevent="handleSendMessage"
      />
      <div class="chat-panel__input-footer">
        <div class="chat-panel__hint">
          {{ store.streaming ? $t('workspace.chat.streamingHint') : $t('workspace.chat.defaultHint') }}
        </div>
        <Space>
          <Button v-if="store.streaming" @click="handleCancelStream">
            {{ $t('workspace.chat.stop') }}
          </Button>
          <Button type="primary" :loading="store.streaming" @click="handleSendMessage">
            {{ store.streaming ? $t('workspace.chat.sending') : $t('workspace.chat.send') }}
          </Button>
        </Space>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  height: 100%;
}

.chat-panel__spin {
  flex: 1;
  min-height: 0;
}

.chat-panel__list {
  min-height: 520px;
  max-height: calc(100vh - 460px);
  padding: 20px;
  overflow-y: auto;
  background: linear-gradient(180deg, rgba(248, 251, 255, 0.95), rgba(244, 248, 253, 0.98));
  border: 1px solid #e8edf4;
  border-radius: 18px;
}

.chat-panel__actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 16px;
}

.chat-panel__input {
  margin-top: 16px;
}

.chat-panel__input-footer {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
}

.chat-panel__hint {
  color: rgb(79, 95, 124);
  font-size: 13px;
}

@media (max-width: 960px) {
  .chat-panel__input-footer {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
