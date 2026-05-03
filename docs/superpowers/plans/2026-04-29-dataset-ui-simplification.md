# Dataset Center UI Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the 7884-line monolithic `index.vue` into three clean route pages (List, Detail, Query) with extracted sub-components, eliminating Drawer overlays and overlapping content.

**Architecture:** Extract shared utilities into a composable (`useDataset.ts`), then build leaf components (VersionTable, AssetPanel, LineagePanel, QueryForm) that are composed into two new page components (Detail.vue, Query.vue). Finally, strip index.vue to list-only and wire up routes.

**Tech Stack:** Vue 3 (Composition API, `<script setup>`), Ant Design Vue 4, TypeScript, Vite, pnpm monorepo, existing `/admin/dataset/*` API layer.

---

## File Map

| File | Responsibility |
|------|---------------|
| `apps/web-antd/src/views/apps/dataset/composables/useDataset.ts` | Shared state, API calls, helpers extracted from index.vue |
| `apps/web-antd/src/views/apps/dataset/components/VersionTable.vue` | Version list table with radio select, lifecycle/release/visibility tags, conditional operations |
| `apps/web-antd/src/views/apps/dataset/components/AssetPanel.vue` | Asset cards with file list, CRUD modals (create/edit asset, register/edit file) |
| `apps/web-antd/src/views/apps/dataset/components/LineagePanel.vue` | Lineage record cards with relation type, create/delete modals |
| `apps/web-antd/src/views/apps/dataset/components/QueryForm.vue` | Operation selector + dynamic parameter fields + execute |
| `apps/web-antd/src/views/apps/dataset/Detail.vue` | Full-width detail page composing VersionTable + AssetPanel + LineagePanel |
| `apps/web-antd/src/views/apps/dataset/Query.vue` | Full-width query page composing QueryForm + results display |
| `apps/web-antd/src/views/apps/dataset/index.vue` | **Modified** — stripped to list-only table with 3 action buttons |

---

### Task 1: Extract shared composable `useDataset.ts`

**Files:**
- Create: `apps/web-antd/src/views/apps/dataset/composables/useDataset.ts`

**Rationale:** Before building new components, extract shared helpers, constants, and API wrappers from index.vue so every new component can import from one place instead of duplicating.

- [ ] **Step 1: Create the composable with constants and helpers**

```typescript
// apps/web-antd/src/views/apps/dataset/composables/useDataset.ts
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import {
  getDatasetListApi,
  getDatasetInfoApi,
  deleteDatasetApi,
  getDatasetVersionListApi,
  getDatasetVersionInfoApi,
  getDatasetVersionQueryCapabilitiesApi,
  getDatasetVersionPublishRecordsApi,
  createDatasetVersionApi,
  activateDatasetVersionApi,
  releaseDatasetVersionApi,
  withdrawDatasetVersionApi,
  setDefaultPublicDatasetVersionApi,
  createDatasetAssetApi,
  updateDatasetAssetApi,
  deleteDatasetAssetApi,
  registerAssetFileApi,
  updateAssetFileApi,
  deleteAssetFileApi,
  getDatasetLineageListApi,
  createDatasetLineageApi,
  deleteDatasetLineageApi,
  executeDatasetVersionQueryApi,
  getAssetTypeOptionsApi,
  type DatasetItem,
  type DatasetDetailItem,
  type DatasetVersionItem,
  type DatasetVersionDetail,
  type DatasetVersionListResult,
  type DatasetAssetItem,
  type AssetFileItem,
  type DatasetLineageItem,
  type DatasetVersionQueryCapabilitiesResult,
  type DatasetVersionQueryExecuteResult,
  type DatasetVersionPublishRecordItem,
} from '#/api/apps/dataset';

// ── Constants ──
export const LIFECYCLE_OPTIONS = [
  { label: '草稿', value: 'draft' },
  { label: '已上传', value: 'uploaded' },
  { label: '校验中', value: 'validating' },
  { label: '已校验', value: 'validated' },
  { label: '索引中', value: 'indexing' },
  { label: '就绪', value: 'ready' },
  { label: '公开', value: 'public' },
  { label: '已归档', value: 'archived' },
];

export const VISIBILITY_OPTIONS = [
  { label: '私有', value: 'private' },
  { label: '受控', value: 'restricted' },
  { label: '公开', value: 'public' },
];

export const FILE_ROLE_OPTIONS = [
  { label: '主文件', value: 'primary' },
  { label: '索引文件', value: 'index' },
  { label: '派生文件', value: 'derived' },
  { label: '元数据', value: 'metadata' },
  { label: '预览文件', value: 'preview' },
];

export const RELATION_TYPE_OPTIONS = [
  { label: 'uses_reference', value: 'uses_reference' },
  { label: 'quantified_against', value: 'quantified_against' },
  { label: 'called_against', value: 'called_against' },
  { label: 'annotated_by', value: 'annotated_by' },
  { label: 'derived_from', value: 'derived_from' },
  { label: 'normalized_from', value: 'normalized_from' },
];

// ── Color helpers ──
export function lifecycleColor(state?: string | null) {
  switch (state) {
    case 'ready': return 'green';
    case 'public': return 'green';
    case 'draft': return 'default';
    case 'validating': return 'processing';
    case 'indexing': return 'processing';
    case 'archived': return 'default';
    default: return 'default';
  }
}

export function visibilityColor(state?: string | null) {
  switch (state) {
    case 'public': return 'green';
    case 'restricted': return 'orange';
    default: return 'default';
  }
}

export function releaseStateColor(state?: string | null) {
  switch (state) {
    case 'released': return 'green';
    case 'withdrawn': return 'red';
    default: return 'default';
  }
}

export function taskStatusColor(status?: string | null) {
  switch (status) {
    case 'done': case 'success': return 'green';
    case 'failed': case 'error': return 'red';
    case 'running': case 'processing': return 'processing';
    default: return 'default';
  }
}

// ── Label helpers ──
export function getPreferredDatasetTypeCode(datasetType?: string | null) {
  switch (datasetType) {
    case 'sequence': return 'genome';
    case 'expression': return 'transcriptome';
    case 'variant': return 'variome';
    default: return datasetType || '-';
  }
}

export function getFileRoleLabel(file?: AssetFileItem | null) {
  switch (file?.file_role) {
    case 'primary': return '主文件';
    case 'index': return '索引文件';
    case 'derived': return '派生文件';
    case 'metadata': return '元数据';
    case 'preview': return '预览文件';
    default: return file?.file_role || '-';
  }
}

export function getFileRoleColor(file?: AssetFileItem | null) {
  switch (file?.file_role) {
    case 'primary': return 'green';
    case 'index': return 'blue';
    case 'derived': return 'purple';
    case 'metadata': return 'orange';
    default: return 'default';
  }
}

export function getLineageRelationColor(relation?: string) {
  switch (relation) {
    case 'uses_reference': case 'annotated_by': return 'blue';
    case 'quantified_against': case 'called_against': return 'green';
    case 'derived_from': case 'normalized_from': return 'orange';
    default: return 'default';
  }
}

export function getLineageRelationLabel(relation?: string) {
  switch (relation) {
    case 'uses_reference': return '使用参考';
    case 'quantified_against': return '量化依赖';
    case 'called_against': return '变异检出';
    case 'annotated_by': return '功能注释';
    case 'derived_from': return '派生自';
    case 'normalized_from': return '标准化自';
    default: return relation || '-';
  }
}

export function getSelectedVersionRoleLabels(version?: DatasetVersionItem | null) {
  if (!version) return [];
  const labels: string[] = [];
  if (version.is_current) labels.push('当前版本');
  if (version.is_default_public) labels.push('默认公开版本');
  if (version.release_state === 'released') labels.push('已发布版本');
  if (!labels.length) labels.push('未发布版本');
  return labels;
}

export function getSelectedVersionExposure(version?: DatasetVersionItem | null) {
  if (!version) return '-';
  if (version.is_default_public) return '公开前台默认访问该版本。';
  if (version.release_state === 'released') return '该版本已 released，但不是默认公开版本。';
  return '该版本当前不对公开前台开放。';
}

export function formatTime(ts?: number | null) {
  if (!ts) return '-';
  const d = new Date(ts * 1000);
  return d.toLocaleString('zh-CN');
}

// ── API composable ──
export function useDataset() {
  const router = useRouter();

  // List
  const listLoading = ref(false);
  const rows = ref<DatasetItem[]>([]);
  const total = ref(0);

  async function loadList(params: Record<string, any>) {
    listLoading.value = true;
    try {
      const res = await getDatasetListApi(params);
      rows.value = res.dataList;
      total.value = res.total;
    } finally {
      listLoading.value = false;
    }
  }

  // Detail
  const detailLoading = ref(false);
  const detailData = ref<DatasetDetailItem | null>(null);

  async function loadDetail(id: number) {
    detailLoading.value = true;
    try {
      detailData.value = await getDatasetInfoApi({ id });
    } finally {
      detailLoading.value = false;
    }
  }

  // Versions
  const versionListLoading = ref(false);
  const versionListData = ref<DatasetVersionListResult | null>(null);

  async function loadVersionList(datasetId: number) {
    versionListLoading.value = true;
    try {
      versionListData.value = await getDatasetVersionListApi({ dataset_id: datasetId });
    } finally {
      versionListLoading.value = false;
    }
  }

  // Selected version detail
  const versionDetailLoading = ref(false);
  const versionDetailData = ref<DatasetVersionDetail | null>(null);

  async function loadVersionDetail(versionId: number) {
    versionDetailLoading.value = true;
    try {
      versionDetailData.value = await getDatasetVersionInfoApi({ id: versionId });
    } finally {
      versionDetailLoading.value = false;
    }
  }

  // Publish records
  const publishRecordsLoading = ref(false);
  const publishRecords = ref<DatasetVersionPublishRecordItem[]>([]);

  async function loadPublishRecords(versionId: number) {
    publishRecordsLoading.value = true;
    try {
      const res = await getDatasetVersionPublishRecordsApi({ version_id: versionId });
      publishRecords.value = res.items;
    } finally {
      publishRecordsLoading.value = false;
    }
  }

  // Version actions
  async function createVersion(data: Record<string, any>) {
    return createDatasetVersionApi(data);
  }

  async function activateVersion(id: number, note?: string) {
    return activateDatasetVersionApi({ id, note });
  }

  async function releaseVersion(id: number, note?: string) {
    return releaseDatasetVersionApi({ id, note });
  }

  async function withdrawVersion(id: number, note?: string) {
    return withdrawDatasetVersionApi({ id, note });
  }

  async function setDefaultPublicVersion(id: number, note?: string) {
    return setDefaultPublicDatasetVersionApi({ id, note });
  }

  // Asset CRUD
  async function createAsset(data: Record<string, any>) {
    return createDatasetAssetApi(data);
  }

  async function updateAsset(data: Record<string, any>) {
    return updateDatasetAssetApi(data);
  }

  async function deleteAsset(id: number) {
    return deleteDatasetAssetApi({ id });
  }

  async function registerFile(data: Record<string, any>) {
    return registerAssetFileApi(data);
  }

  async function updateFile(data: Record<string, any>) {
    return updateAssetFileApi(data);
  }

  async function deleteFile(id: number) {
    return deleteAssetFileApi({ id });
  }

  // Lineage CRUD
  async function createLineage(data: Record<string, any>) {
    return createDatasetLineageApi(data);
  }

  async function deleteLineage(id: number) {
    return deleteDatasetLineageApi({ id });
  }

  // Query
  const queryCapabilitiesLoading = ref(false);
  const queryCapabilities = ref<DatasetVersionQueryCapabilitiesResult | null>(null);

  async function loadQueryCapabilities(versionId: number, assetCode?: string) {
    queryCapabilitiesLoading.value = true;
    try {
      queryCapabilities.value = await getDatasetVersionQueryCapabilitiesApi({
        id: versionId,
        asset_code: assetCode,
      });
    } finally {
      queryCapabilitiesLoading.value = false;
    }
  }

  async function executeQuery(versionId: number, operation: string, params?: Record<string, any>, assetCode?: string) {
    return executeDatasetVersionQueryApi({
      id: versionId,
      operation,
      asset_code: assetCode,
      params,
    });
  }

  // Navigation
  function navigateToDetail(id: number) {
    router.push(`/dataset/${id}`);
  }

  function navigateToQuery(id: number) {
    router.push(`/dataset/${id}/query`);
  }

  return {
    // List
    listLoading, rows, total, loadList,
    // Detail
    detailLoading, detailData, loadDetail,
    // Versions
    versionListLoading, versionListData, loadVersionList,
    versionDetailLoading, versionDetailData, loadVersionDetail,
    createVersion, activateVersion, releaseVersion, withdrawVersion, setDefaultPublicVersion,
    // Publish
    publishRecordsLoading, publishRecords, loadPublishRecords,
    // Assets
    createAsset, updateAsset, deleteAsset, registerFile, updateFile, deleteFile,
    // Lineage
    createLineage, deleteLineage,
    // Query
    queryCapabilitiesLoading, queryCapabilities, loadQueryCapabilities, executeQuery,
    // Navigation
    navigateToDetail, navigateToQuery,
  };
}
```

