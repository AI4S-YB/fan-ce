<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Checkbox,
  Empty,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  deleteDatasetStagingApi,
  registerDatasetFromStagingApi,
  uploadDatasetStagingApi,
} from '#/api/apps/dataset';
import type { DirectoryTreeNode } from '#/api/apps/dataset';
import { requestClient } from '#/api/request';
import { useMessage } from '#/hooks/web/useMessage';
import DirectoryBrowser from './components/DirectoryBrowser.vue';
import RegisterConfirmModal from './components/RegisterConfirmModal.vue';
import { $t } from '@vben/locales';

defineOptions({ name: 'DatasetStagingScanPage' });

interface ScanRootItem {
  id: number;
  root_code: string;
  name: string;
  root_path: string;
  description?: string;
  scan_recursive?: boolean;
  include_hidden?: boolean;
  is_active?: boolean;
  auto_scan_enabled?: boolean;
  scan_interval_minutes?: number;
  last_scan_time?: null | number;
  next_scan_time?: null | number;
}

interface ScanJobItem {
  id: number;
  root_id: number;
  job_code: string;
  status: string;
  scanned_dir_count?: number;
  scanned_file_count?: number;
  staged_file_count?: number;
  skipped_file_count?: number;
  changed_file_count?: number;
  missing_file_count?: number;
  skipped_registered_count?: number;
  error_message?: null | string;
  started_at?: null | number;
  finished_at?: null | number;
}

interface StagingItem {
  id: number;
  source_name?: string;
  file_name?: string;
  local_path?: string;
  relative_path?: string;
  file_format?: string;
  file_size?: null | number;
  dataset_type?: string;
  source_mode?: string;
  stage_status?: string;
  linked_dataset_id?: null | number;
  scan_root_id?: null | number;
  last_seen_at?: null | number;
}

interface BrowseEntryItem {
  name: string;
  path: string;
  is_dir: boolean;
  modified_time?: null | number;
}

interface BrowseResult {
  browse_root: string;
  current_path: string;
  parent_path?: null | string;
  entries: BrowseEntryItem[];
}

const { createMessage } = useMessage();
const router = useRouter();

const rootsLoading = ref(false);
const jobsLoading = ref(false);
const stagingLoading = ref(false);

const rootRows = ref<ScanRootItem[]>([]);
const jobRows = ref<ScanJobItem[]>([]);
const stagingRows = ref<StagingItem[]>([]);
const selectedStagingRowKeys = ref<number[]>([]);

const rootModalVisible = ref(false);
const rootModalLoading = ref(false);
const rootEditMode = ref<'create' | 'update'>('create');
const editingRootId = ref<null | number>(null);
const browseModalVisible = ref(false);
const browseLoading = ref(false);
const browseRows = ref<BrowseEntryItem[]>([]);
const browseRootPath = ref('/');
const browseCurrentPath = ref('/');
const browseParentPath = ref<null | string>(null);

const rootForm = reactive({
  name: '',
  root_path: '',
  description: '',
  scan_recursive: true,
  include_hidden: false,
  is_active: true,
  auto_scan_enabled: false,
  scan_interval_minutes: 1440,
});

const candidateModalVisible = ref(false);
const candidateModalLoading = ref(false);
const uploadVisible = ref(false);
const uploadLoading = ref(false);
const uploadFile = ref<File | null>(null);
const registerVisible = ref(false);
const registerLoading = ref(false);
const candidateForm = reactive({
  candidate_name: '',
  dataset_type: 'generic',
  registration_mode: 'prebuilt',
  version_name: '',
  organism: '',
  assembly: '',
});
const uploadForm = reactive({
  dataset_type: undefined as string | undefined,
  meta_json: '',
});
const registerForm = reactive({
  id: 0,
  source_name: '',
  name: '',
  dataset_type: undefined as string | undefined,
  remark: '',
  is_public: false,
  keep_staging_file: true,
});

const registerModalVisible = ref(false);
const selectedBrowseFiles = ref<DirectoryTreeNode[]>([]);

const activeRootId = ref<null | number>(null);

const activeRoot = computed(
  () => rootRows.value.find((item) => item.id === activeRootId.value) || null,
);
const selectedStagingRows = computed(() =>
  stagingRows.value.filter((item) => selectedStagingRowKeys.value.includes(item.id)),
);
const selectedStagingCount = computed(() => selectedStagingRowKeys.value.length);

const DATASET_TYPE_OPTIONS = [
  { label: $t('dataset.staging.type_genome'), value: 'genome' },
  { label: $t('dataset.staging.type_transcriptome'), value: 'transcriptome' },
  { label: $t('dataset.staging.type_variome'), value: 'variome' },
  { label: $t('dataset.staging.type_phenome'), value: 'phenome' },
  { label: $t('dataset.staging.type_generic'), value: 'generic' },
];

