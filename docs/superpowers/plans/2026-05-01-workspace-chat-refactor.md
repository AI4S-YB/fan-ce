# Workspace 对话工作台重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 workspace 对话区从纯 div + ref 数组，重构为 Pinia session 管理 + ant-design-x-vue BubbleList + markdown-it 渲染的完整对话工作台。

**Architecture:** 新建 `useWorkspaceStore`（Pinia + localStorage 持久化），`SessionSidebar.vue`（对话列表），`ChatPanel.vue`（BubbleList + 输入框 + markdown）。`index.vue` 简化为布局壳。复用已有的 `useMarkdownRender`。

**Tech Stack:** Vue 3 Composition API, Pinia + localStorage, ant-design-x-vue BubbleList, markdown-it + highlight.js (github), vue-i18n

---

## 文件结构

**新建文件（3 个源文件）：**

```
apps/web-antd/src/store/modules/workspace.ts                      # Pinia store
apps/web-antd/src/views/dashboard/workspace/SessionSidebar.vue    # 对话列表侧栏
apps/web-antd/src/views/dashboard/workspace/ChatPanel.vue         # 聊天面板
```

**修改文件（4 个）：**

```
apps/web-antd/src/views/dashboard/workspace/index.vue             # 重构为布局壳
apps/web-antd/src/locales/langs/zh-CN/workspace.json              # 新增 session.* keys
apps/web-antd/src/locales/langs/en-US/workspace.json              # 英文对应
apps/web-antd/src/store/index.ts                                  # 导出 workspace store
```

---

### Task 1: 创建 useWorkspaceStore

**Files:**
- Create: `apps/web-antd/src/store/modules/workspace.ts`

- [ ] **Step 1: 创建 Pinia store**

```typescript
import { acceptHMRUpdate, defineStore } from 'pinia';

import { store } from '#/store';

// ---- Data Models ----

export interface WorkspaceMessage {
  id: string;
  role: 'assistant' | 'user';
  type: 'text' | 'tool_call' | 'tool_result' | 'code_result';
  content: string;
  timestamp: number;
}

export interface WorkspaceMessageGroup {
  id: string;
  messages: WorkspaceMessage[];
  startTime: number;
  isComplete: boolean;
}

export interface WorkspaceSession {
  id: string;
  title: string;
  messageGroups: WorkspaceMessageGroup[];
  createdAt: number;
  updatedAt: number;
}

interface WorkspaceChatState {
  sessions: WorkspaceSession[];
  currentSessionId: null | string;
  streaming: boolean;
}

// ---- Helpers ----

function makeId(): string {
  return Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 11);
}

function createEmptyGroup(startTime?: number): WorkspaceMessageGroup {
  return {
    id: makeId(),
    messages: [],
    startTime: startTime ?? Date.now(),
    isComplete: false,
  };
}

// ---- Store ----

export const useWorkspaceStore = defineStore('workspace-chat', {
  state: (): WorkspaceChatState => ({
    sessions: [],
    currentSessionId: null,
    streaming: false,
  }),

  getters: {
    currentSession: (state): WorkspaceSession | null => {
      if (!state.currentSessionId) return null;
      return state.sessions.find((s) => s.id === state.currentSessionId) ?? null;
    },

    sortedSessions: (state): WorkspaceSession[] => {
      return [...state.sessions].sort((a, b) => b.updatedAt - a.updatedAt);
    },
  },

  actions: {
    // ---- Session CRUD ----

    createSession(): WorkspaceSession {
      const now = Date.now();
      const session: WorkspaceSession = {
        id: makeId(),
        title: '新对话',
        messageGroups: [],
        createdAt: now,
        updatedAt: now,
      };
      this.sessions.push(session);
      this.currentSessionId = session.id;
      return session;
    },

    ensureSession(): WorkspaceSession {
      if (this.currentSession) return this.currentSession;
      return this.createSession();
    },

    switchSession(id: string) {
      this.currentSessionId = id;
    },

    renameSession(id: string, title: string) {
      const s = this.sessions.find((x) => x.id === id);
      if (s) {
        s.title = title;
        s.updatedAt = Date.now();
      }
    },

    deleteSession(id: string) {
      const idx = this.sessions.findIndex((s) => s.id === id);
      if (idx === -1) return;
      this.sessions.splice(idx, 1);
      if (this.currentSessionId === id) {
        if (this.sessions.length > 0) {
          this.currentSessionId = this.sessions[0]!.id;
        } else {
          this.createSession();
        }
      }
    },

    // ---- Message management ----

    addMessage(message: WorkspaceMessage) {
      const session = this.ensureSession();
      let group = session.messageGroups[session.messageGroups.length - 1];

      if (!group || group.isComplete) {
        group = createEmptyGroup(message.timestamp);
        session.messageGroups.push(group);
      }

      group.messages.push(message);
      group.endTime = message.timestamp;
      group.isComplete = false;

      // Auto-name session from first user message
      if (session.title === '新对话' && message.role === 'user' && message.content) {
        session.title = message.content.slice(0, 30);
      }

      session.updatedAt = Date.now();
      return group;
    },

    closeCurrentGroup() {
      const session = this.currentSession;
      if (!session) return;
      const group = session.messageGroups[session.messageGroups.length - 1];
      if (group) {
        group.isComplete = true;
        group.endTime = Date.now();
      }
    },

    clearCurrentSession() {
      const session = this.currentSession;
      if (!session) return;
      session.messageGroups = [];
      session.updatedAt = Date.now();
    },

    // ---- Streaming ----

    setStreaming(val: boolean) {
      this.streaming = val;
    },
  },

  // ---- localStorage persistence ----
  persist: {
    key: 'workspace-chat',
    storage: localStorage,
  },
});

const hot = import.meta.hot;
if (hot) {
  hot.accept(acceptHMRUpdate(useWorkspaceStore, hot));
}

export function useWorkspaceStoreWithOut() {
  return useWorkspaceStore(store);
}
```