- [ ] **Step 2: Verify the file compiles**

Run: `cd apps/web-antd && npx vue-tsc --noEmit src/views/apps/dataset/composables/useDataset.ts 2>&1 | head -20`
Expected: No type errors (may have warnings about unused imports in isolation)

- [ ] **Step 3: Commit**

```bash
git add apps/web-antd/src/views/apps/dataset/composables/useDataset.ts
git commit -m "feat: extract shared dataset composable with constants, helpers, and API wrappers"
```

---

### Task 2: Create VersionTable component

**Files:**
- Create: `apps/web-antd/src/views/apps/dataset/components/VersionTable.vue`

**Rationale:** Extract the version list table (currently in the version workspace Drawer) into a standalone component. It takes `versionListData`, `activeVersionId` as props, emits `select` and version action events.

- [ ] **Step 1: Write the component**

```vue
<!-- apps/web-antd/src/views/apps/dataset/components/VersionTable.vue -->
<script setup lang="ts">
import { Table, Tag, Space, Button, Empty } from 'ant-design-vue';
import type { DatasetVersionItem, DatasetVersionListResult } from '#/api/apps/dataset';
import {
  lifecycleColor,
  releaseStateColor,
  visibilityColor,
} from '../composables/useDataset';

const props = defineProps<{
  versionData: DatasetVersionListResult | null;
  activeVersionId: number | null;
  actionLoadingKey: string;
}>();

const emit = defineEmits<{
  select: [version: DatasetVersionItem];
  activate: [version: DatasetVersionItem];
  release: [version: DatasetVersionItem];
  withdraw: [version: DatasetVersionItem];
  setDefault: [version: DatasetVersionItem];
  createVersion: [];
}>();

const columns = [
  { title: '', dataIndex: 'radio', key: 'radio', width: 40 },
  { title: '版本号', dataIndex: 'version', key: 'version', width: 140 },
  { title: '标题', dataIndex: 'title', key: 'title', width: 180 },
  { title: '生命周期', dataIndex: 'lifecycle_state', key: 'lifecycle_state', width: 120 },
  { title: '发布状态', dataIndex: 'release_state', key: 'release_state', width: 120 },
  { title: '可见性', dataIndex: 'visibility', key: 'visibility', width: 110 },
  { title: '格式', dataIndex: 'file_format', key: 'file_format', width: 120 },
  { title: '操作', dataIndex: 'actions', key: 'actions' },
];

function isActive(version: DatasetVersionItem) {
  return version.id === props.activeVersionId;
}

function isActionLoading(prefix: string, id: number) {
  return props.actionLoadingKey === `${prefix}-${id}`;
}
</script>

<template>
  <div>
    <div style="margin-bottom: 12px;">
      <Button type="primary" ghost @click="emit('createVersion')">新建版本</Button>
    </div>
    <Table
      :columns="columns"
      :data-source="versionData?.items || []"
      :pagination="false"
      :row-key="(r: DatasetVersionItem) => r.id"
      bordered
      size="small"
    >
      <template #emptyText>
        <Empty description="暂无版本" />
      </template>
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'radio'">
          <input
            type="radio"
            :checked="isActive(record as DatasetVersionItem)"
            @change="emit('select', record as DatasetVersionItem)"
          />
        </template>
        <template v-else-if="column.key === 'version'">
          {{ (record as DatasetVersionItem).version || '-' }}
        </template>
        <template v-else-if="column.key === 'lifecycle_state'">
          <Tag :color="lifecycleColor((record as DatasetVersionItem).lifecycle_state)">
            {{ (record as DatasetVersionItem).lifecycle_state || '-' }}
          </Tag>
        </template>
        <template v-else-if="column.key === 'release_state'">
          <Tag :color="releaseStateColor((record as DatasetVersionItem).release_state)">
            {{ (record as DatasetVersionItem).release_state || '-' }}
          </Tag>
        </template>
        <template v-else-if="column.key === 'visibility'">
          <Tag :color="visibilityColor((record as DatasetVersionItem).visibility)">
            {{ (record as DatasetVersionItem).visibility || '-' }}
          </Tag>
        </template>
        <template v-else-if="column.key === 'actions'">
          <Space size="small">
            <template v-if="(record as DatasetVersionItem).lifecycle_state !== 'ready' && (record as DatasetVersionItem).lifecycle_state !== 'public'">
              <Button
                type="link"
                size="small"
                :loading="isActionLoading('activate-version', (record as DatasetVersionItem).id)"
                @click="emit('activate', record as DatasetVersionItem)"
              >
                激活版本
              </Button>
            </template>
            <template v-if="(record as DatasetVersionItem).release_state !== 'released'">
              <Button
                type="link"
                size="small"
                :loading="isActionLoading('release-version', (record as DatasetVersionItem).id)"
                @click="emit('release', record as DatasetVersionItem)"
              >
                发布版本
              </Button>
            </template>
            <template v-if="(record as DatasetVersionItem).release_state === 'released' && !(record as DatasetVersionItem).is_default_public">
              <Button
                type="link"
                size="small"
                :loading="isActionLoading('set-default-version', (record as DatasetVersionItem).id)"
                @click="emit('setDefault', record as DatasetVersionItem)"
              >
                设为默认公开
              </Button>
            </template>
            <template v-if="(record as DatasetVersionItem).release_state === 'released'">
              <Button
                type="link"
                danger
                size="small"
                :loading="isActionLoading('withdraw-version', (record as DatasetVersionItem).id)"
                @click="emit('withdraw', record as DatasetVersionItem)"
              >
                撤回版本
              </Button>
            </template>
          </Space>
        </template>
      </template>
    </Table>
  </div>
</template>
```