const REGISTRATION_MODE_OPTIONS = [
  { label: $t('dataset.staging.prebuiltFileMode'), value: 'prebuilt' },
  { label: $t('dataset.staging.recipeBuild'), value: 'recipe_build' },
  { label: $t('dataset.staging.hybridMode'), value: 'hybrid' },
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

function formatFileSize(value?: null | number) {
  if (!value || value < 0) {
    return '-';
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let current = value;
  let index = 0;
  while (current >= 1024 && index < units.length - 1) {
    current /= 1024;
    index += 1;
  }
  return `${current.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatIntervalMinutes(value?: number) {
  const minutes = Number(value || 0);
  if (!minutes) {
    return '-';
  }
  if (minutes % 1440 === 0) {
    return $t('dataset.staging.daysUnit', { count: minutes / 1440 });
  }
  if (minutes % 60 === 0) {
    return $t('dataset.staging.hoursUnit', { count: minutes / 60 });
  }
  return $t('dataset.staging.minutesUnit', { count: minutes });
}

function resetRootForm() {
  editingRootId.value = null;
  rootForm.name = '';
  rootForm.root_path = '';
  rootForm.description = '';
  rootForm.scan_recursive = true;
  rootForm.include_hidden = false;
  rootForm.is_active = true;
  rootForm.auto_scan_enabled = false;
  rootForm.scan_interval_minutes = 1440;
}

function openCreateRootModal() {
  rootEditMode.value = 'create';
  resetRootForm();
  rootModalVisible.value = true;
}

function openUpdateRootModal(record: ScanRootItem | Record<string, any>) {
  const root = record as ScanRootItem;
  rootEditMode.value = 'update';
  editingRootId.value = root.id;
  rootForm.name = root.name || '';
  rootForm.root_path = root.root_path || '';
  rootForm.description = root.description || '';
  rootForm.scan_recursive = Boolean(root.scan_recursive);
  rootForm.include_hidden = Boolean(root.include_hidden);
  rootForm.is_active = Boolean(root.is_active);
  rootForm.auto_scan_enabled = Boolean(root.auto_scan_enabled);
  rootForm.scan_interval_minutes = Number(root.scan_interval_minutes || 1440);
  rootModalVisible.value = true;
}

async function loadBrowseDirectory(path?: null | string) {
  browseLoading.value = true;
  try {
    const result = await requestClient.post<BrowseResult>(
      '/admin/dataset/staging/scan-root/browse',
      { path: path || undefined },
    );
    browseRows.value = result.entries || [];
    browseRootPath.value = result.browse_root || '/';
    browseCurrentPath.value = result.current_path || '/';
    browseParentPath.value = result.parent_path || null;
  } catch (error: any) {
    createMessage.error(error?.message || $t('dataset.staging.loadDirFailed'));
  } finally {
    browseLoading.value = false;
  }
}

async function openBrowseModal() {
  browseModalVisible.value = true;
  await loadBrowseDirectory(rootForm.root_path || null);
}

async function openBrowseEntry(record: BrowseEntryItem | Record<string, any>) {
  const entry = record as BrowseEntryItem;
  await loadBrowseDirectory(entry.path);
}

async function browseParentDirectory() {
  if (!browseParentPath.value) {
    return;
  }
  await loadBrowseDirectory(browseParentPath.value);
}

function selectBrowseCurrentDirectory() {
  rootForm.root_path = browseCurrentPath.value;
  browseModalVisible.value = false;
}

async function loadRoots() {
  rootsLoading.value = true;
  try {
    const result = await requestClient.post<{
      dataList: ScanRootItem[];
      total: number;
    }>('/admin/dataset/staging/scan-root/list', { page: 1, size: 100 });
    rootRows.value = result.dataList || [];
    if (!activeRootId.value && rootRows.value.length > 0) {
      activeRootId.value = rootRows.value[0].id;
    }
  } catch (error: any) {
    rootRows.value = [];
    createMessage.error(error?.message || $t('dataset.staging.loadScanDirFailed'));
  } finally {
    rootsLoading.value = false;
  }
}

async function loadJobs() {
  jobsLoading.value = true;
  try {
    const result = await requestClient.post<{
      dataList: ScanJobItem[];
      total: number;
    }>('/admin/dataset/staging/scan-job/list', {
      page: 1,
      size: 20,
      root_id: activeRootId.value || undefined,
    });
    jobRows.value = result.dataList || [];
  } catch (error: any) {
    jobRows.value = [];
    createMessage.error(error?.message || $t('dataset.staging.loadScanTaskFailed'));
  } finally {
    jobsLoading.value = false;
  }
}

async function loadStagingRows() {
  stagingLoading.value = true;
  try {
    const result = await requestClient.post<{
      dataList: StagingItem[];
      total: number;
    }>('/admin/dataset/staging/list', {
      page: 1,
      size: 100,
    });
    stagingRows.value = result.dataList || [];
    selectedStagingRowKeys.value = selectedStagingRowKeys.value.filter((id) =>
      stagingRows.value.some((item) => item.id === id),
    );
  } catch (error: any) {
    stagingRows.value = [];
    selectedStagingRowKeys.value = [];
    createMessage.error(error?.message || $t('dataset.staging.loadStagedFilesFailed'));
  } finally {
    stagingLoading.value = false;
  }
}

async function reloadAll() {
  await loadRoots();
  await Promise.all([loadJobs(), loadStagingRows()]);
}

async function submitRootForm() {
  rootModalLoading.value = true;
  try {
    const payload = {
      name: rootForm.name.trim(),
      root_path: rootForm.root_path.trim(),
      description: rootForm.description.trim() || undefined,
      scan_recursive: rootForm.scan_recursive,
      include_hidden: rootForm.include_hidden,
      is_active: rootForm.is_active,
      auto_scan_enabled: rootForm.auto_scan_enabled,
      scan_interval_minutes: Number(rootForm.scan_interval_minutes || 1440),
    };
    if (!payload.name || !payload.root_path) {
      createMessage.error($t('dataset.staging.fillDirNameAndPath'));
      return;
    }
    if (rootEditMode.value === 'create') {
      await requestClient.post(
        '/admin/dataset/staging/scan-root/create',
        payload,
      );
      createMessage.success($t('dataset.staging.scanDirCreated'));
    } else {
      await requestClient.post('/admin/dataset/staging/scan-root/update', {
        id: editingRootId.value,
        ...payload,
      });
      createMessage.success($t('dataset.staging.scanDirUpdated'));
    }
    rootModalVisible.value = false;
    await reloadAll();
  } catch (error: any) {
    createMessage.error(error?.message || $t('dataset.staging.saveScanDirFailed'));
  } finally {
    rootModalLoading.value = false;
  }
}

async function deleteRoot(record: ScanRootItem | Record<string, any>) {
  const root = record as ScanRootItem;
  try {
    await requestClient.post('/admin/dataset/staging/scan-root/delete', {
      id: root.id,
    });
    if (activeRootId.value === root.id) {
      activeRootId.value = null;
    }
    createMessage.success($t('dataset.staging.scanDirDeletedMsg', { name: root.name }));
    await reloadAll();
  } catch (error: any) {
    createMessage.error(error?.message || $t('dataset.staging.deleteScanDirFailed'));
  }
}

async function runScan(record: ScanRootItem | Record<string, any>) {
  const root = record as ScanRootItem;
  const hideLoading = createMessage.loading($t('dataset.staging.scanWithName', { name: root.name }), 0);
  try {
    const result = await requestClient.post<{ job: ScanJobItem }>(
      '/admin/dataset/staging/scan/run',
      { root_id: root.id },
    );
    activeRootId.value = root.id;
    if (result.job?.status === 'success') {
      createMessage.success(
        $t('dataset.staging.scanCompletedDetail', {
          name: root.name,
          scanned: result.job.scanned_file_count ?? 0,
          staged: result.job.staged_file_count ?? 0,
          changed: result.job.changed_file_count ?? 0,
          missing: result.job.missing_file_count ?? 0,
        }),
      );
    } else if (result.job?.status === 'failed') {
      createMessage.error($t('dataset.staging.scanFailedDetail2', { name: root.name, error: result.job.error_message || $t('workspace.error.unknown') }));
    } else {
      createMessage.success($t('dataset.staging.scanComplete'));
    }
    await Promise.all([loadRoots(), loadJobs(), loadStagingRows()]);
  } catch (error: any) {
    createMessage.error(error?.message || $t('dataset.staging.executeScanFailed'));
  } finally {
    hideLoading();
  }
}

function stagingColor(value?: string) {
  switch (value) {
    case 'registered':
      return 'green';
    case 'consumed':
      return 'gold';
    case 'missing':
    case 'deleted':
      return 'red';
    default:
      return 'blue';
  }
}

function sourceModeLabel(value?: string) {
  return value === 'upload' ? $t('dataset.staging.upload') : value === 'server_scan' ? $t('dataset.staging.scan') : value || '-';
}

function openUploadModal() {
  uploadVisible.value = true;
  uploadFile.value = null;
  uploadForm.dataset_type = undefined;
  uploadForm.meta_json = '';
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  uploadFile.value = input.files?.[0] || null;
}

async function uploadStagingFile() {
  if (!uploadFile.value) {
    createMessage.warning($t('dataset.staging.noFileSelected'));
    return;
  }
  uploadLoading.value = true;
  try {
    const formData = new FormData();
    formData.append('file', uploadFile.value);
    if (uploadForm.dataset_type) {
      formData.append('dataset_type', uploadForm.dataset_type);
    }
    if (uploadForm.meta_json) {
      formData.append('meta_json', uploadForm.meta_json);
    }
    await uploadDatasetStagingApi(formData);
    uploadVisible.value = false;
    createMessage.success($t('dataset.staging.fileUploaded'));
    await loadStagingRows();
  } catch (error: any) {
    createMessage.error(error?.message || $t('dataset.staging.upload') + $t('common.errorText'));
  } finally {
    uploadLoading.value = false;
  }
}

function openRegisterModal(record: StagingItem) {
  registerVisible.value = true;
  registerForm.id = record.id;
  registerForm.source_name = record.source_name || record.file_name || '';
  registerForm.name = record.source_name || record.file_name || '';
  registerForm.dataset_type = record.dataset_type || undefined;
  registerForm.remark = '';
  registerForm.is_public = false;
  registerForm.keep_staging_file = true;
}

async function submitRegister() {
  registerLoading.value = true;
  try {
    await registerDatasetFromStagingApi({
      id: registerForm.id,
      name: registerForm.name || undefined,
      dataset_type: registerForm.dataset_type || undefined,
      remark: registerForm.remark || undefined,
      is_public: registerForm.is_public,
      keep_staging_file: registerForm.keep_staging_file,
    });
    registerVisible.value = false;
    createMessage.success($t('dataset.staging.registeredFromStaging'));
    await loadStagingRows();
  } catch (error: any) {
    createMessage.error(error?.message || $t('dataset.staging.registerFailed'));
  } finally {
    registerLoading.value = false;
  }
}

function openRegisterModalForFiles(nodes: DirectoryTreeNode[]) {
  if (!nodes.length) {
    createMessage.warning($t('dataset.staging.selectFileFirst'));
    return;
  }
  selectedBrowseFiles.value = nodes;
  registerModalVisible.value = true;
}

function onRegistered() {
  registerModalVisible.value = false;
  selectedBrowseFiles.value = [];
}

async function handleDeleteStaging(record: StagingItem) {
  try {
    await deleteDatasetStagingApi({ id: record.id });
    createMessage.success($t('dataset.staging.stagingFileDeleted'));
    await loadStagingRows();
  } catch (error: any) {
    createMessage.error(error?.message || $t('dataset.staging.deleteStagingFileFailed'));
  }
}

function inferCandidateDatasetType() {
  const datasetTypes = Array.from(
    new Set(
      selectedStagingRows.value
        .map((item) => item.dataset_type)
        .filter((item): item is string => Boolean(item)),
    ),
  );
  if (datasetTypes.length === 1) {
    return datasetTypes[0]!;
  }
  return 'generic';
}

function openCandidateModal() {
  if (!selectedStagingRowKeys.value.length) {
    createMessage.warning($t('dataset.staging.selectStagingFileFirst'));
    return;
  }
  const today = new Date().toISOString().slice(0, 10);
  candidateForm.candidate_name = `${activeRoot.value?.name || 'scan'}-${today}`;
  candidateForm.dataset_type = inferCandidateDatasetType();
  candidateForm.registration_mode = 'prebuilt';
  candidateForm.version_name = '';
  candidateForm.organism = '';
  candidateForm.assembly = '';
  candidateModalVisible.value = true;
}

async function submitCandidateForm() {
  if (!candidateForm.candidate_name.trim()) {
    createMessage.error($t('dataset.staging.fillCandidateName'));
    return;
  }
  if (!selectedStagingRowKeys.value.length) {
    createMessage.error($t('dataset.staging.noStagingFileToSubmit'));
    return;
  }
  candidateModalLoading.value = true;
  try {
    await requestClient.post('/admin/dataset/candidate/create', {
      candidate_name: candidateForm.candidate_name.trim(),
      dataset_type: candidateForm.dataset_type,
      registration_mode: candidateForm.registration_mode,
      version_name: candidateForm.version_name.trim() || undefined,
      organism: candidateForm.organism.trim() || undefined,
      assembly: candidateForm.assembly.trim() || undefined,
      scan_root_id: activeRootId.value || undefined,
      items: selectedStagingRows.value.map((item, index) => ({
        staging_file_id: item.id,
        is_primary: index === 0,
      })),
    });
    candidateModalVisible.value = false;
    createMessage.success($t('dataset.staging.candidateCreated'));
    selectedStagingRowKeys.value = [];
  } catch (error: any) {
    createMessage.error(error?.message || $t('dataset.staging.candidateCreateFailed'));
  } finally {
    candidateModalLoading.value = false;
  }
}

function openCandidatePage() {
  void router.push('/apps/dataset-candidate');
}

function selectRoot(record: ScanRootItem | Record<string, any>) {
  const root = record as ScanRootItem;
  activeRootId.value = root.id;
  selectedStagingRowKeys.value = [];
  void Promise.all([loadJobs(), loadStagingRows()]);
}

const rootColumns = [
  {
    title: $t('dataset.staging.dirName'),
    dataIndex: 'name',
    key: 'name',
    customRender: ({ record }: { record: ScanRootItem }) => {
      return record.name;
    },
  },
  {
    title: $t('dataset.staging.dirPathCol'),
    dataIndex: 'root_path',
    key: 'root_path',
    ellipsis: true,
  },
  {
    title: $t('dataset.staging.scanStrategy'),
    key: 'scan_rule',
    customRender: ({ record }: { record: ScanRootItem }) =>
      `${record.scan_recursive ? $t('dataset.staging.recursive') : $t('dataset.staging.singleLayer')} / ${
        record.include_hidden ? $t('dataset.staging.includeHidden') : $t('dataset.staging.skipHidden')
      }`,
  },
  {
    title: $t('dataset.staging.lastScan'),
    key: 'last_scan_time',
    customRender: ({ record }: { record: ScanRootItem }) =>
      formatTime(record.last_scan_time),
  },
  {
    title: $t('dataset.list.status'),
    key: 'is_active',
    customRender: ({ record }: { record: ScanRootItem }) =>
      record.is_active ? $t('system.user.enable') : $t('dataset.staging.disabled'),
  },
  {
    title: $t('dataset.staging.autoScan'),
    key: 'auto_scan',
    customRender: ({ record }: { record: ScanRootItem }) =>
      record.auto_scan_enabled
        ? `${$t('dataset.staging.autoScanEnabled')} / ${formatIntervalMinutes(record.scan_interval_minutes)}`
        : $t('component.modal.close'),
  },
  {
    title: $t('dataset.list.action'),
    key: 'actions',
    width: 220,
  },
];

const jobColumns = [
  { title: $t('dataset.staging.jobCode'), dataIndex: 'job_code', key: 'job_code', ellipsis: true },
  { title: $t('dataset.list.status'), dataIndex: 'status', key: 'status', width: 100 },
  {
    title: $t('dataset.staging.dirCount'),
    dataIndex: 'scanned_dir_count',
    key: 'scanned_dir_count',
    width: 90,
  },
  {
    title: $t('dataset.staging.fileCount'),
    dataIndex: 'scanned_file_count',
    key: 'scanned_file_count',
    width: 90,
  },
  {
    title: $t('dataset.staging.newStaged'),
    dataIndex: 'staged_file_count',
    key: 'staged_file_count',
    width: 100,
  },
  {
    title: $t('dataset.staging.changed'),
    dataIndex: 'changed_file_count',
    key: 'changed_file_count',
    width: 90,
  },
  {
    title: $t('dataset.staging.missing'),
    dataIndex: 'missing_file_count',
    key: 'missing_file_count',
    width: 90,
  },
  {
    title: $t('dataset.staging.registeredSkipped'),
    dataIndex: 'skipped_registered_count',
    key: 'skipped_registered_count',
    width: 110,
  },
  {
    title: $t('dataset.staging.alreadyExists'),
    dataIndex: 'skipped_file_count',
    key: 'skipped_file_count',
    width: 90,
  },
  {
    title: $t('dataset.staging.completeTime'),
    key: 'finished_at',
    customRender: ({ record }: { record: ScanJobItem }) =>
      formatTime(record.finished_at || record.started_at),
  },
];

const stagingColumns = [
  { title: $t('component.upload.fileName'), dataIndex: 'file_name', key: 'file_name', width: 220 },
  { title: $t('phenome.query.source'), dataIndex: 'source_mode', key: 'source_mode', width: 100 },
  {
    title: $t('dataset.staging.relativePath'),
    dataIndex: 'relative_path',
    key: 'relative_path',
    ellipsis: true,
  },
  { title: $t('dataset.staging.format'), dataIndex: 'file_format', key: 'file_format', width: 120 },
  {
    title: $t('dataset.staging.recommendedType'),
    dataIndex: 'dataset_type',
    key: 'dataset_type',
    width: 130,
  },
  {
    title: $t('dataset.staging.size'),
    key: 'file_size',
    customRender: ({ record }: { record: StagingItem }) =>
      formatFileSize(record.file_size),
  },
  {
    title: $t('dataset.staging.lastFound'),
    key: 'last_seen_at',
    customRender: ({ record }: { record: StagingItem }) =>
      formatTime(record.last_seen_at),
  },
  {
    title: $t('dataset.list.status'),
    dataIndex: 'stage_status',
    key: 'stage_status',
    width: 120,
  },
  {
    title: $t('dataset.staging.linkedDataset'),
    dataIndex: 'linked_dataset_id',
    key: 'linked_dataset_id',
    width: 120,
  },
  {
    title: $t('dataset.list.action'),
    key: 'actions',
    width: 220,
  },
];

const browseColumns = [
  {
    title: $t('dataset.staging.dirNameCol'),
    dataIndex: 'name',
    key: 'name',
  },
  {
    title: $t('dataset.staging.dirPathCol'),
    dataIndex: 'path',
    key: 'path',
    ellipsis: true,
  },
  {
    title: $t('dataset.staging.modifyTime'),
    key: 'modified_time',
    customRender: ({ record }: { record: BrowseEntryItem }) =>
      formatTime(record.modified_time),
  },
];

onMounted(() => {
  void reloadAll();
});

const stagingRowSelection = computed(() => ({
  selectedRowKeys: selectedStagingRowKeys.value,
  onChange: (keys: (number | string)[]) => {
    selectedStagingRowKeys.value = keys.map((item) => Number(item));
  },
}));
</script>

<template>
  <Page auto-content-height class="dataset-staging-page">
    <div class="hero-card">
      <div>
        <div class="hero-eyebrow">Server File Discovery</div>
        <h2 class="hero-title">{{ $t('dataset.staging.scanTitle') }}</h2>
        <div class="hero-sub">
          {{ $t('dataset.staging.description') }}
        </div>
      </div>
      <Space wrap>
        <Button @click="reloadAll">{{ $t('common.redo') }}</Button>
        <Button type="primary" ghost @click="openUploadModal">{{ $t('dataset.staging.uploadToStaging') }}</Button>
        <Button @click="openCandidatePage">{{ $t('dataset.staging.viewCandidates') }}</Button>
        <Button
          v-if="activeRoot"
          type="primary"
          ghost
          @click="runScan(activeRoot)"
        >
          {{ $t('dataset.staging.scanNowCurrentDir') }}
        </Button>
        <Button type="primary" @click="openCreateRootModal">
          {{ $t('dataset.staging.addScanDir') }}
        </Button>
      </Space>
    </div>

    <div class="summary-grid">
      <Card :bordered="false">
        <div class="summary-label">{{ $t('dataset.staging.scanDirLabel') }}</div>
        <div class="summary-value">{{ rootRows.length }}</div>
      </Card>
      <Card :bordered="false">
        <div class="summary-label">{{ $t('dataset.staging.recentJobs') }}</div>
        <div class="summary-value">{{ jobRows.length }}</div>
      </Card>
      <Card :bordered="false">
        <div class="summary-label">{{ $t('dataset.staging.stagedFiles') }}</div>
        <div class="summary-value">{{ stagingRows.length }}</div>
      </Card>
    </div>

    <div class="layout-grid">
      <Card :bordered="false" class="panel-card">
        <template #title>{{ $t('dataset.staging.scanDirectories') }}</template>
        <Table
          :columns="rootColumns"
          :data-source="rootRows"
          :loading="rootsLoading"
          :pagination="false"
          row-key="id"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'">
              <button
                class="link-button"
                type="button"
                :class="{ active: activeRootId === record.id }"
                @click="selectRoot(record)"
              >
                {{ record.name }}
              </button>
            </template>
            <template v-else-if="column.key === 'is_active'">
              <Tag :color="record.is_active ? 'green' : 'default'">
                {{ record.is_active ? $t('system.user.enable') : $t('dataset.staging.disabled') }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'actions'">
              <Space wrap>
                <Button size="small" type="primary" @click="runScan(record)">
                  {{ $t('dataset.staging.scanNow') }}
                </Button>
                <Button size="small" @click="openUpdateRootModal(record)">
                  {{ $t('dataset.staging.edit') }}
                </Button>
              </Space>
            </template>
          </template>
          <template #expandedRowRender="{ record }">
            <div class="root-actions">
              <div class="root-description">
                {{
                  record.description ||
                  $t('dataset.staging.noDirDescription')
                }}
              </div>
              <Space wrap>
                <Button size="small" type="primary" @click="runScan(record)">
                  {{ $t('dataset.staging.scanNow') }}
                </Button>
                <Button size="small" @click="openUpdateRootModal(record)">
                  {{ $t('dataset.staging.edit') }}
                </Button>
                <Popconfirm
                  :title="$t('dataset.staging.confirmDeleteScanDir')"
                  :ok-text="$t('dataset.list.delete')"
                  :cancel-text="$t('platform.setting.cancelText')"
                  @confirm="deleteRoot(record)"
                >
                  <Button size="small" danger>{{ $t('dataset.list.delete') }}</Button>
                </Popconfirm>
              </Space>
            </div>
          </template>
        </Table>
        <Empty
          v-if="!rootsLoading && rootRows.length === 0"
          :description="$t('dataset.staging.noScanDirYet')"
        />
      </Card>

      <Card :bordered="false" class="panel-card">
        <template #title>
          {{ activeRoot ? `${$t('dataset.staging.scanJobLabel')} / ${activeRoot.name}` : $t('dataset.staging.scanJobLabel') }}
        </template>
        <Table
          :columns="jobColumns"
          :data-source="jobRows"
          :loading="jobsLoading"
          :pagination="false"
          row-key="id"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <Tag
                :color="
                  record.status === 'success'
                    ? 'green'
                    : record.status === 'failed'
                      ? 'red'
                      : 'processing'
                "
              >
                {{ record.status }}
              </Tag>
            </template>
          </template>
        </Table>
        <Empty
          v-if="!jobsLoading && jobRows.length === 0"
          :description="$t('dataset.staging.noScanJobYet')"
        />
      </Card>
    </div>

    <Card :bordered="false" class="panel-card">
      <template #title>{{ $t('dataset.staging.dirBrowse') }}</template>
      <template #extra>
        <Space wrap>
          <Button type="primary" ghost @click="openUploadModal">{{ $t('dataset.staging.uploadToStaging') }}</Button>
          <Button @click="openCandidatePage">{{ $t('dataset.staging.viewCandidates') }}</Button>
        </Space>
      </template>
      <DirectoryBrowser
        :scan-root-ids="activeRootId ? [activeRootId] : []"
        @register="openRegisterModalForFiles"
      />
    </Card>

    <Modal
      v-model:open="uploadVisible"
      :title="$t('dataset.staging.uploadToStaging')"
      :confirm-loading="uploadLoading"
      @ok="uploadStagingFile"
    >
      <div class="modal-form">
        <input type="file" @change="handleFileChange" />
        <Select
          v-model:value="uploadForm.dataset_type"
          allow-clear
          :options="DATASET_TYPE_OPTIONS"
          :placeholder="$t('dataset.staging.optionalDatasetType')"
        />
        <Input
          v-model:value="uploadForm.meta_json"
          allow-clear
          :placeholder="$t('dataset.staging.optionalMetaJson')"
        />
      </div>
    </Modal>

    <Modal
      v-model:open="rootModalVisible"
      :title="rootEditMode === 'create' ? $t('system.dict.add') + $t('dataset.staging.scan') + $t('system.menu.dirType') : $t('system.dict.edit') + $t('dataset.staging.scan') + $t('system.menu.dirType')"
      :confirm-loading="rootModalLoading"
      @ok="submitRootForm"
    >
      <div class="modal-form">
        <Input
          v-model:value="rootForm.name"
          :placeholder="$t('dataset.staging.dirNamePlaceholder')"
        />
        <Space.Compact block>
          <Input
            v-model:value="rootForm.root_path"
            :placeholder="$t('dataset.staging.selectServerDirPlaceholder')"
            readonly
          />
          <Button @click="openBrowseModal">{{ $t('dataset.staging.selectDir') }}</Button>
        </Space.Compact>
        <Input.TextArea
          v-model:value="rootForm.description"
          :auto-size="{ minRows: 2, maxRows: 4 }"
          :placeholder="$t('dataset.staging.optionalDirDesc')"
        />
        <Checkbox v-model:checked="rootForm.scan_recursive">
          {{ $t('dataset.staging.recursiveScanSubdirs') }}
        </Checkbox>
        <Checkbox v-model:checked="rootForm.include_hidden">
          {{ $t('dataset.staging.includeHiddenFiles') }}
        </Checkbox>
        <Checkbox v-model:checked="rootForm.is_active">{{ $t('dataset.staging.enabled') }}</Checkbox>
        <Checkbox v-model:checked="rootForm.auto_scan_enabled">
          {{ $t('dataset.staging.enableAutoScan') }}
        </Checkbox>
        <InputNumber
          v-model:value="rootForm.scan_interval_minutes"
          :min="5"
          :step="5"
          :addon-after="$t('dataset.staging.minutes')"
          style="width: 100%"
        />
      </div>
    </Modal>

    <Modal
      v-model:open="browseModalVisible"
      :title="$t('dataset.staging.selectServerDir')"
      width="960px"
      :footer="null"
    >
      <div class="browse-modal">
        <div class="browse-toolbar">
          <div class="browse-path-block">
            <div class="browse-path-label">{{ $t('dataset.staging.currentDir') }}</div>
            <div class="browse-path-value">{{ browseCurrentPath }}</div>
          </div>
          <Space wrap>
            <Button
              :disabled="!browseParentPath"
              @click="browseParentDirectory"
            >
              {{ $t('dataset.staging.parentDir') }}
            </Button>
            <Button @click="loadBrowseDirectory(browseCurrentPath)">
              {{ $t('dataset.staging.refresh') }}
            </Button>
            <Button type="primary" @click="selectBrowseCurrentDirectory">
              {{ $t('dataset.staging.selectCurrentDir') }}
            </Button>
          </Space>
        </div>
        <div class="browse-tip">{{ $t('dataset.staging.browseRoot') }}{{ browseRootPath }}</div>
        <Table
          :columns="browseColumns"
          :data-source="browseRows"
          :loading="browseLoading"
          :pagination="false"
          row-key="path"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'">
              <button
                class="link-button"
                type="button"
                @click="openBrowseEntry(record)"
              >
                {{ record.name }}
              </button>
            </template>
          </template>
        </Table>
        <Empty
          v-if="!browseLoading && browseRows.length === 0"
          :description="$t('dataset.staging.noSubDirsHint')"
        />
      </div>
    </Modal>

    <Modal
      v-model:open="registerVisible"
      :title="$t('dataset.staging.registerFromStaging')"
      :confirm-loading="registerLoading"
      @ok="submitRegister"
    >
      <div class="modal-form">
        <Input v-model:value="registerForm.source_name" disabled />
        <Input v-model:value="registerForm.name" :placeholder="$t('dataset.staging.datasetName')" />
        <Select
          v-model:value="registerForm.dataset_type"
          :options="DATASET_TYPE_OPTIONS"
          :placeholder="$t('dataset.staging.datasetType')"
        />
        <Input v-model:value="registerForm.remark" allow-clear :placeholder="$t('system.team.remark')" />
        <Checkbox v-model:checked="registerForm.is_public">{{ $t('dataset.staging.markPublicAfterRegister') }}</Checkbox>
        <Checkbox v-model:checked="registerForm.keep_staging_file">{{ $t('dataset.staging.keepStagingFile') }}</Checkbox>
      </div>
    </Modal>

    <Modal
      v-model:open="candidateModalVisible"
      :title="$t('dataset.staging.generateRegistryCandidate')"
      :confirm-loading="candidateModalLoading"
      @ok="submitCandidateForm"
    >
      <div class="modal-form">
        <Input
          v-model:value="candidateForm.candidate_name"
          :placeholder="$t('dataset.staging.candidateNamePlaceholder')"
        />
        <Select
          v-model:value="candidateForm.dataset_type"
          :options="DATASET_TYPE_OPTIONS"
          :placeholder="$t('dataset.staging.targetDataTypePlaceholder')"
        />
        <Select
          v-model:value="candidateForm.registration_mode"
          :options="REGISTRATION_MODE_OPTIONS"
          :placeholder="$t('dataset.staging.registrationModePlaceholder')"
        />
        <Input
          v-model:value="candidateForm.version_name"
          :placeholder="$t('dataset.staging.optionalTargetVersion')"
        />
        <Input
          v-model:value="candidateForm.organism"
          :placeholder="$t('dataset.staging.optionalSpeciesName')"
        />
        <Input
          v-model:value="candidateForm.assembly"
          :placeholder="$t('dataset.staging.optionalAssemblyVersion')"
        />
        <div class="candidate-tip">
          {{ $t('dataset.staging.candidateTipStaging') }}
        </div>
      </div>
    </Modal>

    <RegisterConfirmModal
      v-model:visible="registerModalVisible"
      :files="selectedBrowseFiles"
      :scan-root-id="activeRootId ?? undefined"
      @registered="onRegistered"
    />
  </Page>
</template>

<style scoped>
.dataset-staging-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero-card,
.panel-card {
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
    radial-gradient(
      circle at top right,
      rgb(14 165 233 / 12%),
      transparent 30%
    ),
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
  max-width: 840px;
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

.dataset-file-title .title-main {
  color: rgb(15 23 42);
  font-weight: 600;
}

.dataset-file-title .title-sub {
  color: rgb(100 116 139);
  font-size: 12px;
}

.layout-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  gap: 16px;
}

.link-button {
  padding: 0;
  border: 0;
  background: transparent;
  color: rgb(15 23 42);
  font-weight: 600;
  cursor: pointer;
}

.link-button.active,
.link-button:hover {
  color: rgb(2 132 199);
}

.root-actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.root-description {
  color: rgb(100 116 139);
  font-size: 12px;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.candidate-tip {
  color: rgb(100 116 139);
  font-size: 12px;
  line-height: 1.7;
}

.browse-modal {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.browse-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.browse-path-block {
  min-width: 0;
}

.browse-path-label {
  color: rgb(100 116 139);
  font-size: 12px;
}

.browse-path-value {
  margin-top: 4px;
  color: rgb(15 23 42);
  font-weight: 600;
  word-break: break-all;
}

.browse-tip {
  color: rgb(100 116 139);
  font-size: 12px;
}

@media (max-width: 1200px) {
  .hero-card,
  .root-actions,
  .browse-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .summary-grid,
  .layout-grid {
    grid-template-columns: 1fr;
  }
}
</style>
