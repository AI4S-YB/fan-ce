<script setup lang="ts">
import type {
  GermplasmFieldSchemaItem,
  GermplasmImportBatchDetail,
  GermplasmImportBatchItem,
} from './types';

import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Descriptions,
  Drawer,
  Empty,
  Input,
  message,
  Modal,
  Select,
  Space,
  Table,
  Tag,
} from 'ant-design-vue';

import { $t } from '@vben/locales';
import {
  deleteGermplasmImportBatchApi,
  getGermplasmImportBatchInfoApi,
  getGermplasmImportBatchListApi,
  getGermplasmTaxonomyOptionsApi,
} from './api';

defineOptions({ name: 'GermplasmImportBatchPage' });

const router = useRouter();

const loading = ref(false);
const detailLoading = ref(false);
const items = ref<GermplasmImportBatchItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);
const keyword = ref('');
const status = ref<string | undefined>(undefined);
const taxonomyTaxId = ref<number | undefined>(undefined);
const taxonomyOptions = ref<Array<{ label: string; value: number }>>([]);

const drawerOpen = ref(false);
const currentDetail = ref<GermplasmImportBatchDetail | null>(null);

async function loadTaxonomyOptions() {
  const response = await getGermplasmTaxonomyOptionsApi({
    limit: 100,
    active_only: 1,
  });
  const records =
    (response as any)?.items ?? (response as any)?.data?.items ?? [];
  taxonomyOptions.value = records.map((item: any) => ({
    label: item.common_name
      ? `${item.scientific_name} (${item.common_name})`
      : item.scientific_name,
    value: item.tax_id,
  }));
}

async function loadBatches() {
  loading.value = true;
  try {
    const response = await getGermplasmImportBatchListApi({
      page: page.value,
      size: pageSize.value,
      taxonomy_tax_id: taxonomyTaxId.value,
      status: status.value,
      keyword: keyword.value || undefined,
    });
    items.value = (response as any)?.items ?? [];
    total.value = (response as any)?.total ?? 0;
  } finally {
    loading.value = false;
  }
}

async function openBatchDetail(record: GermplasmImportBatchItem) {
  drawerOpen.value = true;
  detailLoading.value = true;
  currentDetail.value = null;
  try {
    const response = await getGermplasmImportBatchInfoApi({ id: record.id });
    currentDetail.value = response as any;
  } finally {
    detailLoading.value = false;
  }
}

function confirmDeleteBatch(record: GermplasmImportBatchItem) {
  Modal.confirm({
    title: $t('germplasm.batch.deleteConfirmTitle'),
    content: $t('germplasm.batch.deleteConfirmContent'),
    okText: $t('germplasm.batch.confirmDelete'),
    okButtonProps: { danger: true },
    cancelText: $t('germplasm.batch.cancel'),
    async onOk() {
      const result = await deleteGermplasmImportBatchApi({ id: record.id });
      message.success(
        $t('germplasm.batch.deleteSuccess', { batchCode: result.batch_code, count: result.deleted_germplasm_count }),
      );
      if (currentDetail.value?.id === record.id) {
        currentDetail.value = {
          ...currentDetail.value,
          status: result.status,
        };
      }
      await loadBatches();
    },
  });
}

function gotoBatchRecords(record: GermplasmImportBatchItem) {
  router.push({
    path: '/germplasm/list',
    query: {
      taxonomy_tax_id: String(record.taxonomy_tax_id),
      batch_id: String(record.id),
    },
  });
}

const batchColumns = [
  { title: $t('germplasm.batch.batchCode'), dataIndex: 'batch_code', key: 'batch_code', width: 220 },
  {
    title: $t('germplasm.batch.template'),
    dataIndex: 'template_profile',
    key: 'template_profile',
    width: 180,
  },
  {
    title: $t('germplasm.batch.species'),
    dataIndex: ['taxonomy', 'scientific_name'],
    key: 'taxonomy_name',
    width: 220,
  },
  {
    title: $t('germplasm.batch.fileName'),
    dataIndex: 'source_filename',
    key: 'source_filename',
    width: 240,
  },
  { title: $t('germplasm.batch.validRows'), dataIndex: 'valid_rows', key: 'valid_rows', width: 90 },
  { title: $t('germplasm.batch.errorRows'), dataIndex: 'error_rows', key: 'error_rows', width: 90 },
  { title: $t('germplasm.batch.warningRows'), dataIndex: 'warning_rows', key: 'warning_rows', width: 90 },
  { title: $t('germplasm.batch.status'), dataIndex: 'status', key: 'status', width: 110 },
  { title: $t('germplasm.batch.importTime'), dataIndex: 'created_at', key: 'created_at', width: 200 },
];