- [ ] **Step 2: Verify the component builds**

Run: `cd apps/web-antd && npx vue-tsc --noEmit src/views/apps/dataset/components/VersionTable.vue 2>&1 | tail -5`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add apps/web-antd/src/views/apps/dataset/components/VersionTable.vue
git commit -m "feat: extract VersionTable component from monolithic index.vue"
```

---

### Task 3: Create AssetPanel component

**Files:**
- Create: `apps/web-antd/src/views/apps/dataset/components/AssetPanel.vue`

**Rationale:** Asset cards with file details, filter bar, and CRUD modals (create/edit asset, register/edit file). Props: `versionDetail`, `loading`. Emits: `refresh`.

- [ ] **Step 1: Write the component**

```vue
<!-- apps/web-antd/src/views/apps/dataset/components/AssetPanel.vue -->
<script setup lang="ts">
import { ref, computed } from 'vue';
import {
  Button, Space, Tag, Input, Select, Modal, Empty, message,
} from 'ant-design-vue';
import {
  useDataset,
  getAssetTypeOptionsApi,
  getFileRoleLabel,
  getFileRoleColor,
  type DatasetVersionDetail,
  type DatasetAssetItem,
  type AssetFileItem,
} from '../composables/useDataset';

const props = defineProps<{
  versionDetail: DatasetVersionDetail | null;
  loading: boolean;
}>();

const emit = defineEmits<{ refresh: [] }>();

const {
  createAsset, updateAsset, deleteAsset,
  registerFile, updateFile, deleteFile,
} = useDataset();

// Filter
const keyword = ref('');
const assetTypeOptions = ref<{ label: string; value: string }[]>([]);

const filteredAssets = computed(() => {
  const assets = props.versionDetail?.assets || [];
  const kw = keyword.value.trim().toLowerCase();
  if (!kw) return assets;
  return assets.filter(a =>
    [a.asset_code, a.asset_name, a.asset_type, a.file_format, a.query_engine]
      .filter(Boolean)
      .some(v => String(v).toLowerCase().includes(kw)),
  );
});

// Asset create/edit modal
const assetModalVisible = ref(false);
const assetModalLoading = ref(false);
const editingAsset = ref<DatasetAssetItem | null>(null);
const assetForm = ref({
  asset_name: '',
  asset_type: undefined as string | undefined,
  file_format: '',
  query_engine: '',
  is_query_entry: false,
});

function openAssetCreate() {
  editingAsset.value = null;
  assetForm.value = { asset_name: '', asset_type: undefined, file_format: '', query_engine: '', is_query_entry: false };
  assetModalVisible.value = true;
}

function openAssetEdit(asset: DatasetAssetItem) {
  editingAsset.value = asset;
  assetForm.value = {
    asset_name: asset.asset_name || '',
    asset_type: asset.asset_type,
    file_format: asset.file_format || '',
    query_engine: asset.query_engine || '',
    is_query_entry: asset.is_query_entry || false,
  };
  assetModalVisible.value = true;
}

async function submitAsset() {
  assetModalLoading.value = true;
  try {
    if (editingAsset.value) {
      await updateAsset({ id: editingAsset.value.id, ...assetForm.value });
      message.success('资产已更新');
    } else {
      await createAsset({ version_id: props.versionDetail?.id, ...assetForm.value });
      message.success('资产已创建');
    }
    assetModalVisible.value = false;
    emit('refresh');
  } finally {
    assetModalLoading.value = false;
  }
}

// File register modal
const fileModalVisible = ref(false);
const fileModalLoading = ref(false);
const editingFile = ref<AssetFileItem | null>(null);
const currentAssetForFile = ref<DatasetAssetItem | null>(null);
const fileForm = ref({
  file_role: 'primary',
  local_path: '',
  file_format: '',
  index_of_file_id: undefined as number | undefined,
});

function openFileRegister(asset: DatasetAssetItem) {
  currentAssetForFile.value = asset;
  editingFile.value = null;
  fileForm.value = { file_role: 'primary', local_path: '', file_format: '', index_of_file_id: undefined };
  fileModalVisible.value = true;
}

function openFileEdit(asset: DatasetAssetItem, file: AssetFileItem) {
  currentAssetForFile.value = asset;
  editingFile.value = file;
  fileForm.value = {
    file_role: file.file_role || 'primary',
    local_path: file.local_path || '',
    file_format: file.file_format || '',
    index_of_file_id: file.index_of_file_id,
  };
  fileModalVisible.value = true;
}

async function submitFile() {
  if (!currentAssetForFile.value) return;
  fileModalLoading.value = true;
  try {
    if (editingFile.value) {
      await updateFile({ id: editingFile.value.id, ...fileForm.value });
      message.success('文件已更新');
    } else {
      await registerFile({ asset_id: currentAssetForFile.value.id, ...fileForm.value });
      message.success('文件已登记');
    }
    fileModalVisible.value = false;
    emit('refresh');
  } finally {
    fileModalLoading.value = false;
  }
}

async function handleDeleteAsset(asset: DatasetAssetItem) {
  await deleteAsset(asset.id);
  message.success('资产已删除');
  emit('refresh');
}

async function handleDeleteFile(file: AssetFileItem) {
  await deleteFile(file.id);
  message.success('文件已删除');
  emit('refresh');
}
</script>

