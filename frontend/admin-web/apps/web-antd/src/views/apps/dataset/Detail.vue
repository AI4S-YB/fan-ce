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
      const parsed = raw ? (typeof raw === 'string' ? JSON.parse(raw) : raw) : {};
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

      <!-- Section: Description (Markdown) -->
      <div style="margin-bottom: 20px;">
        <h3>{{ $t('dataset.detail.descriptionMd') }}</h3>
        <Input.TextArea
          v-model:value="descriptionMd"
          :placeholder="$t('dataset.detail.descriptionMdPlaceholder')"
          :auto-size="{ minRows: 6, maxRows: 20 }"
        />
      </div>

      <!-- Section: Structured Attributes (extra_json) -->
      <div style="margin-bottom: 20px;">
        <h3>{{ $t('dataset.detail.extraJson') }}</h3>
        <p style="font-size:12px;color:#888;margin-bottom:8px;">{{ $t('dataset.detail.extraJsonHint') }}</p>
        <div v-if="extraJsonFields.length === 0" style="color:#bbb;font-size:13px;margin-bottom:8px;">
          {{ $t('dataset.detail.extraJsonEmpty') }}
        </div>
        <div
          v-for="(field, index) in extraJsonFields"
          :key="index"
          style="display:flex;gap:8px;align-items:center;margin-bottom:6px;"
        >
          <Input
            v-model:value="field.key"
            :placeholder="$t('dataset.detail.extraJsonKeyPlaceholder')"
            style="width:180px;"
            size="small"
            @blur="onExtraFieldChange"
          />
          <Input
            v-model:value="field.value"
            :placeholder="$t('dataset.detail.extraJsonValuePlaceholder')"
            style="flex:1;"
            size="small"
            @blur="onExtraFieldChange"
          />
          <Button size="small" danger type="text" @click="removeExtraField(index)">
            ✕
          </Button>
        </div>
        <Button size="small" type="dashed" @click="addExtraField" style="margin-top:4px;">
          + {{ $t('dataset.detail.extraJsonAddField') }}
        </Button>
      </div>

      <!-- Section 3: Version Table -->
      <div style="margin-bottom: 20px;">
        <h3>{{ $t('dataset.list.versionManage') }}</h3>
        <VersionTable
          :version-data="versionListData"
          :active-version-id="activeVersionId"
          :action-loading-key="actionLoadingKey"
          @select="handleSelectVersion"
          @activate="handleActivate"
          @refresh="loadAll"
        />
      </div>

      <!-- Section 4 & 5: Assets & Lineage (side-by-side) -->
      <div v-if="activeVersionId" style="display: flex; gap: 16px;">
        <div style="flex: 1;">
          <h3>{{ $t('dataset.list.asset') }}</h3>
          <AssetPanel
            :version-detail="versionDetailData"
            :loading="versionDetailLoading"
            @refresh="selectVersion(activeVersionId!)"
          />
        </div>
        <div style="flex: 1;">
          <h3>{{ $t('dataset.list.lineage') }}</h3>
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
        <summary>{{ $t('dataset.list.publishHistory', { count: publishRecords.length }) }}</summary>
        <table style="width: 100%; border-collapse: collapse; margin-top: 8px;">
          <thead>
          <tr style="background: #f5f5f5;">
            <th style="padding: 4px 8px; text-align: left; border: 1px solid #e0e0e0;">{{ $t('dataset.list.time') }}</th>
            <th style="padding: 4px 8px; text-align: left; border: 1px solid #e0e0e0;">{{ $t('dataset.list.action2') }}</th>
            <th style="padding: 4px 8px; text-align: left; border: 1px solid #e0e0e0;">{{ $t('dataset.list.visibility') }}</th>
            <th style="padding: 4px 8px; text-align: left; border: 1px solid #e0e0e0;">{{ $t('dataset.list.lifecycleHeader') }}</th>
            <th style="padding: 4px 8px; text-align: left; border: 1px solid #e0e0e0;">{{ $t('dataset.list.remark2') }}</th>
          </tr>
          </thead>
          <tbody>
          <tr v-for="r in publishRecords" :key="r.id">
            <td style="padding: 3px 6px; border: 1px solid #e0e0e0;">{{ r.create_time ? new Date(r.create_time * 1000).toLocaleString('zh-CN') : '-' }}</td>
            <td style="padding: 3px 6px; border: 1px solid #e0e0e0;">{{ r.action || '-' }}</td>
            <td style="padding: 3px 6px; border: 1px solid #e0e0e0;">{{ r.visibility_before || '-' }} → {{ r.visibility_after || '-' }}</td>
            <td style="padding: 3px 6px; border: 1px solid #e0e0e0;">{{ r.lifecycle_before || '-' }} → {{ r.lifecycle_after || '-' }}</td>
            <td style="padding: 3px 6px; border: 1px solid #e0e0e0;">{{ r.note || '-' }}</td>
          </tr>
          </tbody>
        </table>
      </details>

      <!-- Section 7: System Info (collapsed) -->
      <details style="margin-top: 12px; font-size: 12px; color: #888;">
        <summary>{{ $t('dataset.list.systemInfo') }}</summary>
        <div style="display: flex; gap: 24px; margin-top: 8px;">
          <span>ID: {{ detailData.id }}</span>
          <span>Code: {{ detailData.dataset_code }}</span>
          <span>创建: {{ detailData.create_time ? new Date(detailData.create_time * 1000).toLocaleString('zh-CN') : '-' }}</span>
          <span>更新: {{ detailData.update_time ? new Date(detailData.update_time * 1000).toLocaleString('zh-CN') : '-' }}</span>
        </div>
      </details>

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
          <!-- Program selector -->
          <div>
            <label style="display: block; margin-bottom: 4px; font-weight: 500;">{{ $t('dataset.list.selectProgram') }}</label>
            <Select
              v-model:value="selectedProgramId"
              :options="programStore.programOptions"
              :placeholder="$t('dataset.list.selectProgramPlaceholder')"
              style="width: 100%;"
              :show-search="true"
              :filter-option="(input: string, option: any) => (option?.label || '').toLowerCase().includes(input.toLowerCase())"
            />
          </div>
          <!-- Instruction textarea -->
          <div>
            <label style="display: block; margin-bottom: 4px; font-weight: 500;">{{ $t('dataset.list.linkInstruction') }}</label>
            <Input.TextArea
              v-model:value="linkInstruction"
              :placeholder="$t('dataset.list.linkInstructionPlaceholder')"
              :rows="3"
            />
          </div>
          <!-- LLM preview button (disabled placeholder) -->
          <div>
            <Button block disabled @click="handleLlmPreview">{{ $t('dataset.list.llmPreview') }}</Button>
            <div style="font-size: 11px; color: #aaa; margin-top: 4px;">{{ $t('dataset.list.llmPreviewDisabled') }}</div>
          </div>
        </div>
      </Modal>
    </template>
    <div v-else style="text-align: center; padding: 80px; color: #888;">{{ $t('dataset.list.noDetail') }}</div>
  </Page>
</template>
