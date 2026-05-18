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
  getDatasetVersionListApi,
  publishDatasetApi,
  unpublishDatasetApi,
  transitionDatasetApi,
  updateDatasetApi,
  type DatasetItem,
  type DatasetKindOption,
} from '#/api/apps/dataset';
import { createBrdDatasetSubjectLinkApi } from '#/api/breeding/dataset-subject-link';
import { useProgramStore } from '#/store/modules/program';
import { useMessage } from '#/hooks/web/useMessage';
import { $t } from '@vben/locales';
import {
  lifecycleColor,
  visibilityColor,
  getPreferredDatasetTypeCode,
} from './composables/useDataset';
import { getGermplasmTaxonomyOptionsApi } from '../germplasm/api';

const { createConfirm, createMessage } = useMessage();
const router = useRouter();
const programStore = useProgramStore();

const loading = ref(false);
const rows = ref<DatasetItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);

// Organism edit
// Organism inline edit
const editingOrganismId = ref<number | null>(null);
const organismTaxId = ref<number | undefined>(undefined);
const organismOptions = ref<Array<{ label: string; value: number }>>([]);
const organismSaving = ref(false);

// Inline title editing
const editingTitleId = ref<number | null>(null);
const editingTitleText = ref('');
const editingTitleSaving = ref(false);

function startEditTitle(record: DatasetItem) {
  editingTitleId.value = record.id;
  editingTitleText.value = record.title || record.name || '';
}

async function saveEditTitle() {
  if (editingTitleId.value == null || !editingTitleText.value.trim()) return;
  editingTitleSaving.value = true;
  try {
    await updateDatasetApi({ id: editingTitleId.value, title: editingTitleText.value.trim() });
    createMessage.success('Title updated');
    editingTitleId.value = null;
    await loadDatasets();
  } catch (e: any) {
    createMessage.error(e?.message || 'Update failed');
  } finally {
    editingTitleSaving.value = false;
  }
}

async function searchTaxonomy(keyword: string) {
  if (!keyword || keyword.length < 2) { organismOptions.value = []; return; }
  const res = await getGermplasmTaxonomyOptionsApi({ keyword, limit: 15, active_only: 1 });
  const items = (res as any)?.items || (res as any)?.data?.items || [];
  organismOptions.value = items.map((item: any) => ({
    label: item.scientific_name || `tax_id: ${item.tax_id}`,
    value: item.tax_id,
  }));
}

function startEditOrganism(record: DatasetItem) {
  editingOrganismId.value = record.id;
  organismTaxId.value = (record as any).organism || undefined;
  organismOptions.value = [];
  if ((record as any).organism && (record as any).organism_name) {
    organismOptions.value = [{ label: (record as any).organism_name, value: (record as any).organism }];
  }
}

async function saveOrganism() {
  if (editingOrganismId.value == null || organismTaxId.value == null) return;
  organismSaving.value = true;
  try {
    await updateDatasetApi({ id: editingOrganismId.value, organism: organismTaxId.value });
    createMessage.success('Species updated');
    editingOrganismId.value = null;
    await loadDatasets();
  } catch (e: any) {
    createMessage.error(e?.message || 'Update failed');
  } finally {
    organismSaving.value = false;
  }
}

const kindOptions = ref<DatasetKindOption[]>([]);

const filters = reactive({
  name: '',
  dataset_type: undefined as string | undefined,
  lifecycle_state: undefined as string | undefined,
  visibility: undefined as string | undefined,
});

const lifecycleOptions = [
  { label: $t('dataset.list.lifecycle_draft'), value: 'draft' },
  { label: $t('dataset.list.lifecycle_ready'), value: 'ready' },
  { label: $t('dataset.list.lifecycle_archived'), value: 'archived' },
];