<template>
  <div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px;">
      <Button type="primary" ghost @click="openAssetCreate">新增资产</Button>
      <Input v-model:value="keyword" allow-clear placeholder="筛选资产..." style="width: 200px;" />
      <span style="font-size: 12px; color: #888; line-height: 32px;">
        {{ filteredAssets.length }} / {{ versionDetail?.assets?.length || 0 }} 个资产
      </span>
    </div>

    <div v-if="loading" style="text-align: center; padding: 40px;">加载中...</div>
    <Empty v-else-if="!filteredAssets.length" description="暂无资产" />

    <div v-for="asset in filteredAssets" :key="asset.id" style="border: 1px solid #e0e0e0; border-radius: 4px; padding: 12px; margin-bottom: 8px; background: #fff;">
      <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
        <div>
          <strong>{{ asset.asset_name || asset.asset_code || `asset-${asset.id}` }}</strong>
          <span style="color: #888; font-size: 12px;"> / {{ asset.asset_type || '-' }}</span>
        </div>
        <Space size="small">
          <Tag v-if="asset.is_query_entry" color="blue">查询入口</Tag>
          <Tag>{{ asset.asset_type || '-' }}</Tag>
        </Space>
      </div>

      <div style="font-size: 12px; color: #888; margin-bottom: 8px;">
        文件 {{ asset.files?.length || 0 }} · 主格式 {{ asset.file_format || '-' }} · 查询引擎 {{ asset.query_engine || '-' }}
      </div>

      <!-- Files -->
      <div v-if="asset.files?.length" style="margin-bottom: 8px;">
        <div v-for="file in asset.files" :key="file.id" style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px; border-bottom: 1px dashed #f0f0f0;">
          <div>
            <Tag :color="getFileRoleColor(file as AssetFileItem)">{{ getFileRoleLabel(file as AssetFileItem) }}</Tag>
            <Tag v-if="file.file_format">{{ file.file_format }}</Tag>
            {{ file.file_name || file.local_path || '-' }}
          </div>
          <Space size="small">
            <Button type="link" size="small" @click="openFileEdit(asset as DatasetAssetItem, file as AssetFileItem)">编辑</Button>
            <Button type="link" size="small" danger @click="handleDeleteFile(file as AssetFileItem)">删除</Button>
          </Space>
        </div>
      </div>

      <div style="display: flex; gap: 4px;">
        <Button size="small" @click="openAssetEdit(asset as DatasetAssetItem)">编辑资产</Button>
        <Button size="small" @click="openFileRegister(asset as DatasetAssetItem)">登记文件</Button>
        <Button size="small" danger @click="handleDeleteAsset(asset as DatasetAssetItem)">删除资产</Button>
      </div>
    </div>

    <!-- Asset Modal -->
    <Modal
      v-model:open="assetModalVisible"
      :title="editingAsset ? '编辑资产' : '新增资产'"
      :confirm-loading="assetModalLoading"
      @ok="submitAsset"
    >
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <Input v-model:value="assetForm.asset_name" placeholder="资产名称" />
        <Select v-model:value="assetForm.asset_type" :options="assetTypeOptions" placeholder="资产类型" />
        <Input v-model:value="assetForm.file_format" placeholder="文件格式" />
        <Input v-model:value="assetForm.query_engine" placeholder="查询引擎" />
        <label>
          <input type="checkbox" v-model="assetForm.is_query_entry" /> 设为查询入口
        </label>
      </div>
    </Modal>

    <!-- File Modal -->
    <Modal
      v-model:open="fileModalVisible"
      :title="editingFile ? '编辑文件' : '登记文件'"
      :confirm-loading="fileModalLoading"
      @ok="submitFile"
    >
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <div>{{ currentAssetForFile?.asset_name || '-' }}</div>
        <Select v-model:value="fileForm.file_role" :options="FILE_ROLE_OPTIONS" placeholder="文件角色" />
        <Input v-model:value="fileForm.local_path" placeholder="文件路径" />
        <Input v-model:value="fileForm.file_format" placeholder="文件格式" />
      </div>
    </Modal>
  </div>
</template>
```

Wait — the `FILE_ROLE_OPTIONS` needs to be imported. Let me fix: add `FILE_ROLE_OPTIONS` to the import from composable.

- [ ] **Step 2: Verify the component builds**

Run: `cd apps/web-antd && npx vue-tsc --noEmit src/views/apps/dataset/components/AssetPanel.vue 2>&1 | tail -5`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add apps/web-antd/src/views/apps/dataset/components/AssetPanel.vue
git commit -m "feat: extract AssetPanel component with CRUD modals"
```

---

### Task 4: Create LineagePanel component

**Files:**
- Create: `apps/web-antd/src/views/apps/dataset/components/LineagePanel.vue`

**Rationale:** Lineage records with relation type tags, perspective labels, create/delete modals. Props: `versionDetail`, `versionId`. Emits: `refresh`.

- [ ] **Step 1: Write the component**

```vue
<!-- apps/web-antd/src/views/apps/dataset/components/LineagePanel.vue -->
<script setup lang="ts">
import { ref, computed } from 'vue';
import {
  Button, Space, Tag, Select, Input, Modal, Empty, message,
} from 'ant-design-vue';
import {
  useDataset,
  RELATION_TYPE_OPTIONS,
  getLineageRelationColor,
  getLineageRelationLabel,
  getDatasetOptionsApi,
  getDatasetVersionListApi,
  type DatasetVersionDetail,
  type DatasetLineageItem,
  type DatasetItem,
  type DatasetVersionItem,
} from '../composables/useDataset';

const props = defineProps<{
  versionDetail: DatasetVersionDetail | null;
  versionId: number | null;
  loading: boolean;
}>();

const emit = defineEmits<{ refresh: [] }>();
const { createLineage, deleteLineage } = useDataset();

const lineageCreateVisible = ref(false);
const lineageCreateLoading = ref(false);
const targetDatasetOptions = ref<{ label: string; value: number }[]>([]);
const targetVersionOptions = ref<{ label: string; value: number }[]>([]);
const lineageForm = ref({
  dst_dataset_id: undefined as number | undefined,
  dst_version_id: undefined as number | undefined,
  relation_type: 'uses_reference',
  detail_json: '',
});

async function openLineageCreate() {
  lineageForm.value = { dst_dataset_id: undefined, dst_version_id: undefined, relation_type: 'uses_reference', detail_json: '' };
  targetVersionOptions.value = [];
  try {
    const datasets = await getDatasetOptionsApi({});
    targetDatasetOptions.value = (datasets as DatasetItem[]).map(d => ({
      label: d.title || d.dataset_code || `dataset-${d.id}`,
      value: d.id,
    }));
  } catch { /* ignore */ }
  lineageCreateVisible.value = true;
}

async function onTargetDatasetChange(datasetId: number) {
  try {
    const res = await getDatasetVersionListApi({ dataset_id: datasetId });
    targetVersionOptions.value = (res.items || []).map((v: DatasetVersionItem) => ({
      label: `${v.version || '-'} / ${v.title || '-'}`,
      value: v.id,
    }));
  } catch {
    targetVersionOptions.value = [];
  }
}

async function submitLineage() {
  if (!props.versionId || !lineageForm.value.dst_version_id) return;
  lineageCreateLoading.value = true;
  try {
    await createLineage({
      src_version_id: props.versionId,
      relation_type: lineageForm.value.relation_type,
      dst_version_id: lineageForm.value.dst_version_id,
      detail_json: lineageForm.value.detail_json || undefined,
    });
    message.success('血缘关系已创建');
    lineageCreateVisible.value = false;
    emit('refresh');
  } finally {
    lineageCreateLoading.value = false;
  }
}

async function handleDeleteLineage(record: DatasetLineageItem) {
  await deleteLineage(record.id);
  message.success('血缘关系已删除');
  emit('refresh');
}

function getPerspective(record: DatasetLineageItem) {
  if (record.src_version_id === props.versionId) return '作为源';
  return '作为目标';
}

function getCounterpartLabel(record: DatasetLineageItem) {
  if (record.src_version_id === props.versionId) {
    return `${record.dst_dataset_title || '-'} / ${record.dst_version || '-'}`;
  }
  return `${record.src_dataset_title || '-'} / ${record.src_version || '-'}`;
}

const lineageRecords = computed(() =>
  props.versionDetail?.lineage || [],
);
</script>

<template>
  <div>
    <div style="margin-bottom: 12px;">
      <Button type="primary" ghost @click="openLineageCreate">新增血缘</Button>
    </div>

    <div v-if="loading" style="text-align: center; padding: 40px;">加载中...</div>
    <Empty v-else-if="!lineageRecords.length" description="暂无血缘关系" />

    <div v-for="item in lineageRecords" :key="item.id" style="border: 1px solid #e0e0e0; border-radius: 4px; padding: 8px; margin-bottom: 6px; background: #fff;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <Space size="small">
          <Tag :color="getLineageRelationColor(item.relation_type)">
            {{ getLineageRelationLabel(item.relation_type) }}
          </Tag>
          <Tag>{{ getPerspective(item as DatasetLineageItem) }}</Tag>
          <span style="font-size: 12px;">{{ getCounterpartLabel(item as DatasetLineageItem) }}</span>
        </Space>
        <Button type="link" size="small" danger @click="handleDeleteLineage(item as DatasetLineageItem)">删除</Button>
      </div>
    </div>

    <!-- Create Lineage Modal -->
    <Modal
      v-model:open="lineageCreateVisible"
      title="新增血缘关系"
      :confirm-loading="lineageCreateLoading"
      @ok="submitLineage"
    >
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <Select
          v-model:value="lineageForm.dst_dataset_id"
          :options="targetDatasetOptions"
          placeholder="目标 Dataset"
          @change="(v: number) => onTargetDatasetChange(v)"
        />
        <Select
          v-model:value="lineageForm.dst_version_id"
          :options="targetVersionOptions"
          placeholder="目标版本"
          :disabled="!lineageForm.dst_dataset_id"
        />
        <Select v-model:value="lineageForm.relation_type" :options="RELATION_TYPE_OPTIONS" placeholder="关系类型" />
        <Input v-model:value="lineageForm.detail_json" allow-clear placeholder="可选：detail_json" />
      </div>
    </Modal>
  </div>
</template>
```

