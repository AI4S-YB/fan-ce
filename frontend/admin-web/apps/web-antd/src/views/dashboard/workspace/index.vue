<script lang="ts" setup>
import type { PlatformModelApiSetting } from '#/api/platform/setting';

import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import {
  WorkbenchHeader,
} from '@vben/common-ui';
import { preferences } from '@vben/preferences';
import { useUserStore } from '@vben/stores';
import { Button, Card, Empty, Input, Space, Spin } from 'ant-design-vue';

import { $t } from '@vben/locales';

import { getDatasetListApi } from '#/api/apps/dataset';
import { getPlatformModelApiListApi, platformChatStreamApi } from '#/api/platform/setting';
import type { ChatMessage } from '#/api/platform/setting';
import { getProjectListApi } from '#/api/system/project';
import { useProjectStoreWithOut } from '#/store/modules/project';

interface WorkspaceChatMessage {
  id: string;
  role: 'assistant' | 'user';
  content: string;
}

const userStore = useUserStore();
const projectStore = useProjectStoreWithOut();

const workspaceDescription = computed(() => {
  const teamName = projectStore.getTeamInfo?.team_name?.trim?.();
  const projectName = projectStore.getProjectInfo?.name?.trim?.();

  if (teamName && projectName) {
    return $t('workspace.currentTeamProject', { team: teamName, project: projectName });
  }
  if (teamName) {
    return $t('workspace.currentTeam', { name: teamName });
  }
  if (projectName) {
    return $t('workspace.currentProject', { name: projectName });
  }
  return $t('workspace.fallbackDesc');
});

const router = useRouter();
const chatLoading = ref(false);
const chatInput = ref('');
const streaming = ref(false);
const modelRows = ref<PlatformModelApiSetting[]>([]);
const projectCount = ref(0);
const datasetCount = ref(0);
const chatMessages = ref<WorkspaceChatMessage[]>([
  {
    id: 'welcome',
    role: 'assistant',
    content:
      $t('workspace.chat.welcome'),
  },
]);
const chatScrollRef = ref<HTMLDivElement>();
let abortController: AbortController | null = null;

const primaryModel = computed(() => {
  return (
    modelRows.value.find((item) => item.is_primary) ||
    modelRows.value.find((item) => item.is_active) ||
    null
  );
});


async function scrollChatToBottom() {
  await nextTick();
  if (chatScrollRef.value) {
    chatScrollRef.value.scrollTop = chatScrollRef.value.scrollHeight;
  }
}

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

async function loadStats() {
  try {
    const [projRes, dsRes] = await Promise.all([
      getProjectListApi({ page: 1, size: 1 }),
      getDatasetListApi({ page: 1, size: 1 }),
    ]);
    projectCount.value = projRes?.total ?? 0;
    datasetCount.value = dsRes?.total ?? 0;
  } catch (error) {
    console.error('Load stats failed:', error);
  }
}

function buildApiMessages(): ChatMessage[] {
  const apiMessages: ChatMessage[] = [];
  for (const msg of chatMessages.value) {
    if (msg.id === 'welcome') continue;
    apiMessages.push({ role: msg.role, content: msg.content });
  }
  return apiMessages;
}

