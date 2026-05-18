<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDebounceFn } from '@vueuse/core';
import { Button, Tag, Space, Modal, Select, Input, message } from 'ant-design-vue';
import { Page } from '@vben/common-ui';
import { deleteDatasetApi, updateDatasetApi } from '#/api/apps/dataset';
import { createBrdDatasetSubjectLinkApi } from '#/api/breeding/dataset-subject-link';
import { useProgramStore } from '#/store/modules/program';
import VersionTable from './components/VersionTable.vue';
import AssetPanel from './components/AssetPanel.vue';
import LineagePanel from './components/LineagePanel.vue';
import { $t } from '@vben/locales';
import {
  useDataset,
  lifecycleColor,
  visibilityColor,
  getPreferredDatasetTypeCode,
  type DatasetVersionItem,
} from './composables/useDataset';

const route = useRoute();
const router = useRouter();

const {
  detailLoading, detailData, loadDetail,
  versionListLoading, versionListData, loadVersionList,
  versionDetailLoading, versionDetailData, loadVersionDetail,
  activateVersion, releaseVersion, withdrawVersion,
  loadPublishRecords, publishRecords,
} = useDataset();

const programStore = useProgramStore();

const datasetId = computed(() => Number(route.params.id));
const activeVersionId = ref<number | null>(null);
const actionLoadingKey = ref('');

// ── Program link modal state ──
const linkModalVisible = ref(false);
const selectedProgramId = ref<number | null>(null);
const linkInstruction = ref('');
const linkSubmitting = ref(false);

// Get the version_id for linking (current version or selected)
const currentLinkVersionId = computed(() =>
  versionListData.value?.current_version?.id ?? activeVersionId.value ?? undefined,
);

// Get the asset_id for linking (query_entry_asset or first asset)
const currentLinkAssetId = computed(() =>
  detailData.value?.query_entry_asset?.id ?? detailData.value?.assets?.[0]?.id ?? undefined,
);

// ── Program link handlers ──
async function openLinkModal() {
  selectedProgramId.value = null;
  linkInstruction.value = '';
  linkModalVisible.value = true;
  // lazy-fetch program options if not already loaded
  if (!programStore.programOptions || programStore.programOptions.length === 0) {
    await programStore.fetchProgramOptions();
  }
}

async function handleDirectLink() {
  if (!selectedProgramId.value) {
    message.warning($t('dataset.list.selectProgramPlaceholder'));
    return;
  }
  if (!currentLinkVersionId.value || !currentLinkAssetId.value) {
    message.warning('No version or asset available for linking');
    return;
  }
  linkSubmitting.value = true;
  try {
    await createBrdDatasetSubjectLinkApi({
      dataset_id: datasetId.value,
      version_id: currentLinkVersionId.value,
      asset_id: currentLinkAssetId.value,
      program_id: selectedProgramId.value,
      role: 'manual_link',
      mapping_method: 'manual',
      mapping_status: 'matched',
      is_primary: 1,
      note: linkInstruction.value || null,
    });
    message.success($t('dataset.list.linkSuccess'));
    linkModalVisible.value = false;
  } catch {
    message.error($t('dataset.list.linkFailed'));
  } finally {
    linkSubmitting.value = false;
  }
}

function handleLlmPreview() {
  message.info($t('dataset.list.llmPreviewDisabled'));
}

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
    message.success($t('dataset.list.versionActivated'));
    await loadAll();
  } finally {
    actionLoadingKey.value = '';
  }
}

async function handleRelease(version: DatasetVersionItem) {
  actionLoadingKey.value = `release-version-${version.id}`;
  try {
    await releaseVersion(version.id);
    message.success($t('dataset.list.versionPublished'));
    await loadAll();
  } finally {
    actionLoadingKey.value = '';
  }
}

async function handleWithdraw(version: DatasetVersionItem) {
  actionLoadingKey.value = `withdraw-version-${version.id}`;
  try {
    await withdrawVersion(version.id);
    message.success($t('dataset.list.versionRevoked'));
    await loadAll();
  } finally {
    actionLoadingKey.value = '';
  }
}

function handleDelete() {
  Modal.confirm({
    title: $t('dataset.list.delete') + ' Dataset',
    content: $t('dataset.list.deleteConfirmParam2', { name: detailData.value?.title || detailData.value?.dataset_code || String(datasetId.value) }),
    async onOk() {
      await deleteDatasetApi({ id: datasetId.value });
      message.success($t('dataset.list.datasetDeleted'));
      router.push('/dataset');
    },
  });
}


// ── description_md editor ──
const descriptionMd = ref('');
let descriptionMdInit = false;

// Initialize from loaded detail data (without triggering save)
watch(detailData, (data) => {
  if (data) {
    descriptionMdInit = true;
    descriptionMd.value = data.description_md || '';
    editableTitle.value = data.title || data.name || '';
    editableVersion.value = data.version || '';
  }
});

