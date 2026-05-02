<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

// Use VITE_API_BASE_URL env var, or default to '/api/v1' (proxied in dev)
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

type PublicDatasetItem = {
  id: number;
  dataset_code?: string;
  title?: string;
  dataset_type?: string;
  organism?: string;
  assembly?: string;
  version?: string;
  visibility?: string;
  summary?: string;
};

type QueryExample = {
  operation?: string;
  params?: Record<string, unknown>;
};

type PublicDatasetVersionItem = {
  id: number;
  dataset_id: number;
  version?: string;
  title?: string;
  dataset_type?: string;
  lifecycle_state?: string;
  visibility?: string;
  release_state?: string;
  is_current?: boolean;
  is_default_public?: boolean;
  is_published?: boolean;
};

type PublicAssetFileItem = {
  id: number;
  file_role?: string;
  file_name?: string;
  file_format?: string;
  local_path?: string | null;
  storage_uri?: string | null;
  file_size?: number | null;
  compress_type?: string | null;
  index_of_file_id?: number | null;
};

type PublicAssetItem = {
  id: number;
  asset_code?: string;
  asset_name?: string;
  asset_type?: string;
  file_format?: string;
  query_engine?: string;
  is_required?: boolean;
  is_query_entry?: boolean;
  files?: PublicAssetFileItem[];
};

type PublicLineageItem = {
  id: number;
  src_dataset_id?: number | null;
  src_dataset_title?: string | null;
  src_dataset_type?: string | null;
  src_version_id?: number | null;
  src_version?: string | null;
  src_asset_code?: string | null;
  dst_dataset_id?: number | null;
  dst_dataset_title?: string | null;
  dst_dataset_type?: string | null;
  dst_version_id?: number | null;
  dst_version?: string | null;
  dst_asset_code?: string | null;
  relation_type?: string | null;
  direction?: string | null;
};

type PublicDatasetDetail = PublicDatasetItem & {
  query_adapter?: {
    adapter?: string;
    display_name?: string;
    supported_operations?: string[];
    examples?: Record<string, QueryExample>;
  } | null;
  query_profile?: {
    file_format?: string;
    query_engine?: string;
    validation_summary?: string | null;
    index_summary?: string | null;
  } | null;
  assets?: PublicAssetItem[];
  selected_version?: PublicDatasetVersionItem | null;
  default_public_version?: PublicDatasetVersionItem | null;
  published_version?: PublicDatasetVersionItem | null;
  released_versions?: PublicDatasetVersionItem[];
  lineage?: PublicLineageItem[];
};

type PublicQueryCapabilities = {
  dataset_id: number;
  version_id?: number;
  dataset_code?: string;
  dataset_type?: string;
  file_path?: string | null;
  file_access?: {
    exists_on_server?: boolean;
  } | null;
  query_entry_asset?: {
    asset_code?: string;
    asset_name?: string;
    asset_type?: string;
  } | null;
  query_profile?: {
    file_format?: string;
    query_engine?: string;
  } | null;
  query_adapter?: {
    adapter?: string;
    display_name?: string;
    supported_operations?: string[];
    examples?: Record<string, QueryExample>;
  } | null;
  available_adapters?: Array<{
    adapter?: string;
    display_name?: string;
      supported_dataset_types?: string[];
      supported_file_formats?: string[];
  }>;
  default_public_version?: PublicDatasetVersionItem | null;
  published_version?: PublicDatasetVersionItem | null;
};

const loading = ref(false);
const detailLoading = ref(false);
const keyword = ref('');
const datasets = ref<PublicDatasetItem[]>([]);
const total = ref(0);
const errorText = ref('');
const selectedDatasetId = ref<number | null>(null);
const selectedVersionId = ref<number | null>(null);
const publicVersions = ref<PublicDatasetVersionItem[]>([]);
const publicVersionTotal = ref(0);
const selectedDetail = ref<PublicDatasetDetail | null>(null);
const selectedCapabilities = ref<PublicQueryCapabilities | null>(null);
const queryOperation = ref('');
const queryParamsText = ref('{}');
const queryMode = ref<'json' | 'smart'>('json');
const queryLoading = ref(false);
const queryError = ref('');
const queryResult = ref<null | unknown>(null);
const copyFeedback = ref('');
const sequenceQueryForm = ref({
  seq_id: '',
  start: 1,
  end: 100,
});
const sequenceBatchRegionsText = ref('chr1:1-100');
const variantQueryForm = ref({
  regionsText: 'Chr1:1000-2000',
  includeSamplesText: '',
  excludeSamplesText: '',
});
const expressionQueryForm = ref({
  maxRecords: 20,
  dataType: 'count',
  genesText: '',
  samplesText: '',
});
const annotationQueryForm = ref({
  seqId: 'chr1',
  start: 1,
  end: 10000,
  featureType: 'gene',
  geneId: 'Gene001',
  limit: 100,
});
const functionalQueryForm = ref({
  geneId: 'AT1G01010',
  transcriptId: 'AT1G01010.1',
  termSource: 'go',
  keyword: 'transcription',
  termId: 'GO:0003677',
  limit: 20,
  page: 1,
  size: 20,
});
const phenomeQueryForm = ref({
  subjectId: 'RH00004',
  trait: '花瓣数量',
  keyword: '花瓣',
  timepoint: '',
  limit: 20,
});
const functionalTermSourceOptions = [
  { label: 'GO', value: 'go' },
  { label: 'KEGG', value: 'kegg' },
  { label: 'InterPro', value: 'interpro' },
  { label: 'iTAK', value: 'itak' },
  { label: 'Family', value: 'family' },
];
const signalQueryForm = ref({
  seqId: 'chr1',
  start: 1,
  end: 1000,
  limit: 100,
  bins: 20,
  summaryType: 'mean',
});
const interactionQueryForm = ref({
  seqId: 'chr1',
  start: 1,
  end: 1000,
  targetChrom: 'chr1',
  targetStart: 1,
  targetEnd: 2000,
  limit: 100,
  resolution: 10000,
  balanced: false,
  limitBins: 25,
});
const versionFilters = ref({
  keyword: '',
  isDefaultPublic: 'all',
  isCurrent: 'all',
});

const filteredDatasets = computed(() => {
  const value = keyword.value.trim().toLowerCase();
  if (!value) {
    return datasets.value;
  }
  return datasets.value.filter((item) => {
    return [item.title, item.dataset_code, item.dataset_type, item.organism, item.assembly]
      .filter(Boolean)
      .some((field) => String(field).toLowerCase().includes(value));
  });
});

const selectedDataset = computed(() =>
  filteredDatasets.value.find((item) => item.id === selectedDatasetId.value) ||
  datasets.value.find((item) => item.id === selectedDatasetId.value) ||
  null,
);

const selectedVersion = computed(() =>
  publicVersions.value.find((item) => item.id === selectedVersionId.value) || null,
);

const queryExamples = computed(
  () => selectedCapabilities.value?.query_adapter?.examples || selectedDetail.value?.query_adapter?.examples || {},
);
const supportedOperations = computed(
  () => selectedCapabilities.value?.query_adapter?.supported_operations || selectedDetail.value?.query_adapter?.supported_operations || [],
);
const currentAdapter = computed(
  () => selectedCapabilities.value?.query_adapter?.adapter || selectedDetail.value?.query_adapter?.adapter || 'generic',
);
const isSequenceAdapter = computed(
  () => currentAdapter.value === 'sequence',
);
const isSequenceBatchOperation = computed(() => isSequenceAdapter.value && queryOperation.value === 'batch_fetch');
const isVariantAdapter = computed(() => currentAdapter.value === 'variant');
const isExpressionAdapter = computed(() => currentAdapter.value === 'expression');
const isAnnotationAdapter = computed(() => currentAdapter.value === 'annotation');
const isFunctionalAnnotationAdapter = computed(() => currentAdapter.value === 'functional_annotation');
const isPhenomeAdapter = computed(() => currentAdapter.value === 'phenome');
const isSignalAdapter = computed(() => currentAdapter.value === 'signal');
const isInteractionAdapter = computed(() => currentAdapter.value === 'interaction');
const sequenceQueryResult = computed(() => {
  if (!queryResult.value || !isSequenceAdapter.value || typeof queryResult.value !== 'object') {
    return null;
  }
  return queryResult.value as {
    operation?: string;
    data?: Record<string, unknown>;
  };
});
const variantQueryResult = computed(() => {
  if (!queryResult.value || !isVariantAdapter.value || typeof queryResult.value !== 'object') {
    return null;
  }
  return queryResult.value as {
    operation?: string;
    data?: {
      count?: number;
      samples?: string[];
      ref_id?: string;
      variant_position?: number;
      example_regions?: string[];
      preview?: string | null;
      size?: number;
      download_url?: string | null;
    };
  };
});
const expressionQueryResult = computed(() => {
  if (!queryResult.value || !isExpressionAdapter.value || typeof queryResult.value !== 'object') {
    return null;
  }
  return queryResult.value as {
    operation?: string;
    data?: {
      count?: number;
      genes?: string[];
      samples?: string[];
      data_type?: string;
      matrix?: Array<Array<number | string>>;
      download_path?: string | null;
    };
  };
});
const annotationQueryResult = computed(() => {
  if (!queryResult.value || !isAnnotationAdapter.value || typeof queryResult.value !== 'object') {
    return null;
  }
  return queryResult.value as {
    operation?: string;
    data?: {
      source?: string;
      table?: string;
      tables?: string[];
      count?: number;
      gene?: Record<string, unknown>;
      transcripts?: Array<Record<string, unknown>>;
      transcript_count?: number;
      items?: Array<Record<string, unknown>>;
      region?: string;
    };
  };
});
const functionalQueryResult = computed(() => {
  if (!queryResult.value || !isFunctionalAnnotationAdapter.value || typeof queryResult.value !== 'object') {
    return null;
  }
  return queryResult.value as {
    operation?: string;
    data?: {
      source?: string;
      gene?: Record<string, unknown>;
      transcript?: Record<string, unknown>;
      transcripts?: Array<Record<string, unknown>>;
      canonical_transcript?: Record<string, unknown> | null;
      canonical_transcript_id?: string | null;
      transcript_count?: number;
      annotation_counts?: Record<string, number>;
      annotations?: Record<string, unknown>;
      items?: Array<Record<string, unknown>>;
      total?: number;
      page?: number;
      size?: number;
      term_source?: string;
      term_id?: string;
      by_source?: Array<Record<string, unknown>>;
      top_terms?: Array<Record<string, unknown>>;
    };
  };
});
const phenomeQueryResult = computed(() => {
  if (!queryResult.value || !isPhenomeAdapter.value || typeof queryResult.value !== 'object') {
    return null;
  }
  return queryResult.value as {
    operation?: string;
    data?: {
      source?: string;
      table?: string;
      subject_count?: number;
      trait_count?: number;
      observation_count?: number;
      traits_preview?: string[];
      count?: number;
      keyword?: string;
      trait?: string;
      trait_code?: string;
      timepoint?: string | null;
      non_missing_count?: number;
      items?: Array<Record<string, unknown>>;
      subject_id?: string;
      traits?: Record<string, unknown>;
    };
  };
});
const signalQueryResult = computed(() => {
  if (!queryResult.value || !isSignalAdapter.value || typeof queryResult.value !== 'object') {
    return null;
  }
  return queryResult.value as {
    operation?: string;
    data?: {
      source?: string;
      file_path?: string;
      chromosome_count?: number;
      chromosomes?: Array<Record<string, unknown>>;
      header?: Record<string, unknown>;
      region?: string;
      summary_type?: string;
      bins?: number;
      bin_width?: number;
      count?: number;
      non_null_count?: number;
      summary?: Record<string, unknown>;
      items?: Array<Record<string, unknown>>;
    };
  };
});
const interactionQueryResult = computed(() => {
  if (!queryResult.value || !isInteractionAdapter.value || typeof queryResult.value !== 'object') {
    return null;
  }
  return queryResult.value as {
    operation?: string;
    data?: {
      source?: string;
      format?: string;
      resolution?: number;
      available_resolutions?: number[];
      default_resolution?: number;
      bin_size?: number;
      chroms?: Array<Record<string, unknown>>;
      shape?: number[];
      balanced_supported?: boolean;
      anchor_region?: string;
      region?: string;
      target_region?: string | null;
      x_labels?: string[];
      y_labels?: string[];
      matrix?: Array<Array<number | string>>;
      balanced?: boolean;
      resolutions?: number[];
      count?: number;
      items?: Array<Record<string, unknown>>;
    };
  };
});

const expressionMatrixTsv = computed(() => {
  const data = expressionQueryResult.value?.data;
  if (!data?.matrix?.length) {
    return '';
  }
  const header = ['gene', ...(data.samples || [])].join('\t');
  const rows = (data.matrix || []).map((row, rowIndex) =>
    [data.genes?.[rowIndex] || `Gene-${rowIndex + 1}`, ...row].join('\t'),
  );
  return [header, ...rows].join('\n');
});

const interactionMatrixTsv = computed(() => {
  const data = interactionQueryResult.value?.data;
  if (!data?.matrix?.length) {
    return '';
  }
  const header = ['bin', ...(data.x_labels || [])].join('\t');
  const rows = (data.matrix || []).map((row, rowIndex) =>
    [data.y_labels?.[rowIndex] || `Bin-${rowIndex + 1}`, ...row].join('\t'),
  );
  return [header, ...rows].join('\n');
});

const annotationRegionTsv = computed(() => {
  const data = annotationQueryResult.value?.data;
  const items = data?.items || [];
  if (!items.length) {
    return '';
  }
  const columns = Array.from(
    items.reduce((set, item) => {
      Object.keys(item || {}).forEach((key) => set.add(key));
      return set;
    }, new Set<string>()),
  );
  const lines = items.map((item) => columns.map((column) => String(item[column] ?? '')).join('\t'));
  return [columns.join('\t'), ...lines].join('\n');
});

