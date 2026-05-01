<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import {
  Button,
  Empty,
  Space,
  Tag,
  Tree,
} from 'ant-design-vue';
import type {
  DirectoryTreeNode,
  ScanRootTree,
} from '#/api/apps/dataset';
import {
  getStagingDirectoryViewApi,
} from '#/api/apps/dataset';
import { useMessage } from '#/hooks/web/useMessage';
import { $t } from '@vben/locales';

defineOptions({ name: 'DirectoryBrowser' });

const props = defineProps<{
  scanRootIds: number[];
}>();

const emit = defineEmits<{
  register: [nodes: DirectoryTreeNode[]];
}>();

const { createMessage } = useMessage();

// --- State ---
const loading = ref(false);
const trees = ref<ScanRootTree[]>([]);
const orphanFiles = ref<any[]>([]);
const expandedKeys = ref<string[]>([]);
const checkedKeys = ref<string[]>([]);

// --- Computed ---
const selectedFileNodes = computed(() => {
  const selected: DirectoryTreeNode[] = [];
  function collect(nodes: DirectoryTreeNode[]) {
    for (const node of nodes) {
      if (!node.is_dir && checkedKeys.value.includes(node.path)) {
        selected.push(node);
      }
      if (node.children) collect(node.children);
    }
  }
  for (const t of trees.value) {
    collect(t.children);
  }
  return selected;
});

// --- Methods ---
async function loadDirectoryView() {
  loading.value = true;
  try {
    const result = await getStagingDirectoryViewApi({
      scan_root_id: props.scanRootIds.length === 1 ? props.scanRootIds[0] : undefined,
    });
    trees.value = result.trees;
    orphanFiles.value = result.orphan_files;
  } catch (error: any) {
    createMessage.error(error?.message || $t('dataset.staging.loadDirectoryViewFailed'));
  } finally {
    loading.value = false;
  }
}

function handleCheck(_checked: (string | number)[] | { checked: (string | number)[]; halfChecked: (string | number)[] }) {
  const keys = Array.isArray(_checked) ? _checked : _checked.checked;
  // Only keep file-level keys (not directories)
  checkedKeys.value = keys.map(String).filter((k) => {
    function isFile(nodes: DirectoryTreeNode[]): boolean {
      for (const node of nodes) {
        if (node.path === k && !node.is_dir) return true;
        if (node.children && isFile(node.children)) return true;
      }
      return false;
    }
    for (const t of trees.value) {
      if (isFile(t.children)) return true;
    }
    return false;
  });
}

function handleRegister() {
  emit('register', selectedFileNodes.value);
}

function formatSize(bytes: number): string {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIdx = 0;
  while (size >= 1024 && unitIdx < units.length - 1) {
    size /= 1024;
    unitIdx++;
  }
  return `${size.toFixed(unitIdx === 0 ? 0 : 1)} ${units[unitIdx]}`;
}

// --- Init ---
watch(
  () => props.scanRootIds,
  () => {
    checkedKeys.value = [];
    expandedKeys.value = [];
    void loadDirectoryView();
  },
  { immediate: true },
);
</script>

<template>
  <div class="directory-browser">
    <!-- Toolbar -->
    <div class="browser-toolbar">
      <Space>
        <Button size="small" :loading="loading" @click="loadDirectoryView()">
          {{ $t('dataset.staging.refresh') }}
        </Button>
      </Space>
      <Space>
        <span v-if="selectedFileNodes.length > 0" class="selection-count">
          {{ $t('dataset.staging.selectedFileCount', { count: selectedFileNodes.length }) }}
        </span>
        <Button
          type="primary"
          size="small"
          :disabled="selectedFileNodes.length === 0"
          @click="handleRegister"
        >
          {{ $t('dataset.staging.registerSelectedFiles') }}
        </Button>
      </Space>
    </div>

    <!-- Tree -->
    <div class="tree-area">
      <Empty
        v-if="!loading && trees.length === 0 && orphanFiles.length === 0"
        :description="$t('dataset.staging.noStagingFilesHint')"
      />

      <div v-for="tree in trees" :key="tree.scan_root_id" class="tree-root">
        <div class="tree-root-label">{{ tree.root_path }}</div>
        <Tree
          v-if="tree.children.length > 0"
          :tree-data="tree.children"
          :expanded-keys="expandedKeys"
          :checked-keys="checkedKeys"
          :field-names="{ title: 'name', key: 'path', children: 'children' }"
          checkable
          check-strictly
          block-node
          @expand="(keys: (string | number)[]) => (expandedKeys = keys.map(String))"
          @check="handleCheck"
        >
          <template #title="{ name, is_dir, file_count, size, format }">
            <span v-if="is_dir" class="tree-dir-node">
              {{ name }}
              <Tag size="small" class="tree-file-count">{{ $t('dataset.staging.dirFileCount', { count: file_count ?? 0 }) }}</Tag>
            </span>
            <span v-else class="tree-file-node">
              <span class="file-name">{{ name }}</span>
              <span class="file-meta">
                <Tag size="small">{{ format }}</Tag>
                <span class="file-size">{{ formatSize(size) }}</span>
              </span>
            </span>
          </template>
        </Tree>
      </div>

      <!-- Orphan files -->
      <div v-if="orphanFiles.length > 0" class="orphan-section">
        <div class="section-title">{{ $t('dataset.staging.orphanFilesRoot') }}</div>
        <div v-for="file in orphanFiles" :key="file.id" class="orphan-file-row">
          <span>{{ file.file_name }}</span>
          <Tag color="blue">{{ file.dataset_type || 'generic' }}</Tag>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.directory-browser {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.browser-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.selection-count {
  color: #1677ff;
  font-weight: 500;
}

.tree-area {
  min-height: 200px;
}

.tree-root {
  margin-bottom: 8px;
}

.tree-root-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 6px;
  font-family: monospace;
  word-break: break-all;
}

.tree-dir-node {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.tree-file-count {
  font-size: 10px;
}

.tree-file-node {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.file-name {
  font-weight: 400;
}

.file-meta {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #888;
}

.file-size {
  font-size: 11px;
  color: #999;
}

.orphan-section {
  margin-top: 16px;
}

.section-title {
  font-weight: 500;
  margin-bottom: 8px;
}

.orphan-file-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}
</style>
