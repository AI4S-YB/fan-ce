<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Page } from '@vben/common-ui';
import {
  Button, Empty, Input, Modal, Select, Space, Table, Tag,
} from 'ant-design-vue';
import {
  deleteDatasetApi,
  getDatasetKindOptionsApi,
  getDatasetListApi,
  publishDatasetApi,
  unpublishDatasetApi,
  type DatasetItem,
  type DatasetKindOption,
} from '#/api/apps/dataset';
import { useMessage } from '#/hooks/web/useMessage';
import { $t } from '@vben/locales';
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
  { label: $t('dataset.list.lifecycle_draft'), value: 'draft' },
  { label: $t('dataset.list.lifecycle_uploaded'), value: 'uploaded' },
  { label: $t('dataset.list.lifecycle_validating'), value: 'validating' },
  { label: $t('dataset.list.lifecycle_validated'), value: 'validated' },
  { label: $t('dataset.list.lifecycle_indexing'), value: 'indexing' },
  { label: $t('dataset.list.lifecycle_ready'), value: 'ready' },
  { label: $t('dataset.list.visibility_public'), value: 'public' },
  { label: $t('dataset.list.lifecycle_archived'), value: 'archived' },
];

const visibilityOptions = [
  { label: $t('dataset.list.visibility_private'), value: 'private' },
  { label: $t('dataset.list.visibility_controlled'), value: 'restricted' },
  { label: $t('dataset.list.visibility_public'), value: 'public' },
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
  { title: $t('dataset.list.type'), dataIndex: 'dataset_type', key: 'dataset_type', width: 140 },
  { title: $t('dataset.list.organism'), dataIndex: 'organism', key: 'organism', width: 220 },
  { title: $t('dataset.list.currentVersion'), dataIndex: 'version', key: 'version', width: 120 },
  { title: $t('dataset.list.lifecycle'), dataIndex: 'lifecycle_state', key: 'lifecycle_state', width: 120 },
  { title: $t('dataset.list.visibility'), dataIndex: 'visibility', key: 'visibility', width: 110 },
  { title: $t('dataset.list.action'), dataIndex: 'action', key: 'action' },
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
    title: $t('dataset.list.delete') + ' Dataset',
    content: $t('dataset.list.deleteConfirmParam', { name: record.title || record.name || String(record.id) }),
    async onOk() {
      await deleteDatasetApi({ id: record.id });
      createMessage.success($t('dataset.list.datasetDeleted'));
      await loadDatasets();
    },
  });
}

const visibilityLoading = ref<number | null>(null);

async function handleToggleVisibility(record: DatasetItem) {
  visibilityLoading.value = record.id;
  try {
    if (record.visibility === 'public') {
      await unpublishDatasetApi({ id: record.id });
      createMessage.success($t('dataset.list.cancelPublic'));
    } else {
      await publishDatasetApi({ id: record.id });
      createMessage.success($t('dataset.list.makePublic'));
    }
    await loadDatasets();
  } catch (e: any) {
    createMessage.error(e?.message || $t('dataset.list.actionFailed'));
  } finally {
    visibilityLoading.value = null;
  }
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
        <Input v-model:value="filters.name" allow-clear :placeholder="$t('dataset.list.searchPlaceholder')" style="width: 220px;" />
        <Select v-model:value="filters.dataset_type" allow-clear :options="datasetTypeOptions" :placeholder="$t('dataset.list.typePlaceholder')" style="width: 180px;" />
        <Select v-model:value="filters.lifecycle_state" allow-clear :options="lifecycleOptions" :placeholder="$t('dataset.list.lifecyclePlaceholder')" style="width: 160px;" />
        <Select v-model:value="filters.visibility" allow-clear :options="visibilityOptions" :placeholder="$t('dataset.list.visibilityPlaceholder')" style="width: 140px;" />
        <Button type="primary" @click="loadDatasets">{{ $t('dataset.list.query') }}</Button>
        <Button @click="resetFilters">{{ $t('dataset.list.reset') }}</Button>
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
        showTotal: (v: number) => $t('dataset.list.total', { total: v }),
      }"
      :row-key="(r: DatasetItem) => r.id"
      bordered
      size="middle"
      @change="handleTableChange"
    >
      <template #emptyText>
        <Empty :description="$t('dataset.list.emptyHint')" />
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
            <Button type="link" @click="router.push(`/dataset/${(record as DatasetItem).id}`)">{{ $t('dataset.list.detail') }}</Button>
            <Button type="link" @click="router.push(`/dataset/${(record as DatasetItem).id}/query`)">{{ $t('dataset.list.dataQuery') }}</Button>
            <Button
              v-if="(record as DatasetItem).visibility !== 'public'"
              type="link"
              :loading="visibilityLoading === (record as DatasetItem).id"
              @click="handleToggleVisibility(record as DatasetItem)"
            >
              {{ $t('dataset.list.makePublic') }}
            </Button>
            <Button
              v-else
              type="link"
              :loading="visibilityLoading === (record as DatasetItem).id"
              @click="handleToggleVisibility(record as DatasetItem)"
            >
              {{ $t('dataset.list.cancelPublic') }}
            </Button>
            <Button danger type="link" @click="handleDelete(record as DatasetItem)">{{ $t('dataset.list.delete') }}</Button>
          </Space>
        </template>
      </template>
    </Table>
  </Page>
</template>