const issueColumns = [
  { title: $t('germplasm.import.rowNo'), dataIndex: 'row_no', key: 'row_no', width: 90 },
  { title: $t('germplasm.import.columnName'), dataIndex: 'column_name', key: 'column_name', width: 140 },
  { title: $t('germplasm.import.issueType'), dataIndex: 'error_code', key: 'error_code', width: 180 },
  { title: $t('germplasm.import.description'), dataIndex: 'message', key: 'message' },
];
const fieldSchemaColumns = [
  { title: $t('germplasm.import.fieldName'), dataIndex: 'field_label', key: 'field_label', width: 160 },
  {
    title: $t('germplasm.import.sourceColumn'),
    dataIndex: 'source_header',
    key: 'source_header',
    width: 160,
  },
  { title: $t('germplasm.import.systemKey'), dataIndex: 'field_key', key: 'field_key', width: 180 },
  { title: $t('germplasm.import.type'), dataIndex: 'data_type', key: 'data_type', width: 100 },
  { title: $t('germplasm.batch.builtin'), dataIndex: 'is_builtin', key: 'is_builtin', width: 100 },
];

const errorRows = computed(
  () => currentDetail.value?.validation_report?.errors || [],
);
const warningRows = computed(
  () => currentDetail.value?.validation_report?.warnings || [],
);
const fieldSchemaRows = computed(() => currentDetail.value?.field_schema || []);

function fieldSchemaRowKey(record: GermplasmFieldSchemaItem) {
  return `${record.field_key}-${record.source_header}`;
}

onMounted(async () => {
  await loadTaxonomyOptions();
  await loadBatches();
});
</script>