- [ ] **Step 2: Verify the component builds**

Run: `cd apps/web-antd && npx vue-tsc --noEmit src/views/apps/dataset/components/LineagePanel.vue 2>&1 | tail -5`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add apps/web-antd/src/views/apps/dataset/components/LineagePanel.vue
git commit -m "feat: extract LineagePanel component with CRUD modal"
```

---

### Task 5: Create QueryForm component

**Files:**
- Create: `apps/web-antd/src/views/apps/dataset/components/QueryForm.vue`

**Rationale:** Operation selector + dynamic parameter form. Props: `capabilities`, `loading`. Emits: `execute` with operation and params.

- [ ] **Step 1: Write the component**

```vue
<!-- apps/web-antd/src/views/apps/dataset/components/QueryForm.vue -->
<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import {
  Button, Select, Input, Tag, Descriptions, Space,
} from 'ant-design-vue';
import type { DatasetVersionQueryCapabilitiesResult } from '#/api/apps/dataset';

const props = defineProps<{
  capabilities: DatasetVersionQueryCapabilitiesResult | null;
  loading: boolean;
}>();

const emit = defineEmits<{
  execute: [operation: string, params: Record<string, any>];
}>();

const operation = ref('');
const paramsText = ref('{}');
const executing = ref(false);

const operationOptions = computed(() =>
  (props.capabilities?.query_adapter?.supported_operations || []).map(op => ({
    label: op,
    value: op,
  })),
);

const defaultParams: Record<string, Record<string, any>> = {
  genes_list: { max_records: 100 },
  samples_list: { max_records: 100 },
  matrix_slice: { data_type: 'count', genes: [], samples: [] },
  query: { regions: [] },
  region_features: { region: '', feature_type: 'gene', limit: 100 },
  gene_search: { keyword: '', page: 1, page_size: 20 },
  gene_list: { page: 1, page_size: 20 },
  gene_info: { gene_id: '' },
  transcript_list: { page: 1, page_size: 20 },
  term_lookup: { term_source: 'go', keyword: '', limit: 20 },
  term_gene_list: { term_source: 'go', term_id: '', page: 1, size: 20 },
  batch_fetch: { regions: [] },
  dataset_summary: {},
  trait_list: { limit: 20 },
  trait_search: { keyword: '', limit: 20 },
  trait_values: { trait: '', timepoint: '', limit: 20 },
  subject_list: { limit: 20 },
  subject_detail: { subject_id: '' },
};

function loadExample() {
  if (!operation.value) return;
  const example = defaultParams[operation.value];
  paramsText.value = example ? JSON.stringify(example, null, 2) : '{}';
}

watch(operation, () => {
  loadExample();
});

async function handleExecute() {
  let params: Record<string, any>;
  try {
    params = JSON.parse(paramsText.value);
  } catch {
    params = {};
  }
  executing.value = true;
  try {
    emit('execute', operation.value, params);
  } finally {
    executing.value = false;
  }
}
</script>

<template>
  <div>
    <div v-if="!capabilities?.query_adapter?.supported_operations?.length" style="color: #888; padding: 20px; text-align: center;">
      当前版本没有可用查询操作
    </div>

    <template v-else>
      <div style="margin-bottom: 8px; font-size: 12px; color: #888;">文件可访问</div>
      <Tag :color="capabilities?.file_access?.exists_on_server ? 'success' : 'warning'" style="margin-bottom: 12px;">
        {{ capabilities?.file_access?.exists_on_server ? '是' : '否' }}
      </Tag>

      <div style="display: flex; flex-direction: column; gap: 8px;">
        <label>
          <span style="font-size: 12px;">查询操作</span>
          <Select
            v-model:value="operation"
            :options="operationOptions"
            placeholder="选择查询操作"
            style="width: 100%;"
          />
        </label>

        <label>
          <span style="font-size: 12px;">参数 JSON</span>
          <Input.TextArea
            v-model:value="paramsText"
            :rows="12"
            placeholder="请输入 JSON 查询参数"
          />
        </label>

        <Space>
          <Button type="primary" :loading="executing" @click="handleExecute">执行查询</Button>
          <Button :disabled="!operation" @click="loadExample">载入示例参数</Button>
        </Space>
      </div>
    </template>
  </div>
</template>
```

- [ ] **Step 2: Verify the component builds**

Run: `cd apps/web-antd && npx vue-tsc --noEmit src/views/apps/dataset/components/QueryForm.vue 2>&1 | tail -5`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add apps/web-antd/src/views/apps/dataset/components/QueryForm.vue
git commit -m "feat: add QueryForm component with dynamic operation selector"
```

---

### Task 6: Create Detail.vue page

**Files:**
- Create: `apps/web-antd/src/views/apps/dataset/Detail.vue`

**Rationale:** Full-width detail page composing VersionTable, AssetPanel, LineagePanel. Uses `useDataset()` composable. Route params provide dataset ID. This replaces both the 概览 Drawer and 版本工作台 Drawer.

- [ ] **Step 1: Write the page component**