- [ ] **Step 2: 注册 store 导出**

在 `apps/web-antd/src/store/index.ts` 中添加：

```typescript
export * from './modules/workspace';
```

- [ ] **Step 3: 验证 store 创建成功**

```bash
cd apps/web-antd && pnpm check:type 2>&1 | head -5
```

Expected: No type errors.

---

### Task 2: 创建 SessionSidebar.vue

**Files:**
- Create: `apps/web-antd/src/views/dashboard/workspace/SessionSidebar.vue`

- [ ] **Step 1: 创建侧栏组件**

```vue
<script lang="ts" setup>
import { nextTick, ref } from 'vue';

import { Button, Input, Popconfirm, Tooltip } from 'ant-design-vue';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons-vue';

import { $t } from '@vben/locales';

import { useWorkspaceStore } from '#/store/modules/workspace';

const store = useWorkspaceStore();
const editingId = ref<null | string>(null);
const editTitle = ref('');

function handleNew() {
  store.createSession();
}

function handleSelect(id: string) {
  store.switchSession(id);
}

function startRename(id: string, currentTitle: string) {
  editingId.value = id;
  editTitle.value = currentTitle;
}

async function confirmRename(id: string) {
  const title = editTitle.value.trim();
  if (title) {
    store.renameSession(id, title);
  }
  editingId.value = null;
  await nextTick();
}

function cancelRename() {
  editingId.value = null;
}

function handleDelete(id: string) {
  store.deleteSession(id);
}

function formatTime(ts: number): string {
  const now = Date.now();
  const diff = now - ts;
  if (diff < 60_000) return '刚刚';
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`;
  return `${Math.floor(diff / 86_400_000)} 天前`;
}
</script>

<template>
  <div class="session-sidebar">
    <div class="session-sidebar__header">
      <span class="session-sidebar__title">对话列表</span>
      <Tooltip :title="$t('workspace.session.newSessionBtn')">
        <Button size="small" type="text" @click="handleNew">
          <PlusOutlined />
        </Button>
      </Tooltip>
    </div>

    <div class="session-sidebar__list">
      <div
        v-for="session in store.sortedSessions"
        :key="session.id"
        class="session-item"
        :class="{ 'session-item--active': session.id === store.currentSessionId }"
        @click="handleSelect(session.id)"
      >
        <div class="session-item__content">
          <Input
            v-if="editingId === session.id"
            v-model:value="editTitle"
            size="small"
            @press-enter="confirmRename(session.id)"
            @blur="confirmRename(session.id)"
            @keydown.escape="cancelRename"
          />
          <template v-else>
            <div class="session-item__title" @dblclick="startRename(session.id, session.title)">
              {{ session.title }}
            </div>
            <div class="session-item__meta">
              <span>{{ formatTime(session.updatedAt) }}</span>
              <Popconfirm
                :title="$t('workspace.session.deleteConfirm')"
                placement="right"
                @confirm="handleDelete(session.id)"
                @click.stop
              >
                <Button
                  size="small"
                  type="text"
                  class="session-item__delete"
                  @click.stop
                >
                  <DeleteOutlined />
                </Button>
              </Popconfirm>
            </div>
          </template>
        </div>
      </div>

      <div v-if="store.sessions.length === 0" class="session-sidebar__empty">
        {{ $t('workspace.session.emptyList') }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.session-sidebar {
  display: flex;
  flex-direction: column;
  width: 260px;
  height: 100%;
  border-right: 1px solid #e8edf4;
  background: #fafbfc;
}

.session-sidebar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #e8edf4;
}

