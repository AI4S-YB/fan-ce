<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { Button, Card, Descriptions, Drawer, Empty, Input, Modal, Select, Space, Table, Tag } from 'ant-design-vue';

import { requestClient } from '#/api/request';
import { getAssetFileTypeOptionsApi, getAssetTypeOptionsApi } from '#/api/apps/dataset';
import { useMessage } from '#/hooks/web/useMessage';
import { $t } from '@vben/locales';

defineOptions({ name: 'DatasetRegistrationCandidatePage' });

interface CandidateFileStagingItem {
  id?: number;
  file_name?: string;
  relative_path?: string;
  local_path?: string | null;
  file_format?: string;
  dataset_type?: string;
  stage_status?: string;
}

interface CandidateFileItem {
  id: number;
  staging_file_id?: number | null;
  source_role?: string | null;
  asset_type?: string | null;
  asset_file_type_code?: string | null;
  file_role?: string | null;
  is_primary?: boolean;
  is_required?: boolean;
  validation_status?: string | null;
  confidence?: number | null;
  origin_type?: string | null;
  sort_order?: number | null;
  staging_file?: CandidateFileStagingItem | null;
}

interface RegistryOptionItem {
  label: string;
  value: string;
  file_role?: string;
}

interface CandidateItem {
  id: number;
  candidate_code: string;
  scan_root_id?: number | null;
  dataset_type?: string | null;
  recipe_code?: string | null;
  registration_mode?: string | null;
  candidate_name?: string | null;
  version_name?: string | null;
  organism?: string | null;
  assembly?: string | null;
  reference_dataset_id?: number | null;
  reference_version_id?: number | null;
  status?: string | null;
  validation_status?: string | null;
  build_status?: string | null;
  registration_status?: string | null;
  source_kind?: string | null;
  meta_json?: string | null;
  registered_dataset_id?: number | null;
  registered_version_id?: number | null;
  registered_at?: number | null;
  create_time?: number | null;
  update_time?: number | null;
  items?: CandidateFileItem[];
}

const { createMessage } = useMessage();
const router = useRouter();

const loading = ref(false);
const detailLoading = ref(false);
const detailVisible = ref(false);
const registerSubmittingId = ref<null | number>(null);
const fileMappingVisible = ref(false);
const fileMappingLoading = ref(false);
const mappingOptionLoading = ref(false);
const editingCandidateFile = ref<CandidateFileItem | null>(null);
const assetTypeOptions = ref<RegistryOptionItem[]>([]);
const assetFileTypeOptions = ref<RegistryOptionItem[]>([]);
const rows = ref<CandidateItem[]>([]);
const currentDetail = ref<CandidateItem | null>(null);

const filters = reactive({
  keyword: '',
  dataset_type: undefined as string | undefined,
  registration_mode: undefined as string | undefined,
  status: undefined as string | undefined,
});

const DATASET_TYPE_OPTIONS = [
  { label: $t('dataset.staging.type_genome'), value: 'genome' },
  { label: $t('dataset.staging.type_transcriptome'), value: 'transcriptome' },
  { label: $t('dataset.staging.type_variome'), value: 'variome' },
  { label: $t('dataset.staging.type_phenome'), value: 'phenome' },
  { label: $t('dataset.staging.type_generic'), value: 'generic' },
];

const REGISTRATION_MODE_OPTIONS = [
  { label: $t('dataset.candidate.prebuiltFile'), value: 'prebuilt' },
  { label: $t('dataset.candidate.recipeBuildMode'), value: 'recipe_build' },
  { label: $t('dataset.candidate.hybridMode'), value: 'hybrid' },
];

const STATUS_OPTIONS = [
  { label: $t('dataset.list.lifecycle_draft'), value: 'draft' },
  { label: $t('dataset.candidate.pendingValidate'), value: 'pending' },
  { label: $t('dataset.candidate.reviewing'), value: 'reviewing' },
  { label: $t('dataset.staging.ready'), value: 'ready' },
];