```vue
<!-- apps/web-antd/src/views/apps/dataset/Detail.vue -->
<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Button, Tag, Space, Modal, message } from 'ant-design-vue';
import { Page } from '@vben/common-ui';
import VersionTable from './components/VersionTable.vue';
import AssetPanel from './components/AssetPanel.vue';
import LineagePanel from './components/LineagePanel.vue';
import {
  useDataset,
  lifecycleColor,
  visibilityColor,
  getPreferredDatasetTypeCode,
  getSelectedVersionExposure,
  type DatasetVersionItem,
} from './composables/useDataset';

const route = useRoute();
const router = useRouter();

const {
  detailLoading, detailData, loadDetail,
  versionListLoading, versionListData, loadVersionList,
  versionDetailLoading, versionDetailData, loadVersionDetail,
  activateVersion, releaseVersion, withdrawVersion, setDefaultPublicVersion,
  loadPublishRecords, publishRecords,
  deleteDatasetApi,
} = useDataset();

const datasetId = computed(() => Number(route.params.id));
const activeVersionId = ref<number | null>(null);
const actionLoadingKey = ref('');

// Load data
async function loadAll() {
  await Promise.all([
    loadDetail(datasetId.value),
    loadVersionList(datasetId.value),
  ]);
  // Default to current version
  if (versionListData.value?.current_version?.id) {
    activeVersionId.value = versionListData.value.current_version.id;
    await selectVersion(activeVersionId.value);
  }
}

async function selectVersion(versionId: number) {
  activeVersionId.value = versionId;
  await Promise.all([
    loadVersionDetail(versionId),
    loadPublishRecords(versionId),
  ]);
}

async function handleSelectVersion(version: DatasetVersionItem) {
  await selectVersion(version.id);
}

async function handleActivate(version: DatasetVersionItem) {
  actionLoadingKey.value = `activate-version-${version.id}`;
  try {
    await activateVersion(version.id);
    message.success('版本已激活');
    await loadAll();
  } finally {
    actionLoadingKey.value = '';
  }
}

async function handleRelease(version: DatasetVersionItem) {
  actionLoadingKey.value = `release-version-${version.id}`;
  try {
    await releaseVersion(version.id);
    message.success('版本已发布');
    await loadAll();
  } finally {
    actionLoadingKey.value = '';
  }
}

async function handleWithdraw(version: DatasetVersionItem) {
  actionLoadingKey.value = `withdraw-version-${version.id}`;
  try {
    await withdrawVersion(version.id);
    message.success('版本已撤回');
    await loadAll();
  } finally {
    actionLoadingKey.value = '';
  }
}

async function handleSetDefault(version: DatasetVersionItem) {
  actionLoadingKey.value = `set-default-version-${version.id}`;
  try {
    await setDefaultPublicVersion(version.id);
    message.success('已设为默认公开版本');
    await loadAll();
  } finally {
    actionLoadingKey.value = '';
  }
}

function handleDelete() {
  Modal.confirm({
    title: '删除 Dataset',
    content: `确认删除 ${detailData.value?.title || detailData.value?.dataset_code || datasetId.value} 吗？`,
    async onOk() {
      await deleteDatasetApi({ id: datasetId.value });
      message.success('Dataset 已删除');
      router.push('/dataset');
    },
  });
}

const versionMismatch = computed(() =>
  versionListData.value?.current_version?.id &&
  versionListData.value?.default_public_version?.id &&
  versionListData.value.current_version.id !== versionListData.value.default_public_version.id,
);

onMounted(() => loadAll());
</script>

<template>
  <Page auto-content-height>
    <div v-if="detailLoading" style="text-align: center; padding: 80px;">加载中...</div>
    <template v-else-if="detailData">
      <!-- Section 1: Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
        <div>
          <h2 style="margin: 0;">{{ detailData.dataset_code || '-' }}</h2>
          <div style="color: #888; font-size: 13px;">
            <span>{{ detailData.organism || '-' }} · {{ detailData.assembly || '-' }}</span>
            <span style="margin-left: 8px;">{{ getPreferredDatasetTypeCode(detailData.dataset_type) }}</span>
            <span style="margin-left: 8px;">{{ detailData.query_profile?.file_format || detailData.file_format || '-' }}</span>
          </div>
        </div>
        <Space>
          <Tag :color="lifecycleColor(detailData.lifecycle_state)">{{ detailData.lifecycle_state || '-' }}</Tag>
          <Tag :color="visibilityColor(detailData.visibility)">{{ detailData.visibility || '-' }}</Tag>
          <Button type="primary" ghost @click="router.push(`/dataset/${datasetId}/query`)">数据查询</Button>
          <Button danger @click="handleDelete">删除</Button>
        </Space>
      </div>

      <!-- Section 2: Status Bar -->
      <div style="display: flex; gap: 24px; font-size: 13px; padding: 8px 12px; background: #fafafa; border-radius: 4px; margin-bottom: 16px;">
        <span>查询入口：<strong>{{ detailData.query_entry_asset?.asset_code || '未配置' }}</strong></span>
        <span>当前版本：<strong>{{ versionListData?.current_version?.version || '-' }}</strong></span>
        <span>默认公开版本：<strong>{{ versionListData?.default_public_version?.version || '-' }}</strong></span>
      </div>

      <div v-if="versionMismatch" style="background: #fffbe6; border: 1px solid #ffe58f; padding: 6px 12px; border-radius: 4px; margin-bottom: 12px; font-size: 12px;">
        ⚠ 当前版本与默认公开版本不同，前台默认访问的是 {{ versionListData?.default_public_version?.version }}
      </div>

      <!-- Section 3: Version Table -->
      <div style="margin-bottom: 20px;">
        <h3>版本管理</h3>
        <VersionTable
          :version-data="versionListData"
          :active-version-id="activeVersionId"
          :action-loading-key="actionLoadingKey"
          @select="handleSelectVersion"
          @activate="handleActivate"
          @release="handleRelease"
          @withdraw="handleWithdraw"
          @set-default="handleSetDefault"
          @create-version="() => {}"
        />
      </div>

      <!-- Section 4 & 5: Assets & Lineage (side-by-side) -->
      <div v-if="activeVersionId" style="display: flex; gap: 16px;">
        <div style="flex: 1;">
          <h3>资产</h3>
          <AssetPanel
            :version-detail="versionDetailData"
            :loading="versionDetailLoading"
            @refresh="selectVersion(activeVersionId!)"
          />
        </div>
        <div style="flex: 1;">
          <h3>血缘</h3>
          <LineagePanel
            :version-detail="versionDetailData"
            :version-id="activeVersionId"
            :loading="versionDetailLoading"
            @refresh="selectVersion(activeVersionId!)"
          />
        </div>
      </div>

      <!-- Section 6: Publish History (collapsed) -->
      <details style="margin-top: 20px; font-size: 12px; color: #888;">
        <summary>版本发布历史（{{ publishRecords.length }} 条）</summary>
        <table style="width: 100%; border-collapse: collapse; margin-top: 8px;">
          <tr style="background: #f5f5f5;">
            <th style="padding: 4px 8px; text-align: left; border: 1px solid #e0e0e0;">时间</th>
            <th style="padding: 4px 8px; text-align: left; border: 1px solid #e0e0e0;">动作</th>
            <th style="padding: 4px 8px; text-align: left; border: 1px solid #e0e0e0;">可见性</th>
            <th style="padding: 4px 8px; text-align: left; border: 1px solid #e0e0e0;">生命周期</th>
            <th style="padding: 4px 8px; text-align: left; border: 1px solid #e0e0e0;">备注</th>
          </tr>
          <tr v-for="r in publishRecords" :key="r.id">
            <td style="padding: 3px 6px; border: 1px solid #e0e0e0;">{{ r.create_time ? new Date(r.create_time * 1000).toLocaleString('zh-CN') : '-' }}</td>
            <td style="padding: 3px 6px; border: 1px solid #e0e0e0;">{{ r.action || '-' }}</td>
            <td style="padding: 3px 6px; border: 1px solid #e0e0e0;">{{ r.visibility_before || '-' }} → {{ r.visibility_after || '-' }}</td>
            <td style="padding: 3px 6px; border: 1px solid #e0e0e0;">{{ r.lifecycle_before || '-' }} → {{ r.lifecycle_after || '-' }}</td>
            <td style="padding: 3px 6px; border: 1px solid #e0e0e0;">{{ r.note || '-' }}</td>
          </tr>
        </table>
      </details>

      <!-- Section 7: System Info (collapsed) -->
      <details style="margin-top: 12px; font-size: 12px; color: #888;">
        <summary>系统信息</summary>
        <div style="display: flex; gap: 24px; margin-top: 8px;">
          <span>ID: {{ detailData.id }}</span>
          <span>Code: {{ detailData.dataset_code }}</span>
          <span>创建: {{ detailData.create_time ? new Date(detailData.create_time * 1000).toLocaleString('zh-CN') : '-' }}</span>
          <span>更新: {{ detailData.update_time ? new Date(detailData.update_time * 1000).toLocaleString('zh-CN') : '-' }}</span>
        </div>
      </details>
    </template>
    <div v-else style="text-align: center; padding: 80px; color: #888;">未获取到 dataset 详情</div>
  </Page>
</template>
```

- [ ] **Step 2: Verify the page compiles**