function formatFileSize(size?: null | number) {
  if (!size) {
    return '-';
  }
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  if (size < 1024 * 1024 * 1024) {
    return `${(size / 1024 / 1024).toFixed(1)} MB`;
  }
  return `${(size / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

function getPublicAssetFiles(asset?: PublicAssetItem | null) {
  return asset?.files || [];
}

function hasPublicExplicitPrimaryFile(asset?: PublicAssetItem | null) {
  return getPublicAssetFiles(asset).some((item) => item.file_role === 'primary');
}

function getPublicPrimaryFile(asset?: PublicAssetItem | null) {
  const files = getPublicAssetFiles(asset);
  return files.find((item) => item.file_role === 'primary') || files[0] || null;
}

function getPublicSortedAssetFiles(asset?: PublicAssetItem | null) {
  const rankMap: Record<string, number> = {
    primary: 0,
    index: 1,
    metadata: 2,
    derived: 3,
    preview: 4,
  };
  return [...getPublicAssetFiles(asset)].sort((left, right) => {
    const leftRank = rankMap[left.file_role || ''] ?? 99;
    const rightRank = rankMap[right.file_role || ''] ?? 99;
    if (leftRank !== rightRank) {
      return leftRank - rightRank;
    }
    return Number(left.id || 0) - Number(right.id || 0);
  });
}

function getPublicAssetLabels(asset?: PublicAssetItem | null) {
  const labels: string[] = [];
  if (!asset) {
    return labels;
  }
  if (asset.is_query_entry) {
    labels.push('Query Entry');
  }
  if (asset.is_required) {
    labels.push('Required');
  }
  return labels;
}

function getPublicAssetMeta(asset?: PublicAssetItem | null) {
  if (!asset) {
    return '-';
  }
  const parts: string[] = [];
  if (asset.asset_code) {
    parts.push(`code: ${asset.asset_code}`);
  }
  if (asset.file_format) {
    parts.push(`format: ${asset.file_format}`);
  }
  if (asset.query_engine) {
    parts.push(`engine: ${asset.query_engine}`);
  }
  return parts.join(' / ') || '-';
}

function getPublicFileDisplayName(file?: PublicAssetFileItem | null) {
  if (!file) {
    return '-';
  }
  return file.file_name || file.local_path || file.storage_uri || `file-${file.id}`;
}

function getPublicAssetCoverage(asset?: PublicAssetItem | null) {
  if (!asset) {
    return '-';
  }
  const files = getPublicAssetFiles(asset);
  if (!files.length) {
    return 'This asset currently exposes no public files.';
  }
  const primary = getPublicPrimaryFile(asset);
  const indexCount = files.filter((item) => item.file_role === 'index').length;
  const primaryMode = hasPublicExplicitPrimaryFile(asset) ? '' : ' (fallback to first file)';
  const indexLabel = indexCount ? ` / index files: ${indexCount}` : '';
  return `Primary file: ${getPublicFileDisplayName(primary)}${primaryMode}${indexLabel}`;
}

function getPublicFileRoleLabel(file?: PublicAssetFileItem | null) {
  switch (file?.file_role) {
    case 'primary':
      return 'Primary';
    case 'index':
      return 'Index';
    case 'derived':
      return 'Derived';
    case 'metadata':
      return 'Metadata';
    case 'preview':
      return 'Preview';
    default:
      return file?.file_role || '-';
  }
}

function isPublicPrimaryFile(asset?: PublicAssetItem | null, file?: PublicAssetFileItem | null) {
  if (!asset || !file) {
    return false;
  }
  return getPublicPrimaryFile(asset)?.id === file.id;
}

function getPublicIndexTarget(asset?: PublicAssetItem | null, file?: PublicAssetFileItem | null) {
  if (!asset || !file?.index_of_file_id) {
    return '';
  }
  const target = getPublicAssetFiles(asset).find((item) => item.id === file.index_of_file_id);
  if (target) {
    return `index of ${getPublicFileDisplayName(target)}`;
  }
  return `index_of_file_id=${file.index_of_file_id}`;
}

function getPublicFileSummary(asset?: PublicAssetItem | null, file?: PublicAssetFileItem | null) {
  if (!file) {
    return '-';
  }
  const parts: string[] = [];
  if (file.file_format) {
    parts.push(`format: ${file.file_format}`);
  }
  if (file.file_size) {
    parts.push(formatFileSize(file.file_size));
  }
  if (file.compress_type) {
    parts.push(`compressed: ${file.compress_type}`);
  }
  const indexTarget = getPublicIndexTarget(asset, file);
  if (indexTarget) {
    parts.push(indexTarget);
  }
  return parts.join(' / ') || 'No extra metadata';
}

const selectedVersionStatusText = computed(() => {
  const version = selectedVersion.value || selectedDetail.value?.selected_version || null;
  if (!version) {
    return '-';
  }
  if (version.is_default_public) {
    return 'This version is the default public version of the dataset.';
  }
  return 'This version is publicly accessible, but users only reach it when they explicitly switch to it.';
});

const selectedPublicEntryAssetLabel = computed(() => {
  const capabilityEntry = selectedCapabilities.value?.query_entry_asset;
  if (capabilityEntry?.asset_name || capabilityEntry?.asset_code) {
    return capabilityEntry.asset_name || capabilityEntry.asset_code || '-';
  }
  const detailAssets = selectedDetail.value?.assets || [];
  const queryEntryAsset = detailAssets.find((item) => item.is_query_entry) || detailAssets[0] || null;
  return queryEntryAsset?.asset_name || queryEntryAsset?.asset_code || '-';
});

const selectedVersionStatusCards = computed(() => {
  const version = selectedVersion.value || selectedDetail.value?.selected_version || null;
  const queryAdapter = selectedCapabilities.value?.query_adapter?.display_name || selectedDetail.value?.query_adapter?.display_name || '-';
  const queryEngine = selectedCapabilities.value?.query_profile?.query_engine || selectedDetail.value?.query_profile?.query_engine || '-';
  const engineReady = selectedCapabilities.value?.file_access?.exists_on_server;

  return [
    {
      key: 'reach-mode',
      label: 'Public Reach',
      value: version?.is_default_public ? 'Default Public' : version?.release_state === 'released' ? 'Version Switch' : 'Unavailable',
      hint: selectedVersionStatusText.value,
    },
    {
      key: 'release-state',
      label: 'Release State',
      value: version?.release_state || '-',
      hint: `Lifecycle: ${version?.lifecycle_state || '-'}`,
    },
    {
      key: 'entry-asset',
      label: 'Entry Asset',
      value: selectedPublicEntryAssetLabel.value,
      hint: `Engine: ${queryEngine}`,
    },
    {
      key: 'engine-ready',
      label: 'Engine Ready',
      value: engineReady === undefined ? 'Pending' : engineReady ? 'Yes' : 'No',
      hint: `Adapter: ${queryAdapter}`,
    },
  ];
});

const selectedLineage = computed(() => selectedDetail.value?.lineage || []);

function getLineagePeer(lineage: PublicLineageItem, selectedVersionId?: number | null) {
  if (selectedVersionId && lineage.src_version_id === selectedVersionId) {
    return {
      datasetId: lineage.dst_dataset_id,
      datasetTitle: lineage.dst_dataset_title,
      datasetType: lineage.dst_dataset_type,
      versionId: lineage.dst_version_id,
      version: lineage.dst_version,
      assetCode: lineage.dst_asset_code,
      direction: 'outbound',
    };
  }
  return {
    datasetId: lineage.src_dataset_id,
    datasetTitle: lineage.src_dataset_title,
    datasetType: lineage.src_dataset_type,
    versionId: lineage.src_version_id,
    version: lineage.src_version,
    assetCode: lineage.src_asset_code,
    direction: 'inbound',
  };
}

function getLineageLabel(lineage: PublicLineageItem) {
  switch (lineage.relation_type) {
    case 'quantified_against':
      return 'Quantified Against';
    case 'annotated_by':
      return 'Annotated By';
    case 'derived_from':
      return 'Derived From';
    default:
      return lineage.relation_type || 'Related To';
  }
}

function getLineageSummary(lineage: PublicLineageItem) {
  const peer = getLineagePeer(lineage, selectedVersionId.value);
  const parts = [
    peer.datasetTitle || (peer.datasetId ? `dataset-${peer.datasetId}` : 'unknown dataset'),
    peer.version ? `version ${peer.version}` : null,
    peer.assetCode ? `asset ${peer.assetCode}` : null,
  ].filter(Boolean);
  return parts.join(' / ') || '-';
}

async function copyText(text: string, successLabel: string) {
  if (!text) {
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
    copyFeedback.value = successLabel;
    window.setTimeout(() => {
      if (copyFeedback.value === successLabel) {
        copyFeedback.value = '';
      }
    }, 2000);
  } catch {
    copyFeedback.value = '复制失败';
    window.setTimeout(() => {
      if (copyFeedback.value === '复制失败') {
        copyFeedback.value = '';
      }
    }, 2000);
  }
}

function toLineText(items?: string[]) {
  return (items || []).join('\n');
}

function normalizeSequenceQueryForm(operation?: string, params?: Record<string, unknown>) {
  if (operation === 'batch_fetch') {
    const regions = Array.isArray(params?.regions) ? params.regions : [];
    sequenceBatchRegionsText.value = regions.length
      ? regions
          .map((item) => {
            const region = item as Record<string, unknown>;
            return `${String(region.seq_id || '')}:${Number(region.start || 1)}-${Number(region.end || 1)}`;
          })
          .join('\n')
      : 'chr1:1-100';
    return;
  }
  const start = Number(params?.start);
  const end = Number(params?.end);
  sequenceQueryForm.value = {
    seq_id: String(params?.seq_id || ''),
    start: Number.isFinite(start) && start > 0 ? start : 1,
    end: Number.isFinite(end) && end > 0 ? end : 100,
  };
}

function parseSequenceBatchRegions(text: string) {
  const lines = text
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);
  if (!lines.length) {
    throw new Error('请至少填写一个区间');
  }
  return lines.map((line) => {
    const matched = line.match(/^([^:\s]+):(\d+)-(\d+)$/);
    if (!matched) {
      throw new Error(`区间格式错误: ${line}，请使用 seq_id:start-end`);
    }
    return {
      seq_id: matched[1],
      start: Number(matched[2]),
      end: Number(matched[3]),
    };
  });
}

function splitLines(text: string) {
  return text
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeVariantQueryForm(operation?: string, params?: Record<string, unknown>) {
  if (operation === 'query') {
    const regions = Array.isArray(params?.regions) ? (params.regions as string[]) : [];
    variantQueryForm.value.regionsText = regions.length ? regions.join('\n') : 'Chr1:1000-2000';
    variantQueryForm.value.includeSamplesText = Array.isArray(params?.include_samples)
      ? (params?.include_samples as string[]).join('\n')
      : '';
    variantQueryForm.value.excludeSamplesText = Array.isArray(params?.exclude_samples)
      ? (params?.exclude_samples as string[]).join('\n')
      : '';
    return;
  }
  variantQueryForm.value.regionsText = 'Chr1:1000-2000';
  variantQueryForm.value.includeSamplesText = '';
  variantQueryForm.value.excludeSamplesText = '';
}

function normalizeExpressionQueryForm(operation?: string, params?: Record<string, unknown>) {
  if (operation === 'genes_list' || operation === 'samples_list') {
    expressionQueryForm.value.maxRecords = Number(params?.max_records || 20);
    return;
  }
  if (operation === 'matrix_slice') {
    expressionQueryForm.value.dataType = String(params?.data_type || 'count');
    expressionQueryForm.value.genesText = Array.isArray(params?.genes) ? (params?.genes as string[]).join('\n') : '';
    expressionQueryForm.value.samplesText = Array.isArray(params?.samples) ? (params?.samples as string[]).join('\n') : '';
    return;
  }
  expressionQueryForm.value.maxRecords = 20;
  expressionQueryForm.value.dataType = 'count';
  expressionQueryForm.value.genesText = '';
  expressionQueryForm.value.samplesText = '';
}

function normalizeAnnotationQueryForm(operation?: string, params?: Record<string, unknown>) {
  if (operation === 'gene_lookup') {
    annotationQueryForm.value.geneId = String(params?.gene_id || 'Gene001');
    return;
  }
  if (operation === 'region_features') {
    annotationQueryForm.value.seqId = String(params?.seq_id || params?.chrom || 'chr1');
    annotationQueryForm.value.start = Number(params?.start || 1);
    annotationQueryForm.value.end = Number(params?.end || 10000);
    annotationQueryForm.value.featureType = String(params?.feature_type || 'gene');
    annotationQueryForm.value.limit = Number(params?.limit || 100);
    return;
  }
  annotationQueryForm.value.geneId = 'Gene001';
  annotationQueryForm.value.seqId = 'chr1';
  annotationQueryForm.value.start = 1;
  annotationQueryForm.value.end = 10000;
  annotationQueryForm.value.featureType = 'gene';
  annotationQueryForm.value.limit = 100;
}

function normalizeFunctionalAnnotationQueryForm(operation?: string, params?: Record<string, unknown>) {
  if (operation === 'transcript_detail') {
    functionalQueryForm.value.transcriptId = String(params?.transcript_id || 'AT1G01010.1');
    return;
  }
  if (operation === 'term_lookup') {
    functionalQueryForm.value.termSource = String(params?.term_source || 'go');
    functionalQueryForm.value.keyword = String(params?.keyword || 'transcription');
    functionalQueryForm.value.termId = String(params?.term_id || '');
    functionalQueryForm.value.limit = Number(params?.limit || 20);
    return;
  }
  if (operation === 'term_gene_list') {
    functionalQueryForm.value.termSource = String(params?.term_source || 'go');
    functionalQueryForm.value.termId = String(params?.term_id || 'GO:0003677');
    functionalQueryForm.value.page = Number(params?.page || 1);
    functionalQueryForm.value.size = Number(params?.size || 20);
    return;
  }
  if (operation === 'term_aggregation') {
    functionalQueryForm.value.termSource = String(params?.term_source || 'go');
    functionalQueryForm.value.limit = Number(params?.limit || 20);
    return;
  }
  functionalQueryForm.value.geneId = String(params?.gene_id || 'AT1G01010');
}

function normalizePhenomeQueryForm(operation?: string, params?: Record<string, unknown>) {
  if (operation === 'subject_detail') {
    phenomeQueryForm.value.subjectId = String(params?.subject_id || params?.sample_id || params?.id || 'RH00004');
    return;
  }
  if (operation === 'trait_search') {
    phenomeQueryForm.value.keyword = String(params?.keyword || '花瓣');
    phenomeQueryForm.value.limit = Number(params?.limit || 20);
    return;
  }
  if (operation === 'trait_values') {
    phenomeQueryForm.value.trait = String(params?.trait || params?.trait_name || params?.trait_code || '花瓣数量');
    phenomeQueryForm.value.timepoint = String(params?.timepoint || '');
    phenomeQueryForm.value.limit = Number(params?.limit || 20);
    return;
  }
  if (operation === 'trait_list' || operation === 'subject_list') {
    phenomeQueryForm.value.limit = Number(params?.limit || 20);
    return;
  }
  phenomeQueryForm.value.subjectId = 'RH00004';
  phenomeQueryForm.value.trait = '花瓣数量';
  phenomeQueryForm.value.keyword = '花瓣';
  phenomeQueryForm.value.timepoint = '';
  phenomeQueryForm.value.limit = 20;
}

function normalizeSignalQueryForm(operation?: string, params?: Record<string, unknown>) {
  if (operation === 'region_features' || operation === 'region_signal') {
    signalQueryForm.value.seqId = String(params?.seq_id || params?.chrom || 'chr1');
    signalQueryForm.value.start = Number(params?.start || 1);
    signalQueryForm.value.end = Number(params?.end || 1000);
    signalQueryForm.value.limit = Number(params?.limit || 100);
    signalQueryForm.value.bins = Number(params?.bins || 20);
    signalQueryForm.value.summaryType = String(params?.summary_type || 'mean');
    return;
  }
  signalQueryForm.value.seqId = 'chr1';
  signalQueryForm.value.start = 1;
  signalQueryForm.value.end = 1000;
  signalQueryForm.value.limit = 100;
  signalQueryForm.value.bins = 20;
  signalQueryForm.value.summaryType = 'mean';
}

function normalizeInteractionQueryForm(operation?: string, params?: Record<string, unknown>) {
  if (operation === 'region_contacts') {
    interactionQueryForm.value.seqId = String(params?.seq_id || params?.chrom || 'chr1');
    interactionQueryForm.value.start = Number(params?.start || 1);
    interactionQueryForm.value.end = Number(params?.end || 1000);
    interactionQueryForm.value.targetChrom = String(params?.target_chrom || 'chr1');
    interactionQueryForm.value.targetStart = Number(params?.target_start || 1);
    interactionQueryForm.value.targetEnd = Number(params?.target_end || 2000);
    interactionQueryForm.value.limit = Number(params?.limit || 100);
    return;
  }
  if (operation === 'matrix_slice') {
    interactionQueryForm.value.seqId = String(params?.seq_id || params?.chrom || 'chr1');
    interactionQueryForm.value.start = Number(params?.start || 0);
    interactionQueryForm.value.end = Number(params?.end || 100000);
    interactionQueryForm.value.targetChrom = String(params?.target_chrom || '');
    interactionQueryForm.value.targetStart = Number(params?.target_start || params?.start || 0);
    interactionQueryForm.value.targetEnd = Number(params?.target_end || params?.end || 100000);
    interactionQueryForm.value.resolution = Number(params?.resolution || 10000);
    interactionQueryForm.value.balanced = Boolean(params?.balanced || false);
    interactionQueryForm.value.limitBins = Number(params?.limit_bins || 25);
    return;
  }
  interactionQueryForm.value.seqId = 'chr1';
  interactionQueryForm.value.start = 1;
  interactionQueryForm.value.end = 1000;
  interactionQueryForm.value.targetChrom = 'chr1';
  interactionQueryForm.value.targetStart = 1;
  interactionQueryForm.value.targetEnd = 2000;
  interactionQueryForm.value.limit = 100;
  interactionQueryForm.value.resolution = 10000;
  interactionQueryForm.value.balanced = false;
  interactionQueryForm.value.limitBins = 25;
}

function applyFirstExample(detail: null | PublicDatasetDetail) {
  const examples = detail?.query_adapter?.examples || {};
  const firstExample = Object.values(examples)[0];
  if (!firstExample?.operation) {
    queryOperation.value = '';
    queryParamsText.value = '{}';
    queryMode.value = ['sequence', 'variant', 'expression', 'annotation', 'functional_annotation', 'phenome', 'signal', 'interaction'].includes(
      detail?.query_adapter?.adapter || '',
    )
      ? 'smart'
      : 'json';
    normalizeSequenceQueryForm();
    return;
  }
  queryOperation.value = firstExample.operation;
  queryParamsText.value = JSON.stringify(firstExample.params || {}, null, 2);
  queryMode.value = detail?.query_adapter?.adapter === 'sequence' ? 'smart' : 'json';
  if (detail?.query_adapter?.adapter === 'sequence') {
    normalizeSequenceQueryForm(firstExample.operation, firstExample.params);
  } else if (detail?.query_adapter?.adapter === 'variant') {
    queryMode.value = 'smart';
    normalizeVariantQueryForm(firstExample.operation, firstExample.params);
  } else if (detail?.query_adapter?.adapter === 'expression') {
    queryMode.value = 'smart';
    normalizeExpressionQueryForm(firstExample.operation, firstExample.params);
  } else if (detail?.query_adapter?.adapter === 'annotation') {
    queryMode.value = 'smart';
    normalizeAnnotationQueryForm(firstExample.operation, firstExample.params);
  } else if (detail?.query_adapter?.adapter === 'functional_annotation') {
    queryMode.value = 'smart';
    normalizeFunctionalAnnotationQueryForm(firstExample.operation, firstExample.params);
  } else if (detail?.query_adapter?.adapter === 'phenome') {
    queryMode.value = 'smart';
    normalizePhenomeQueryForm(firstExample.operation, firstExample.params);
  } else if (detail?.query_adapter?.adapter === 'signal') {
    queryMode.value = 'smart';
    normalizeSignalQueryForm(firstExample.operation, firstExample.params);
  } else if (detail?.query_adapter?.adapter === 'interaction') {
    queryMode.value = 'smart';
    normalizeInteractionQueryForm(firstExample.operation, firstExample.params);
  }
}

function applyQueryExample(example: QueryExample) {
  queryOperation.value = example.operation || '';
  queryParamsText.value = JSON.stringify(example.params || {}, null, 2);
  if (isSequenceAdapter.value) {
    queryMode.value = 'smart';
    normalizeSequenceQueryForm(example.operation, example.params);
  } else if (isVariantAdapter.value) {
    queryMode.value = 'smart';
    normalizeVariantQueryForm(example.operation, example.params);
  } else if (isExpressionAdapter.value) {
    queryMode.value = 'smart';
    normalizeExpressionQueryForm(example.operation, example.params);
  } else if (isAnnotationAdapter.value) {
    queryMode.value = 'smart';
    normalizeAnnotationQueryForm(example.operation, example.params);
  } else if (isFunctionalAnnotationAdapter.value) {
    queryMode.value = 'smart';
    normalizeFunctionalAnnotationQueryForm(example.operation, example.params);
  } else if (isPhenomeAdapter.value) {
    queryMode.value = 'smart';
    normalizePhenomeQueryForm(example.operation, example.params);
  } else if (isSignalAdapter.value) {
    queryMode.value = 'smart';
    normalizeSignalQueryForm(example.operation, example.params);
  } else if (isInteractionAdapter.value) {
    queryMode.value = 'smart';
    normalizeInteractionQueryForm(example.operation, example.params);
  }
}

function buildQueryParams() {
  if (isSequenceAdapter.value && queryMode.value === 'smart') {
    if (queryOperation.value === 'batch_fetch') {
      return {
        regions: parseSequenceBatchRegions(sequenceBatchRegionsText.value),
      };
    }
    return {
      seq_id: sequenceQueryForm.value.seq_id.trim(),
      start: Number(sequenceQueryForm.value.start),
      end: Number(sequenceQueryForm.value.end),
    };
  }
  if (isVariantAdapter.value && queryMode.value === 'smart') {
    if (queryOperation.value === 'query') {
      return {
        regions: splitLines(variantQueryForm.value.regionsText),
        include_samples: splitLines(variantQueryForm.value.includeSamplesText),
        exclude_samples: splitLines(variantQueryForm.value.excludeSamplesText),
      };
    }
    return {};
  }
  if (isExpressionAdapter.value && queryMode.value === 'smart') {
    if (queryOperation.value === 'genes_list' || queryOperation.value === 'samples_list') {
      return {
        max_records: Number(expressionQueryForm.value.maxRecords || 20),
      };
    }
    if (queryOperation.value === 'matrix_slice') {
      return {
        data_type: expressionQueryForm.value.dataType || 'count',
        genes: splitLines(expressionQueryForm.value.genesText),
        samples: splitLines(expressionQueryForm.value.samplesText),
      };
    }
  }
  if (isAnnotationAdapter.value && queryMode.value === 'smart') {
    if (queryOperation.value === 'gene_lookup') {
      return {
        gene_id: annotationQueryForm.value.geneId.trim(),
      };
    }
    if (queryOperation.value === 'region_features') {
      return {
        seq_id: annotationQueryForm.value.seqId.trim(),
        start: Number(annotationQueryForm.value.start),
        end: Number(annotationQueryForm.value.end),
        feature_type: annotationQueryForm.value.featureType.trim() || 'gene',
        limit: Number(annotationQueryForm.value.limit || 100),
      };
    }
    return {};
  }
  if (isFunctionalAnnotationAdapter.value && queryMode.value === 'smart') {
    if (queryOperation.value === 'transcript_detail') {
      return {
        transcript_id: functionalQueryForm.value.transcriptId.trim(),
      };
    }
    if (queryOperation.value === 'term_lookup') {
      return {
        term_source: functionalQueryForm.value.termSource,
        keyword: functionalQueryForm.value.keyword.trim() || undefined,
        term_id: functionalQueryForm.value.termId.trim() || undefined,
        limit: Number(functionalQueryForm.value.limit || 20),
      };
    }
    if (queryOperation.value === 'term_gene_list') {
      return {
        term_source: functionalQueryForm.value.termSource,
        term_id: functionalQueryForm.value.termId.trim(),
        page: Number(functionalQueryForm.value.page || 1),
        size: Number(functionalQueryForm.value.size || 20),
      };
    }
    if (queryOperation.value === 'term_aggregation') {
      return {
        term_source: functionalQueryForm.value.termSource || undefined,
        limit: Number(functionalQueryForm.value.limit || 20),
      };
    }
    return {
      gene_id: functionalQueryForm.value.geneId.trim(),
    };
  }
  if (isPhenomeAdapter.value && queryMode.value === 'smart') {
    if (queryOperation.value === 'subject_detail') {
      return {
        subject_id: phenomeQueryForm.value.subjectId.trim(),
      };
    }
    if (queryOperation.value === 'trait_search') {
      return {
        keyword: phenomeQueryForm.value.keyword.trim() || undefined,
        limit: Number(phenomeQueryForm.value.limit || 20),
      };
    }
    if (queryOperation.value === 'trait_values') {
      return {
        trait: phenomeQueryForm.value.trait.trim(),
        timepoint: phenomeQueryForm.value.timepoint.trim() || undefined,
        limit: Number(phenomeQueryForm.value.limit || 20),
      };
    }
    if (queryOperation.value === 'trait_list' || queryOperation.value === 'subject_list') {
      return {
        limit: Number(phenomeQueryForm.value.limit || 20),
      };
    }
    return {};
  }
  if (isSignalAdapter.value && queryMode.value === 'smart') {
    if (queryOperation.value === 'region_features') {
      return {
        seq_id: signalQueryForm.value.seqId.trim(),
        start: Number(signalQueryForm.value.start),
        end: Number(signalQueryForm.value.end),
        limit: Number(signalQueryForm.value.limit || 100),
      };
    }
    if (queryOperation.value === 'region_signal') {
      return {
        seq_id: signalQueryForm.value.seqId.trim(),
        start: Number(signalQueryForm.value.start),
        end: Number(signalQueryForm.value.end),
        bins: Number(signalQueryForm.value.bins || 20),
        summary_type: signalQueryForm.value.summaryType.trim() || 'mean',
      };
    }
    return {};
  }
  if (isInteractionAdapter.value && queryMode.value === 'smart') {
    if (queryOperation.value === 'region_contacts') {
      return {
        seq_id: interactionQueryForm.value.seqId.trim(),
        start: Number(interactionQueryForm.value.start),
        end: Number(interactionQueryForm.value.end),
        target_chrom: interactionQueryForm.value.targetChrom.trim() || undefined,
        target_start: Number(interactionQueryForm.value.targetStart),
        target_end: Number(interactionQueryForm.value.targetEnd),
        limit: Number(interactionQueryForm.value.limit || 100),
      };
    }
    if (queryOperation.value === 'matrix_slice') {
      return {
        chrom: interactionQueryForm.value.seqId.trim(),
        start: Number(interactionQueryForm.value.start),
        end: Number(interactionQueryForm.value.end),
        target_chrom: interactionQueryForm.value.targetChrom.trim() || undefined,
        target_start: interactionQueryForm.value.targetChrom.trim()
          ? Number(interactionQueryForm.value.targetStart)
          : undefined,
        target_end: interactionQueryForm.value.targetChrom.trim()
          ? Number(interactionQueryForm.value.targetEnd)
          : undefined,
        resolution: Number(interactionQueryForm.value.resolution || 10000),
        balanced: Boolean(interactionQueryForm.value.balanced),
        limit_bins: Number(interactionQueryForm.value.limitBins || 25),
      };
    }
    return {};
  }
  return JSON.parse(queryParamsText.value || '{}');
}

async function loadDatasets() {
  loading.value = true;
  errorText.value = '';
  try {
    const response = await fetch(`${API_BASE}/public/dataset/list`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ page: 1, size: 50 }),
    });
    const payload = await response.json();
    if (payload.code !== 2000) {
      throw new Error(payload.msg || 'Failed to load datasets');
    }
    datasets.value = payload.data?.dataList || [];
    total.value = payload.data?.total || 0;
    if (!selectedDatasetId.value && datasets.value.length > 0) {
      selectedDatasetId.value = datasets.value[0].id;
    }
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : 'Unknown error';
    datasets.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

async function loadDatasetDetail(datasetId: number) {
  detailLoading.value = true;
  queryError.value = '';
  queryResult.value = null;
  copyFeedback.value = '';
  try {
    const versionsResponse = await fetch(`${API_BASE}/public/dataset/version/list`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: datasetId,
        keyword: versionFilters.value.keyword.trim() || undefined,
        is_default_public:
          versionFilters.value.isDefaultPublic === 'all'
            ? undefined
            : versionFilters.value.isDefaultPublic === 'yes',
        is_current:
          versionFilters.value.isCurrent === 'all' ? undefined : versionFilters.value.isCurrent === 'yes',
      }),
    });
    const versionsPayload = await versionsResponse.json();
    if (versionsPayload.code !== 2000) {
      throw new Error(versionsPayload.msg || 'Failed to load dataset versions');
    }
    publicVersions.value = versionsPayload.data?.items || [];
    publicVersionTotal.value = Number(versionsPayload.data?.total || publicVersions.value.length || 0);
    const requestedVersionId = selectedVersionId.value;
    const nextVersionId = publicVersions.value.some((item) => item.id === requestedVersionId)
      ? requestedVersionId
      : versionsPayload.data?.default_public_version?.id || publicVersions.value[0]?.id || null;
    selectedVersionId.value = nextVersionId;
    if (!nextVersionId) {
      selectedDetail.value = null;
      selectedCapabilities.value = null;
      return;
    }

    const [detailResponse, capabilitiesResponse] = await Promise.all([
      fetch(`${API_BASE}/public/dataset/version/info`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: datasetId, version_id: nextVersionId }),
      }),
      fetch(`${API_BASE}/public/dataset/version/query/capabilities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: datasetId, version_id: nextVersionId }),
      }),
    ]);
    const detailPayload = await detailResponse.json();
    const capabilitiesPayload = await capabilitiesResponse.json();
    if (detailPayload.code !== 2000) {
      throw new Error(detailPayload.msg || 'Failed to load dataset detail');
    }
    if (capabilitiesPayload.code !== 2000) {
      throw new Error(capabilitiesPayload.msg || 'Failed to load dataset capabilities');
    }
    selectedDetail.value = detailPayload.data || null;
    selectedCapabilities.value = capabilitiesPayload.data || null;
    applyFirstExample(selectedDetail.value);
  } catch (error) {
    publicVersions.value = [];
    publicVersionTotal.value = 0;
    selectedVersionId.value = null;
    selectedDetail.value = null;
    selectedCapabilities.value = null;
    queryError.value = error instanceof Error ? error.message : 'Unknown error';
  } finally {
    detailLoading.value = false;
  }
}