const draftCount = computed(
  () => rows.value.filter((item) => item.status === 'draft').length,
);
const prebuiltCount = computed(
  () => rows.value.filter((item) => item.registration_mode === 'prebuilt').length,
);

const fileMappingForm = reactive({
  asset_type: undefined as string | undefined,
  asset_file_type_code: undefined as string | undefined,
  file_role: undefined as string | undefined,
  is_primary: false,
  is_required: true,
});

const FILE_ROLE_OPTIONS = [
  { label: $t('dataset.candidate.primaryFile'), value: 'primary' },
  { label: $t('dataset.candidate.indexFile'), value: 'index' },
  { label: $t('dataset.candidate.derivedFile'), value: 'derived' },
  { label: $t('dataset.staging.metadata'), value: 'metadata' },
];

function formatTime(value?: null | number) {
  if (!value) {
    return '-';
  }
  const date = new Date(value * 1000);
  if (Number.isNaN(date.getTime())) {
    return '-';
  }
  return date.toLocaleString('zh-CN', { hour12: false });
}

function getErrorMessage(error: unknown) {
  const responseData = (error as any)?.response?.data ?? {};
  return (
    responseData?.msg ||
    responseData?.message ||
    (error instanceof Error ? error.message : '') ||
    $t('dataset.staging.requestFailed')
  );
}

async function loadCandidates() {
  loading.value = true;
  try {
    const result = await requestClient.post<{ dataList: CandidateItem[]; total: number }>(
      '/admin/dataset/candidate/list',
      {
        page: 1,
        size: 200,
        keyword: filters.keyword.trim() || undefined,
        dataset_type: filters.dataset_type,
        registration_mode: filters.registration_mode,
        status: filters.status,
      },
    );
    rows.value = result.dataList || [];
  } catch (error) {
    rows.value = [];
    createMessage.error(getErrorMessage(error) || $t('dataset.candidate.loadCandidateFailed'));
  } finally {
    loading.value = false;
  }
}

async function openDetail(record: CandidateItem | Record<string, any>) {
  const candidate = record as CandidateItem;
  detailLoading.value = true;
  detailVisible.value = true;
  try {
    currentDetail.value = await requestClient.post<CandidateItem>(
      '/admin/dataset/candidate/info',
      { id: candidate.id },
    );
  } catch (error) {
    currentDetail.value = null;
    createMessage.error(getErrorMessage(error) || $t('dataset.candidate.loadCandidateDetailFailed'));
  } finally {
    detailLoading.value = false;
  }
}

async function registerCandidate(record: CandidateItem | Record<string, any>) {
  const candidate = record as CandidateItem;
  if (candidate.registration_status === 'done') {
    return;
  }
  registerSubmittingId.value = candidate.id;
  try {
    await requestClient.post('/admin/dataset/candidate/register', { id: candidate.id });
    createMessage.success($t('dataset.candidate.registeredToCenter'));
    await loadCandidates();
    await openDetail(candidate);
  } catch (error) {
    createMessage.error(getErrorMessage(error) || $t('dataset.candidate.registerFailed'));
  } finally {
    registerSubmittingId.value = null;
  }
}

function openDatasetCenter() {
  void router.push('/apps/dataset');
}

async function loadAssetTypeOptions() {
  if (!currentDetail.value?.dataset_type) {
    assetTypeOptions.value = [];
    return;
  }
  assetTypeOptions.value = await getAssetTypeOptionsApi({
    dataset_type: currentDetail.value.dataset_type,
    active_only: true,
  });
}

async function loadAssetFileTypeOptions(assetType?: string) {
  if (!assetType) {
    assetFileTypeOptions.value = [];
    return;
  }
  assetFileTypeOptions.value = await getAssetFileTypeOptionsApi({
    asset_type: assetType,
    active_only: true,
  });
}