const debouncedSaveDescription = useDebounceFn(async (val: string) => {
  if (detailData.value) {
    await updateDatasetApi({ id: datasetId.value, description_md: val });
  }
}, 2000);

// Auto-save on change (skip the init-induced change)
watch(descriptionMd, (val) => {
  if (!descriptionMdInit) return;
  if (val === (detailData.value?.description_md || '')) return;
  debouncedSaveDescription(val);
});

// ── extra_json (structured attributes) editor ──
interface KvField { key: string; value: string }
const extraJsonFields = ref<KvField[]>([]);
let extraJsonInit = false;

const debouncedSaveExtraJson = useDebounceFn(async () => {
  if (!detailData.value) return;
  // Build JSON from fields, skip empty keys
  const obj: Record<string, string> = {};
  for (const f of extraJsonFields.value) {
    if (f.key.trim()) obj[f.key.trim()] = f.value;
  }
  const json = Object.keys(obj).length > 0 ? JSON.stringify(obj) : '';
  await updateDatasetApi({ id: datasetId.value, meta_json: json });
}, 2000);

function addExtraField() {
  extraJsonFields.value.push({ key: '', value: '' });
}
function removeExtraField(index: number) {
  extraJsonFields.value.splice(index, 1);
  debouncedSaveExtraJson();
}
function onExtraFieldChange() {
  debouncedSaveExtraJson();
}

// Initialize from loaded detail data
watch(detailData, (data) => {
  if (data) {
    extraJsonInit = true;
    try {
      const raw = data.meta_json;
      const parsed = raw
        ? (typeof raw === 'string' ? JSON.parse(raw) : raw)
        : {};
      const fields: KvField[] = [];
      for (const [key, value] of Object.entries(parsed)) {
        fields.push({ key, value: String(value) });
      }
      extraJsonFields.value = fields;
    } catch {
      extraJsonFields.value = [];
    }
  }
});

// ── Inline title / version editing ──
const editableTitle = ref('');
const editableVersion = ref('');

const debouncedSaveTitle = useDebounceFn(async (val: string) => {
  if (detailData.value && val !== (detailData.value.title || detailData.value.name || '')) {
    await updateDatasetApi({ id: datasetId.value, title: val });
  }
}, 1000);

const debouncedSaveVersion = useDebounceFn(async (val: string) => {
  if (detailData.value && val !== (detailData.value.version || '')) {
    await updateDatasetApi({ id: datasetId.value, version: val });
  }
}, 1000);

onMounted(() => loadAll());
</script>

<template>
  <Page auto-content-height>
    <div v-if="detailLoading" style="text-align: center; padding: 80px;">{{ $t('dataset.list.loading') }}</div>
    <template v-else-if="detailData">
      <!-- Section 1: Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
        <div style="flex:1">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">
            <span style="font-size:18px;font-weight:600;">{{ detailData.title || detailData.name || '-' }}</span>
            <Tag>{{ detailData.dataset_code || '-' }}</Tag>
          </div>
          <div style="color: #888; font-size: 13px;">
            <span>{{ (detailData as any).organism_name || detailData.organism || '-' }}</span>
            <span style="margin-left: 8px;">{{ getPreferredDatasetTypeCode(detailData.dataset_type) }}</span>
            <span style="margin-left: 8px;">{{ detailData.query_profile?.file_format || detailData.file_format || '-' }}</span>
          </div>
        </div>
        <Space>
          <Tag :color="lifecycleColor(detailData.lifecycle_state)">{{ detailData.lifecycle_state || '-' }}</Tag>
          <Tag :color="visibilityColor(detailData.visibility)">{{ detailData.visibility || '-' }}</Tag>
          <Button type="primary" ghost @click="openLinkModal">{{ $t('dataset.list.linkToProgram') }}</Button>
          <Button type="primary" ghost @click="router.push(`/dataset/${datasetId}/query`)">{{ $t('dataset.list.dataQuery') }}</Button>
          <Button danger @click="handleDelete">{{ $t('dataset.list.delete') }}</Button>
        </Space>
      </div>

      <!-- Section 2: Status Bar -->
      <div style="display: flex; gap: 24px; font-size: 13px; padding: 8px 12px; background: #fafafa; border-radius: 4px; margin-bottom: 16px; align-items: center;">
        <span>{{ $t('dataset.list.queryEntry') }}<strong>{{ detailData.query_entry_asset?.asset_code || $t('dataset.list.notConfigured') }}</strong></span>
        <span>{{ $t('dataset.list.currentVersion') }}：<strong>{{ versionListData?.current_version?.version || '-' }}</strong></span>
        <span style="display:flex;align-items:center;gap:4px;">{{ $t('dataset.detail.versionLabel') }}：<Input v-model:value="editableVersion" size="small" style="width:120px;" @blur="debouncedSaveVersion(editableVersion)" /></span>
      </div>

    </template>
  </Page>
</template>
