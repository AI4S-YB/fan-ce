import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { $t } from '@vben/locales';
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
  createDatasetLineageApi,
  deleteDatasetLineageApi,
  executeDatasetVersionQueryApi,
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
  { label: $t('dataset.list.lifecycle_draft'), value: 'draft' },
  { label: $t('dataset.list.lifecycle_ready'), value: 'ready' },
  { label: $t('dataset.list.lifecycle_archived'), value: 'archived' },
];

export const VISIBILITY_OPTIONS = [
  { label: $t('dataset.list.visibility_private'), value: 'private' },
  { label: $t('dataset.list.visibility_public'), value: 'public' },
];

export const FILE_ROLE_OPTIONS = [
  { label: $t('dataset.candidate.primaryFile'), value: 'primary' },
  { label: $t('dataset.candidate.indexFile'), value: 'index' },
  { label: $t('dataset.candidate.derivedFile'), value: 'derived' },
  { label: $t('dataset.staging.metadata'), value: 'metadata' },
  { label: $t('dataset.composables.previewFile'), value: 'preview' },
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
    case 'draft': return 'orange';
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
    case 'primary': return $t('dataset.candidate.primaryFile');
    case 'index': return $t('dataset.candidate.indexFile');
    case 'derived': return $t('dataset.candidate.derivedFile');
    case 'metadata': return $t('dataset.staging.metadata');
    case 'preview': return $t('dataset.composables.previewFile');
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
    case 'uses_reference': return $t('dataset.composables.useReference');
    case 'quantified_against': return $t('dataset.composables.quantifiedAgainst');
    case 'called_against': return $t('dataset.composables.calledAgainst');
    case 'annotated_by': return $t('dataset.composables.annotatedBy');
    case 'derived_from': return $t('dataset.composables.derivedFrom');
    case 'normalized_from': return $t('dataset.composables.normalizedFrom');
    default: return relation || '-';
  }
}

export function getSelectedVersionRoleLabels(version?: DatasetVersionItem | null) {
  if (!version) return [];
  const labels: string[] = [];
  if (version.is_current) labels.push($t('dataset.composables.currentVersionPrefix'));
  if (!labels.length) labels.push($t('dataset.composables.unpublishedVersion'));
  return labels;
}

export function getSelectedVersionExposure(version?: DatasetVersionItem | null) {
  if (!version) return '-';
  return $t('dataset.composables.notOpenToPublic');
}

export function formatTime(ts?: number | null) {
  if (!ts) return '-';
  const d = new Date(typeof ts === "number" ? ts * 1000 : ts);
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
}