Run: `cd apps/web-antd && npx vue-tsc --noEmit src/views/apps/dataset/Detail.vue 2>&1 | tail -5`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add apps/web-antd/src/views/apps/dataset/Detail.vue
git commit -m "feat: add Detail page composing VersionTable, AssetPanel, LineagePanel"
```

---

### Task 7: Create Query.vue page

**Files:**
- Create: `apps/web-antd/src/views/apps/dataset/Query.vue`

**Rationale:** Full-width query page. Loads capabilities on mount, renders QueryForm in left panel, results in right panel.

- [ ] **Step 1: Write the page component**

```vue
<!-- apps/web-antd/src/views/apps/dataset/Query.vue -->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Button, Tag, Space, Empty, Descriptions, message } from 'ant-design-vue';
import { Page } from '@vben/common-ui';
import QueryForm from './components/QueryForm.vue';
import {
  useDataset,
  getPreferredDatasetTypeCode,
  type DatasetVersionQueryExecuteResult,
} from './composables/useDataset';

const route = useRoute();
const router = useRouter();

const datasetId = computed(() => Number(route.params.id));

const {
  detailLoading, detailData, loadDetail,
  versionListLoading, versionListData, loadVersionList,
  queryCapabilitiesLoading, queryCapabilities, loadQueryCapabilities,
  executeQuery,
} = useDataset();

const queryResult = ref<DatasetVersionQueryExecuteResult | null>(null);
const queryError = ref('');

const activeVersionId = computed(() =>
  versionListData.value?.current_version?.id || null,
);

async function loadPageData() {
  await Promise.all([
    loadDetail(datasetId.value),
    loadVersionList(datasetId.value),
  ]);
  if (activeVersionId.value) {
    await loadQueryCapabilities(activeVersionId.value);
  }
}

async function handleExecute(operation: string, params: Record<string, any>) {
  if (!activeVersionId.value) return;
  queryError.value = '';
  queryResult.value = null;
  try {
    queryResult.value = await executeQuery(activeVersionId.value, operation, params);
  } catch (e: any) {
    queryError.value = e?.message || '查询执行失败';
  }
}

function copyResult() {
  if (queryResult.value) {
    navigator.clipboard.writeText(JSON.stringify(queryResult.value, null, 2));
    message.success('结果已复制');
  }
}

onMounted(() => loadPageData());
</script>

<template>
  <Page auto-content-height>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <div>
        <h2 style="margin: 0;">数据查询：{{ detailData?.dataset_code || '-' }}</h2>
        <div style="color: #888; font-size: 13px;">
          {{ versionListData?.current_version?.version || '-' }}
          · {{ getPreferredDatasetTypeCode(detailData?.dataset_type) }}
          · {{ detailData?.query_profile?.file_format || detailData?.file_format || '-' }}
        </div>
      </div>
      <Button @click="router.push(`/dataset/${datasetId}`)">← 返回详情</Button>
    </div>

    <div style="display: flex; gap: 16px;">
      <!-- Left: Query Form -->
      <div style="width: 360px; flex-shrink: 0;">
        <h3>查询配置</h3>
        <Descriptions bordered :column="1" size="small" style="margin-bottom: 12px;">
          <Descriptions.Item label="查询入口资产">
            {{ queryCapabilities?.query_entry_asset?.asset_code || '-' }}
          </Descriptions.Item>
          <Descriptions.Item label="主文件路径">
            {{ queryCapabilities?.file_path || '-' }}
          </Descriptions.Item>
          <Descriptions.Item label="可用操作">
            {{ queryCapabilities?.query_adapter?.supported_operations?.join(', ') || '-' }}
          </Descriptions.Item>
        </Descriptions>
        <QueryForm
          :capabilities="queryCapabilities"
          :loading="queryCapabilitiesLoading"
          @execute="handleExecute"
        />
      </div>

      <!-- Right: Results -->
      <div style="flex: 1;">
        <h3>查询结果</h3>
        <div v-if="queryError" style="color: #ff4d4f; padding: 20px; background: #fff2f0; border-radius: 4px;">
          {{ queryError }}
        </div>
        <div v-else-if="queryResult" style="background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 4px; padding: 12px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <Space>
              <Tag color="processing">{{ queryResult.operation }}</Tag>
              <Tag>{{ queryResult.adapter }}</Tag>
            </Space>
            <Button size="small" @click="copyResult">复制 JSON</Button>
          </div>
          <pre style="max-height: 500px; overflow: auto; font-size: 11px; background: #fff; padding: 8px; border-radius: 4px;">{{ JSON.stringify(queryResult.data || queryResult, null, 2) }}</pre>
        </div>
        <Empty v-else description="选择操作并填写参数后，点击执行查询" />
      </div>
    </div>
  </Page>
</template>
```

- [ ] **Step 2: Verify the page compiles**

Run: `cd apps/web-antd && npx vue-tsc --noEmit src/views/apps/dataset/Query.vue 2>&1 | tail -5`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add apps/web-antd/src/views/apps/dataset/Query.vue
git commit -m "feat: add Query page with two-column layout"
```

---

### Task 8: Simplify index.vue to list-only

**Files:**
- Modify: `apps/web-antd/src/views/apps/dataset/index.vue`

**Rationale:** Strip the 7884-line file down to just the dataset list table with 3 action buttons (详情, 数据查询, 删除), removing all Drawers, modals, tabs, and query logic.

- [ ] **Step 1: Write the simplified list page**