async function handleVersionChange(event: Event) {
  const value = Number((event.target as HTMLSelectElement).value || 0);
  selectedVersionId.value = Number.isFinite(value) && value > 0 ? value : null;
  if (selectedDatasetId.value) {
    await loadDatasetDetail(selectedDatasetId.value);
  }
}

async function reloadVersionFilters() {
  if (selectedDatasetId.value) {
    await loadDatasetDetail(selectedDatasetId.value);
  }
}

async function resetVersionFilters() {
  versionFilters.value = {
    keyword: '',
    isDefaultPublic: 'all',
    isCurrent: 'all',
  };
  await reloadVersionFilters();
}

async function runQuery() {
  if (!selectedDatasetId.value || !selectedVersionId.value || !queryOperation.value) {
    queryError.value = '请选择数据集并填写查询操作';
    return;
  }
  queryLoading.value = true;
  queryError.value = '';
  queryResult.value = null;
  copyFeedback.value = '';
  try {
    const parsedParams = buildQueryParams();
    if (isSequenceAdapter.value && queryMode.value === 'smart') {
      if (queryOperation.value === 'batch_fetch') {
        if (!Array.isArray(parsedParams.regions) || parsedParams.regions.length === 0) {
          throw new Error('请至少填写一个区间');
        }
      } else if (!String(parsedParams.seq_id || '').trim()) {
        throw new Error('请填写序列 ID');
      } else if (!Number.isFinite(Number(parsedParams.start)) || !Number.isFinite(Number(parsedParams.end))) {
        throw new Error('起止坐标必须是数字');
      }
    } else if (isVariantAdapter.value && queryMode.value === 'smart') {
      if (queryOperation.value === 'query' && (!Array.isArray(parsedParams.regions) || parsedParams.regions.length === 0)) {
        throw new Error('请至少填写一个变异区间');
      }
    } else if (isAnnotationAdapter.value && queryMode.value === 'smart') {
      if (queryOperation.value === 'gene_lookup' && !String(parsedParams.gene_id || '').trim()) {
        throw new Error('请填写 gene_id');
      }
      if (queryOperation.value === 'region_features') {
        if (!String(parsedParams.seq_id || '').trim()) {
          throw new Error('请填写 seq_id');
        }
        if (!Number.isFinite(Number(parsedParams.start)) || !Number.isFinite(Number(parsedParams.end))) {
          throw new Error('起止坐标必须是数字');
        }
      }
    } else if (isFunctionalAnnotationAdapter.value && queryMode.value === 'smart') {
      if (
        (queryOperation.value === 'gene_detail' || queryOperation.value === 'gene_function_summary') &&
        !String(parsedParams.gene_id || '').trim()
      ) {
        throw new Error('请填写 gene_id');
      }
      if (queryOperation.value === 'transcript_detail' && !String(parsedParams.transcript_id || '').trim()) {
        throw new Error('请填写 transcript_id');
      }
      if (queryOperation.value === 'term_gene_list') {
        if (!String(parsedParams.term_source || '').trim()) {
          throw new Error('请填写 term_source');
        }
        if (!String(parsedParams.term_id || '').trim()) {
          throw new Error('请填写 term_id');
        }
      }
    } else if (isPhenomeAdapter.value && queryMode.value === 'smart') {
      if (queryOperation.value === 'subject_detail' && !String(parsedParams.subject_id || '').trim()) {
        throw new Error('请填写 subject_id');
      }
      if (queryOperation.value === 'trait_values' && !String(parsedParams.trait || '').trim()) {
        throw new Error('请填写 trait');
      }
    } else if (isSignalAdapter.value && queryMode.value === 'smart') {
      if (queryOperation.value === 'region_features' || queryOperation.value === 'region_signal') {
        if (!String(parsedParams.seq_id || '').trim()) {
          throw new Error('请填写 seq_id');
        }
        if (!Number.isFinite(Number(parsedParams.start)) || !Number.isFinite(Number(parsedParams.end))) {
          throw new Error('起止坐标必须是数字');
        }
        if (
          queryOperation.value === 'region_signal' &&
          !Number.isFinite(Number(parsedParams.bins || 0))
        ) {
          throw new Error('bins 必须是数字');
        }
      }
    } else if (isInteractionAdapter.value && queryMode.value === 'smart') {
      if (queryOperation.value === 'region_contacts') {
        if (!String(parsedParams.seq_id || '').trim()) {
          throw new Error('请填写 anchor seq_id');
        }
        if (!Number.isFinite(Number(parsedParams.start)) || !Number.isFinite(Number(parsedParams.end))) {
          throw new Error('anchor 起止坐标必须是数字');
        }
      }
    }
    const response = await fetch(`${API_BASE}/public/dataset/version/query/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: selectedDatasetId.value,
        version_id: selectedVersionId.value,
        operation: queryOperation.value,
        params: parsedParams,
      }),
    });
    const payload = await response.json();
    if (payload.code !== 2000) {
      throw new Error(payload.msg || 'Failed to execute public query');
    }
    queryResult.value = payload.data;
  } catch (error) {
    queryError.value = error instanceof Error ? error.message : 'Unknown error';
  } finally {
    queryLoading.value = false;
  }
}

watch(selectedDatasetId, async (datasetId) => {
  if (!datasetId) {
    return;
  }
  await loadDatasetDetail(datasetId);
});

watch(
  sequenceQueryForm,
  (value) => {
    if (!isSequenceAdapter.value || queryMode.value !== 'smart' || queryOperation.value === 'batch_fetch') {
      return;
    }
    queryParamsText.value = JSON.stringify(
      {
        seq_id: value.seq_id,
        start: Number(value.start),
        end: Number(value.end),
      },
      null,
      2,
    );
  },
  { deep: true },
);

watch(sequenceBatchRegionsText, (value) => {
  if (!isSequenceAdapter.value || queryMode.value !== 'smart' || queryOperation.value !== 'batch_fetch') {
    return;
  }
  try {
    queryParamsText.value = JSON.stringify({ regions: parseSequenceBatchRegions(value) }, null, 2);
  } catch {
    queryParamsText.value = JSON.stringify({ regions: [] }, null, 2);
  }
});

watch(queryOperation, (value) => {
  if (queryMode.value !== 'smart') {
    return;
  }
  if (isSequenceAdapter.value) {
    if (value === 'batch_fetch') {
      try {
        queryParamsText.value = JSON.stringify({ regions: parseSequenceBatchRegions(sequenceBatchRegionsText.value) }, null, 2);
      } catch {
        queryParamsText.value = JSON.stringify({ regions: [] }, null, 2);
      }
      return;
    }
    queryParamsText.value = JSON.stringify(
      {
        seq_id: sequenceQueryForm.value.seq_id,
        start: Number(sequenceQueryForm.value.start),
        end: Number(sequenceQueryForm.value.end),
      },
      null,
      2,
    );
    return;
  }
  if (isVariantAdapter.value) {
    queryParamsText.value = value === 'query'
      ? JSON.stringify(
          {
            regions: splitLines(variantQueryForm.value.regionsText),
            include_samples: splitLines(variantQueryForm.value.includeSamplesText),
            exclude_samples: splitLines(variantQueryForm.value.excludeSamplesText),
          },
          null,
          2,
        )
      : '{}';
    return;
  }
  if (isExpressionAdapter.value) {
    queryParamsText.value =
      value === 'matrix_slice'
        ? JSON.stringify(
            {
              data_type: expressionQueryForm.value.dataType,
              genes: splitLines(expressionQueryForm.value.genesText),
              samples: splitLines(expressionQueryForm.value.samplesText),
            },
            null,
            2,
          )
        : JSON.stringify({ max_records: Number(expressionQueryForm.value.maxRecords || 20) }, null, 2);
    return;
  }
  if (isAnnotationAdapter.value) {
    queryParamsText.value =
      value === 'gene_lookup'
        ? JSON.stringify({ gene_id: annotationQueryForm.value.geneId.trim() }, null, 2)
        : value === 'region_features'
          ? JSON.stringify(
              {
                seq_id: annotationQueryForm.value.seqId.trim(),
                start: Number(annotationQueryForm.value.start),
                end: Number(annotationQueryForm.value.end),
                feature_type: annotationQueryForm.value.featureType.trim() || 'gene',
                limit: Number(annotationQueryForm.value.limit || 100),
              },
              null,
              2,
            )
          : '{}';
    return;
  }
  if (isFunctionalAnnotationAdapter.value) {
    queryParamsText.value =
      value === 'transcript_detail'
        ? JSON.stringify({ transcript_id: functionalQueryForm.value.transcriptId.trim() }, null, 2)
        : value === 'term_lookup'
          ? JSON.stringify(
              {
                term_source: functionalQueryForm.value.termSource,
                keyword: functionalQueryForm.value.keyword.trim() || undefined,
                term_id: functionalQueryForm.value.termId.trim() || undefined,
                limit: Number(functionalQueryForm.value.limit || 20),
              },
              null,
              2,
            )
          : value === 'term_gene_list'
            ? JSON.stringify(
                {
                  term_source: functionalQueryForm.value.termSource,
                  term_id: functionalQueryForm.value.termId.trim(),
                  page: Number(functionalQueryForm.value.page || 1),
                  size: Number(functionalQueryForm.value.size || 20),
                },
                null,
                2,
              )
            : value === 'term_aggregation'
              ? JSON.stringify(
                  {
                    term_source: functionalQueryForm.value.termSource || undefined,
                    limit: Number(functionalQueryForm.value.limit || 20),
                  },
                  null,
                  2,
                )
              : JSON.stringify({ gene_id: functionalQueryForm.value.geneId.trim() }, null, 2);
    return;
  }
  if (isPhenomeAdapter.value) {
    queryParamsText.value =
      value === 'subject_detail'
        ? JSON.stringify({ subject_id: phenomeQueryForm.value.subjectId.trim() }, null, 2)
        : value === 'trait_search'
          ? JSON.stringify(
              {
                keyword: phenomeQueryForm.value.keyword.trim() || undefined,
                limit: Number(phenomeQueryForm.value.limit || 20),
              },
              null,
              2,
            )
          : value === 'trait_values'
            ? JSON.stringify(
                {
                  trait: phenomeQueryForm.value.trait.trim(),
                  timepoint: phenomeQueryForm.value.timepoint.trim() || undefined,
                  limit: Number(phenomeQueryForm.value.limit || 20),
                },
                null,
                2,
              )
            : value === 'trait_list' || value === 'subject_list'
              ? JSON.stringify({ limit: Number(phenomeQueryForm.value.limit || 20) }, null, 2)
              : '{}';
    return;
  }
  if (isSignalAdapter.value) {
    queryParamsText.value =
      value === 'region_features'
        ? JSON.stringify(
            {
              seq_id: signalQueryForm.value.seqId.trim(),
              start: Number(signalQueryForm.value.start),
              end: Number(signalQueryForm.value.end),
              limit: Number(signalQueryForm.value.limit || 100),
            },
            null,
            2,
          )
        : '{}';
    return;
  }
  if (isInteractionAdapter.value) {
    queryParamsText.value =
      value === 'region_contacts'
        ? JSON.stringify(
            {
              seq_id: interactionQueryForm.value.seqId.trim(),
              start: Number(interactionQueryForm.value.start),
              end: Number(interactionQueryForm.value.end),
              target_chrom: interactionQueryForm.value.targetChrom.trim() || undefined,
              target_start: Number(interactionQueryForm.value.targetStart),
              target_end: Number(interactionQueryForm.value.targetEnd),
              limit: Number(interactionQueryForm.value.limit || 100),
            },
            null,
            2,
          )
        : value === 'matrix_slice'
          ? JSON.stringify(
              {
                chrom: interactionQueryForm.value.seqId.trim(),
                start: Number(interactionQueryForm.value.start),
                end: Number(interactionQueryForm.value.end),
                target_chrom: interactionQueryForm.value.targetChrom.trim() || undefined,
                target_start: interactionQueryForm.value.targetChrom.trim()
                  ? Number(interactionQueryForm.value.targetStart)
                  : undefined,
                target_end: interactionQueryForm.value.targetChrom.trim()
                  ? Number(interactionQueryForm.value.targetEnd)
                  : undefined,
                resolution: Number(interactionQueryForm.value.resolution || 10000),
                balanced: Boolean(interactionQueryForm.value.balanced),
                limit_bins: Number(interactionQueryForm.value.limitBins || 25),
              },
              null,
              2,
            )
        : '{}';
  }
});

watch(
  variantQueryForm,
  (value) => {
    if (!isVariantAdapter.value || queryMode.value !== 'smart' || queryOperation.value !== 'query') {
      return;
    }
    queryParamsText.value = JSON.stringify(
      {
        regions: splitLines(value.regionsText),
        include_samples: splitLines(value.includeSamplesText),
        exclude_samples: splitLines(value.excludeSamplesText),
      },
      null,
      2,
    );
  },
  { deep: true },
);

watch(
  expressionQueryForm,
  (value) => {
    if (!isExpressionAdapter.value || queryMode.value !== 'smart') {
      return;
    }
    queryParamsText.value =
      queryOperation.value === 'matrix_slice'
        ? JSON.stringify(
            {
              data_type: value.dataType,
              genes: splitLines(value.genesText),
              samples: splitLines(value.samplesText),
            },
            null,
            2,
          )
        : JSON.stringify({ max_records: Number(value.maxRecords || 20) }, null, 2);
  },
  { deep: true },
);

watch(
  interactionQueryForm,
  (value) => {
    if (!isInteractionAdapter.value || queryMode.value !== 'smart') {
      return;
    }
    queryParamsText.value =
      queryOperation.value === 'region_contacts'
        ? JSON.stringify(
            {
              seq_id: value.seqId.trim(),
              start: Number(value.start),
              end: Number(value.end),
              target_chrom: value.targetChrom.trim() || undefined,
              target_start: Number(value.targetStart),
              target_end: Number(value.targetEnd),
              limit: Number(value.limit || 100),
            },
            null,
            2,
          )
        : queryOperation.value === 'matrix_slice'
          ? JSON.stringify(
              {
                chrom: value.seqId.trim(),
                start: Number(value.start),
                end: Number(value.end),
                target_chrom: value.targetChrom.trim() || undefined,
                target_start: value.targetChrom.trim() ? Number(value.targetStart) : undefined,
                target_end: value.targetChrom.trim() ? Number(value.targetEnd) : undefined,
                resolution: Number(value.resolution || 10000),
                balanced: Boolean(value.balanced),
                limit_bins: Number(value.limitBins || 25),
              },
              null,
              2,
            )
          : '{}';
  },
  { deep: true },
);

watch(
  annotationQueryForm,
  (value) => {
    if (!isAnnotationAdapter.value || queryMode.value !== 'smart') {
      return;
    }
    queryParamsText.value =
      queryOperation.value === 'gene_lookup'
        ? JSON.stringify({ gene_id: value.geneId.trim() }, null, 2)
        : queryOperation.value === 'region_features'
          ? JSON.stringify(
              {
                seq_id: value.seqId.trim(),
                start: Number(value.start),
                end: Number(value.end),
                feature_type: value.featureType.trim() || 'gene',
                limit: Number(value.limit || 100),
              },
              null,
              2,
            )
          : '{}';
  },
  { deep: true },
);

watch(
  functionalQueryForm,
  (value) => {
    if (!isFunctionalAnnotationAdapter.value || queryMode.value !== 'smart') {
      return;
    }
    queryParamsText.value =
      queryOperation.value === 'transcript_detail'
        ? JSON.stringify({ transcript_id: value.transcriptId.trim() }, null, 2)
        : queryOperation.value === 'term_lookup'
          ? JSON.stringify(
              {
                term_source: value.termSource,
                keyword: value.keyword.trim() || undefined,
                term_id: value.termId.trim() || undefined,
                limit: Number(value.limit || 20),
              },
              null,
              2,
            )
          : queryOperation.value === 'term_gene_list'
            ? JSON.stringify(
                {
                  term_source: value.termSource,
                  term_id: value.termId.trim(),
                  page: Number(value.page || 1),
                  size: Number(value.size || 20),
                },
                null,
                2,
              )
            : queryOperation.value === 'term_aggregation'
              ? JSON.stringify(
                  {
                    term_source: value.termSource || undefined,
                    limit: Number(value.limit || 20),
                  },
                  null,
                  2,
                )
              : JSON.stringify({ gene_id: value.geneId.trim() }, null, 2);
  },
  { deep: true },
);

watch(
  phenomeQueryForm,
  (value) => {
    if (!isPhenomeAdapter.value || queryMode.value !== 'smart') {
      return;
    }
    queryParamsText.value =
      queryOperation.value === 'subject_detail'
        ? JSON.stringify({ subject_id: value.subjectId.trim() }, null, 2)
        : queryOperation.value === 'trait_search'
          ? JSON.stringify(
              {
                keyword: value.keyword.trim() || undefined,
                limit: Number(value.limit || 20),
              },
              null,
              2,
            )
          : queryOperation.value === 'trait_values'
            ? JSON.stringify(
                {
                  trait: value.trait.trim(),
                  timepoint: value.timepoint.trim() || undefined,
                  limit: Number(value.limit || 20),
                },
                null,
                2,
              )
            : queryOperation.value === 'trait_list' || queryOperation.value === 'subject_list'
              ? JSON.stringify({ limit: Number(value.limit || 20) }, null, 2)
              : '{}';
  },
  { deep: true },
);

watch(
  signalQueryForm,
  (value) => {
    if (!isSignalAdapter.value || queryMode.value !== 'smart') {
      return;
    }
    queryParamsText.value =
      queryOperation.value === 'region_features'
        ? JSON.stringify(
            {
              seq_id: value.seqId.trim(),
              start: Number(value.start),
              end: Number(value.end),
              limit: Number(value.limit || 100),
            },
            null,
            2,
          )
        : '{}';
  },
  { deep: true },
);

watch(
  interactionQueryForm,
  (value) => {
    if (!isInteractionAdapter.value || queryMode.value !== 'smart') {
      return;
    }
    queryParamsText.value =
      queryOperation.value === 'region_contacts'
        ? JSON.stringify(
            {
              seq_id: value.seqId.trim(),
              start: Number(value.start),
              end: Number(value.end),
              target_chrom: value.targetChrom.trim() || undefined,
              target_start: Number(value.targetStart),
              target_end: Number(value.targetEnd),
              limit: Number(value.limit || 100),
            },
            null,
            2,
          )
        : '{}';
  },
  { deep: true },
);

onMounted(loadDatasets);
</script>

<template>
  <main class="portal-shell">
    <section class="hero">
      <p class="eyebrow">FAN Omics Portal</p>
      <h1>Public Dataset Portal</h1>
      <p class="hero-copy">
        面向公开组学数据的统一入口。当前页面直接消费后台公开 API，
        提供目录浏览、数据详情和在线查询能力。
      </p>
      <div class="hero-actions">
        <input
          v-model="keyword"
          class="search-input"
          placeholder="搜索 dataset / 物种 / 组装版本"
        />
        <button class="ghost-button" type="button" @click="loadDatasets">
          刷新目录
        </button>
      </div>
    </section>

    <section class="summary">
      <div class="summary-card">
        <span class="summary-label">公开数据集</span>
        <strong>{{ total }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">筛选结果</span>
        <strong>{{ filteredDatasets.length }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">当前选中</span>
        <strong>{{ selectedDataset?.title || selectedDataset?.dataset_code || '-' }}</strong>
      </div>
    </section>

    <section class="portal-grid">
      <section class="catalog">
        <header class="section-head">
          <h2>Dataset Catalog</h2>
          <span v-if="loading">加载中...</span>
        </header>

        <div v-if="errorText" class="state-card error-card">
          {{ errorText }}
        </div>

        <div v-else-if="loading" class="state-card">
          正在从 `/api/v1/public/dataset/list` 加载公开数据...
        </div>

        <div v-else-if="filteredDatasets.length === 0" class="state-card">
          当前还没有公开 dataset。
        </div>

        <div v-else class="dataset-list">
          <button
            v-for="dataset in filteredDatasets"
            :key="dataset.id"
            class="dataset-card"
            :class="{ active: selectedDatasetId === dataset.id }"
            type="button"
            @click="selectedDatasetId = dataset.id"
          >
            <div class="dataset-card-head">
              <span class="dataset-kind">{{ dataset.dataset_type || 'generic' }}</span>
              <span class="dataset-version">{{ dataset.version || 'v?' }}</span>
            </div>
            <h3>{{ dataset.title || dataset.dataset_code || `dataset-${dataset.id}` }}</h3>
            <dl class="dataset-meta">
              <div>
                <dt>Code</dt>
                <dd>{{ dataset.dataset_code || '-' }}</dd>
              </div>
              <div>
                <dt>Organism</dt>
                <dd>{{ dataset.organism || '-' }}</dd>
              </div>
              <div>
                <dt>Assembly</dt>
                <dd>{{ dataset.assembly || '-' }}</dd>
              </div>
            </dl>
          </button>
        </div>
      </section>

      <section class="detail-panel">
        <header class="section-head">
          <h2>Dataset Detail</h2>
          <span v-if="detailLoading">加载中...</span>
        </header>

        <div v-if="detailLoading" class="state-card">
          正在加载公开 dataset 详情...
        </div>

        <div v-else-if="!selectedDetail" class="state-card">
          请选择一个公开 dataset。
        </div>

        <template v-else>
          <div class="detail-card">
            <div class="detail-top">
              <div>
                <p class="eyebrow inner">{{ selectedDetail.dataset_type || 'generic' }}</p>
                <h3>{{ selectedDetail.title || selectedDetail.dataset_code || `dataset-${selectedDetail.id}` }}</h3>
              </div>
              <div class="detail-version-panel">
                <select
                  v-if="publicVersions.length"
                  :value="selectedVersionId || ''"
                  class="search-input compact version-select"
                  @change="handleVersionChange"
                >
                  <option v-for="version in publicVersions" :key="version.id" :value="version.id">
                    {{ version.version || 'v?' }}{{ version.is_default_public ? ' · default public' : '' }}
                  </option>
                </select>
                <div class="detail-badge">{{ selectedDetail.version || 'v?' }}</div>
              </div>
            </div>
            <div class="version-filter-bar">
              <input
                :value="versionFilters.keyword"
                class="search-input compact"
                placeholder="Filter versions by version/title"
                @change="
                  async (event) => {
                    versionFilters.keyword = String((event.target as HTMLInputElement).value || '');
                    await reloadVersionFilters();
                  }
                "
              />
              <select
                :value="versionFilters.isDefaultPublic"
                class="search-input compact version-filter-select"
                @change="
                  async (event) => {
                    versionFilters.isDefaultPublic = String((event.target as HTMLSelectElement).value || 'all');
                    await reloadVersionFilters();
                  }
                "
              >
                <option value="all">All Public Versions</option>
                <option value="yes">Default Public Only</option>
                <option value="no">Exclude Default Public</option>
              </select>
              <select
                :value="versionFilters.isCurrent"
                class="search-input compact version-filter-select"
                @change="
                  async (event) => {
                    versionFilters.isCurrent = String((event.target as HTMLSelectElement).value || 'all');
                    await reloadVersionFilters();
                  }
                "
              >
                <option value="all">All Current States</option>
                <option value="yes">Current Version Only</option>
                <option value="no">Exclude Current Version</option>
              </select>
              <button class="tiny-button" type="button" @click="resetVersionFilters">
                Reset
              </button>
            </div>
            <p class="detail-note version-filter-note">
              Showing {{ publicVersions.length }} version(s){{ publicVersionTotal ? ` / filtered total ${publicVersionTotal}` : '' }}.
            </p>
            <dl class="detail-meta">
              <div>
                <dt>Dataset Code</dt>
                <dd>{{ selectedDetail.dataset_code || '-' }}</dd>
              </div>
              <div>
                <dt>Selected Version</dt>
                <dd>
                  {{ selectedVersion?.version || selectedDetail.selected_version?.version || selectedDetail.version || '-' }}
                </dd>
              </div>
              <div>
                <dt>Default Public</dt>
                <dd>{{ selectedDetail.default_public_version?.version || '-' }}</dd>
              </div>
              <div>
                <dt>Query Adapter</dt>
                <dd>{{ selectedDetail.query_adapter?.display_name || '-' }}</dd>
              </div>
              <div>
                <dt>File Format</dt>
                <dd>{{ selectedDetail.query_profile?.file_format || '-' }}</dd>
              </div>
              <div>
                <dt>Query Engine</dt>
                <dd>{{ selectedDetail.query_profile?.query_engine || '-' }}</dd>
              </div>
              <div>
                <dt>Released Versions</dt>
                <dd>{{ publicVersions.length || selectedDetail.released_versions?.length || 0 }}</dd>
              </div>
            </dl>
            <div class="public-status-grid">
              <article v-for="card in selectedVersionStatusCards" :key="card.key" class="summary-card status-summary-card">
                <span class="summary-label">{{ card.label }}</span>
                <strong>{{ card.value }}</strong>
                <p>{{ card.hint }}</p>
              </article>
            </div>
            <p class="detail-note">{{ selectedVersionStatusText }}</p>
          </div>

          <div v-if="selectedCapabilities" class="detail-card">
            <div class="query-head">
              <h3>Query Capabilities</h3>
              <span class="capability-badge">
                {{ selectedCapabilities.query_adapter?.display_name || '-' }}
              </span>
            </div>
            <dl class="detail-meta">
              <div>
                <dt>Selected Public Version</dt>
                <dd>{{ selectedCapabilities.published_version?.version || selectedDetail.version || '-' }}</dd>
              </div>
              <div>
                <dt>Default Public Version</dt>
                <dd>{{ selectedCapabilities.default_public_version?.version || '-' }}</dd>
              </div>
              <div>
                <dt>Entry Asset</dt>
                <dd>
                  {{
                    selectedCapabilities.query_entry_asset?.asset_name ||
                    selectedCapabilities.query_entry_asset?.asset_code ||
                    '-'
                  }}
                </dd>
              </div>
              <div>
                <dt>Engine Ready</dt>
                <dd>{{ selectedCapabilities.file_access?.exists_on_server ? 'Yes' : 'No' }}</dd>
              </div>
            </dl>
            <div class="capability-group">
              <span class="summary-label">Supported Operations</span>
              <div class="capability-chip-list">
                <button
                  v-for="operation in supportedOperations"
                  :key="operation"
                  class="tiny-button"
                  :class="{ active: queryOperation === operation }"
                  type="button"
                  @click="queryOperation = operation"
                >
                  {{ operation }}
                </button>
                <span v-if="supportedOperations.length === 0" class="muted-path">No declared operations</span>
              </div>
            </div>
            <div class="capability-group">
              <span class="summary-label">Adapter Landscape</span>
              <div class="capability-chip-list">
                <span
                  v-for="adapter in selectedCapabilities.available_adapters || []"
                  :key="adapter.adapter"
                  class="adapter-chip"
                >
                  {{ adapter.display_name || adapter.adapter || '-' }}
                </span>
              </div>
            </div>
          </div>

          <div class="detail-card">
            <div class="query-head">
              <h3>Dataset Relationships</h3>
              <span class="capability-badge">{{ selectedLineage.length }} links</span>
            </div>
            <div v-if="!selectedLineage.length" class="state-inline">
              当前公开版本没有可展示的 lineage 关系。
            </div>
            <div v-else class="asset-list">
              <article v-for="lineage in selectedLineage" :key="lineage.id" class="asset-card">
                <div class="asset-head">
                  <div class="asset-head-main">
                    <strong>{{ getLineageLabel(lineage) }}</strong>
                    <p class="muted-path">{{ getLineageSummary(lineage) }}</p>
                  </div>
                  <div class="capability-chip-list asset-chip-list">
                    <span class="adapter-chip">{{ getLineagePeer(lineage, selectedVersionId).datasetType || '-' }}</span>
                    <span class="adapter-chip emphasis-chip">
                      {{ getLineagePeer(lineage, selectedVersionId).direction === 'outbound' ? 'Outgoing' : 'Incoming' }}
                    </span>
                  </div>
                </div>
                <p class="asset-summary">
                  {{
                    getLineagePeer(lineage, selectedVersionId).datasetTitle ||
                    `dataset-${getLineagePeer(lineage, selectedVersionId).datasetId || lineage.id}`
                  }}
                  <template v-if="getLineagePeer(lineage, selectedVersionId).version">
                    · {{ getLineagePeer(lineage, selectedVersionId).version }}
                  </template>
                  <template v-if="getLineagePeer(lineage, selectedVersionId).assetCode">
                    · {{ getLineagePeer(lineage, selectedVersionId).assetCode }}
                  </template>
                </p>
              </article>
            </div>
          </div>

          <div class="detail-card">
            <h3>Assets</h3>
            <div v-if="!selectedDetail.assets?.length" class="state-inline">
              当前没有公开资产信息。
            </div>
            <div v-else class="asset-list">
              <article v-for="asset in selectedDetail.assets" :key="asset.id" class="asset-card">
                <div class="asset-head">
                  <div class="asset-head-main">
                    <strong>{{ asset.asset_name || asset.asset_code || `asset-${asset.id}` }}</strong>
                    <p class="muted-path">{{ getPublicAssetMeta(asset) }}</p>
                  </div>
                  <div class="capability-chip-list asset-chip-list">
                    <span class="adapter-chip">{{ asset.asset_type || '-' }}</span>
                    <span
                      v-for="label in getPublicAssetLabels(asset)"
                      :key="`${asset.id}-${label}`"
                      class="adapter-chip emphasis-chip"
                    >
                      {{ label }}
                    </span>
                  </div>
                </div>
                <p class="asset-summary">{{ getPublicAssetCoverage(asset) }}</p>
                <div v-if="asset.files?.length" class="asset-files">
                  <div v-for="file in getPublicSortedAssetFiles(asset)" :key="file.id" class="asset-file-card">
                    <div class="asset-file-head">
                      <div class="capability-chip-list asset-chip-list">
                        <span class="adapter-chip role-chip">{{ getPublicFileRoleLabel(file) }}</span>
                        <span v-if="isPublicPrimaryFile(asset, file)" class="adapter-chip primary-chip">Query File</span>
                        <span v-if="file.file_format" class="adapter-chip">{{ file.file_format }}</span>
                      </div>
                      <code>{{ getPublicFileDisplayName(file) }}</code>
                    </div>
                    <p class="muted-path">{{ getPublicFileSummary(asset, file) }}</p>
                  </div>
                </div>
              </article>
            </div>
          </div>

          <div class="detail-card">
            <div class="query-head">
              <h3>Public Query</h3>
              <div class="example-actions">
                <button
                  v-for="(example, key) in queryExamples"
                  :key="key"
                  class="tiny-button"
                  type="button"
                  @click="applyQueryExample(example)"
                >
                  {{ key }}
                </button>
              </div>
            </div>
            <div class="query-form">
              <label>
                <span>Operation</span>
                <select v-if="supportedOperations.length" v-model="queryOperation" class="search-input compact">
                  <option v-for="operation in supportedOperations" :key="operation" :value="operation">
                    {{ operation }}
                  </option>
                </select>
                <input v-else v-model="queryOperation" class="search-input compact" />
              </label>
              <div v-if="isSequenceAdapter || isVariantAdapter || isExpressionAdapter || isAnnotationAdapter || isFunctionalAnnotationAdapter || isPhenomeAdapter || isSignalAdapter || isInteractionAdapter" class="query-mode-switch">
                <button
                  class="tiny-button"
                  :class="{ active: queryMode === 'smart' }"
                  type="button"
                  @click="queryMode = 'smart'"
                >
                  Smart 表单
                </button>
                <button
                  class="tiny-button"
                  :class="{ active: queryMode === 'json' }"
                  type="button"
                  @click="queryMode = 'json'"
                >
                  JSON 模式
                </button>
              </div>
              <div v-if="isSequenceAdapter && queryMode === 'smart' && selectedLineage.length" class="query-hint">
                当前版本的 lineage 已在上方展示，可结合关系信息查看参考基因组、注释或表达资产。
              </div>
              <div v-if="isSequenceAdapter && queryMode === 'smart'" class="sequence-query-grid">
                <label v-if="!isSequenceBatchOperation">
                  <span>Sequence ID</span>
                  <input v-model="sequenceQueryForm.seq_id" class="search-input compact" placeholder="例如 chr1" />
                </label>
                <label v-if="!isSequenceBatchOperation">
                  <span>Start</span>
                  <input v-model.number="sequenceQueryForm.start" class="search-input compact" type="number" min="1" />
                </label>
                <label v-if="!isSequenceBatchOperation">
                  <span>End</span>
                  <input v-model.number="sequenceQueryForm.end" class="search-input compact" type="number" min="1" />
                </label>
                <label v-if="isSequenceBatchOperation" class="sequence-batch-field">
                  <span>Regions</span>
                  <textarea
                    v-model="sequenceBatchRegionsText"
                    class="query-textarea"
                    placeholder="每行一个区间，例如&#10;chr1:1-100&#10;chr1:200-300"
                  ></textarea>
                </label>
              </div>
              <div v-if="isVariantAdapter && queryMode === 'smart'" class="sequence-query-grid">
                <label v-if="queryOperation === 'query'" class="sequence-batch-field">
                  <span>Regions</span>
                  <textarea
                    v-model="variantQueryForm.regionsText"
                    class="query-textarea"
                    placeholder="每行一个区间，例如&#10;Chr1:1000-2000&#10;Chr2:3000-4500"
                  ></textarea>
                </label>
                <label v-if="queryOperation === 'query'">
                  <span>Include Samples</span>
                  <textarea
                    v-model="variantQueryForm.includeSamplesText"
                    class="query-textarea compact-area"
                    placeholder="每行一个 sample，可留空"
                  ></textarea>
                </label>
                <label v-if="queryOperation === 'query'">
                  <span>Exclude Samples</span>
                  <textarea
                    v-model="variantQueryForm.excludeSamplesText"
                    class="query-textarea compact-area"
                    placeholder="每行一个 sample，可留空"
                  ></textarea>
                </label>
                <div v-if="queryOperation !== 'query'" class="query-hint">
                  当前操作不需要额外参数，可直接执行。
                </div>
              </div>
              <div v-if="isExpressionAdapter && queryMode === 'smart'" class="sequence-query-grid">
                <label v-if="queryOperation === 'genes_list' || queryOperation === 'samples_list'">
                  <span>Max Records</span>
                  <input
                    v-model.number="expressionQueryForm.maxRecords"
                    class="search-input compact"
                    type="number"
                    min="1"
                  />
                </label>
                <template v-if="queryOperation === 'matrix_slice'">
                  <label>
                    <span>Data Type</span>
                    <input v-model="expressionQueryForm.dataType" class="search-input compact" placeholder="count / tpm / fpkm" />
                  </label>
                  <label class="sequence-batch-field">
                    <span>Genes</span>
                    <textarea
                      v-model="expressionQueryForm.genesText"
                      class="query-textarea compact-area"
                      placeholder="每行一个 gene，可留空表示不限制"
                    ></textarea>
                  </label>
                  <label class="sequence-batch-field">
                    <span>Samples</span>
                    <textarea
                      v-model="expressionQueryForm.samplesText"
                      class="query-textarea compact-area"
                      placeholder="每行一个 sample，可留空表示不限制"
                    ></textarea>
                  </label>
                </template>
              </div>
              <div v-if="isAnnotationAdapter && queryMode === 'smart'" class="sequence-query-grid">
                <label v-if="queryOperation === 'gene_lookup'">
                  <span>Gene ID</span>
                  <input v-model="annotationQueryForm.geneId" class="search-input compact" placeholder="例如 Gene001" />
                </label>
                <template v-else-if="queryOperation === 'region_features'">
                  <label>
                    <span>Seq ID</span>
                    <input v-model="annotationQueryForm.seqId" class="search-input compact" placeholder="例如 chr1" />
                  </label>
                  <label>
                    <span>Start</span>
                    <input v-model.number="annotationQueryForm.start" class="search-input compact" type="number" min="1" />
                  </label>
                  <label>
                    <span>End</span>
                    <input v-model.number="annotationQueryForm.end" class="search-input compact" type="number" min="1" />
                  </label>
                  <label>
                    <span>Feature Type</span>
                    <input v-model="annotationQueryForm.featureType" class="search-input compact" placeholder="gene / transcript / exon" />
                  </label>
                  <label>
                    <span>Limit</span>
                    <input v-model.number="annotationQueryForm.limit" class="search-input compact" type="number" min="1" />
                  </label>
                </template>
                <div v-else class="query-hint">
                  当前操作不需要额外参数，可直接执行。
                </div>
              </div>
              <div v-if="isFunctionalAnnotationAdapter && queryMode === 'smart'" class="sequence-query-grid">
                <label v-if="queryOperation === 'transcript_detail'">
                  <span>Transcript ID</span>
                  <input v-model="functionalQueryForm.transcriptId" class="search-input compact" placeholder="例如 AT1G01010.1" />
                </label>
                <template v-else-if="queryOperation === 'term_lookup'">
                  <label>
                    <span>Term Source</span>
                    <select v-model="functionalQueryForm.termSource" class="search-input compact">
                      <option v-for="item in functionalTermSourceOptions" :key="item.value" :value="item.value">
                        {{ item.label }}
                      </option>
                    </select>
                  </label>
                  <label>
                    <span>Keyword</span>
                    <input v-model="functionalQueryForm.keyword" class="search-input compact" placeholder="例如 transcription" />
                  </label>
                  <label>
                    <span>Term ID</span>
                    <input v-model="functionalQueryForm.termId" class="search-input compact" placeholder="例如 GO:0003677，可留空" />
                  </label>
                  <label>
                    <span>Limit</span>
                    <input v-model.number="functionalQueryForm.limit" class="search-input compact" type="number" min="1" />
                  </label>
                </template>
                <template v-else-if="queryOperation === 'term_gene_list'">
                  <label>
                    <span>Term Source</span>
                    <select v-model="functionalQueryForm.termSource" class="search-input compact">
                      <option v-for="item in functionalTermSourceOptions" :key="item.value" :value="item.value">
                        {{ item.label }}
                      </option>
                    </select>
                  </label>
                  <label>
                    <span>Term ID</span>
                    <input v-model="functionalQueryForm.termId" class="search-input compact" placeholder="例如 GO:0003677" />
                  </label>
                  <label>
                    <span>Page</span>
                    <input v-model.number="functionalQueryForm.page" class="search-input compact" type="number" min="1" />
                  </label>
                  <label>
                    <span>Size</span>
                    <input v-model.number="functionalQueryForm.size" class="search-input compact" type="number" min="1" />
                  </label>
                </template>
                <template v-else-if="queryOperation === 'term_aggregation'">
                  <label>
                    <span>Term Source</span>
                    <select v-model="functionalQueryForm.termSource" class="search-input compact">
                      <option value="">全部</option>
                      <option v-for="item in functionalTermSourceOptions" :key="item.value" :value="item.value">
                        {{ item.label }}
                      </option>
                    </select>
                  </label>
                  <label>
                    <span>Limit</span>
                    <input v-model.number="functionalQueryForm.limit" class="search-input compact" type="number" min="1" />
                  </label>
                </template>
                <label v-else>
                  <span>Gene ID</span>
                  <input v-model="functionalQueryForm.geneId" class="search-input compact" placeholder="例如 AT1G01010" />
                </label>
              </div>
              <div v-if="isPhenomeAdapter && queryMode === 'smart'" class="sequence-query-grid">
                <template v-if="queryOperation === 'subject_detail'">
                  <label>
                    <span>Subject ID</span>
                    <input v-model="phenomeQueryForm.subjectId" class="search-input compact" placeholder="例如 RH00004" />
                  </label>
                </template>
                <template v-else-if="queryOperation === 'trait_search'">
                  <label>
                    <span>Keyword</span>
                    <input v-model="phenomeQueryForm.keyword" class="search-input compact" placeholder="例如 花瓣" />
                  </label>
                  <label>
                    <span>Limit</span>
                    <input v-model.number="phenomeQueryForm.limit" class="search-input compact" type="number" min="1" />
                  </label>
                </template>
                <template v-else-if="queryOperation === 'trait_values'">
                  <label>
                    <span>Trait</span>
                    <input v-model="phenomeQueryForm.trait" class="search-input compact" placeholder="例如 花瓣数量" />
                  </label>
                  <label>
                    <span>Timepoint</span>
                    <input v-model="phenomeQueryForm.timepoint" class="search-input compact" placeholder="例如 2022，可留空" />
                  </label>
                  <label>
                    <span>Limit</span>
                    <input v-model.number="phenomeQueryForm.limit" class="search-input compact" type="number" min="1" />
                  </label>
                </template>
                <template v-else-if="queryOperation === 'trait_list' || queryOperation === 'subject_list'">
                  <label>
                    <span>Limit</span>
                    <input v-model.number="phenomeQueryForm.limit" class="search-input compact" type="number" min="1" />
                  </label>
                </template>
                <div v-else class="query-hint">
                  当前操作不需要额外参数，可直接执行。
                </div>
              </div>
              <div v-if="isSignalAdapter && queryMode === 'smart'" class="sequence-query-grid">
                <label>
                  <span>Seq ID</span>
                  <input v-model="signalQueryForm.seqId" class="search-input compact" placeholder="例如 chr1" />
                </label>
                <label>
                  <span>Start</span>
                  <input v-model.number="signalQueryForm.start" class="search-input compact" type="number" min="1" />
                </label>
                <label>
                  <span>End</span>
                  <input v-model.number="signalQueryForm.end" class="search-input compact" type="number" min="1" />
                </label>
                <label v-if="queryOperation === 'region_features'">
                  <span>Limit</span>
                  <input v-model.number="signalQueryForm.limit" class="search-input compact" type="number" min="1" />
                </label>
                <template v-if="queryOperation === 'region_signal'">
                  <label>
                    <span>Bins</span>
                    <input v-model.number="signalQueryForm.bins" class="search-input compact" type="number" min="1" />
                  </label>
                  <label>
                    <span>Summary Type</span>
                    <input v-model="signalQueryForm.summaryType" class="search-input compact" placeholder="mean / max / min / coverage / std" />
                  </label>
                </template>
              </div>
              <div v-if="isInteractionAdapter && queryMode === 'smart'" class="sequence-query-grid">
                <template v-if="queryOperation === 'region_contacts'">
                  <label>
                    <span>Anchor Seq ID</span>
                    <input v-model="interactionQueryForm.seqId" class="search-input compact" placeholder="例如 chr1" />
                  </label>
                  <label>
                    <span>Anchor Start</span>
                    <input v-model.number="interactionQueryForm.start" class="search-input compact" type="number" min="1" />
                  </label>
                  <label>
                    <span>Anchor End</span>
                    <input v-model.number="interactionQueryForm.end" class="search-input compact" type="number" min="1" />
                  </label>
                  <label>
                    <span>Target Chrom</span>
                    <input v-model="interactionQueryForm.targetChrom" class="search-input compact" placeholder="可留空" />
                  </label>
                  <label>
                    <span>Target Start</span>
                    <input v-model.number="interactionQueryForm.targetStart" class="search-input compact" type="number" min="1" />
                  </label>
                  <label>
                    <span>Target End</span>
                    <input v-model.number="interactionQueryForm.targetEnd" class="search-input compact" type="number" min="1" />
                  </label>
                  <label>
                    <span>Limit</span>
                    <input v-model.number="interactionQueryForm.limit" class="search-input compact" type="number" min="1" />
                  </label>
                </template>
                <template v-else-if="queryOperation === 'matrix_slice'">
                  <label>
                    <span>Chrom</span>
                    <input v-model="interactionQueryForm.seqId" class="search-input compact" placeholder="例如 chr1" />
                  </label>
                  <label>
                    <span>Start</span>
                    <input v-model.number="interactionQueryForm.start" class="search-input compact" type="number" min="0" />
                  </label>
                  <label>
                    <span>End</span>
                    <input v-model.number="interactionQueryForm.end" class="search-input compact" type="number" min="1" />
                  </label>
                  <label>
                    <span>Target Chrom</span>
                    <input v-model="interactionQueryForm.targetChrom" class="search-input compact" placeholder="留空表示同一区间" />
                  </label>
                  <label>
                    <span>Target Start</span>
                    <input v-model.number="interactionQueryForm.targetStart" class="search-input compact" type="number" min="0" />
                  </label>
                  <label>
                    <span>Target End</span>
                    <input v-model.number="interactionQueryForm.targetEnd" class="search-input compact" type="number" min="1" />
                  </label>
                  <label>
                    <span>Resolution</span>
                    <input v-model.number="interactionQueryForm.resolution" class="search-input compact" type="number" min="1" />
                  </label>
                  <label>
                    <span>Limit Bins</span>
                    <input v-model.number="interactionQueryForm.limitBins" class="search-input compact" type="number" min="1" />
                  </label>
                  <label>
                    <span>Balanced</span>
                    <input v-model="interactionQueryForm.balanced" class="search-input compact" type="checkbox" />
                  </label>
                </template>
                <div v-else class="query-hint">
                  当前操作不需要额外参数，可直接执行。
                </div>
              </div>
              <label v-if="queryMode === 'json' || (!isSequenceAdapter && !isVariantAdapter && !isExpressionAdapter && !isAnnotationAdapter && !isFunctionalAnnotationAdapter && !isPhenomeAdapter && !isSignalAdapter && !isInteractionAdapter)">
                <span>Params JSON</span>
                <textarea v-model="queryParamsText" class="query-textarea"></textarea>
              </label>
              <div class="query-actions">
                <button class="ghost-button" type="button" :disabled="queryLoading" @click="runQuery">
                  {{ queryLoading ? '执行中...' : '执行公开查询' }}
                </button>
              </div>
              <div v-if="copyFeedback" class="copy-feedback">{{ copyFeedback }}</div>
              <div v-if="queryError" class="query-error">{{ queryError }}</div>
              <div
                v-else-if="sequenceQueryResult?.operation === 'fetch' && sequenceQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>{{ sequenceQueryResult.data.seq_id || '-' }}</span>
                  <span>{{ sequenceQueryResult.data.start || '-' }} - {{ sequenceQueryResult.data.end || '-' }}</span>
                  <span>{{ sequenceQueryResult.data.length || 0 }} bp</span>
                </div>
                <div class="result-toolbar">
                  <button
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(String(sequenceQueryResult.data.sequence || ''), '序列已复制')"
                  >
                    复制序列
                  </button>
                </div>
                <code class="sequence-code">{{ sequenceQueryResult.data.sequence || '-' }}</code>
              </div>
              <div
                v-else-if="sequenceQueryResult?.operation === 'batch_fetch' && sequenceQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Batch Fetch</span>
                  <span>{{ (sequenceQueryResult.data.regions as unknown[] | undefined)?.length || 0 }} regions</span>
                </div>
                <div class="batch-region-list">
                  <span
                    v-for="item in (sequenceQueryResult.data.regions as string[] | undefined) || []"
                    :key="item"
                    class="batch-region-chip"
                  >
                    {{ item }}
                  </span>
                </div>
                <div class="result-toolbar">
                  <button
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(String(sequenceQueryResult.data.output_path || ''), '输出路径已复制')"
                  >
                    复制路径
                  </button>
                </div>
                <div class="muted-path">
                  output_path: {{ sequenceQueryResult.data.output_path || '-' }}
                </div>
              </div>
              <div
                v-else-if="variantQueryResult?.operation === 'samples_list' && variantQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Samples List</span>
                  <span>{{ variantQueryResult.data.count || 0 }} samples</span>
                </div>
                <div class="result-toolbar">
                  <button
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(toLineText(variantQueryResult.data.samples), '样本列表已复制')"
                  >
                    复制样本列表
                  </button>
                </div>
                <div class="batch-region-list">
                  <span
                    v-for="sample in variantQueryResult.data.samples || []"
                    :key="sample"
                    class="batch-region-chip"
                  >
                    {{ sample }}
                  </span>
                </div>
              </div>
              <div
                v-else-if="variantQueryResult?.operation === 'region_example' && variantQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Example Region</span>
                  <span>{{ variantQueryResult.data.ref_id || '-' }}</span>
                  <span>POS {{ variantQueryResult.data.variant_position || '-' }}</span>
                </div>
                <div class="result-toolbar">
                  <button
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(toLineText(variantQueryResult.data.example_regions), '示例区间已复制')"
                  >
                    复制区间
                  </button>
                </div>
                <div class="batch-region-list">
                  <span
                    v-for="region in variantQueryResult.data.example_regions || []"
                    :key="region"
                    class="batch-region-chip"
                  >
                    {{ region }}
                  </span>
                </div>
              </div>
              <div
                v-else-if="variantQueryResult?.operation === 'query' && variantQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Variant Query</span>
                  <span>{{ variantQueryResult.data.count || 0 }} records</span>
                  <span v-if="variantQueryResult.data.size">{{ variantQueryResult.data.size }} bytes</span>
                </div>
                <div class="result-toolbar">
                  <button
                    v-if="variantQueryResult.data.preview"
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(String(variantQueryResult.data.preview || ''), 'VCF 预览已复制')"
                  >
                    复制预览
                  </button>
                  <button
                    v-if="variantQueryResult.data.download_url"
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(String(variantQueryResult.data.download_url || ''), '下载链接已复制')"
                  >
                    复制下载链接
                  </button>
                  <a
                    v-if="variantQueryResult.data.download_url"
                    class="result-link"
                    :href="String(variantQueryResult.data.download_url)"
                    target="_blank"
                    rel="noreferrer"
                  >
                    下载结果
                  </a>
                </div>
                <pre v-if="variantQueryResult.data.preview" class="embedded-result">{{ variantQueryResult.data.preview }}</pre>
                <div v-if="variantQueryResult.data.download_url" class="muted-path">
                  download_url: {{ variantQueryResult.data.download_url }}
                </div>
              </div>
              <div
                v-else-if="expressionQueryResult?.operation === 'genes_list' && expressionQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Genes List</span>
                  <span>{{ expressionQueryResult.data.count || 0 }} genes</span>
                </div>
                <div class="result-toolbar">
                  <button
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(toLineText(expressionQueryResult.data.genes), '基因列表已复制')"
                  >
                    复制基因列表
                  </button>
                </div>
                <div class="batch-region-list">
                  <span
                    v-for="gene in expressionQueryResult.data.genes || []"
                    :key="gene"
                    class="batch-region-chip"
                  >
                    {{ gene }}
                  </span>
                </div>
              </div>
              <div
                v-else-if="expressionQueryResult?.operation === 'samples_list' && expressionQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Samples List</span>
                  <span>{{ expressionQueryResult.data.count || 0 }} samples</span>
                </div>
                <div class="result-toolbar">
                  <button
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(toLineText(expressionQueryResult.data.samples), '样本列表已复制')"
                  >
                    复制样本列表
                  </button>
                </div>
                <div class="batch-region-list">
                  <span
                    v-for="sample in expressionQueryResult.data.samples || []"
                    :key="sample"
                    class="batch-region-chip"
                  >
                    {{ sample }}
                  </span>
                </div>
              </div>
              <div
                v-else-if="expressionQueryResult?.operation === 'matrix_slice' && expressionQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Matrix Slice</span>
                  <span>{{ expressionQueryResult.data.data_type || '-' }}</span>
                  <span>{{ (expressionQueryResult.data.genes || []).length }} genes</span>
                  <span>{{ (expressionQueryResult.data.samples || []).length }} samples</span>
                </div>
                <div class="result-toolbar">
                  <button
                    v-if="expressionMatrixTsv"
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(expressionMatrixTsv, '矩阵结果已复制')"
                  >
                    复制矩阵 TSV
                  </button>
                  <button
                    v-if="expressionQueryResult.data.download_path"
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(String(expressionQueryResult.data.download_path || ''), '下载路径已复制')"
                  >
                    复制下载路径
                  </button>
                </div>
                <div v-if="expressionQueryResult.data.matrix?.length" class="matrix-table-wrap">
                  <table class="matrix-table">
                    <thead>
                      <tr>
                        <th>Gene</th>
                        <th
                          v-for="sample in expressionQueryResult.data.samples || []"
                          :key="sample"
                        >
                          {{ sample }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="(row, rowIndex) in expressionQueryResult.data.matrix || []"
                        :key="expressionQueryResult.data.genes?.[rowIndex] || rowIndex"
                      >
                        <th>{{ expressionQueryResult.data.genes?.[rowIndex] || `Gene-${rowIndex + 1}` }}</th>
                        <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="expressionQueryResult.data.download_path" class="muted-path">
                  download_path: {{ expressionQueryResult.data.download_path }}
                </div>
              </div>
              <div
                v-else-if="annotationQueryResult?.operation === 'table_stats' && annotationQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Annotation Tables</span>
                  <span>{{ annotationQueryResult.data.count || 0 }} tables</span>
                </div>
                <div class="result-toolbar">
                  <button
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(toLineText((annotationQueryResult.data.tables || []).map((item) => String(item))), '表名已复制')"
                  >
                    复制表名
                  </button>
                </div>
                <div class="batch-region-list">
                  <span
                    v-for="tableName in annotationQueryResult.data.tables || []"
                    :key="String(tableName)"
                    class="batch-region-chip"
                  >
                    {{ tableName }}
                  </span>
                </div>
              </div>
              <div
                v-else-if="annotationQueryResult?.operation === 'gene_lookup' && annotationQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Gene Lookup</span>
                  <span>{{ String(annotationQueryResult.data.gene?.gene_id || '-') }}</span>
                  <span>{{ annotationQueryResult.data.transcript_count || 0 }} transcripts</span>
                </div>
                <div class="annotation-gene-card">
                  <div class="annotation-gene-head">
                    <strong>{{ String(annotationQueryResult.data.gene?.gene_id || '-') }}</strong>
                    <span>
                      {{ String(annotationQueryResult.data.gene?.chrom || '-') }}:
                      {{ String(annotationQueryResult.data.gene?.start || '-') }}-{{ String(annotationQueryResult.data.gene?.stop || '-') }}
                    </span>
                  </div>
                  <div class="annotation-gene-meta">
                    <span>strand: {{ String(annotationQueryResult.data.gene?.strand || '-') }}</span>
                    <span>canonical: {{ String(annotationQueryResult.data.gene?.canonical_transcript || '-') }}</span>
                    <span>family: {{ String(annotationQueryResult.data.gene?.family || '-') }}</span>
                  </div>
                  <p class="annotation-gene-desc">
                    {{ String(annotationQueryResult.data.gene?.description || '-') }}
                  </p>
                </div>
                <div class="result-toolbar">
                  <button
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(JSON.stringify(annotationQueryResult.data.gene || {}, null, 2), 'gene 信息已复制')"
                  >
                    复制 gene JSON
                  </button>
                </div>
                <div v-if="annotationQueryResult.data.transcripts?.length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>Transcript</th>
                        <th>Region</th>
                        <th>Strand</th>
                        <th>Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="transcript in annotationQueryResult.data.transcripts || []"
                        :key="String(transcript.transcript_id || transcript.id || JSON.stringify(transcript))"
                      >
                        <th>{{ String(transcript.transcript_id || '-') }}</th>
                        <td>{{ String(transcript.chrom || '-') }}:{{ String(transcript.start || '-') }}-{{ String(transcript.stop || '-') }}</td>
                        <td>{{ String(transcript.strand || '-') }}</td>
                        <td>{{ String(transcript.description || '-') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              <div
                v-else-if="annotationQueryResult?.operation === 'region_features' && annotationQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Region Features</span>
                  <span>{{ annotationQueryResult.data.region || annotationQueryForm.seqId }}</span>
                  <span>{{ annotationQueryResult.data.count || 0 }} items</span>
                  <span v-if="annotationQueryResult.data.table">{{ annotationQueryResult.data.table }}</span>
                </div>
                <div class="result-toolbar">
                  <button
                    v-if="annotationRegionTsv"
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(annotationRegionTsv, '区域结果已复制')"
                  >
                    复制 TSV
                  </button>
                </div>
                <div v-if="annotationQueryResult.data.items?.length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Region</th>
                        <th>Strand</th>
                        <th>Type</th>
                        <th>Description / Name</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="item in annotationQueryResult.data.items || []"
                        :key="String(item.gene_id || item.transcript_id || item.id || JSON.stringify(item))"
                      >
                        <th>{{ String(item.gene_id || item.transcript_id || item.id || '-') }}</th>
                        <td>{{ String(item.chrom || item.seq_id || '-') }}:{{ String(item.start || '-') }}-{{ String(item.stop || item.end || '-') }}</td>
                        <td>{{ String(item.strand || '-') }}</td>
                        <td>{{ String(item.feature_type || annotationQueryForm.featureType || '-') }}</td>
                        <td>{{ String(item.description || item.name || '-') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="state-inline">
                  当前区间没有命中注释记录。
                </div>
              </div>
              <div
                v-else-if="functionalQueryResult?.operation === 'gene_detail' && functionalQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Gene Detail</span>
                  <span>{{ String(functionalQueryResult.data.gene?.gene_id || '-') }}</span>
                  <span>{{ functionalQueryResult.data.transcript_count || 0 }} transcripts</span>
                </div>
                <div class="annotation-gene-card">
                  <div class="annotation-gene-head">
                    <strong>{{ String(functionalQueryResult.data.gene?.gene_id || '-') }}</strong>
                    <span>
                      {{ String(functionalQueryResult.data.gene?.chrom || '-') }}:
                      {{ String(functionalQueryResult.data.gene?.start || '-') }}-{{ String(functionalQueryResult.data.gene?.stop || '-') }}
                    </span>
                  </div>
                  <div class="annotation-gene-meta">
                    <span>strand: {{ String(functionalQueryResult.data.gene?.strand || '-') }}</span>
                    <span>canonical: {{ String(functionalQueryResult.data.gene?.canonical_transcript || '-') }}</span>
                    <span>family: {{ String(functionalQueryResult.data.gene?.family || '-') }}</span>
                  </div>
                  <p class="annotation-gene-desc">
                    {{ String(functionalQueryResult.data.gene?.description || '-') }}
                  </p>
                </div>
                <div v-if="functionalQueryResult.data.canonical_transcript" class="result-toolbar">
                  <span class="capability-badge">
                    canonical transcript: {{ String(functionalQueryResult.data.canonical_transcript.transcript_id || '-') }}
                  </span>
                  <span class="capability-badge">
                    GO {{ Number(functionalQueryResult.data.canonical_transcript.annotation_counts?.go || 0) }}
                  </span>
                  <span class="capability-badge">
                    KEGG {{ Number(functionalQueryResult.data.canonical_transcript.annotation_counts?.kegg || 0) }}
                  </span>
                  <span class="capability-badge">
                    InterPro {{ Number(functionalQueryResult.data.canonical_transcript.annotation_counts?.interpro || 0) }}
                  </span>
                </div>
                <div v-if="functionalQueryResult.data.transcripts?.length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>Transcript</th>
                        <th>Region</th>
                        <th>GO</th>
                        <th>KEGG</th>
                        <th>InterPro</th>
                        <th>Family</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="transcript in functionalQueryResult.data.transcripts || []"
                        :key="String(transcript.transcript_id || JSON.stringify(transcript))"
                      >
                        <th>{{ String(transcript.transcript_id || '-') }}</th>
                        <td>{{ String(transcript.chrom || '-') }}:{{ String(transcript.start || '-') }}-{{ String(transcript.stop || '-') }}</td>
                        <td>{{ Number(transcript.annotation_counts?.go || 0) }}</td>
                        <td>{{ Number(transcript.annotation_counts?.kegg || 0) }}</td>
                        <td>{{ Number(transcript.annotation_counts?.interpro || 0) }}</td>
                        <td>{{ Number(transcript.annotation_counts?.family || 0) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              <div
                v-else-if="functionalQueryResult?.operation === 'transcript_detail' && functionalQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Transcript Detail</span>
                  <span>{{ String(functionalQueryResult.data.transcript?.transcript_id || '-') }}</span>
                  <span>{{ String(functionalQueryResult.data.transcript?.gene_id || '-') }}</span>
                </div>
                <div class="annotation-gene-card">
                  <div class="annotation-gene-head">
                    <strong>{{ String(functionalQueryResult.data.transcript?.transcript_id || '-') }}</strong>
                    <span>
                      {{ String(functionalQueryResult.data.transcript?.chrom || '-') }}:
                      {{ String(functionalQueryResult.data.transcript?.start || '-') }}-{{ String(functionalQueryResult.data.transcript?.stop || '-') }}
                    </span>
                  </div>
                  <div class="annotation-gene-meta">
                    <span>gene: {{ String(functionalQueryResult.data.transcript?.gene_id || '-') }}</span>
                    <span>strand: {{ String(functionalQueryResult.data.transcript?.strand || '-') }}</span>
                    <span>family: {{ Number(functionalQueryResult.data.transcript?.annotation_counts?.family || 0) }}</span>
                  </div>
                  <p class="annotation-gene-desc">
                    {{ String(functionalQueryResult.data.transcript?.description || '-') }}
                  </p>
                </div>
                <div class="result-toolbar">
                  <span class="capability-badge">GO {{ Number(functionalQueryResult.data.transcript?.annotation_counts?.go || 0) }}</span>
                  <span class="capability-badge">KEGG {{ Number(functionalQueryResult.data.transcript?.annotation_counts?.kegg || 0) }}</span>
                  <span class="capability-badge">InterPro {{ Number(functionalQueryResult.data.transcript?.annotation_counts?.interpro || 0) }}</span>
                  <span class="capability-badge">Blast {{ Number(functionalQueryResult.data.transcript?.annotation_counts?.blast_sources || 0) }}</span>
                </div>
                <div v-if="(functionalQueryResult.data.transcript?.annotations?.family || []).length" class="batch-region-list">
                  <span
                    v-for="item in functionalQueryResult.data.transcript?.annotations?.family || []"
                    :key="JSON.stringify(item)"
                    class="batch-region-chip"
                  >
                    {{ String(item.name || item.family || item.type || item) }}
                  </span>
                </div>
                <div v-if="(functionalQueryResult.data.transcript?.annotations?.go || []).length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>GO</th>
                        <th>Name</th>
                        <th>Namespace</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="item in functionalQueryResult.data.transcript?.annotations?.go || []"
                        :key="String(item.term || JSON.stringify(item))"
                      >
                        <th>{{ String(item.term || '-') }}</th>
                        <td>{{ String(item.name || '-') }}</td>
                        <td>{{ String(item.namespace || '-') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="(functionalQueryResult.data.transcript?.annotations?.kegg || []).length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>Pathway</th>
                        <th>Description</th>
                        <th>Orthology</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="item in functionalQueryResult.data.transcript?.annotations?.kegg || []"
                        :key="String(item.pathway || JSON.stringify(item))"
                      >
                        <th>{{ String(item.pathway || '-') }}</th>
                        <td>{{ String(item.description || '-') }}</td>
                        <td>{{ Array.isArray(item.orthology) ? item.orthology.join(', ') : String(item.orthology || '-') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <pre
                  v-if="functionalQueryResult.data.transcript?.annotations?.interpro"
                  class="embedded-result"
                >{{ JSON.stringify(functionalQueryResult.data.transcript?.annotations?.interpro, null, 2) }}</pre>
              </div>
              <div
                v-else-if="functionalQueryResult?.operation === 'gene_function_summary' && functionalQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Function Summary</span>
                  <span>{{ String(functionalQueryResult.data.gene?.gene_id || '-') }}</span>
                  <span>{{ String(functionalQueryResult.data.canonical_transcript_id || '-') }}</span>
                </div>
                <div class="public-status-grid compact-status-grid">
                  <article class="summary-card status-summary-card">
                    <span class="summary-label">GO</span>
                    <strong>{{ Number(functionalQueryResult.data.annotation_counts?.go || 0) }}</strong>
                    <p>canonical transcript terms</p>
                  </article>
                  <article class="summary-card status-summary-card">
                    <span class="summary-label">KEGG</span>
                    <strong>{{ Number(functionalQueryResult.data.annotation_counts?.kegg || 0) }}</strong>
                    <p>canonical transcript pathways</p>
                  </article>
                  <article class="summary-card status-summary-card">
                    <span class="summary-label">InterPro</span>
                    <strong>{{ Number(functionalQueryResult.data.annotation_counts?.interpro || 0) }}</strong>
                    <p>domain matches</p>
                  </article>
                </div>
                <div v-if="(functionalQueryResult.data.annotations?.family || []).length" class="batch-region-list">
                  <span
                    v-for="item in functionalQueryResult.data.annotations?.family || []"
                    :key="JSON.stringify(item)"
                    class="batch-region-chip"
                  >
                    {{ String(item.name || item.family || item.type || item) }}
                  </span>
                </div>
              </div>
              <div
                v-else-if="functionalQueryResult?.operation === 'term_lookup' && functionalQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Term Lookup</span>
                  <span>{{ String(functionalQueryResult.data.source || '-') }}</span>
                  <span>{{ Number(functionalQueryResult.data.total || 0) }} terms</span>
                </div>
                <div class="result-toolbar">
                  <button
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(JSON.stringify(functionalQueryResult.data.items || [], null, 2), 'term 列表已复制')"
                  >
                    复制 term JSON
                  </button>
                </div>
                <div v-if="functionalQueryResult.data.items?.length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>Source</th>
                        <th>Term ID</th>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Genes</th>
                        <th>Assignments</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="item in functionalQueryResult.data.items || []"
                        :key="String(item.term_source || '') + ':' + String(item.term_id || '')"
                      >
                        <td>{{ String(item.term_source || '-') }}</td>
                        <th>{{ String(item.term_id || '-') }}</th>
                        <td>{{ String(item.term_name || item.description || '-') }}</td>
                        <td>{{ String(item.term_type || '-') }}</td>
                        <td>{{ Number(item.gene_count || 0) }}</td>
                        <td>{{ Number(item.assignment_count || 0) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="state-inline">当前条件没有命中 term。</div>
              </div>
              <div
                v-else-if="functionalQueryResult?.operation === 'term_gene_list' && functionalQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Term Gene List</span>
                  <span>{{ String(functionalQueryResult.data.term_source || '-') }}</span>
                  <span>{{ String(functionalQueryResult.data.term_id || '-') }}</span>
                </div>
                <div class="result-toolbar">
                  <span class="capability-badge">{{ Number(functionalQueryResult.data.total || 0) }} genes</span>
                  <button
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(JSON.stringify(functionalQueryResult.data.items || [], null, 2), 'gene 列表已复制')"
                  >
                    复制 gene JSON
                  </button>
                </div>
                <div v-if="functionalQueryResult.data.items?.length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>Gene</th>
                        <th>Canonical</th>
                        <th>Region</th>
                        <th>Hits</th>
                        <th>Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="item in functionalQueryResult.data.items || []"
                        :key="String(item.gene?.gene_id || JSON.stringify(item))"
                      >
                        <th>{{ String(item.gene?.gene_id || '-') }}</th>
                        <td>{{ String(item.gene?.canonical_transcript_id || '-') }}</td>
                        <td>{{ String(item.gene?.chrom || '-') }}:{{ String(item.gene?.start || '-') }}-{{ String(item.gene?.end || item.gene?.stop || '-') }}</td>
                        <td>{{ Number(item.assignment_hits || 0) }}</td>
                        <td>{{ String(item.gene?.description || '-') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="state-inline">当前 term 没有命中 gene。</div>
              </div>
              <div
                v-else-if="functionalQueryResult?.operation === 'term_aggregation' && functionalQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Term Aggregation</span>
                  <span>{{ String(functionalQueryResult.data.source || '-') }}</span>
                  <span>{{ Number(functionalQueryResult.data.top_terms?.length || 0) }} top terms</span>
                </div>
                <div class="result-toolbar">
                  <button
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(JSON.stringify(functionalQueryResult.data || {}, null, 2), 'term 聚合结果已复制')"
                  >
                    复制 aggregation JSON
                  </button>
                </div>
                <div v-if="functionalQueryResult.data.by_source?.length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>Source</th>
                        <th>Term Count</th>
                        <th>Gene Hits</th>
                        <th>Assignments</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="item in functionalQueryResult.data.by_source || []"
                        :key="String(item.term_source || JSON.stringify(item))"
                      >
                        <th>{{ String(item.term_source || '-') }}</th>
                        <td>{{ Number(item.term_count || 0) }}</td>
                        <td>{{ Number(item.gene_hits || 0) }}</td>
                        <td>{{ Number(item.assignment_hits || 0) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="functionalQueryResult.data.top_terms?.length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>Top Term</th>
                        <th>Name</th>
                        <th>Genes</th>
                        <th>Assignments</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="item in functionalQueryResult.data.top_terms || []"
                        :key="String(item.term_source || '') + ':' + String(item.term_id || '')"
                      >
                        <th>{{ String(item.term_source || '-') }} / {{ String(item.term_id || '-') }}</th>
                        <td>{{ String(item.term_name || item.description || '-') }}</td>
                        <td>{{ Number(item.gene_count || 0) }}</td>
                        <td>{{ Number(item.assignment_count || 0) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div
                  v-if="!functionalQueryResult.data.by_source?.length && !functionalQueryResult.data.top_terms?.length"
                  class="state-inline"
                >
                  当前版本还没有 term 聚合结果。
                </div>
              </div>
              <div
                v-else-if="phenomeQueryResult?.operation === 'dataset_summary' && phenomeQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Phenome Summary</span>
                  <span>{{ phenomeQueryResult.data.source || '-' }}</span>
                  <span>{{ Number(phenomeQueryResult.data.subject_count || 0) }} subjects</span>
                  <span>{{ Number(phenomeQueryResult.data.trait_count || 0) }} traits</span>
                </div>
                <div class="public-status-grid compact-status-grid">
                  <article class="summary-card status-summary-card">
                    <span class="summary-label">Subjects</span>
                    <strong>{{ Number(phenomeQueryResult.data.subject_count || 0) }}</strong>
                    <p>indexed materials or samples</p>
                  </article>
                  <article class="summary-card status-summary-card">
                    <span class="summary-label">Traits</span>
                    <strong>{{ Number(phenomeQueryResult.data.trait_count || 0) }}</strong>
                    <p>grouped trait definitions</p>
                  </article>
                  <article class="summary-card status-summary-card">
                    <span class="summary-label">Observations</span>
                    <strong>{{ Number(phenomeQueryResult.data.observation_count || 0) }}</strong>
                    <p>trait measurements in current version</p>
                  </article>
                </div>
                <div v-if="phenomeQueryResult.data.traits_preview?.length" class="batch-region-list">
                  <span
                    v-for="item in phenomeQueryResult.data.traits_preview || []"
                    :key="String(item)"
                    class="batch-region-chip"
                  >
                    {{ String(item) }}
                  </span>
                </div>
              </div>
              <div
                v-else-if="phenomeQueryResult?.operation === 'trait_list' && phenomeQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Trait List</span>
                  <span>{{ phenomeQueryResult.data.source || '-' }}</span>
                  <span>{{ Number(phenomeQueryResult.data.count || 0) }} traits</span>
                </div>
                <div class="result-toolbar">
                  <button
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(JSON.stringify(phenomeQueryResult.data.items || [], null, 2), 'trait 列表已复制')"
                  >
                    复制 trait JSON
                  </button>
                </div>
                <div v-if="phenomeQueryResult.data.items?.length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>Trait</th>
                        <th>Code</th>
                        <th>Value Type</th>
                        <th>Time Axis</th>
                        <th>Order</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="item in phenomeQueryResult.data.items || []"
                        :key="String(item.trait_code || item.name || JSON.stringify(item))"
                      >
                        <th>{{ String(item.name || item.trait_name || '-') }}</th>
                        <td>{{ String(item.trait_code || '-') }}</td>
                        <td>{{ String(item.declared_type || '-') }}</td>
                        <td>{{ String(item.time_axis_type || '-') }}</td>
                        <td>{{ String(item.position || '-') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="state-inline">当前版本没有 trait 条目。</div>
              </div>
              <div
                v-else-if="phenomeQueryResult?.operation === 'trait_search' && phenomeQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Trait Search</span>
                  <span>{{ String(phenomeQueryResult.data.keyword || '-') }}</span>
                  <span>{{ Number(phenomeQueryResult.data.count || 0) }} hits</span>
                </div>
                <div v-if="phenomeQueryResult.data.items?.length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>Trait</th>
                        <th>Code</th>
                        <th>Value Type</th>
                        <th>Time Axis</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="item in phenomeQueryResult.data.items || []"
                        :key="String(item.trait_code || item.name || JSON.stringify(item))"
                      >
                        <th>{{ String(item.name || '-') }}</th>
                        <td>{{ String(item.trait_code || '-') }}</td>
                        <td>{{ String(item.declared_type || '-') }}</td>
                        <td>{{ String(item.time_axis_type || '-') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="state-inline">当前关键词没有命中 trait。</div>
              </div>
              <div
                v-else-if="phenomeQueryResult?.operation === 'subject_list' && phenomeQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Subject List</span>
                  <span>{{ Number(phenomeQueryResult.data.count || 0) }} subjects</span>
                </div>
                <div class="result-toolbar">
                  <button
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(toLineText((phenomeQueryResult.data.items || []).map((item) => String(item))), 'subject 列表已复制')"
                  >
                    复制 subject 列表
                  </button>
                </div>
                <div class="batch-region-list">
                  <span
                    v-for="item in phenomeQueryResult.data.items || []"
                    :key="String(item)"
                    class="batch-region-chip"
                  >
                    {{ String(item) }}
                  </span>
                </div>
              </div>
              <div
                v-else-if="phenomeQueryResult?.operation === 'subject_detail' && phenomeQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Subject Detail</span>
                  <span>{{ String(phenomeQueryResult.data.subject_id || '-') }}</span>
                  <span>{{ Object.keys(phenomeQueryResult.data.traits || {}).length }} traits</span>
                </div>
                <div class="result-toolbar">
                  <button
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(JSON.stringify(phenomeQueryResult.data.traits || {}, null, 2), 'subject 详情已复制')"
                  >
                    复制 subject JSON
                  </button>
                </div>
                <div v-if="Object.keys(phenomeQueryResult.data.traits || {}).length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>Trait</th>
                        <th>Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="(value, traitName) in (phenomeQueryResult.data.traits || {})"
                        :key="String(traitName)"
                      >
                        <th>{{ String(traitName) }}</th>
                        <td>{{ String(value ?? '-') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              <div
                v-else-if="phenomeQueryResult?.operation === 'trait_values' && phenomeQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Trait Values</span>
                  <span>{{ String(phenomeQueryResult.data.trait || phenomeQueryResult.data.trait_code || '-') }}</span>
                  <span v-if="phenomeQueryResult.data.timepoint">timepoint {{ String(phenomeQueryResult.data.timepoint) }}</span>
                  <span>{{ Number(phenomeQueryResult.data.non_missing_count || 0) }} / {{ Number(phenomeQueryResult.data.count || 0) }}</span>
                </div>
                <div class="result-toolbar">
                  <button
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(JSON.stringify(phenomeQueryResult.data.items || [], null, 2), 'trait values 已复制')"
                  >
                    复制 values JSON
                  </button>
                </div>
                <div v-if="phenomeQueryResult.data.items?.length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>Subject</th>
                        <th>Value</th>
                        <th>Raw Value</th>
                        <th>Timepoint</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="item in phenomeQueryResult.data.items || []"
                        :key="String(item.subject_id || JSON.stringify(item)) + ':' + String(item.timepoint || '')"
                      >
                        <th>{{ String(item.subject_id || '-') }}</th>
                        <td>{{ String(item.value ?? '-') }}</td>
                        <td>{{ String(item.raw_value ?? '-') }}</td>
                        <td>{{ String(item.timepoint || '-') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="state-inline">当前条件没有命中观测值。</div>
              </div>
              <div
                v-else-if="signalQueryResult?.operation === 'describe_signal' && signalQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Signal Track</span>
                  <span>{{ signalQueryResult.data.source || 'signal' }}</span>
                  <span>{{ signalQueryResult.data.chromosome_count || 0 }} chromosomes</span>
                </div>
                <div class="public-status-grid compact-status-grid">
                  <article class="summary-card status-summary-card">
                    <span class="summary-label">Coverage</span>
                    <strong>{{ String(signalQueryResult.data.header?.nBasesCovered || 0) }}</strong>
                    <p>covered bases reported by BigWig header</p>
                  </article>
                  <article class="summary-card status-summary-card">
                    <span class="summary-label">Min Signal</span>
                    <strong>{{ String(signalQueryResult.data.header?.minVal ?? '-') }}</strong>
                    <p>header minimum value</p>
                  </article>
                  <article class="summary-card status-summary-card">
                    <span class="summary-label">Max Signal</span>
                    <strong>{{ String(signalQueryResult.data.header?.maxVal ?? '-') }}</strong>
                    <p>header maximum value</p>
                  </article>
                </div>
                <div v-if="signalQueryResult.data.chromosomes?.length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>Chromosome</th>
                        <th>Length</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="item in signalQueryResult.data.chromosomes || []"
                        :key="String(item.chrom || JSON.stringify(item))"
                      >
                        <th>{{ String(item.chrom || '-') }}</th>
                        <td>{{ String(item.length || '-') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              <div
                v-else-if="signalQueryResult?.operation === 'region_signal' && signalQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Signal Region</span>
                  <span>{{ signalQueryResult.data.region || signalQueryForm.seqId }}</span>
                  <span>{{ signalQueryResult.data.summary_type || signalQueryForm.summaryType }}</span>
                  <span>{{ signalQueryResult.data.non_null_count || 0 }} / {{ signalQueryResult.data.count || 0 }} bins</span>
                </div>
                <div class="public-status-grid compact-status-grid">
                  <article class="summary-card status-summary-card">
                    <span class="summary-label">Summary</span>
                    <strong>{{ String(signalQueryResult.data.summary?.value ?? '-') }}</strong>
                    <p>overall {{ String(signalQueryResult.data.summary_type || 'mean') }} value</p>
                  </article>
                  <article class="summary-card status-summary-card">
                    <span class="summary-label">Min Bin</span>
                    <strong>{{ String(signalQueryResult.data.summary?.min ?? '-') }}</strong>
                    <p>minimum non-null bin value</p>
                  </article>
                  <article class="summary-card status-summary-card">
                    <span class="summary-label">Max Bin</span>
                    <strong>{{ String(signalQueryResult.data.summary?.max ?? '-') }}</strong>
                    <p>maximum non-null bin value</p>
                  </article>
                </div>
                <div v-if="signalQueryResult.data.items?.length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>Bin</th>
                        <th>Region</th>
                        <th>Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="(item, index) in signalQueryResult.data.items || []"
                        :key="`${String(item.chrom || '-')}:${String(item.start || '-')}-${String(item.end || '-')}:${index}`"
                      >
                        <th>bin-{{ index + 1 }}</th>
                        <td>{{ String(item.chrom || '-') }}:{{ String(item.start || '-') }}-{{ String(item.end || '-') }}</td>
                        <td>{{ String(item.value ?? '-') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="state-inline">
                  当前区间没有可返回的 signal bin。
                </div>
              </div>
              <div
                v-else-if="signalQueryResult?.operation === 'region_features' && signalQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Signal Region</span>
                  <span>{{ signalQueryResult.data.region || signalQueryForm.seqId }}</span>
                  <span>{{ signalQueryResult.data.count || 0 }} items</span>
                </div>
                <div v-if="signalQueryResult.data.items?.length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Region</th>
                        <th>Score</th>
                        <th>Strand</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="item in signalQueryResult.data.items || []"
                        :key="String(item.name || item.chrom || JSON.stringify(item))"
                      >
                        <th>{{ String(item.name || '-') }}</th>
                        <td>{{ String(item.chrom || '-') }}:{{ String(item.start || '-') }}-{{ String(item.end || '-') }}</td>
                        <td>{{ String(item.score || '-') }}</td>
                        <td>{{ String(item.strand || '-') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="state-inline">
                  当前区间没有命中 signal 记录。
                </div>
              </div>
              <div
                v-else-if="interactionQueryResult?.operation === 'matrix_meta' && interactionQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Interaction Matrix</span>
                  <span>{{ interactionQueryResult.data.format || '-' }}</span>
                  <span>bin {{ interactionQueryResult.data.bin_size || '-' }}</span>
                  <span>{{ interactionQueryResult.data.chroms?.length || 0 }} chroms</span>
                </div>
                <div class="batch-region-list">
                  <span
                    v-for="chrom in interactionQueryResult.data.chroms || []"
                    :key="String(chrom.name || JSON.stringify(chrom))"
                    class="batch-region-chip"
                  >
                    {{ String(chrom.name || '-') }}:{{ String(chrom.length || '-') }}
                  </span>
                </div>
                <div
                  v-if="interactionQueryResult.data.available_resolutions?.length"
                  class="batch-region-list"
                >
                  <span
                    v-for="resolution in interactionQueryResult.data.available_resolutions || []"
                    :key="String(resolution)"
                    class="batch-region-chip"
                  >
                    {{ resolution }}
                  </span>
                </div>
              </div>
              <div
                v-else-if="interactionQueryResult?.operation === 'resolutions_list' && interactionQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Available Resolutions</span>
                  <span>{{ interactionQueryResult.data.format || '-' }}</span>
                  <span>default {{ interactionQueryResult.data.default_resolution || '-' }}</span>
                </div>
                <div class="batch-region-list">
                  <span
                    v-for="resolution in interactionQueryResult.data.resolutions || []"
                    :key="String(resolution)"
                    class="batch-region-chip"
                  >
                    {{ resolution }}
                  </span>
                </div>
              </div>
              <div
                v-else-if="interactionQueryResult?.operation === 'matrix_slice' && interactionQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Interaction Matrix Slice</span>
                  <span>{{ interactionQueryResult.data.format || '-' }}</span>
                  <span>{{ interactionQueryResult.data.region || '-' }}</span>
                  <span>{{ interactionQueryResult.data.target_region || interactionQueryResult.data.region || '-' }}</span>
                  <span>bin {{ interactionQueryResult.data.bin_size || '-' }}</span>
                </div>
                <div class="result-toolbar">
                  <button
                    v-if="interactionMatrixTsv"
                    class="tiny-button secondary"
                    type="button"
                    @click="copyText(interactionMatrixTsv, '矩阵结果已复制')"
                  >
                    复制矩阵 TSV
                  </button>
                </div>
                <div v-if="interactionQueryResult.data.matrix?.length" class="matrix-table-wrap">
                  <table class="matrix-table">
                    <thead>
                      <tr>
                        <th>Bin</th>
                        <th
                          v-for="label in interactionQueryResult.data.x_labels || []"
                          :key="label"
                        >
                          {{ label }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="(row, rowIndex) in interactionQueryResult.data.matrix || []"
                        :key="interactionQueryResult.data.y_labels?.[rowIndex] || rowIndex"
                      >
                        <th>{{ interactionQueryResult.data.y_labels?.[rowIndex] || `Bin-${rowIndex + 1}` }}</th>
                        <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="state-inline">
                  当前区间没有可展示的 interaction matrix bin。
                </div>
              </div>
              <div
                v-else-if="interactionQueryResult?.operation === 'region_contacts' && interactionQueryResult.data"
                class="query-result sequence-result"
              >
                <div class="result-meta">
                  <span>Interaction Region</span>
                  <span>{{ interactionQueryResult.data.anchor_region || interactionQueryForm.seqId }}</span>
                  <span v-if="interactionQueryResult.data.target_region">{{ interactionQueryResult.data.target_region }}</span>
                  <span>{{ interactionQueryResult.data.count || 0 }} items</span>
                </div>
                <div v-if="interactionQueryResult.data.items?.length" class="annotation-table-wrap">
                  <table class="annotation-table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Anchor</th>
                        <th>Target</th>
                        <th>Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="item in interactionQueryResult.data.items || []"
                        :key="String(item.name || JSON.stringify(item))"
                      >
                        <th>{{ String(item.name || '-') }}</th>
                        <td>{{ String(item.chrom1 || '-') }}:{{ String(item.start1 || '-') }}-{{ String(item.end1 || '-') }}</td>
                        <td>{{ String(item.chrom2 || '-') }}:{{ String(item.start2 || '-') }}-{{ String(item.end2 || '-') }}</td>
                        <td>{{ String(item.score || '-') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="state-inline">
                  当前区间没有命中 interaction 记录。
                </div>
              </div>
              <pre v-else-if="queryResult" class="query-result">{{ JSON.stringify(queryResult, null, 2) }}</pre>
            </div>
          </div>
        </template>
      </section>
    </section>
  </main>
</template>