.session-sidebar__title {
  font-weight: 600;
  font-size: 14px;
  color: #1e293b;
}

.session-sidebar__list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item {
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.session-item:hover {
  background: #edf2f7;
}

.session-item--active {
  background: #e0edff;
}

.session-item__title {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-item__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 11px;
  color: #94a3b8;
}

.session-item__delete {
  opacity: 0;
  transition: opacity 0.15s;
}

.session-item:hover .session-item__delete {
  opacity: 1;
}

.session-sidebar__empty {
  padding: 24px 12px;
  text-align: center;
  font-size: 13px;
  color: #94a3b8;
}
</style>
```

- [ ] **Step 2: 验证**

```bash
cd apps/web-antd && pnpm check:type 2>&1 | head -5
```

Expected: No type errors.

---

### Task 3: 创建 ChatPanel.vue

**Files:**
- Create: `apps/web-antd/src/views/dashboard/workspace/ChatPanel.vue`

- [ ] **Step 1: 创建聊天面板组件**

```vue
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

  if (!primaryModel.value) {
    store.addMessage({
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      type: 'text',
      content: $t('workspace.error.noModel'),
      timestamp: Date.now(),
    });
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
          // skip unparseable
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
    store.closeCurrentGroup();
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
```

- [ ] **Step 2: 验证类型**

```bash
cd apps/web-antd && pnpm check:type 2>&1 | head -5
```

Expected: No type errors.

---

### Task 4: 重构 index.vue 为布局壳

**Files:**
- Modify: `apps/web-antd/src/views/dashboard/workspace/index.vue`

- [ ] **Step 1: 用全新内容替换 index.vue**

将 493 行替换为：

```vue
<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';

import { WorkbenchHeader } from '@vben/common-ui';
import { preferences } from '@vben/preferences';
import { useUserStore } from '@vben/stores';

import { $t } from '@vben/locales';

import { getDatasetListApi } from '#/api/apps/dataset';
import { getProjectListApi } from '#/api/system/project';
import { useProjectStoreWithOut } from '#/store/modules/project';

import ChatPanel from './ChatPanel.vue';
import SessionSidebar from './SessionSidebar.vue';

const userStore = useUserStore();
const projectStore = useProjectStoreWithOut();

const projectCount = ref(0);
const datasetCount = ref(0);

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

onMounted(() => {
  void loadStats();
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

    <div class="workspace-body mt-5">
      <SessionSidebar />
      <ChatPanel />
    </div>
  </div>
</template>

<style scoped>
.workspace-body {
  display: flex;
  height: calc(100vh - 220px);
  min-height: 600px;
  border: 1px solid #e8edf4;
  border-radius: 18px;
  overflow: hidden;
  background: #ffffff;
}

@media (max-width: 768px) {
  .workspace-body {
    flex-direction: column;
  }
}
</style>
```

- [ ] **Step 2: 验证类型和构建**

```bash
cd apps/web-antd && pnpm check:type 2>&1 | tail -3
```

Expected: No type errors.

---

### Task 5: 添加 i18n keys

**Files:**
- Modify: `apps/web-antd/src/locales/langs/zh-CN/workspace.json`
- Modify: `apps/web-antd/src/locales/langs/en-US/workspace.json`

- [ ] **Step 1: 添加中文 keys**

在 `zh-CN/workspace.json` 中添加 `session` section：

```json
{
  "greeting": { "morning": "早安, {name}, 开始您一天的工作吧！" },
  "currentTeam": "当前团队：{name}",
  "currentProject": "当前项目：{name}",
  "currentTeamProject": "当前团队：{team}，当前项目：{project}",
  "fallbackDesc": "欢迎使用 FAN-CE 数据管理后台。",
  "stats": { "project": "项目", "dataset": "数据集" },
  "chat": {
    "welcome": "你好！我是 FAN-CE 工作台的 AI 助手。我可以帮你分析数据、解答生物信息学问题、查询数据库等。请随时向我提问。",
    "placeholder": "输入你的问题，AI 助手将实时回复...",
    "emptyHint": "暂时还没有对话消息",
    "streamingHint": "AI 正在回复中...",
    "defaultHint": "基于已配置的模型平台进行流式对话",
    "send": "发送",
    "sending": "回复中",
    "stop": "停止生成",
    "clear": "清空当前对话",
    "cancelled": "已取消"
  },
  "error": {
    "noModel": "当前没有可用的模型配置。请先在\"平台管理 -> 平台设置\"中配置模型 API 后再使用对话功能。",
    "requestFailed": "请求失败 ({code}): {message}",
    "noStreamBody": "无法读取流式响应",
    "streamFailed": "流式请求失败: {message}",
    "unknown": "未知错误"
  },
  "action": { "platformSetting": "打开平台设置" },
  "session": {
    "newSessionBtn": "+ 新对话",
    "deleteConfirm": "确定要删除这个对话吗？",
    "emptyList": "暂无对话记录",
    "defaultTitle": "新对话"
  }
}
```

- [ ] **Step 2: 添加英文 keys**

在 `en-US/workspace.json` 中添加：

```json
{
  "greeting": { "morning": "Good morning, {name}, let's start your day!" },
  "currentTeam": "Current Team: {name}",
  "currentProject": "Current Project: {name}",
  "currentTeamProject": "Team: {team}, Project: {project}",
  "fallbackDesc": "Welcome to FAN-CE Admin Console.",
  "stats": { "project": "Projects", "dataset": "Datasets" },
  "chat": {
    "welcome": "Hello! I'm the FAN-CE workspace AI assistant. I can help you analyze data, answer bioinformatics questions, query databases, and more. Feel free to ask me anything.",
    "placeholder": "Ask a question, AI will respond in real-time...",
    "emptyHint": "No messages yet",
    "streamingHint": "AI is responding...",
    "defaultHint": "Streaming conversation based on the configured model",
    "send": "Send",
    "sending": "Responding",
    "stop": "Stop",
    "clear": "Clear Chat",
    "cancelled": "Cancelled"
  },
  "error": {
    "noModel": "No model configured. Please set up a model API in \"Platform -> Settings\" first.",
    "requestFailed": "Request failed ({code}): {message}",
    "noStreamBody": "Cannot read streaming response",
    "streamFailed": "Stream failed: {message}",
    "unknown": "Unknown error"
  },
  "action": { "platformSetting": "Platform Settings" },
  "session": {
    "newSessionBtn": "+ New Chat",
    "deleteConfirm": "Delete this conversation?",
    "emptyList": "No conversations yet",
    "defaultTitle": "New Chat"
  }
}
```

- [ ] **Step 3: 验证 JSON 格式**

```bash
python3 -c "
import json
with open('apps/web-antd/src/locales/langs/zh-CN/workspace.json') as f:
    json.load(f)
with open('apps/web-antd/src/locales/langs/en-US/workspace.json') as f:
    json.load(f)
print('Both JSON valid')
"
```

---

### Task 6: 集成验证

- [ ] **Step 1: 类型检查**

```bash
cd apps/web-antd && pnpm check:type
```

Expected: No type errors.

- [ ] **Step 2: Lint 检查**

```bash
cd apps/web-antd && pnpm lint 2>&1 | tail -5
```

Expected: No lint errors.

- [ ] **Step 3: 启动开发服务器并手动验证**

```bash
pnpm dev:antd
```

打开 http://127.0.0.1:5666/ ，验证：

1. 工作台左侧出现对话列表（初始为空）
2. 发送第一条消息 → 自动创建 session，标题取首条消息前 30 字
3. 发送消息后输入框立即清空
4. AI 回复以 markdown 渲染（代码块有语法高亮、表格正确渲染）
5. 新建对话 → 切换到空 session
6. 切换 session → 消息列表切换，输入框清空
7. 双击 session 标题 → 可重命名
8. 删除 session → 切换到最近一个
9. 切换语言 (zh-CN / en-US) → session sidebar 文本跟随
10. 刷新页面 → session 和消息从 localStorage 恢复
