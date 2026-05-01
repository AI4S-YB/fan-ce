<script setup lang="ts">
import { ref, computed } from 'vue';
import {
  Button, Space, Tag, Select, Input, Modal, Empty, message,
} from 'ant-design-vue';
import { getDatasetOptionsApi, getDatasetVersionListApi } from '#/api/apps/dataset';
import { $t } from '@vben/locales';
import type {
  DatasetVersionDetail,
  DatasetLineageItem,
  DatasetItem,
  DatasetVersionItem,
} from '#/api/apps/dataset';
import {
  useDataset,
  RELATION_TYPE_OPTIONS,
  getLineageRelationColor,
  getLineageRelationLabel,
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
    message.success($t('dataset.list.lineageRelationCreated'));
    lineageCreateVisible.value = false;
    emit('refresh');
  } finally {
    lineageCreateLoading.value = false;
  }
}

async function handleDeleteLineage(record: DatasetLineageItem) {
  await deleteLineage(record.id);
  message.success($t('dataset.list.lineageRelationDeleted'));
  emit('refresh');
}

function getPerspective(record: DatasetLineageItem) {
  if (record.src_version_id === props.versionId) return $t('dataset.list.asSource');
  return $t('dataset.list.asTarget');
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
      <Button type="primary" ghost @click="openLineageCreate">{{ $t('dataset.list.newLineage') }}</Button>
    </div>

    <div v-if="loading" style="text-align: center; padding: 40px;">{{ $t('dataset.list.loading') }}</div>
    <Empty v-else-if="!lineageRecords.length" :description="$t('dataset.list.noLineageRelation')" />

    <div v-for="item in lineageRecords" :key="item.id" style="border: 1px solid #e0e0e0; border-radius: 4px; padding: 8px; margin-bottom: 6px; background: #fff;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <Space size="small">
          <Tag :color="getLineageRelationColor(item.relation_type)">
            {{ getLineageRelationLabel(item.relation_type) }}
          </Tag>
          <Tag>{{ getPerspective(item as DatasetLineageItem) }}</Tag>
          <span style="font-size: 12px;">{{ getCounterpartLabel(item as DatasetLineageItem) }}</span>
        </Space>
        <Button type="link" size="small" danger @click="handleDeleteLineage(item as DatasetLineageItem)">{{ $t('dataset.list.delete') }}</Button>
      </div>
    </div>

    <!-- Create Lineage Modal -->
    <Modal
      v-model:open="lineageCreateVisible"
      :title="$t('dataset.list.newLineageRelation')"
      :confirm-loading="lineageCreateLoading"
      @ok="submitLineage"
    >
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <Select
          v-model:value="lineageForm.dst_dataset_id"
          :options="targetDatasetOptions"
          :placeholder="$t('dataset.list.targetDataset')"
          @change="(v: number) => onTargetDatasetChange(v)"
        />
        <Select
          v-model:value="lineageForm.dst_version_id"
          :options="targetVersionOptions"
          :placeholder="$t('dataset.list.targetVersion')"
          :disabled="!lineageForm.dst_dataset_id"
        />
        <Select v-model:value="lineageForm.relation_type" :options="RELATION_TYPE_OPTIONS" :placeholder="$t('dataset.list.relationType')" />
        <Input v-model:value="lineageForm.detail_json" allow-clear :placeholder="$t('dataset.list.detailJsonOptional')" />
      </div>
    </Modal>
  </div>
</template>