async function openFileMappingModal(record: CandidateFileItem | Record<string, any>) {
  const file = record as CandidateFileItem;
  if (!currentDetail.value || currentDetail.value.registration_status === 'done') {
    return;
  }
  editingCandidateFile.value = file;
  fileMappingForm.asset_type = file.asset_type || undefined;
  fileMappingForm.asset_file_type_code = file.asset_file_type_code || undefined;
  fileMappingForm.file_role = file.file_role || undefined;
  fileMappingForm.is_primary = Boolean(file.is_primary);
  fileMappingForm.is_required = file.is_required !== false;
  fileMappingVisible.value = true;
  mappingOptionLoading.value = true;
  try {
    await loadAssetTypeOptions();
    await loadAssetFileTypeOptions(fileMappingForm.asset_type);
  } catch (error) {
    createMessage.error(getErrorMessage(error) || $t('dataset.candidate.loadMappingFailed'));
  } finally {
    mappingOptionLoading.value = false;
  }
}

async function onAssetTypeChange(value: string) {
  fileMappingForm.asset_type = value;
  fileMappingForm.asset_file_type_code = undefined;
  await loadAssetFileTypeOptions(value);
}

function onAssetFileTypeChange(value: string) {
  fileMappingForm.asset_file_type_code = value;
  const matched = assetFileTypeOptions.value.find((item) => item.value === value);
  if (matched?.file_role) {
    fileMappingForm.file_role = matched.file_role;
  }
}

async function submitFileMapping() {
  if (!editingCandidateFile.value) {
    return;
  }
  fileMappingLoading.value = true;
  try {
    await requestClient.post('/admin/dataset/candidate/file/update', {
      id: editingCandidateFile.value.id,
      asset_type: fileMappingForm.asset_type,
      asset_file_type_code: fileMappingForm.asset_file_type_code,
      file_role: fileMappingForm.file_role,
      is_primary: fileMappingForm.is_primary,
      is_required: fileMappingForm.is_required,
    });
    createMessage.success($t('dataset.candidate.mappingUpdated'));
    fileMappingVisible.value = false;
    if (currentDetail.value) {
      await openDetail(currentDetail.value);
    }
    await loadCandidates();
  } catch (error) {
    createMessage.error(getErrorMessage(error) || $t('dataset.candidate.updateMappingFailed'));
  } finally {
    fileMappingLoading.value = false;
  }
}

const candidateColumns = [
  { title: $t('dataset.candidate.candidateName'), dataIndex: 'candidate_name', key: 'candidate_name', width: 220 },
  { title: $t('dataset.candidate.targetType'), dataIndex: 'dataset_type', key: 'dataset_type', width: 120 },
  { title: $t('dataset.candidate.registrationMode'), dataIndex: 'registration_mode', key: 'registration_mode', width: 130 },
  { title: $t('dataset.candidate.sourceKind'), dataIndex: 'source_kind', key: 'source_kind', width: 150 },
  { title: $t('dataset.list.status'), dataIndex: 'status', key: 'status', width: 110 },
  { title: $t('dataset.candidate.validationStatus'), dataIndex: 'validation_status', key: 'validation_status', width: 110 },
  { title: $t('page.auth.register'), dataIndex: 'registration_status', key: 'registration_status', width: 110 },
  { title: $t('dataset.candidate.versionNameCol'), dataIndex: 'version_name', key: 'version_name', width: 140 },
  { title: 'Dataset', dataIndex: 'registered_dataset_id', key: 'registered_dataset_id', width: 120 },
  { title: $t('dataset.candidate.updateTimeCol'), dataIndex: 'update_time', key: 'update_time', width: 180 },
  { title: $t('dataset.list.action'), key: 'actions', width: 220, fixed: 'right' as const },
];

