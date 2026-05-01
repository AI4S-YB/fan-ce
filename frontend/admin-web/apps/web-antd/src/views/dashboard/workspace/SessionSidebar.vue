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