const visibilityOptions = [
  { label: $t('dataset.list.visibility_private'), value: 'private' },
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

async function handleArchive(record: DatasetItem) {
  const isArchived = record.lifecycle_state === 'archived';
  const target = isArchived ? 'ready' : 'archived';
  const actionLabel = isArchived ? $t('dataset.list.unarchive') : $t('dataset.list.archive');
  createConfirm({
    iconType: 'warning',
    title: `${actionLabel} Dataset`,
    content: $t('dataset.list.archiveConfirmParam', { name: record.title || record.name || String(record.id), action: actionLabel }),
    async onOk() {
      await transitionDatasetApi({ id: record.id, target_state: target });
      createMessage.success($t('dataset.list.actionSuccess', { action: actionLabel }));
      await loadDatasets();
    },
  });
}

// ── Program link modal state ──
const linkModalVisible = ref(false);
const selectedProgramId = ref<number | null>(null);
const linkInstruction = ref('');
const linkSubmitting = ref(false);
const linkDatasetId = ref<number | null>(null);
const linkVersionId = ref<number | null>(null);

async function openLinkModal(record: DatasetItem) {
  selectedProgramId.value = null;
  linkInstruction.value = '';
  linkDatasetId.value = record.id;
  linkVersionId.value = null;
  linkModalVisible.value = true;

  // Fetch program options and version info in parallel
  const promises: Promise<any>[] = [];
  if (!programStore.programOptions || programStore.programOptions.length === 0) {
    promises.push(programStore.fetchProgramOptions());
  }
  promises.push(
    getDatasetVersionListApi({ dataset_id: record.id }).then((res) => {
      const ver = res.current_version || res.items?.[0];
      if (ver) linkVersionId.value = ver.id;
    }).catch(() => {}),
  );
  await Promise.all(promises);
}

async function handleDirectLink() {
  if (!selectedProgramId.value) {
    createMessage.warning($t('dataset.list.selectProgramPlaceholder'));
    return;
  }
  if (!linkVersionId.value) {
    createMessage.warning('No version available for linking');
    return;
  }
  linkSubmitting.value = true;
  try {
    await createBrdDatasetSubjectLinkApi({
      dataset_id: linkDatasetId.value!,
      version_id: linkVersionId.value,
      program_id: selectedProgramId.value,
      role: 'manual_link',
      mapping_method: 'manual',
      mapping_status: 'matched',
      is_primary: 1,
      note: linkInstruction.value || undefined,
    });
    createMessage.success($t('dataset.list.linkSuccess'));
    linkModalVisible.value = false;
  } catch {
    createMessage.error($t('dataset.list.linkFailed'));
  } finally {
    linkSubmitting.value = false;
  }
}

function handleLlmPreview() {
  createMessage.info($t('dataset.list.llmPreviewDisabled'));
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
          <div v-if="editingTitleId !== (record as DatasetItem).id">
            <Space size="small">
              <span>{{ (record as DatasetItem).title || (record as DatasetItem).name || `dataset-${(record as DatasetItem).id}` }}</span>
              <Button size="small" type="text" @click="startEditTitle(record as DatasetItem)" title="Edit title">✏️</Button>
            </Space>
            <div style="font-size: 12px; color: #888;">{{ (record as DatasetItem).dataset_code || '-' }}</div>
          </div>
          <div v-else>
            <Input v-model:value="editingTitleText" style="width: 200px;" size="small" />
            <Space size="small" style="margin-top: 4px;">
              <Button size="small" type="primary" :loading="editingTitleSaving" @click="saveEditTitle">OK</Button>
              <Button size="small" @click="editingTitleId = null">Cancel</Button>
            </Space>
          </div>
        </template>
        <template v-else-if="column.key === 'dataset_type'">
          <Tag>{{ (record as any).dataset_kind?.name || getPreferredDatasetTypeCode((record as DatasetItem).dataset_type) }}</Tag>
        </template>
        <template v-else-if="column.key === 'organism'">
          <div v-if="editingOrganismId !== (record as DatasetItem).id">
            <Space size="small">
              <span>{{ (record as any).organism_name || '-' }}</span>
              <Tag v-if="(record as any).organism" color="default" style="font-size: 10px;">tax_id:{{ (record as any).organism }}</Tag>
              <Button size="small" type="text" @click="startEditOrganism(record as DatasetItem)" title="Edit species">✏️</Button>
            </Space>
          </div>
          <div v-else>
            <Select
              v-model:value="organismTaxId"
              show-search
              :filter-option="false"
              style="width: 260px;"
              size="small"
              placeholder="Search species name..."
              :options="organismOptions"
              @search="searchTaxonomy"
            />
            <Space size="small" style="margin-top: 4px;">
              <Button size="small" type="primary" :loading="organismSaving" @click="saveOrganism">OK</Button>
              <Button size="small" @click="editingOrganismId = null">Cancel</Button>
            </Space>
          </div>
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
            <Button type="link" @click="openLinkModal(record as DatasetItem)">{{ $t('dataset.list.linkToProgram') }}</Button>
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
            <Button
              v-if="(record as DatasetItem).lifecycle_state === 'archived'"
              type="link"
              @click="handleArchive(record as DatasetItem)"
            >
              {{ $t('dataset.list.unarchive') }}
            </Button>
            <Button
              v-else
              type="link"
              @click="handleArchive(record as DatasetItem)"
            >
              {{ $t('dataset.list.archive') }}
            </Button>
            <Button danger type="link" @click="handleDelete(record as DatasetItem)">{{ $t('dataset.list.delete') }}</Button>
          </Space>
        </template>
      </template>
    </Table>

    <!-- Link to Program Modal -->
    <Modal
      v-model:open="linkModalVisible"
      :title="$t('dataset.list.linkToProgramTitle')"
      :confirm-loading="linkSubmitting"
      @ok="handleDirectLink"
      :ok-text="$t('dataset.list.directLink')"
      :cancel-text="$t('common.cancelText')"
    >
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div>
          <label style="display: block; margin-bottom: 4px; font-weight: 500;">{{ $t('dataset.list.selectProgram') }}</label>
          <Select
            v-model:value="selectedProgramId"
            :options="programStore.programOptions"
            :placeholder="$t('dataset.list.selectProgramPlaceholder')"
            style="width: 100%;"
            show-search
            :filter-option="(input: string, option: any) => (option?.label || '').toLowerCase().includes(input.toLowerCase())"
          />
        </div>
        <div>
          <label style="display: block; margin-bottom: 4px; font-weight: 500;">{{ $t('dataset.list.linkInstruction') }}</label>
          <Input.TextArea
            v-model:value="linkInstruction"
            :placeholder="$t('dataset.list.linkInstructionPlaceholder')"
            :rows="3"
          />
        </div>
        <div>
          <Button block disabled @click="handleLlmPreview">{{ $t('dataset.list.llmPreview') }}</Button>
          <div style="font-size: 11px; color: #aaa; margin-top: 4px;">{{ $t('dataset.list.llmPreviewDisabled') }}</div>
        </div>
      </div>
    </Modal>
  </Page>
</template>