```vue
<!-- apps/web-antd/src/views/apps/dataset/index.vue -->
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Page } from '@vben/common-ui';
import {
  Button, Checkbox, Empty, Input, Modal, Select, Space, Table, Tag,
} from 'ant-design-vue';
import {
  getDatasetListApi,
  deleteDatasetApi,
  getDatasetKindOptionsApi,
  type DatasetItem,
  type DatasetKindOption,
} from '#/api/apps/dataset';
import { useMessage } from '#/hooks/web/useMessage';
import {
  lifecycleColor,
  visibilityColor,
  getPreferredDatasetTypeCode,
} from './composables/useDataset';

const { createConfirm, createMessage } = useMessage();
const router = useRouter();

const loading = ref(false);
const rows = ref<DatasetItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);

const kindOptions = ref<DatasetKindOption[]>([]);

const filters = reactive({
  name: '',
  dataset_type: undefined as string | undefined,
  lifecycle_state: undefined as string | undefined,
  visibility: undefined as string | undefined,
});

const lifecycleOptions = [
  { label: '草稿', value: 'draft' },
  { label: '已上传', value: 'uploaded' },
  { label: '校验中', value: 'validating' },
  { label: '已校验', value: 'validated' },
  { label: '索引中', value: 'indexing' },
  { label: '就绪', value: 'ready' },
  { label: '公开', value: 'public' },
  { label: '已归档', value: 'archived' },
];

const visibilityOptions = [
  { label: '私有', value: 'private' },
  { label: '受控', value: 'restricted' },
  { label: '公开', value: 'public' },
];

const datasetTypeOptions = [
  { label: 'Genome', value: 'sequence' },
  { label: 'Transcriptome', value: 'expression' },
  { label: 'Variome', value: 'variant' },
  { label: 'Phenome', value: 'phenome' },
  { label: 'Annotation', value: 'annotation' },
  { label: 'Interaction', value: 'interaction' },
  { label: 'Signal', value: 'signal' },
];

const columns: any[] = [
  { title: 'Dataset', dataIndex: 'title', key: 'title', width: 260 },
  { title: '类型', dataIndex: 'dataset_type', key: 'dataset_type', width: 140 },
  { title: '物种 / 组装', dataIndex: 'organism', key: 'organism', width: 220 },
  { title: '当前版本', dataIndex: 'version', key: 'version', width: 120 },
  { title: '生命周期', dataIndex: 'lifecycle_state', key: 'lifecycle_state', width: 120 },
  { title: '可见性', dataIndex: 'visibility', key: 'visibility', width: 110 },
  { title: '操作', dataIndex: 'action', key: 'action' },
];

async function loadDatasets() {
  loading.value = true;
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value };
    if (filters.name) params.name = filters.name;
    if (filters.dataset_type) params.dataset_type = filters.dataset_type;
    if (filters.lifecycle_state) params.lifecycle_state = filters.lifecycle_state;
    if (filters.visibility) params.visibility = filters.visibility;
    const res = await getDatasetListApi(params);
    rows.value = res.dataList;
    total.value = res.total;
  } finally {
    loading.value = false;
  }
}

function handleTableChange(pag: { current: number; pageSize: number }) {
  page.value = pag.current;
  pageSize.value = pag.pageSize;
  loadDatasets();
}

function resetFilters() {
  filters.name = '';
  filters.dataset_type = undefined;
  filters.lifecycle_state = undefined;
  filters.visibility = undefined;
  loadDatasets();
}

async function handleDelete(record: DatasetItem) {
  createConfirm({
    iconType: 'warning',
    title: '删除 Dataset',
    content: `确认删除 dataset ${record.title || record.name || record.id} 吗？`,
    async onOk() {
      await deleteDatasetApi({ id: record.id });
      createMessage.success('Dataset 已删除');
      await loadDatasets();
    },
  });
}

onMounted(async () => {
  await loadDatasets();
  try {
    kindOptions.value = await getDatasetKindOptionsApi();
  } catch { /* ignore */ }
});
</script>

<template>
  <Page auto-content-height>
    <div style="margin-bottom: 16px;">
      <Space wrap>
        <Input v-model:value="filters.name" allow-clear placeholder="Dataset 名称 / code" style="width: 220px;" />
        <Select v-model:value="filters.dataset_type" allow-clear :options="datasetTypeOptions" placeholder="类型" style="width: 180px;" />
        <Select v-model:value="filters.lifecycle_state" allow-clear :options="lifecycleOptions" placeholder="生命周期" style="width: 160px;" />
        <Select v-model:value="filters.visibility" allow-clear :options="visibilityOptions" placeholder="可见性" style="width: 140px;" />
        <Button type="primary" @click="loadDatasets">查询</Button>
        <Button @click="resetFilters">重置</Button>
      </Space>
    </div>

    <Table
      :columns="columns"
      :data-source="rows"
      :loading="loading"
      :pagination="{
        current: page,
        pageSize,
        total,
        showSizeChanger: true,
        showTotal: (v: number) => `共 ${v} 条`,
      }"
      :row-key="(r: DatasetItem) => r.id"
      bordered
      size="middle"
      @change="handleTableChange"
    >
      <template #emptyText>
        <Empty description="当前没有 dataset" />
      </template>
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'title'">
          <div>
            <div>{{ (record as DatasetItem).title || (record as DatasetItem).name || `dataset-${(record as DatasetItem).id}` }}</div>
            <div style="font-size: 12px; color: #888;">{{ (record as DatasetItem).dataset_code || '-' }}</div>
          </div>
        </template>
        <template v-else-if="column.key === 'dataset_type'">
          <Tag>{{ getPreferredDatasetTypeCode((record as DatasetItem).dataset_type) }}</Tag>
        </template>
        <template v-else-if="column.key === 'organism'">
          <div>{{ (record as DatasetItem).organism || '-' }}</div>
          <div style="font-size: 12px; color: #888;">{{ (record as DatasetItem).assembly || '-' }}</div>
        </template>
        <template v-else-if="column.key === 'version'">
          <Tag color="blue">{{ (record as DatasetItem).version || '-' }}</Tag>
        </template>
        <template v-else-if="column.key === 'lifecycle_state'">
          <Tag :color="lifecycleColor((record as DatasetItem).lifecycle_state)">
            {{ (record as DatasetItem).lifecycle_state || '-' }}
          </Tag>
        </template>
        <template v-else-if="column.key === 'visibility'">
          <Tag :color="visibilityColor((record as DatasetItem).visibility)">
            {{ (record as DatasetItem).visibility || '-' }}
          </Tag>
        </template>
        <template v-else-if="column.key === 'action'">
          <Space wrap>
            <Button type="link" @click="router.push(`/dataset/${(record as DatasetItem).id}`)">详情</Button>
            <Button type="link" @click="router.push(`/dataset/${(record as DatasetItem).id}/query`)">数据查询</Button>
            <Button danger type="link" @click="handleDelete(record as DatasetItem)">删除</Button>
          </Space>
        </template>
      </template>
    </Table>
  </Page>
</template>
```

- [ ] **Step 2: Verify page compiles**

Run: `cd apps/web-antd && npx vue-tsc --noEmit src/views/apps/dataset/index.vue 2>&1 | tail -5`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add apps/web-antd/src/views/apps/dataset/index.vue
git commit -m "refactor: simplify index.vue to list-only with 3 action buttons"
```

---

### Task 9: Add routes for /dataset/:id and /dataset/:id/query

**Files:**
- Create: `apps/web-antd/src/views/apps/dataset/route.ts`

**Rationale:** Add frontend static routes for the new Detail and Query pages. Since the project uses dynamic route loading from `./routes/static/**/*.ts`, creating a route file in that directory will auto-register the routes.

- [ ] **Step 1: Create route config**

```typescript
// apps/web-antd/src/views/apps/dataset/route.ts
import type { RouteRecordRaw } from 'vue-router';

const datasetRoutes: RouteRecordRaw[] = [
  {
    path: '/dataset/:id',
    name: 'DatasetDetail',
    component: () => import('./Detail.vue'),
    meta: {
      title: 'Dataset 详情',
    },
  },
  {
    path: '/dataset/:id/query',
    name: 'DatasetQuery',
    component: () => import('./Query.vue'),
    meta: {
      title: '数据查询',
    },
  },
];

export default datasetRoutes;
```

Wait — the static routes auto-import is at `router/routes/static/**/*.ts`. The route file needs to be there, not in the views directory. Let me check the exact location:

The route files are at:
- `apps/web-antd/src/router/routes/static/breeding.ts`
- `apps/web-antd/src/router/routes/static/demos.ts`
- etc.

So the route file needs to go to `apps/web-antd/src/router/routes/static/dataset.ts`, not the views directory.

Let me fix this:

- [ ] **Step 1: Create route config in the static routes directory**

```typescript
// apps/web-antd/src/router/routes/static/dataset.ts
import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/dataset/:id',
    name: 'DatasetDetail',
    component: () => import('../../../views/apps/dataset/Detail.vue'),
    meta: { title: 'Dataset 详情' },
  },
  {
    path: '/dataset/:id/query',
    name: 'DatasetQuery',
    component: () => import('../../../views/apps/dataset/Query.vue'),
    meta: { title: '数据查询' },
  },
];

export default routes;
```

- [ ] **Step 2: Verify routes load**

Run: `cd apps/web-antd && pnpm dev:antd` and check that navigating to `/dataset/1` loads the Detail page.
Expected: Detail page renders (may show loading/error if no dataset with id=1)

- [ ] **Step 3: Commit**

```bash
git add apps/web-antd/src/router/routes/static/dataset.ts
git commit -m "feat: add routes for Dataset Detail and Query pages"
```

---

### Task 10: Integration — start dev server and verify all pages

**Files:** None (verification only)

- [ ] **Step 1: Start dev server**

Run: `cd /Users/kentnf/projects/omicsagent/odata/frontend/admin-web && pnpm dev:antd`
Expected: Vite dev server starts on http://127.0.0.1:5666/

- [ ] **Step 2: Verify list page**

Open http://127.0.0.1:5666/dataset (or the route that loads the list page)
Expected: Dataset list renders with 3 action buttons (详情, 数据查询, 删除)

- [ ] **Step 3: Verify detail page**

Click "详情" on any dataset or navigate to `/dataset/1`
Expected: Detail page loads with Header, Status Bar, Version Table. Selecting a version shows Assets and Lineage panels.

- [ ] **Step 4: Verify query page**

Click "数据查询" or navigate to `/dataset/1/query`
Expected: Query page loads with operation selector and params on left, results area on right.

- [ ] **Step 5: Verify delete**

Click "删除" on the list page
Expected: Confirm modal appears, dataset is deleted on confirm.

- [ ] **Step 6: Check for console errors**

Open browser DevTools Console during all the above steps.
Expected: No red errors.

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "chore: complete Dataset Center UI simplification

- Replace 7884-line monolithic index.vue with 7 focused files
- Move from Drawer overlay to independent route pages
- Eliminate overlapping content between 概览 and 版本工作台
- Simplify query from 17 sub-tabs to operation dropdown + dynamic form
- Remove redundant health cards, recent tasks, merged into status bar"
```