const candidateFileColumns = [
  { title: $t('dataset.candidate.stagingFile'), key: 'staging_file', width: 200 },
  { title: $t('dataset.candidate.fileFormat'), key: 'file_format', width: 120 },
  { title: $t('dataset.candidate.targetAssetTypeCol'), dataIndex: 'asset_type', key: 'asset_type', width: 160 },
  { title: $t('dataset.candidate.targetFileTypeFull'), dataIndex: 'asset_file_type_code', key: 'asset_file_type_code', width: 180 },
  { title: $t('dataset.candidate.fileRole'), dataIndex: 'file_role', key: 'file_role', width: 120 },
  { title: $t('dataset.candidate.validationStatusCol'), dataIndex: 'validation_status', key: 'validation_status', width: 120 },
  { title: $t('dataset.staging.relativePath'), key: 'relative_path', ellipsis: true },
  { title: $t('dataset.list.action'), key: 'actions', width: 120 },
];

onMounted(() => {
  void loadCandidates();
});
</script>

<template>
  <Page auto-content-height class="dataset-candidate-page">
    <div class="hero-card">
      <div>
        <div class="hero-eyebrow">Registration Candidate</div>
        <h2 class="hero-title">{{ $t('dataset.candidate.title') }}</h2>
        <div class="hero-sub">
          {{ $t('dataset.candidate.descriptionText') }}
        </div>
      </div>
      <Space wrap>
        <Button @click="loadCandidates">{{ $t('common.redo') }}</Button>
      </Space>
    </div>

    <div class="summary-grid">
      <Card :bordered="false">
        <div class="summary-label">{{ $t('dataset.candidate.totalCandidates') }}</div>
        <div class="summary-value">{{ rows.length }}</div>
      </Card>
      <Card :bordered="false">
        <div class="summary-label">{{ $t('dataset.candidate.draftCandidates') }}</div>
        <div class="summary-value">{{ draftCount }}</div>
      </Card>
      <Card :bordered="false">
        <div class="summary-label">{{ $t('dataset.candidate.prebuiltMode') }}</div>
        <div class="summary-value">{{ prebuiltCount }}</div>
      </Card>
    </div>

    <Card :bordered="false" class="panel-card">
      <div class="toolbar">
        <Input
          v-model:value="filters.keyword"
          allow-clear
          :placeholder="$t('dataset.candidate.searchPlaceholderFull')"
          style="width: 280px"
          @press-enter="loadCandidates"
        />
        <Select
          v-model:value="filters.dataset_type"
          allow-clear
          :placeholder="$t('dataset.candidate.targetTypePlaceholder')"
          :options="DATASET_TYPE_OPTIONS"
          style="width: 160px"
        />
        <Select
          v-model:value="filters.registration_mode"
          allow-clear
          :placeholder="$t('dataset.candidate.registrationModePlaceholder')"
          :options="REGISTRATION_MODE_OPTIONS"
          style="width: 160px"
        />
        <Select
          v-model:value="filters.status"
          allow-clear
          :placeholder="$t('dataset.list.status')"
          :options="STATUS_OPTIONS"
          style="width: 140px"
        />
        <Button type="primary" @click="loadCandidates">{{ $t('dataset.list.query') }}</Button>
      </div>

      <Table
        :columns="candidateColumns"
        :data-source="rows"
        :loading="loading"
        :pagination="false"
        row-key="id"
        :scroll="{ x: 1400 }"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'candidate_name'">
            <div class="candidate-name">{{ record.candidate_name || '-' }}</div>
            <div class="candidate-code">{{ record.candidate_code }}</div>
          </template>
          <template v-else-if="column.key === 'dataset_type'">
            <Tag v-if="record.dataset_type" color="blue">{{ record.dataset_type }}</Tag>
            <span v-else>-</span>
          </template>
          <template v-else-if="column.key === 'registration_mode'">
            <Tag color="cyan">{{ record.registration_mode || '-' }}</Tag>
          </template>
          <template v-else-if="column.key === 'source_kind'">
            <Tag color="purple">{{ record.source_kind || '-' }}</Tag>
          </template>
          <template v-else-if="column.key === 'status'">
            <Tag :color="record.status === 'ready' ? 'green' : record.status === 'reviewing' ? 'gold' : 'default'">
              {{ record.status || '-' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'validation_status'">
            <Tag :color="record.validation_status === 'passed' ? 'green' : 'default'">
              {{ record.validation_status || '-' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'registration_status'">
            <Tag :color="record.registration_status === 'done' ? 'green' : 'default'">
              {{ record.registration_status || '-' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'registered_dataset_id'">
            <Tag v-if="record.registered_dataset_id" color="green">
              #{{ record.registered_dataset_id }}
            </Tag>
            <span v-else>-</span>
          </template>
          <template v-else-if="column.key === 'update_time'">
            {{ formatTime(record.update_time) }}
          </template>
          <template v-else-if="column.key === 'actions'">
            <Space wrap>
              <Button size="small" type="primary" @click="openDetail(record)">{{ $t('common.title.view') }}</Button>
              <Button
                size="small"
                :loading="registerSubmittingId === record.id"
                :disabled="record.registration_status === 'done'"
                @click="registerCandidate(record)"
              >
                {{ $t('dataset.candidate.registerFormally') }}
              </Button>
            </Space>
          </template>
        </template>
      </Table>

      <Empty
        v-if="!loading && rows.length === 0"
        :description=”$t('dataset.candidate.noCandidatesHintFull')”
      />
    </Card>

    <Drawer
      v-model:open="detailVisible"
      :title="$t('dataset.candidate.detailedTitle')"
      width="920"
      :destroy-on-close="false"
    >
      <div v-if="detailLoading" class="detail-placeholder">{{ $t('dataset.list.loading') }}</div>
      <template v-else-if="currentDetail">
        <Card :bordered="false" class="detail-card">
          <Descriptions :column="2" size="small" bordered>
            <Descriptions.Item :label="$t('dataset.candidate.candidateNameLabel')">
              {{ currentDetail.candidate_name || '-' }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('dataset.candidate.candidateCodeLabel')">
              {{ currentDetail.candidate_code }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('dataset.candidate.targetTypeLabel')">
              {{ currentDetail.dataset_type || '-' }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('dataset.candidate.registrationModeLabel')">
              {{ currentDetail.registration_mode || '-' }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('dataset.candidate.sourceKindLabel')">
              {{ currentDetail.source_kind || '-' }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('dataset.candidate.versionNameLabelFull')">
              {{ currentDetail.version_name || '-' }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('geneset.list.species')">
              {{ currentDetail.organism || '-' }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('dataset.candidate.assemblyVersionLabelFull')">
              {{ currentDetail.assembly || '-' }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('dataset.candidate.candidateStatusLabelFull')">
              {{ currentDetail.status || '-' }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('dataset.candidate.validationStatusLabelFull')">
              {{ currentDetail.validation_status || '-' }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('dataset.candidate.buildStatusLabel')">
              {{ currentDetail.build_status || '-' }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('dataset.candidate.registrationStatusLabelFull')">
              {{ currentDetail.registration_status || '-' }}
            </Descriptions.Item>
            <Descriptions.Item label="Dataset ID">
              {{ currentDetail.registered_dataset_id ? `#${currentDetail.registered_dataset_id}` : '-' }}
            </Descriptions.Item>
            <Descriptions.Item label="Version ID">
              {{ currentDetail.registered_version_id ? `#${currentDetail.registered_version_id}` : '-' }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('dataset.staging.registerTime')">
              {{ formatTime(currentDetail.registered_at) }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('system.menu.createTime')">
              {{ formatTime(currentDetail.create_time) }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('dataset.candidate.updateTimeLabelFull')">
              {{ formatTime(currentDetail.update_time) }}
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Card :bordered="false" class="detail-card">
          <template #title>{{ $t('dataset.registry.candidateFile') }}</template>
          <template #extra>
            <Button
              v-if="currentDetail.registered_dataset_id"
              size="small"
              type="primary"
              ghost
              @click="openDatasetCenter"
            >
              {{ $t('dataset.candidate.openDatasetCenterLink') }}
            </Button>
          </template>
          <Table
            :columns="candidateFileColumns"
            :data-source="currentDetail.items || []"
            :pagination="false"
            row-key="id"
            :scroll="{ x: 1200 }"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'staging_file'">
                <div class="candidate-name">{{ record.staging_file?.file_name || `#${record.staging_file_id}` }}</div>
                <div class="candidate-code">staging #{{ record.staging_file_id }}</div>
              </template>
              <template v-else-if="column.key === 'file_format'">
                {{ record.staging_file?.file_format || '-' }}
              </template>
              <template v-else-if="column.key === 'relative_path'">
                {{ record.staging_file?.relative_path || record.staging_file?.local_path || '-' }}
              </template>
            <template v-else-if="column.key === 'validation_status'">
              <Tag :color="record.validation_status === 'passed' ? 'green' : 'default'">
                {{ record.validation_status || '-' }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'actions'">
              <Button
                size="small"
                :disabled="currentDetail?.registration_status === 'done'"
                @click="openFileMappingModal(record)"
              >
                {{ $t('dataset.candidate.editMappingBtn') }}
              </Button>
            </template>
          </template>
        </Table>
        <Empty
          v-if="!(currentDetail.items || []).length"
          :description="$t('dataset.staging.noCandidateFiles')"
          />
        </Card>
      </template>
      <Empty v-else :description="$t('dataset.candidate.noCandidateDetailHint')" />
    </Drawer>

    <Modal
      v-model:open="fileMappingVisible"
      :title="$t('dataset.candidate.editFileMappingTitle')"
      :confirm-loading="fileMappingLoading"
      @ok="submitFileMapping"
    >
      <div class="mapping-form">
        <Select
          v-model:value="fileMappingForm.asset_type"
          :options="assetTypeOptions"
          :loading="mappingOptionLoading"
          :placeholder="$t('dataset.candidate.targetAssetTypePlaceholder')"
          @update:value="onAssetTypeChange"
        />
        <Select
          v-model:value="fileMappingForm.asset_file_type_code"
          allow-clear
          :options="assetFileTypeOptions"
          :loading="mappingOptionLoading"
          :placeholder="$t('dataset.candidate.targetFileTypePlaceholder')"
          @update:value="onAssetFileTypeChange"
        />
        <Select
          v-model:value="fileMappingForm.file_role"
          :options="FILE_ROLE_OPTIONS"
          :placeholder="$t('dataset.candidate.fileRolePlaceholder')"
        />
        <div class="mapping-flags">
          <label><input v-model="fileMappingForm.is_primary" type="checkbox" />>{{ $t('dataset.candidate.asPrimaryFile') }}</label>
          <label><input v-model="fileMappingForm.is_required" type="checkbox" /> {{ $t('dataset.registry.requiredFile') }}</label>
        </div>
      </div>
    </Modal>
  </Page>
</template>

<style scoped>
.dataset-candidate-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero-card,
.panel-card,
.detail-card {
  border: 1px solid rgb(226 232 240);
  border-radius: 16px;
  background: #fff;
}

.hero-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 24px;
  background:
    radial-gradient(circle at top right, rgb(14 165 233 / 12%), transparent 30%),
    linear-gradient(135deg, #f8fcff 0%, #fff 100%);
}

.hero-eyebrow {
  color: rgb(2 132 199);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-title {
  margin: 8px 0;
  color: rgb(15 23 42);
  font-size: 28px;
  font-weight: 700;
}

.hero-sub {
  max-width: 820px;
  color: rgb(100 116 139);
  line-height: 1.8;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.summary-label {
  color: rgb(100 116 139);
  font-size: 12px;
}

.summary-value {
  margin-top: 8px;
  color: rgb(15 23 42);
  font-size: 28px;
  font-weight: 700;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.candidate-name {
  color: rgb(15 23 42);
  font-weight: 600;
}

.candidate-code {
  color: rgb(100 116 139);
  font-size: 12px;
}

.detail-card + .detail-card {
  margin-top: 16px;
}

.detail-placeholder {
  color: rgb(100 116 139);
}

.mapping-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mapping-flags {
  display: flex;
  gap: 16px;
  color: rgb(51 65 85);
  font-size: 13px;
}
</style>