async function handleSendMessage() {
  const content = chatInput.value.trim();
  if (!content || streaming.value) {
    return;
  }

  if (!primaryModel.value) {
    chatMessages.value.push({
      id: `user-${Date.now()}`,
      role: 'user',
      content,
    });
    chatMessages.value.push({
      id: `assistant-${Date.now() + 1}`,
      role: 'assistant',
      content: $t('workspace.error.noModel'),
    });
    chatInput.value = '';
    void scrollChatToBottom();
    return;
  }

  chatMessages.value.push({
    id: `user-${Date.now()}`,
    role: 'user',
    content,
  });
  chatInput.value = '';
  void scrollChatToBottom();

  const assistantId = `assistant-${Date.now()}`;
  chatMessages.value.push({
    id: assistantId,
    role: 'assistant',
    content: '',
  });

  streaming.value = true;
  abortController = new AbortController();

  try {
    const apiMessages = buildApiMessages();
    const response = await platformChatStreamApi(
      apiMessages.slice(0, -1),
      abortController.signal,
    );

    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
      updateAssistantMessage(assistantId, $t('workspace.error.requestFailed', { code: response.status, message: errorText || $t('workspace.error.unknown') }));
      return;
    }

    if (!response.body) {
      updateAssistantMessage(assistantId, $t('workspace.error.noStreamBody'));
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

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

          // Our custom SSE format: {"type": "output_msg", "content": "..."}
          if (parsed.type === 'output_msg' && parsed.content) {
            appendAssistantContent(assistantId, parsed.content);
            continue;
          }

          // Tool call notification
          if (parsed.type === 'tool_call') {
            // Optionally show tool call status; skip for now
            continue;
          }

          // Tool result
          if (parsed.type === 'tool_result') {
            // Skip rendering raw data in the chat bubble
            continue;
          }

          // Complete event
          if (parsed.type === 'complete') {
            continue;
          }

          // Error event
          if (parsed.type === 'error') {
            updateAssistantMessage(assistantId, parsed.message || $t('workspace.error.unknown'));
            return;
          }

          // OpenAI format fallback: {"choices": [{"delta": {"content": "..."}}]}
          const delta = parsed.choices?.[0]?.delta?.content;
          if (delta) {
            appendAssistantContent(assistantId, delta);
          }
        } catch {
          // Skip unparseable chunks
        }
      }
    }
  } catch (error: any) {
    if (error?.name === 'AbortError') {
      const currentContent = getAssistantContent(assistantId);
      if (!currentContent) {
        updateAssistantMessage(assistantId, $t('workspace.chat.cancelled'));
      }
    } else {
      console.error('Chat stream error:', error);
      const currentContent = getAssistantContent(assistantId);
      updateAssistantMessage(
        assistantId,
        currentContent || $t('workspace.error.streamFailed', { message: error?.message || $t('workspace.error.unknown') }),
      );
    }
  } finally {
    streaming.value = false;
    abortController = null;
  }
}

function getAssistantContent(id: string): string {
  const msg = chatMessages.value.find(m => m.id === id);
  return msg?.content || '';
}

function updateAssistantMessage(id: string, content: string) {
  const msg = chatMessages.value.find(m => m.id === id);
  if (msg) {
    msg.content = content;
  }
  void scrollChatToBottom();
}

function appendAssistantContent(id: string, delta: string) {
  const msg = chatMessages.value.find(m => m.id === id);
  if (msg) {
    msg.content += delta;
  }
  void scrollChatToBottom();
}

function handleCancelStream() {
  if (abortController) {
    abortController.abort();
  }
}

function handleClearChat() {
  if (streaming.value) {
    handleCancelStream();
  }
  chatMessages.value = [chatMessages.value[0]!];
  void scrollChatToBottom();
}

function openPlatformSetting() {
  router.push('/platform/setting').catch((error) => {
    console.error('Navigation failed:', error);
  });
}

onMounted(() => {
  void loadModelSettings();
  void loadStats();
});

onUnmounted(() => {
  if (abortController) {
    abortController.abort();
  }
});
</script>