<template>
  <Page auto-content-height content-class="p-5">
    <div class="batch-page">
      <Card :bordered="false" class="hero-card">
        <template #extra>
          <Space>
            <Button @click="router.push('/germplasm/import')">
              {{ $t('germplasm.batch.importGermplasm') }}
            </Button>
            <Button type="primary" @click="loadBatches">{{ $t('germplasm.batch.refresh') }}</Button>
          </Space>
        </template>
        <div class="hero-eyebrow">{{ $t('germplasm.batch.heroEyebrow') }}</div>
        <h2 class="hero-title">{{ $t('germplasm.batch.title') }}</h2>
        <p class="hero-description">
          {{ $t('germplasm.batch.description') }}
        </p>
      </Card>

      <Card :bordered="false">
        <div class="toolbar">
          <Select
            v-model:value="taxonomyTaxId"
            allow-clear
            style="width: 260px"
            :placeholder="$t('germplasm.batch.placeholderSpecies')"
            :options="taxonomyOptions"
            @change="loadBatches"
          />
          <Select
            v-model:value="status"
            allow-clear
            style="width: 180px"
            :placeholder="$t('germplasm.batch.placeholderStatus')"
            :options="[
              { label: 'validated', value: 'validated' },
              { label: 'imported', value: 'imported' },
              { label: 'invalid', value: 'invalid' },
              { label: 'deleted', value: 'deleted' },
            ]"
            @change="loadBatches"
          />
          <Input
            v-model:value="keyword"
            allow-clear
            :placeholder="$t('germplasm.batch.placeholderSearch')"
            style="width: 320px"
            @press-enter="loadBatches"
          />
          <Button @click="loadBatches">{{ $t('germplasm.batch.query') }}</Button>
        </div>

        <Table
          :columns="batchColumns"
          :data-source="items"
          :loading="loading"
          row-key="id"
          :pagination="{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            onChange: (nextPage: number, nextPageSize: number) => {
              page = nextPage;
              pageSize = nextPageSize;
              loadBatches();
            },
          }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <Tag
                :color="
                  record.status === 'imported'
                    ? 'green'
                    : record.status === 'deleted'
                      ? 'default'
                      : record.status === 'invalid'
                        ? 'red'
                        : 'blue'
                "
              >
                {{ record.status }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'created_at'">
              {{ record.created_at || '-' }}
            </template>
          </template>
          <template #expandedRowRender="{ record }">
            <div class="row-actions">
              <Button size="small" @click="openBatchDetail(record)">
                {{ $t('germplasm.batch.viewDetail') }}
              </Button>
              <Button
                size="small"
                type="primary"
                ghost
                @click="gotoBatchRecords(record)"
              >
                {{ $t('germplasm.batch.viewBatchGermplasm') }}
              </Button>
              <Button
                v-if="record.status !== 'deleted'"
                size="small"
                danger
                @click="confirmDeleteBatch(record)"
              >
                {{ $t('germplasm.batch.deleteBatchData') }}
              </Button>
            </div>
          </template>
        </Table>
      </Card>

      <Drawer v-model:open="drawerOpen" :title="$t('germplasm.batch.detailDrawerTitle')" width="720">
        <template v-if="currentDetail">
          <Descriptions bordered :column="1" size="small">
            <Descriptions.Item :label="$t('germplasm.batch.batchCode')">
              {{ currentDetail.batch_code }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('germplasm.batch.template')">
              {{ currentDetail.template_profile }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('germplasm.batch.species')">
              {{ currentDetail.taxonomy?.scientific_name || '-' }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('germplasm.batch.fileName')">
              {{ currentDetail.source_filename || '-' }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('germplasm.batch.status')">
              {{ currentDetail.status }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('germplasm.batch.rowStats')">
              {{ $t('germplasm.batch.total') }} {{ currentDetail.total_rows }} /
              {{ $t('germplasm.batch.valid') }} {{ currentDetail.valid_rows }} /
              {{ $t('germplasm.batch.error') }} {{ currentDetail.error_rows }} /
              {{ $t('germplasm.batch.warning') }} {{ currentDetail.warning_rows }}
            </Descriptions.Item>
          </Descriptions>

          <Card :bordered="false" :title="$t('germplasm.batch.errorDetail')" class="mt-4">
            <Table
              size="small"
              :columns="fieldSchemaColumns"
              :data-source="fieldSchemaRows"
              :pagination="false"
              :row-key="fieldSchemaRowKey"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'is_builtin'">
                  <Tag :color="record.is_builtin ? 'blue' : 'gold'">
                    {{ record.is_builtin ? $t('germplasm.batch.fixedField') : $t('germplasm.batch.dynamicField') }}
                  </Tag>
                </template>
              </template>
            </Table>
          </Card>

          <Card :bordered="false" :title="$t('germplasm.batch.errorDetail')" class="mt-4">
            <Table
              size="small"
              :columns="issueColumns"
              :data-source="errorRows"
              :pagination="{ pageSize: 5 }"
              row-key="message"
            />
          </Card>

          <Card :bordered="false" :title="$t('germplasm.batch.warningDetail')" class="mt-4">
            <Table
              size="small"
              :columns="issueColumns"
              :data-source="warningRows"
              :pagination="{ pageSize: 5 }"
              row-key="message"
            />
          </Card>
        </template>
        <Empty v-else-if="!detailLoading" :description="$t('germplasm.batch.noDetail')" />
      </Drawer>
    </div>
  </Page>
</template>

<style scoped lang="less">
.batch-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero-card {
  background:
    radial-gradient(
      circle at top right,
      rgba(22, 119, 255, 0.12),
      transparent 34%
    ),
    linear-gradient(135deg, #f8fbff 0%, #f6f8fc 100%);
}

.hero-eyebrow {
  color: #1677ff;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-title {
  margin: 8px 0;
  color: #13213a;
  font-size: 28px;
  font-weight: 700;
}

.hero-description {
  max-width: 860px;
  margin: 0;
  color: #516074;
  line-height: 1.7;
}

.toolbar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.row-actions {
  display: flex;
  gap: 12px;
}
</style>