<template>
  <div class="p-5">
    <WorkbenchHeader
      :avatar="userStore.userInfo?.avatar || preferences.app.defaultAvatar"
    >
      <template #title>
        {{ $t('workspace.greeting.morning', { name: userStore.userInfo?.realName }) }}
      </template>
      <template #description>
        {{ workspaceDescription }}
      </template>
      <template #stats>
        <div class="flex flex-col justify-center text-right">
          <span class="text-foreground/80"> {{ $t('workspace.stats.project') }} </span>
          <span class="text-2xl">{{ projectCount }}</span>
        </div>
        <div class="mx-12 flex flex-col justify-center text-right md:mx-16">
          <span class="text-foreground/80"> {{ $t('workspace.stats.dataset') }} </span>
          <span class="text-2xl">{{ datasetCount }}</span>
        </div>
      </template>
    </WorkbenchHeader>

    <Card :bordered="false" class="mt-5 workspace-chat-card">

      <Spin :spinning="chatLoading">
        <div ref="chatScrollRef" class="workspace-chat-shell">
          <Empty
            v-if="chatMessages.length === 0"
            :description="$t('workspace.chat.emptyHint')"
          />
          <div
            v-for="message in chatMessages"
            :key="message.id"
            class="workspace-chat-shell__row"
            :class="
              message.role === 'user'
                ? 'workspace-chat-shell__row--user'
                : 'workspace-chat-shell__row--assistant'
            "
          >
            <div
              class="workspace-chat-shell__bubble"
              :class="
                message.role === 'user'
                  ? 'workspace-chat-shell__bubble--user'
                  : 'workspace-chat-shell__bubble--assistant'
              "
            >
              {{ message.content }}
              <span
                v-if="streaming && message.role === 'assistant' && message.id === chatMessages[chatMessages.length - 1]?.id && !message.content"
                class="streaming-cursor"
              />
            </div>
          </div>
        </div>
      </Spin>

      <div class="workspace-chat-actions">
        <Button @click="openPlatformSetting">{{ $t('workspace.action.platformSetting') }}</Button>
        <Button @click="handleClearChat">{{ $t('workspace.chat.clear') }}</Button>
      </div>

      <div class="workspace-chat-input">
        <Input.TextArea
          v-model:value="chatInput"
          :auto-size="{ minRows: 3, maxRows: 6 }"
          :disabled="streaming"
          :placeholder="$t('workspace.chat.placeholder')"
          @press-enter.prevent="handleSendMessage"
        />
        <div class="workspace-chat-input__footer">
          <div class="workspace-chat-input__hint">
            {{ streaming ? $t('workspace.chat.streamingHint') : $t('workspace.chat.defaultHint') }}
          </div>
          <Space>
            <Button v-if="streaming" @click="handleCancelStream">{{ $t('workspace.chat.stop') }}</Button>
            <Button type="primary" :loading="streaming" @click="handleSendMessage">
              {{ streaming ? $t('workspace.chat.sending') : $t('workspace.chat.send') }}
            </Button>
          </Space>
        </div>
      </div>
    </Card>
  </div>
</template>

<style scoped>
.workspace-chat-shell {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 520px;
  max-height: calc(100vh - 380px);
  padding: 20px;
  overflow-y: auto;
  background:
    linear-gradient(180deg, rgba(248, 251, 255, 0.95), rgba(244, 248, 253, 0.98));
  border: 1px solid #e8edf4;
  border-radius: 18px;
}

.workspace-chat-shell__row {
  display: flex;
}

.workspace-chat-shell__row--assistant {
  justify-content: flex-start;
}

.workspace-chat-shell__row--user {
  justify-content: flex-end;
}

.workspace-chat-shell__bubble {
  max-width: min(78%, 820px);
  padding: 14px 16px;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
  border-radius: 18px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.workspace-chat-shell__bubble--assistant {
  color: #20324d;
  background: #ffffff;
  border-top-left-radius: 6px;
}

.workspace-chat-shell__bubble--user {
  color: #ffffff;
  background: linear-gradient(135deg, #1677ff, #0958d9);
  border-top-right-radius: 6px;
}

.streaming-cursor {
  display: inline-block;
  width: 2px;
  height: 18px;
  margin-left: 2px;
  vertical-align: text-bottom;
  background-color: #1677ff;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.workspace-chat-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 16px;
}

.workspace-chat-input {
  margin-top: 16px;
}

.workspace-chat-input__footer {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
}

.workspace-chat-input__hint {
  color: rgb(79, 95, 124);
  font-size: 13px;
}

@media (max-width: 960px) {
  .workspace-chat-input__footer {
    flex-direction: column;
    align-items: stretch;
  }

  .workspace-chat-shell__bubble {
    max-width: 100%;
  }
}
</style>
