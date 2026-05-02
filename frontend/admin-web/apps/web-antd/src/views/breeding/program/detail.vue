<script setup lang="ts">
import type {
  BreedingAssayItem,
  BreedingBioSampleItem,
  BreedingDataFileItem,
  BreedingMaterialItem,
  BreedingObservationItem,
  BreedingPlotItem,
  BreedingProgramItem,
  BreedingProgramOverview,
  BreedingTrialItem,
} from '#/api/breeding/program';

import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Descriptions,
  DescriptionsItem,
  Empty,
  Spin,
  TabPane,
  Table,
  Tabs,
  Tag,
} from 'ant-design-vue';

import {
  getBreedingAssayListApi,
  getBreedingBioSampleListApi,
  getBreedingDataFileListApi,
  getBreedingMaterialListApi,
  getBreedingObservationListApi,
  getBreedingPlotListApi,
  getBreedingProgramInfoApi,
  getBreedingProgramOverviewApi,
  getBreedingTrialListApi,
} from '#/api/breeding/program';
import { $t } from '@vben/locales';

defineOptions({ name: 'BreedingProgramDetailPage' });

type DetailTabKey =
  | 'overview'
  | 'materials'
  | 'trials'
  | 'plots'
  | 'observations'
  | 'biosamples'
  | 'omics';

const route = useRoute();
const router = useRouter();

const activeTab = ref<DetailTabKey>('overview');
const activeMaterialId = ref<number | null>(null);
const pageLoading = ref(false);
const programInfo = ref<BreedingProgramItem | null>(null);
const programOverview = ref<BreedingProgramOverview | null>(null);

const materialsLoading = ref(false);
const trialsLoading = ref(false);
const plotsLoading = ref(false);
const observationsLoading = ref(false);
const biosamplesLoading = ref(false);
const assaysLoading = ref(false);
const dataFilesLoading = ref(false);

const materialRows = ref<BreedingMaterialItem[]>([]);
const trialRows = ref<BreedingTrialItem[]>([]);
const plotRows = ref<BreedingPlotItem[]>([]);
const observationRows = ref<BreedingObservationItem[]>([]);
const biosampleRows = ref<BreedingBioSampleItem[]>([]);
const assayRows = ref<BreedingAssayItem[]>([]);
const dataFileRows = ref<BreedingDataFileItem[]>([]);

const loadedTabs = reactive<Record<DetailTabKey, boolean>>({
  overview: false,
  materials: false,
  trials: false,
  plots: false,
  observations: false,
  biosamples: false,
  omics: false,
});

const currentProgramId = computed(() => Number(route.params.id || 0));
const selectedMaterial = computed(() =>
  activeMaterialId.value ? materialMap.value[activeMaterialId.value] || null : null,
);

const materialMap = computed(() =>
  Object.fromEntries(materialRows.value.map(item => [item.id, item])),
);

const materialByCodeMap = computed(() =>
  Object.fromEntries(materialRows.value.map(item => [item.material_code, item])),
);

const materialByGermplasmMap = computed(() =>
  Object.fromEntries(
    materialRows.value
      .filter(item => item.germplasm_accession)
      .map(item => [item.germplasm_accession as string, item]),
  ),
);

const trialMap = computed(() =>
  Object.fromEntries(trialRows.value.map(item => [item.id, item])),
);

const plotMap = computed(() =>
  Object.fromEntries(plotRows.value.map(item => [item.id, item])),
);

const biosampleMap = computed(() =>
  Object.fromEntries(biosampleRows.value.map(item => [item.id, item])),
);

const assayMap = computed(() =>
  Object.fromEntries(assayRows.value.map(item => [item.id, item])),
);

const parsedMeta = computed(() => {
  const metaJson = programInfo.value?.meta_json;
  if (!metaJson) {
    return null;
  }
  try {
    return JSON.parse(metaJson) as {
      assumptions?: string[];
      source_files?: Record<string, string>;
    };
  } catch {
    return null;
  }
});

const sourceFileRows = computed(() => {
  const sourceFiles = parsedMeta.value?.source_files || {};
  return Object.entries(sourceFiles).map(([key, value]) => ({ key, value }));
});

const assumptionRows = computed(() => parsedMeta.value?.assumptions || []);

function parseMaterialMeta(metaJson?: string | null) {
  if (!metaJson) {
    return null;
  }
  try {
    return JSON.parse(metaJson) as {
      english_name?: string;
      father_accession?: string;
      mother_accession?: string;
      father_name?: string;
      mother_name?: string;
      history?: string;
      flower_traits?: string;
      plant_traits?: string;
      usage?: string;
    };
  } catch {
    return null;
  }
}

const selectedMaterialMeta = computed(() => {
  return parseMaterialMeta(selectedMaterial.value?.meta_json);
});

const selectedMaterialParents = computed(() => {
  const meta = selectedMaterialMeta.value;
  return [
    {
      role: $t('breeding.detail.father'),
      accession: meta?.father_accession || null,
      name: meta?.father_name || null,
      material:
        (meta?.father_accession && (materialByCodeMap.value[meta.father_accession] || materialByGermplasmMap.value[meta.father_accession])) ||
        null,
    },
    {
      role: $t('breeding.detail.mother'),
      accession: meta?.mother_accession || null,
      name: meta?.mother_name || null,
      material:
        (meta?.mother_accession && (materialByCodeMap.value[meta.mother_accession] || materialByGermplasmMap.value[meta.mother_accession])) ||
        null,
    },
  ];
});

const filteredPlotRows = computed(() => {
  if (!activeMaterialId.value) {
    return plotRows.value;
  }
  return plotRows.value.filter(item => item.material_id === activeMaterialId.value);
});

const filteredTrialRows = computed(() => {
  if (!activeMaterialId.value) {
    return trialRows.value;
  }
  const trialIds = new Set(filteredPlotRows.value.map(item => item.trial_id));
  return trialRows.value.filter(item => trialIds.has(item.id));
});

const filteredObservationRows = computed(() => {
  if (!activeMaterialId.value) {
    return observationRows.value;
  }
  return observationRows.value.filter(item => item.material_id === activeMaterialId.value);
});

const filteredBioSampleRows = computed(() => {
  if (!activeMaterialId.value) {
    return biosampleRows.value;
  }
  return biosampleRows.value.filter(item => item.material_id === activeMaterialId.value);
});

const filteredAssayRows = computed(() => {
  if (!activeMaterialId.value) {
    return assayRows.value;
  }
  const biosampleIds = new Set(filteredBioSampleRows.value.map(item => item.id));
  return assayRows.value.filter(item => biosampleIds.has(item.biosample_id));
});

const filteredDataFileRows = computed(() => {
  if (!activeMaterialId.value) {
    return dataFileRows.value;
  }
  const assayIds = new Set(filteredAssayRows.value.map(item => item.id));
  return dataFileRows.value.filter(item => assayIds.has(item.assay_id));
});

const pedigreeOverviewRows = computed(() =>
  materialRows.value
    .map((material) => {
      const meta = parseMaterialMeta(material.meta_json);
      const fatherAccession = meta?.father_accession || null;
      const motherAccession = meta?.mother_accession || null;
      const fatherMaterial =
        (fatherAccession && (materialByCodeMap.value[fatherAccession] || materialByGermplasmMap.value[fatherAccession])) ||
        null;
      const motherMaterial =
        (motherAccession && (materialByCodeMap.value[motherAccession] || materialByGermplasmMap.value[motherAccession])) ||
        null;
      return {
        id: material.id,
        materialCode: material.material_code,
        materialName: material.material_name,
        fatherAccession,
        fatherName: meta?.father_name || fatherMaterial?.material_name || fatherAccession,
        fatherMaterial,
        motherAccession,
        motherName: meta?.mother_name || motherMaterial?.material_name || motherAccession,
        motherMaterial,
        knownParentCount: Number(Boolean(fatherAccession)) + Number(Boolean(motherAccession)),
      };
    })
    .filter(item => item.knownParentCount > 0)
    .sort((a, b) => b.knownParentCount - a.knownParentCount || a.materialCode.localeCompare(b.materialCode))
    .slice(0, 8),
);

const pedigreeOverviewStats = computed(() => ({
  withPedigree: pedigreeOverviewRows.value.length,
  linkedParents: pedigreeOverviewRows.value.reduce(
    (acc, item) => acc + Number(Boolean(item.fatherMaterial)) + Number(Boolean(item.motherMaterial)),
    0,
  ),
}));

const focusSummary = computed(() => ({
  plots: filteredPlotRows.value.length,
  trials: filteredTrialRows.value.length,
  observations: filteredObservationRows.value.length,
  biosamples: filteredBioSampleRows.value.length,
  assays: filteredAssayRows.value.length,
  dataFiles: filteredDataFileRows.value.length,
}));

const materialSpotlightRows = computed(() =>
  materialRows.value
    .map((material) => {
      const plotCount = plotRows.value.filter(item => item.material_id === material.id).length;
      const observationCount = observationRows.value.filter(item => item.material_id === material.id).length;
      const biosampleList = biosampleRows.value.filter(item => item.material_id === material.id);
      const biosampleCount = biosampleList.length;
      const biosampleIds = new Set(biosampleList.map(item => item.id));
      const assayList = assayRows.value.filter(item => biosampleIds.has(item.biosample_id));
      const assayCount = assayList.length;
      const assayIds = new Set(assayList.map(item => item.id));
      const dataFileCount = dataFileRows.value.filter(item => assayIds.has(item.assay_id)).length;
      return {
        ...material,
        plotCount,
        observationCount,
        biosampleCount,
        assayCount,
        dataFileCount,
      };
    })
    .sort((a, b) => b.observationCount - a.observationCount || b.assayCount - a.assayCount || a.material_code.localeCompare(b.material_code))
    .slice(0, 6),
);

const traitSummaryRows = computed(() => {
  const summaryMap = new Map<string, {
    key: string;
    traitName: string;
    traitCode: string;
    count: number;
    numericCount: number;
    numericSum: number;
    latestDate: string | null;
  }>();
  observationRows.value.forEach((item) => {
    const traitKey = item.trait_code || item.trait_name || String(item.id);
    if (!summaryMap.has(traitKey)) {
      summaryMap.set(traitKey, {
        key: traitKey,
        traitName: item.trait_name || item.trait_code,
        traitCode: item.trait_code,
        count: 0,
        numericCount: 0,
        numericSum: 0,
        latestDate: null,
      });
    }
    const target = summaryMap.get(traitKey)!;
    target.count += 1;
    if (typeof item.obs_value_num === 'number') {
      target.numericCount += 1;
      target.numericSum += item.obs_value_num;
    }
    if (item.obs_date && (!target.latestDate || item.obs_date > target.latestDate)) {
      target.latestDate = item.obs_date;
    }
  });
  return Array.from(summaryMap.values())
    .map(item => ({
      ...item,
      meanValue: item.numericCount ? (item.numericSum / item.numericCount).toFixed(2) : '-',
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);
});

const sampleTypeSummaryRows = computed(() => {
  const summary = new Map<string, number>();
  biosampleRows.value.forEach((item) => {
    const key = item.sample_type || 'unknown';
    summary.set(key, (summary.get(key) || 0) + 1);
  });
  return Array.from(summary.entries()).map(([label, count]) => ({ label, count }));
});

const assayTypeSummaryRows = computed(() => {
  const summary = new Map<string, number>();
  assayRows.value.forEach((item) => {
    const key = item.assay_type || 'unknown';
    summary.set(key, (summary.get(key) || 0) + 1);
  });
  return Array.from(summary.entries()).map(([label, count]) => ({ label, count }));
});

const fileRoleSummaryRows = computed(() => {
  const summary = new Map<string, number>();
  dataFileRows.value.forEach((item) => {
    const key = item.file_role || 'unknown';
    summary.set(key, (summary.get(key) || 0) + 1);
  });
  return Array.from(summary.entries()).map(([label, count]) => ({ label, count }));
});

const activeMaterialTraitSummaryRows = computed(() => {
  const summaryMap = new Map<string, {
    key: string;
    traitName: string;
    traitCode: string;
    count: number;
    numericCount: number;
    numericSum: number;
  }>();
  filteredObservationRows.value.forEach((item) => {
    if (!activeMaterialId.value || item.material_id !== activeMaterialId.value) {
      return;
    }
    const key = item.trait_code || item.trait_name || String(item.id);
    if (!summaryMap.has(key)) {
      summaryMap.set(key, {
        key,
        traitName: item.trait_name || item.trait_code,
        traitCode: item.trait_code,
        count: 0,
        numericCount: 0,
        numericSum: 0,
      });
    }
    const target = summaryMap.get(key)!;
    target.count += 1;
    if (typeof item.obs_value_num === 'number') {
      target.numericCount += 1;
      target.numericSum += item.obs_value_num;
    }
  });
  return Array.from(summaryMap.values())
    .map(item => ({
      ...item,
      meanValue: item.numericCount ? (item.numericSum / item.numericCount).toFixed(2) : '-',
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6);
});

const activeMaterialAssayTypeRows = computed(() => {
  const summary = new Map<string, number>();
  filteredAssayRows.value.forEach((item) => {
    const key = item.assay_type || 'unknown';
    summary.set(key, (summary.get(key) || 0) + 1);
  });
  return Array.from(summary.entries()).map(([label, count]) => ({ label, count }));
});

const activeMaterialFileRoleRows = computed(() => {
  const summary = new Map<string, number>();
  filteredDataFileRows.value.forEach((item) => {
    const key = item.file_role || 'unknown';
    summary.set(key, (summary.get(key) || 0) + 1);
  });
  return Array.from(summary.entries()).map(([label, count]) => ({ label, count }));
});

const activeMaterialBioSamplePreviewRows = computed(() =>
  filteredBioSampleRows.value
    .slice(0, 6)
    .map(item => ({
      id: item.id,
      sampleCode: item.sample_code,
      sampleType: item.sample_type || '-',
      tissueType: item.tissue_type || '-',
      timepoint: item.timepoint || '-',
    })),
);

const materialColumns = [
  { title: $t('breeding.detail.materialCode'), dataIndex: 'material_code', key: 'material_code', width: 160 },
  { title: $t('breeding.detail.materialName'), dataIndex: 'material_name', key: 'material_name', minWidth: 220 },
  { title: $t('breeding.detail.type'), dataIndex: 'material_type', key: 'material_type', width: 120 },
  { title: $t('breeding.detail.germplasmAccession'), dataIndex: 'germplasm_accession', key: 'germplasm_accession', width: 160 },
  { title: $t('breeding.detail.germplasmName'), dataIndex: 'germplasm_name', key: 'germplasm_name', width: 180 },
  { title: $t('breeding.detail.germplasmSourceFile'), dataIndex: 'germplasm_source_file', key: 'germplasm_source_file', minWidth: 320 },
  { title: $t('breeding.detail.generation'), dataIndex: 'generation_code', key: 'generation_code', width: 120 },
  { title: $t('breeding.detail.origin'), dataIndex: 'origin', key: 'origin', width: 160 },
  { title: $t('breeding.detail.isCheck'), dataIndex: 'is_check', key: 'is_check', width: 80 },
  { title: $t('breeding.detail.status'), dataIndex: 'status', key: 'status', width: 100 },
  { title: $t('breeding.detail.action'), key: 'action', width: 120, fixed: 'right' as const },
];

const trialColumns = [
  { title: $t('breeding.detail.trialCode'), dataIndex: 'trial_code', key: 'trial_code', width: 160 },
  { title: $t('breeding.detail.trialName'), dataIndex: 'trial_name', key: 'trial_name', minWidth: 220 },
  { title: $t('breeding.detail.type'), dataIndex: 'trial_type', key: 'trial_type', width: 120 },
  { title: $t('breeding.detail.location'), dataIndex: 'location_name', key: 'location_name', width: 160 },
  { title: $t('breeding.detail.season'), dataIndex: 'season_label', key: 'season_label', width: 120 },
  { title: $t('breeding.detail.design'), dataIndex: 'design_type', key: 'design_type', width: 120 },
  { title: $t('breeding.detail.replicates'), dataIndex: 'replicate_count', key: 'replicate_count', width: 100 },
  { title: $t('breeding.detail.status'), dataIndex: 'status', key: 'status', width: 100 },
];

const plotColumns = [
  { title: $t('breeding.detail.plotCode'), dataIndex: 'plot_code', key: 'plot_code', width: 160 },
  { title: $t('breeding.detail.trials'), dataIndex: 'trial_id', key: 'trial_id', minWidth: 220 },
  { title: $t('breeding.detail.materials'), dataIndex: 'material_id', key: 'material_id', minWidth: 220 },
  { title: $t('breeding.detail.replicate'), dataIndex: 'replicate_no', key: 'replicate_no', width: 100 },
  { title: $t('breeding.detail.block'), dataIndex: 'block_no', key: 'block_no', width: 100 },
  { title: $t('breeding.detail.row'), dataIndex: 'row_no', key: 'row_no', width: 80 },
  { title: $t('breeding.detail.col'), dataIndex: 'col_no', key: 'col_no', width: 80 },
  { title: $t('breeding.detail.treatment'), dataIndex: 'treatment_code', key: 'treatment_code', width: 120 },
  { title: $t('breeding.detail.status'), dataIndex: 'status', key: 'status', width: 100 },
];

const biosampleColumns = [
  { title: $t('breeding.detail.sampleCode'), dataIndex: 'sample_code', key: 'sample_code', width: 160 },
  { title: $t('breeding.detail.materials'), dataIndex: 'material_id', key: 'material_id', minWidth: 220 },
  { title: $t('breeding.detail.plots'), dataIndex: 'plot_id', key: 'plot_id', minWidth: 200 },
  { title: $t('breeding.detail.sampleType'), dataIndex: 'sample_type', key: 'sample_type', width: 120 },
  { title: $t('breeding.detail.tissue'), dataIndex: 'tissue_type', key: 'tissue_type', width: 120 },
  { title: $t('breeding.detail.timepoint'), dataIndex: 'timepoint', key: 'timepoint', width: 120 },
  { title: $t('breeding.detail.collectionDate'), dataIndex: 'collection_date', key: 'collection_date', width: 140 },
  { title: $t('breeding.detail.status'), dataIndex: 'status', key: 'status', width: 100 },
  { title: $t('breeding.detail.chain'), key: 'action', width: 120, fixed: 'right' as const },
];

const observationColumns = [
  { title: $t('breeding.detail.materials'), dataIndex: 'material_id', key: 'material_id', minWidth: 220 },
  { title: $t('breeding.detail.plots'), dataIndex: 'plot_id', key: 'plot_id', minWidth: 200 },
  { title: $t('breeding.detail.observationLevel'), dataIndex: 'observation_level', key: 'observation_level', width: 100 },
  { title: $t('breeding.detail.traitCode'), dataIndex: 'trait_code', key: 'trait_code', width: 160 },
  { title: $t('breeding.detail.traitName'), dataIndex: 'trait_name', key: 'trait_name', minWidth: 180 },
  { title: $t('breeding.detail.numericValue'), dataIndex: 'obs_value_num', key: 'obs_value_num', width: 120 },
  { title: $t('breeding.detail.textValue'), dataIndex: 'obs_value_text', key: 'obs_value_text', minWidth: 180 },
  { title: $t('breeding.detail.score'), dataIndex: 'obs_value_score', key: 'obs_value_score', width: 100 },
  { title: $t('breeding.detail.obsDate'), dataIndex: 'obs_date', key: 'obs_date', width: 140 },
  { title: $t('breeding.detail.qcStatus'), dataIndex: 'qc_status', key: 'qc_status', width: 120 },
  { title: $t('breeding.detail.sourceRowKey'), dataIndex: 'source_row_key', key: 'source_row_key', width: 140 },
];

const assayColumns = [
  { title: $t('breeding.detail.assayCode'), dataIndex: 'assay_code', key: 'assay_code', width: 160 },
  { title: $t('breeding.detail.sample'), dataIndex: 'biosample_id', key: 'biosample_id', minWidth: 260 },
  { title: $t('breeding.detail.assayType'), dataIndex: 'assay_type', key: 'assay_type', width: 140 },
  { title: $t('breeding.detail.platform'), dataIndex: 'platform', key: 'platform', width: 140 },
  { title: $t('breeding.detail.vendor'), dataIndex: 'vendor', key: 'vendor', width: 140 },
  { title: $t('breeding.detail.runDate'), dataIndex: 'run_date', key: 'run_date', width: 140 },
  { title: $t('breeding.detail.status'), dataIndex: 'status', key: 'status', width: 100 },
  { title: $t('breeding.detail.chain'), key: 'action', width: 120, fixed: 'right' as const },
];

const dataFileColumns = [
  { title: $t('breeding.detail.relatedAssay'), dataIndex: 'assay_id', key: 'assay_id', minWidth: 220 },
  { title: $t('breeding.detail.fileName'), dataIndex: 'file_name', key: 'file_name', minWidth: 220 },
  { title: $t('breeding.detail.fileRole'), dataIndex: 'file_role', key: 'file_role', width: 120 },
  { title: $t('breeding.detail.format'), dataIndex: 'file_format', key: 'file_format', width: 120 },
  { title: $t('breeding.detail.sourceMode'), dataIndex: 'source_mode', key: 'source_mode', width: 140 },
  { title: $t('breeding.detail.datasetRef'), dataIndex: 'dataset_id', key: 'dataset_ref', minWidth: 220 },
  { title: $t('breeding.detail.status'), dataIndex: 'status', key: 'status', width: 100 },
  { title: $t('breeding.detail.chain'), key: 'action', width: 120, fixed: 'right' as const },
];

function statusColor(status?: string | null) {
  if (status === 'active') {
    return 'green';
  }
  if (status === 'archived') {
    return 'orange';
  }
  if (status === 'draft') {
    return 'blue';
  }
  return 'default';
}

function resolveMaterialLabel(materialId?: number | null) {
  if (!materialId) {
    return '-';
  }
  const material = materialMap.value[materialId];
  if (!material) {
    return `#${materialId}`;
  }
  return `${material.material_code} / ${material.material_name}`;
}

function resolveTrialLabel(trialId?: number | null) {
  if (!trialId) {
    return '-';
  }
  const trial = trialMap.value[trialId];
  if (!trial) {
    return `#${trialId}`;
  }
  return `${trial.trial_code} / ${trial.trial_name}`;
}

function resolvePlotLabel(plotId?: number | null) {
  if (!plotId) {
    return '-';
  }
  const plot = plotMap.value[plotId];
  if (!plot) {
    return `#${plotId}`;
  }
  return `${plot.plot_code} · ${resolveMaterialLabel(plot.material_id)}`;
}

function resolveBioSampleLabel(biosampleId?: number | null) {
  if (!biosampleId) {
    return '-';
  }
  const biosample = biosampleMap.value[biosampleId];
  if (!biosample) {
    return `#${biosampleId}`;
  }
  return `${biosample.sample_code} · ${resolveMaterialLabel(biosample.material_id)}`;
}

function resolveAssayLabel(assayId?: number | null) {
  if (!assayId) {
    return '-';
  }
  const assay = assayMap.value[assayId];
  if (!assay) {
    return `#${assayId}`;
  }
  return `${assay.assay_code} · ${assay.assay_type}`;
}

function formatDatasetRef(record: Partial<BreedingDataFileItem>) {
  const parts = [];
  if (record.dataset_id) {
    parts.push(`D${record.dataset_id}`);
  }
  if (record.version_id) {
    parts.push(`V${record.version_id}`);
  }
  if (record.asset_id) {
    parts.push(`A${record.asset_id}`);
  }
  return parts.length > 0 ? parts.join(' / ') : '-';
}

function formatMetaJson(metaJson?: string | null) {
  if (!metaJson) {
    return '-';
  }
  try {
    return JSON.stringify(JSON.parse(metaJson), null, 2);
  } catch {
    return metaJson;
  }
}

function setMaterialFocus(materialId?: number | null) {
  activeMaterialId.value = materialId || null;
}

function clearMaterialFocus() {
  activeMaterialId.value = null;
}

function focusMaterialByReference(reference?: string | null) {
  if (!reference) {
    return;
  }
  const material = materialByCodeMap.value[reference] || materialByGermplasmMap.value[reference];
  if (material) {
    setMaterialFocus(material.id);
  }
}

async function openMaterialFlow(materialId?: number | null, tab: DetailTabKey = 'omics') {
  if (materialId) {
    setMaterialFocus(materialId);
  }
  activeTab.value = tab;
  await ensureTabLoaded(tab);
}

async function openBioSampleFlow(record: Partial<BreedingBioSampleItem>) {
  await openMaterialFlow(record.material_id, 'omics');
}

async function openAssayFlow(record: Partial<BreedingAssayItem>) {
  const biosample = record.biosample_id ? biosampleMap.value[record.biosample_id] : null;
  await openMaterialFlow(biosample?.material_id, 'omics');
}

async function openDataFileFlow(record: Partial<BreedingDataFileItem>) {
  const assay = record.assay_id ? assayMap.value[record.assay_id] : null;
  await openAssayFlow(assay || {});
}

async function loadSummary() {
  if (!currentProgramId.value) {
    return;
  }
  pageLoading.value = true;
  try {
    const [info, overview] = await Promise.all([
      getBreedingProgramInfoApi({ id: currentProgramId.value }),
      getBreedingProgramOverviewApi({ id: currentProgramId.value }),
    ]);
    programInfo.value = info;
    programOverview.value = overview;
    loadedTabs.overview = true;
  } finally {
    pageLoading.value = false;
  }
}

async function loadMaterials() {
  materialsLoading.value = true;
  try {
    const result = await getBreedingMaterialListApi({
      page: 1,
      size: 100,
      program_id: currentProgramId.value,
    });
    materialRows.value = result.items || [];
    loadedTabs.materials = true;
  } finally {
    materialsLoading.value = false;
  }
}

async function loadTrials() {
  trialsLoading.value = true;
  try {
    const result = await getBreedingTrialListApi({
      page: 1,
      size: 100,
      program_id: currentProgramId.value,
    });
    trialRows.value = result.items || [];
    loadedTabs.trials = true;
  } finally {
    trialsLoading.value = false;
  }
}

async function loadPlots() {
  plotsLoading.value = true;
  try {
    const result = await getBreedingPlotListApi({
      page: 1,
      size: 100,
      program_id: currentProgramId.value,
    });
    plotRows.value = result.items || [];
    loadedTabs.plots = true;
  } finally {
    plotsLoading.value = false;
  }
}

async function loadObservations() {
  observationsLoading.value = true;
  try {
    const result = await getBreedingObservationListApi({
      page: 1,
      size: 500,
      program_id: currentProgramId.value,
    });
    observationRows.value = result.items || [];
    loadedTabs.observations = true;
  } finally {
    observationsLoading.value = false;
  }
}

async function loadBioSamples() {
  biosamplesLoading.value = true;
  try {
    const result = await getBreedingBioSampleListApi({
      page: 1,
      size: 100,
      program_id: currentProgramId.value,
    });
    biosampleRows.value = result.items || [];
    loadedTabs.biosamples = true;
  } finally {
    biosamplesLoading.value = false;
  }
}

async function loadOmics() {
  assaysLoading.value = true;
  dataFilesLoading.value = true;
  try {
    const [assays, dataFiles] = await Promise.all([
      getBreedingAssayListApi({
        page: 1,
        size: 100,
        program_id: currentProgramId.value,
      }),
      getBreedingDataFileListApi({
        page: 1,
        size: 100,
        program_id: currentProgramId.value,
      }),
    ]);
    assayRows.value = assays.items || [];
    dataFileRows.value = dataFiles.items || [];
    loadedTabs.omics = true;
  } finally {
    assaysLoading.value = false;
    dataFilesLoading.value = false;
  }
}

async function ensureTabLoaded(tab: DetailTabKey) {
  if (tab === 'overview' && !loadedTabs.overview) {
    await loadSummary();
  }
  if (tab === 'materials' && !loadedTabs.materials) {
    await loadMaterials();
  }
  if (tab === 'trials' && !loadedTabs.trials) {
    await loadTrials();
  }
  if (tab === 'plots' && !loadedTabs.plots) {
    await loadPlots();
  }
  if (tab === 'observations' && !loadedTabs.observations) {
    await loadObservations();
  }
  if (tab === 'biosamples' && !loadedTabs.biosamples) {
    await loadBioSamples();
  }
  if (tab === 'omics' && !loadedTabs.omics) {
    await loadOmics();
  }
}

function handleTabChange(activeKey: string | number) {
  void ensureTabLoaded(activeKey as DetailTabKey);
}

function resetLoadedTabs() {
  (Object.keys(loadedTabs) as DetailTabKey[]).forEach((key) => {
    loadedTabs[key] = false;
  });
}

function goBack() {
  router.push('/breeding/program').catch((error) => {
    console.error('Navigation failed:', error);
  });
}

function openGermplasmInfo(material: Partial<BreedingMaterialItem> | null | undefined) {
  if (!material?.germplasm_accession) {
    return;
  }
  router.push({
    path: '/germplasm/info',
    query: {
      id: material.germplasm_accession,
      file_path: material.germplasm_source_file || undefined,
    },
  });
}

async function initializePage() {
  resetLoadedTabs();
  activeMaterialId.value = null;
  materialRows.value = [];
  trialRows.value = [];
  plotRows.value = [];
  observationRows.value = [];
  biosampleRows.value = [];
  assayRows.value = [];
  dataFileRows.value = [];
  activeTab.value = 'overview';
  await loadSummary();
  await Promise.all([
    loadMaterials(),
    loadTrials(),
    loadPlots(),
    loadObservations(),
    loadBioSamples(),
    loadOmics(),
  ]);
}

watch(
  () => route.params.id,
  () => {
    void initializePage();
  },
);

onMounted(() => {
  void initializePage();
});
</script>

<template>
  <Page auto-content-height content-class="p-5">
    <div class="program-detail-page">
      <div class="page-header">
        <Button @click="goBack">{{ $t('breeding.detail.backToList') }}</Button>
      </div>

      <Spin :spinning="pageLoading">
        <Card v-if="programInfo" :bordered="false" class="hero-card">
          <div class="hero-eyebrow">{{ $t('breeding.detail.heroEyebrow') }}</div>
          <h2 class="hero-title">{{ programInfo.name }}</h2>
          <div class="hero-meta">
            <Tag color="blue">{{ programInfo.code }}</Tag>
            <Tag :color="statusColor(programInfo.status)">
              {{ programInfo.status || $t('breeding.detail.unknown') }}
            </Tag>
            <Tag v-if="programInfo.species_name">{{ programInfo.species_name }}</Tag>
          </div>
          <p class="hero-description">
            {{ programInfo.breeding_goal || $t('breeding.detail.noBreedingGoal') }}
          </p>
        </Card>

        <Empty v-else :description="$t('breeding.detail.noProjectFound')" />
      </Spin>

      <div v-if="programOverview" class="stats-grid">
        <Card :bordered="false"><div class="stat-label">{{ $t('breeding.detail.materials') }}</div><div class="stat-value">{{ programOverview.counts.materials }}</div></Card>
        <Card :bordered="false"><div class="stat-label">{{ $t('breeding.detail.trials') }}</div><div class="stat-value">{{ programOverview.counts.trials }}</div></Card>
        <Card :bordered="false"><div class="stat-label">{{ $t('breeding.detail.plots') }}</div><div class="stat-value">{{ programOverview.counts.plots }}</div></Card>
        <Card :bordered="false"><div class="stat-label">{{ $t('breeding.detail.observations') }}</div><div class="stat-value">{{ programOverview.counts.observations }}</div></Card>
        <Card :bordered="false"><div class="stat-label">{{ $t('breeding.detail.biosamples') }}</div><div class="stat-value">{{ programOverview.counts.biosamples }}</div></Card>
        <Card :bordered="false"><div class="stat-label">{{ $t('breeding.detail.omicsExperiments') }}</div><div class="stat-value">{{ programOverview.counts.assays }}</div></Card>
        <Card :bordered="false"><div class="stat-label">{{ $t('breeding.detail.datasetLinks') }}</div><div class="stat-value">{{ programOverview.counts.dataset_links }}</div></Card>
      </div>

      <Card :bordered="false">
        <div class="focus-toolbar">
          <div class="focus-heading">
            <div class="focus-title">{{ $t('breeding.detail.materialFocus') }}</div>
            <div class="focus-description">
              {{ $t('breeding.detail.materialFocusDesc') }}
            </div>
          </div>
          <div class="focus-actions">
            <Button
              :type="!activeMaterialId ? 'primary' : 'default'"
              size="small"
              @click="clearMaterialFocus"
            >
              {{ $t('breeding.detail.viewAll') }}
            </Button>
            <Button
              v-for="item in materialRows"
              :key="item.id"
              :type="activeMaterialId === item.id ? 'primary' : 'default'"
              size="small"
              @click="setMaterialFocus(item.id)"
            >
              {{ item.material_code }}
            </Button>
          </div>
        </div>

        <div v-if="selectedMaterial" class="focus-summary-grid">
          <Card :bordered="false" class="focus-summary-card">
            <div class="focus-summary-eyebrow">{{ $t('breeding.detail.focusedMaterial') }}</div>
            <div class="focus-summary-title">
              {{ selectedMaterial.material_code }} / {{ selectedMaterial.material_name }}
            </div>
            <div class="focus-summary-meta">
              <Tag color="blue">{{ selectedMaterial.material_type }}</Tag>
              <Tag v-if="selectedMaterial.germplasm_accession">
                {{ selectedMaterial.germplasm_accession }}
              </Tag>
              <Tag v-if="selectedMaterial.is_check">{{ $t('breeding.detail.checkMaterial') }}</Tag>
            </div>
          </Card>
          <Card :bordered="false"><div class="stat-label">{{ $t('breeding.detail.relatedTrial') }}</div><div class="stat-value stat-value-sm">{{ focusSummary.trials }}</div></Card>
          <Card :bordered="false"><div class="stat-label">{{ $t('breeding.detail.relatedPlot') }}</div><div class="stat-value stat-value-sm">{{ focusSummary.plots }}</div></Card>
          <Card :bordered="false"><div class="stat-label">{{ $t('breeding.detail.relatedObservation') }}</div><div class="stat-value stat-value-sm">{{ focusSummary.observations }}</div></Card>
          <Card :bordered="false"><div class="stat-label">{{ $t('breeding.detail.relatedSample') }}</div><div class="stat-value stat-value-sm">{{ focusSummary.biosamples }}</div></Card>
          <Card :bordered="false"><div class="stat-label">{{ $t('breeding.detail.relatedExperiment') }}</div><div class="stat-value stat-value-sm">{{ focusSummary.assays }}</div></Card>
          <Card :bordered="false"><div class="stat-label">{{ $t('breeding.detail.relatedFile') }}</div><div class="stat-value stat-value-sm">{{ focusSummary.dataFiles }}</div></Card>
        </div>

        <Tabs v-model:active-key="activeTab" @change="handleTabChange">
          <TabPane key="overview" :tab="$t('breeding.detail.overview')">
            <Descriptions v-if="programInfo" bordered :column="2">
              <DescriptionsItem :label="$t('breeding.detail.programCode')">{{ programInfo.code }}</DescriptionsItem>
              <DescriptionsItem :label="$t('breeding.detail.programName')">{{ programInfo.name }}</DescriptionsItem>
              <DescriptionsItem :label="$t('breeding.detail.species')">{{ programInfo.species_name || '-' }}</DescriptionsItem>
              <DescriptionsItem :label="$t('breeding.detail.startYear')">{{ programInfo.start_year || '-' }}</DescriptionsItem>
              <DescriptionsItem :label="$t('breeding.detail.owner')">{{ programInfo.owner_name || '-' }}</DescriptionsItem>
              <DescriptionsItem :label="$t('breeding.detail.status')">
                <Tag :color="statusColor(programInfo.status)">
                  {{ programInfo.status || $t('breeding.detail.unknown') }}
                </Tag>
              </DescriptionsItem>
              <DescriptionsItem :span="2" :label="$t('breeding.detail.breedingGoal')">
                {{ programInfo.breeding_goal || '-' }}
              </DescriptionsItem>
              <DescriptionsItem :span="2" :label="$t('breeding.detail.sourceFile')">
                <div v-if="sourceFileRows.length" class="source-file-list">
                  <div v-for="item in sourceFileRows" :key="item.key" class="source-file-item">
                    <span class="source-file-key">{{ item.key }}</span>
                    <span class="source-file-value">{{ item.value }}</span>
                  </div>
                </div>
                <span v-else>-</span>
              </DescriptionsItem>
              <DescriptionsItem :span="2" :label="$t('breeding.detail.assumptions')">
                <div v-if="assumptionRows.length" class="assumption-list">
                  <div v-for="item in assumptionRows" :key="item" class="assumption-item">
                    {{ item }}
                  </div>
                </div>
                <span v-else>-</span>
              </DescriptionsItem>
              <DescriptionsItem :span="2" :label="$t('breeding.detail.extendedInfo')">
                <pre class="meta-json">{{ formatMetaJson(programInfo.meta_json) }}</pre>
              </DescriptionsItem>
            </Descriptions>

            <div class="overview-section-grid">
              <Card :bordered="false" class="overview-panel">
                <div class="overview-panel-title">{{ $t('breeding.detail.currentFocus') }}</div>
                <div v-if="selectedMaterial" class="overview-focus-card">
                  <div class="overview-focus-name">
                    {{ selectedMaterial.material_code }} / {{ selectedMaterial.material_name }}
                  </div>
                  <div class="overview-focus-meta">
                    <Tag color="blue">{{ selectedMaterial.material_type }}</Tag>
                    <Tag v-if="selectedMaterial.germplasm_accession">
                      {{ selectedMaterial.germplasm_accession }}
                    </Tag>
                  </div>
                  <div class="overview-action-row">
                    <Button size="small" type="primary" @click="openMaterialFlow(selectedMaterial.id, 'observations')">
                      {{ $t('breeding.detail.viewObservation') }}
                    </Button>
                    <Button size="small" @click="openMaterialFlow(selectedMaterial.id, 'biosamples')">
                      {{ $t('breeding.detail.viewSample') }}
                    </Button>
                    <Button size="small" @click="openMaterialFlow(selectedMaterial.id, 'omics')">
                      {{ $t('breeding.detail.viewOmics') }}
                    </Button>
                  </div>
                </div>
                <div v-else class="overview-empty-hint">
                  {{ $t('breeding.detail.selectMaterialHint') }}
                </div>
              </Card>

              <Card :bordered="false" class="overview-panel">
                <div class="overview-panel-title">{{ $t('breeding.detail.materialEntry') }}</div>
                <div class="overview-chip-grid">
                  <button
                    v-for="item in materialSpotlightRows"
                    :key="item.id"
                    class="overview-chip"
                    type="button"
                    @click="setMaterialFocus(item.id)"
                  >
                    <span class="overview-chip-code">{{ item.material_code }}</span>
                    <span class="overview-chip-name">{{ item.material_name }}</span>
                    <span class="overview-chip-meta">
                      {{ $t('breeding.detail.observationsTag') }} {{ item.observationCount }} / {{ $t('breeding.detail.experimentsTag') }} {{ item.assayCount }}
                    </span>
                  </button>
                </div>
              </Card>
            </div>

            <div class="overview-section-grid">
              <Card :bordered="false" class="overview-panel">
                <div class="overview-panel-title">{{ $t('breeding.detail.traitSummary') }}</div>
                <div class="overview-list">
                  <div v-for="item in traitSummaryRows" :key="item.key" class="overview-list-item">
                    <div class="overview-list-main">
                      <div class="overview-list-title">{{ item.traitName }}</div>
                      <div class="overview-list-subtitle">{{ item.traitCode }}</div>
                    </div>
                    <div class="overview-list-stats">
                      <span>{{ item.count }} {{ $t('breeding.detail.entries') }}</span>
                      <span>{{ $t('breeding.detail.mean') }} {{ item.meanValue }}</span>
                    </div>
                  </div>
                </div>
              </Card>

              <Card :bordered="false" class="overview-panel">
                <div class="overview-panel-title">{{ $t('breeding.detail.omicsSummary') }}</div>
                <div class="overview-summary-block">
                  <div class="overview-summary-group">
                    <div class="overview-summary-title">{{ $t('breeding.detail.sampleTypeSummary') }}</div>
                    <div class="overview-tag-list">
                      <Tag v-for="item in sampleTypeSummaryRows" :key="item.label" color="purple">
                        {{ item.label }} · {{ item.count }}
                      </Tag>
                    </div>
                  </div>
                  <div class="overview-summary-group">
                    <div class="overview-summary-title">{{ $t('breeding.detail.assayTypeSummary') }}</div>
                    <div class="overview-tag-list">
                      <Tag v-for="item in assayTypeSummaryRows" :key="item.label" color="cyan">
                        {{ item.label }} · {{ item.count }}
                      </Tag>
                    </div>
                  </div>
                  <div class="overview-summary-group">
                    <div class="overview-summary-title">{{ $t('breeding.detail.fileRoleSummary') }}</div>
                    <div class="overview-tag-list">
                      <Tag v-for="item in fileRoleSummaryRows" :key="item.label" color="geekblue">
                        {{ item.label }} · {{ item.count }}
                      </Tag>
                    </div>
                  </div>
                </div>
              </Card>
            </div>

            <div class="overview-section-grid">
              <Card :bordered="false" class="overview-panel">
                <div class="overview-panel-title">{{ $t('breeding.detail.pedigreeOverview') }}</div>
                <div class="pedigree-overview-meta">
                  <Tag color="blue">{{ $t('breeding.detail.pedigreeOverviewMeta') }} {{ pedigreeOverviewStats.withPedigree }}</Tag>
                  <Tag color="cyan">{{ $t('breeding.detail.parentLinks') }} {{ pedigreeOverviewStats.linkedParents }}</Tag>
                </div>
                <div v-if="pedigreeOverviewRows.length" class="pedigree-overview-list">
                  <div
                    v-for="item in pedigreeOverviewRows"
                    :key="item.id"
                    class="pedigree-overview-item"
                  >
                    <div class="pedigree-overview-child">
                      <div class="pedigree-overview-code">{{ item.materialCode }}</div>
                      <div class="pedigree-overview-name">{{ item.materialName }}</div>
                    </div>
                    <div class="pedigree-overview-arrow">←</div>
                    <div class="pedigree-overview-parents">
                      <button
                        class="pedigree-parent-chip"
                        type="button"
                        @click="focusMaterialByReference(item.fatherAccession)"
                      >
                        <span class="pedigree-parent-role">{{ $t('breeding.detail.father') }}</span>
                        <span class="pedigree-parent-name">{{ item.fatherName || '-' }}</span>
                        <span class="pedigree-parent-ref">{{ item.fatherAccession || '-' }}</span>
                      </button>
                      <button
                        class="pedigree-parent-chip"
                        type="button"
                        @click="focusMaterialByReference(item.motherAccession)"
                      >
                        <span class="pedigree-parent-role">{{ $t('breeding.detail.mother') }}</span>
                        <span class="pedigree-parent-name">{{ item.motherName || '-' }}</span>
                        <span class="pedigree-parent-ref">{{ item.motherAccession || '-' }}</span>
                      </button>
                    </div>
                  </div>
                </div>
                <div v-else class="overview-empty-hint">
                  {{ $t('breeding.detail.noPedigreeAvailable') }}
                </div>
              </Card>

              <Card :bordered="false" class="overview-panel">
                <div class="overview-panel-title">{{ $t('breeding.detail.pedigreeSuggestion') }}</div>
                <div class="overview-list">
                  <div class="overview-list-item">
                    <div class="overview-list-main">
                      <div class="overview-list-title">{{ $t('breeding.detail.suggestionTitle1') }}</div>
                      <div class="overview-list-subtitle">{{ $t('breeding.detail.suggestionDesc1') }}</div>
                    </div>
                  </div>
                  <div class="overview-list-item">
                    <div class="overview-list-main">
                      <div class="overview-list-title">{{ $t('breeding.detail.suggestionTitle2') }}</div>
                      <div class="overview-list-subtitle">{{ $t('breeding.detail.suggestionDesc2') }}</div>
                    </div>
                  </div>
                  <div class="overview-list-item">
                    <div class="overview-list-main">
                      <div class="overview-list-title">{{ $t('breeding.detail.suggestionTitle3') }}</div>
                      <div class="overview-list-subtitle">{{ $t('breeding.detail.suggestionDesc3') }}</div>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </TabPane>

          <TabPane key="materials" :tab="$t('breeding.detail.materials')">
            <Table
              :columns="materialColumns"
              :data-source="materialRows"
              :loading="materialsLoading"
              :pagination="false"
              :scroll="{ x: 1000 }"
              row-key="id"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'is_check'">
                  {{ record.is_check ? $t('breeding.detail.yes') : $t('breeding.detail.no') }}
                </template>
                <template v-else-if="column.key === 'action'">
                  <div class="cell-actions">
                    <Button size="small" type="link" @click="setMaterialFocus(record.id)">
                      {{ activeMaterialId === record.id ? $t('breeding.detail.focused') : $t('breeding.detail.focus') }}
                    </Button>
                    <Button size="small" type="link" @click="openMaterialFlow(record.id, 'observations')">
                      {{ $t('breeding.detail.observation') }}
                    </Button>
                    <Button size="small" type="link" @click="openMaterialFlow(record.id, 'omics')">
                      {{ $t('breeding.detail.omicsShort') }}
                    </Button>
                  </div>
                </template>
                <template v-else-if="column.key === 'status'">
                  <Tag :color="statusColor(record.status)">{{ record.status || $t('breeding.detail.unknown') }}</Tag>
                </template>
              </template>
            </Table>

            <Card v-if="selectedMaterial" :bordered="false" class="material-detail-card">
              <div class="material-detail-header">
                <div>
                  <div class="material-detail-eyebrow">{{ $t('breeding.detail.materialDetailEyebrow') }}</div>
                  <div class="material-detail-title">
                    {{ selectedMaterial.material_code }} / {{ selectedMaterial.material_name }}
                  </div>
                  <div class="material-detail-tags">
                    <Tag color="blue">{{ selectedMaterial.material_type }}</Tag>
                    <Tag v-if="selectedMaterial.germplasm_accession">
                      {{ selectedMaterial.germplasm_accession }}
                    </Tag>
                    <Tag v-if="selectedMaterial.is_check" color="gold">{{ $t('breeding.detail.checkMaterial') }}</Tag>
                  </div>
                </div>
                <div class="material-detail-actions">
                  <Button size="small" type="primary" @click="openMaterialFlow(selectedMaterial.id, 'observations')">
                    {{ $t('breeding.detail.viewObservation') }}
                  </Button>
                  <Button size="small" @click="openMaterialFlow(selectedMaterial.id, 'biosamples')">
                    {{ $t('breeding.detail.viewSample') }}
                  </Button>
                  <Button size="small" @click="openMaterialFlow(selectedMaterial.id, 'omics')">
                    {{ $t('breeding.detail.viewOmics') }}
                  </Button>
                  <Button
                    v-if="selectedMaterial.germplasm_accession"
                    size="small"
                    @click="openGermplasmInfo(selectedMaterial)"
                  >
                    {{ $t('breeding.detail.openGermplasmDetail') }}
                  </Button>
                </div>
              </div>

              <div class="material-detail-grid">
                <div class="material-detail-panel">
                  <div class="material-detail-panel-title">{{ $t('breeding.detail.germplasmAndSource') }}</div>
                  <div class="material-kv-list">
                    <div class="material-kv-item">
                      <span class="material-kv-label">{{ $t('breeding.detail.englishName') }}</span>
                      <span class="material-kv-value">{{ selectedMaterialMeta?.english_name || '-' }}</span>
                    </div>
                    <div class="material-kv-item">
                      <span class="material-kv-label">{{ $t('breeding.detail.origin') }}</span>
                      <span class="material-kv-value">{{ selectedMaterial.origin || '-' }}</span>
                    </div>
                    <div class="material-kv-item">
                      <span class="material-kv-label">{{ $t('breeding.detail.generation') }}</span>
                      <span class="material-kv-value">{{ selectedMaterial.generation_code || '-' }}</span>
                    </div>
                    <div class="material-kv-item">
                      <span class="material-kv-label">{{ $t('breeding.detail.germplasmName') }}</span>
                      <span class="material-kv-value">{{ selectedMaterial.germplasm_name || '-' }}</span>
                    </div>
                    <div class="material-kv-item">
                      <span class="material-kv-label">{{ $t('breeding.detail.sourceFile') }}</span>
                      <span class="material-kv-value">{{ selectedMaterial.germplasm_source_file || '-' }}</span>
                    </div>
                  </div>
                </div>

                <div class="material-detail-panel">
                  <div class="material-detail-panel-title">{{ $t('breeding.detail.pedigree') }}</div>
                  <div class="pedigree-list">
                    <div
                      v-for="item in selectedMaterialParents"
                      :key="item.role"
                      class="pedigree-item"
                    >
                      <div class="pedigree-role">{{ item.role }}</div>
                      <div class="pedigree-main">
                        <div class="pedigree-name">{{ item.name || item.accession || '-' }}</div>
                        <div class="pedigree-accession">{{ item.accession || '-' }}</div>
                      </div>
                      <Button
                        v-if="item.material"
                        size="small"
                        type="link"
                        @click="focusMaterialByReference(item.accession)"
                      >
                        {{ $t('breeding.detail.jumpToMaterial') }}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>

              <div class="material-detail-grid">
                <div class="material-detail-panel">
                  <div class="material-detail-panel-title">{{ $t('breeding.detail.varietyDescription') }}</div>
                  <div class="material-kv-list">
                    <div class="material-kv-item">
                      <span class="material-kv-label">{{ $t('breeding.detail.breedingHistory') }}</span>
                      <span class="material-kv-value">{{ selectedMaterialMeta?.history || '-' }}</span>
                    </div>
                    <div class="material-kv-item">
                      <span class="material-kv-label">{{ $t('breeding.detail.flowerTraits') }}</span>
                      <span class="material-kv-value">{{ selectedMaterialMeta?.flower_traits || '-' }}</span>
                    </div>
                    <div class="material-kv-item">
                      <span class="material-kv-label">{{ $t('breeding.detail.plantFeatures') }}</span>
                      <span class="material-kv-value">{{ selectedMaterialMeta?.plant_traits || '-' }}</span>
                    </div>
                    <div class="material-kv-item">
                      <span class="material-kv-label">{{ $t('breeding.detail.usage') }}</span>
                      <span class="material-kv-value">{{ selectedMaterialMeta?.usage || '-' }}</span>
                    </div>
                  </div>
                </div>

                <div class="material-detail-panel">
                  <div class="material-detail-panel-title">{{ $t('breeding.detail.keyTraitSummary') }}</div>
                  <div v-if="activeMaterialTraitSummaryRows.length" class="material-summary-list">
                    <div
                      v-for="item in activeMaterialTraitSummaryRows"
                      :key="item.key"
                      class="material-summary-item"
                    >
                      <div class="material-summary-main">
                        <div class="material-summary-title">{{ item.traitName }}</div>
                        <div class="material-summary-subtitle">{{ item.traitCode }}</div>
                      </div>
                      <div class="material-summary-stats">
                        <span>{{ item.count }} {{ $t('breeding.detail.entries') }}</span>
                        <span>{{ $t('breeding.detail.mean') }} {{ item.meanValue }}</span>
                      </div>
                    </div>
                  </div>
                  <div v-else class="material-empty-hint">
                    {{ $t('breeding.detail.noObservationSummary') }}
                  </div>
                </div>
              </div>

              <div class="material-detail-grid">
                <div class="material-detail-panel">
                  <div class="material-detail-panel-title">{{ $t('breeding.detail.relatedBiosamples') }}</div>
                  <div v-if="activeMaterialBioSamplePreviewRows.length" class="material-chip-list">
                    <div
                      v-for="item in activeMaterialBioSamplePreviewRows"
                      :key="item.id"
                      class="material-sample-chip"
                    >
                      <div class="material-sample-code">{{ item.sampleCode }}</div>
                      <div class="material-sample-meta">
                        {{ item.sampleType }} / {{ item.tissueType }} / {{ item.timepoint }}
                      </div>
                    </div>
                  </div>
                  <div v-else class="material-empty-hint">
                    {{ $t('breeding.detail.noBiosamples') }}
                  </div>
                </div>

                <div class="material-detail-panel">
                  <div class="material-detail-panel-title">{{ $t('breeding.detail.omicsOverview') }}</div>
                  <div class="material-omics-summary">
                    <div class="material-omics-group">
                      <div class="material-omics-label">{{ $t('breeding.detail.assayTypeSummary') }}</div>
                      <div class="overview-tag-list">
                        <Tag
                          v-for="item in activeMaterialAssayTypeRows"
                          :key="item.label"
                          color="cyan"
                        >
                          {{ item.label }} · {{ item.count }}
                        </Tag>
                        <span v-if="!activeMaterialAssayTypeRows.length" class="material-empty-inline">{{ $t('breeding.detail.empty') }}</span>
                      </div>
                    </div>
                    <div class="material-omics-group">
                      <div class="material-omics-label">{{ $t('breeding.detail.fileRoleSummary') }}</div>
                      <div class="overview-tag-list">
                        <Tag
                          v-for="item in activeMaterialFileRoleRows"
                          :key="item.label"
                          color="geekblue"
                        >
                          {{ item.label }} · {{ item.count }}
                        </Tag>
                        <span v-if="!activeMaterialFileRoleRows.length" class="material-empty-inline">{{ $t('breeding.detail.empty') }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </TabPane>

          <TabPane key="trials" :tab="$t('breeding.detail.trials')">
            <Table
              :columns="trialColumns"
              :data-source="filteredTrialRows"
              :loading="trialsLoading"
              :pagination="false"
              :scroll="{ x: 1100 }"
              row-key="id"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'trial_id'">
                  {{ resolveTrialLabel(record.trial_id) }}
                </template>
                <template v-else-if="column.key === 'material_id'">
                  {{ resolveMaterialLabel(record.material_id) }}
                </template>
                <template v-else-if="column.key === 'status'">
                  <Tag :color="statusColor(record.status)">{{ record.status || $t('breeding.detail.unknown') }}</Tag>
                </template>
              </template>
            </Table>
          </TabPane>

          <TabPane key="plots" :tab="$t('breeding.detail.plots')">
            <Table
              :columns="plotColumns"
              :data-source="filteredPlotRows"
              :loading="plotsLoading"
              :pagination="false"
              :scroll="{ x: 1100 }"
              row-key="id"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'">
                  <Tag :color="statusColor(record.status)">{{ record.status || $t('breeding.detail.unknown') }}</Tag>
                </template>
              </template>
            </Table>
          </TabPane>

          <TabPane key="observations" :tab="$t('breeding.detail.observations')">
            <Table
              :columns="observationColumns"
              :data-source="filteredObservationRows"
              :loading="observationsLoading"
              :pagination="false"
              :scroll="{ x: 1500, y: 560 }"
              row-key="id"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'material_id'">
                  {{ resolveMaterialLabel(record.material_id) }}
                </template>
                <template v-else-if="column.key === 'plot_id'">
                  {{ resolvePlotLabel(record.plot_id) }}
                </template>
                <template v-else-if="column.key === 'qc_status'">
                  <Tag :color="statusColor(record.qc_status)">{{ record.qc_status || $t('breeding.detail.unknown') }}</Tag>
                </template>
              </template>
            </Table>
          </TabPane>

          <TabPane key="biosamples" :tab="$t('breeding.detail.biosamples')">
            <Table
              :columns="biosampleColumns"
              :data-source="filteredBioSampleRows"
              :loading="biosamplesLoading"
              :pagination="false"
              :scroll="{ x: 1100 }"
              row-key="id"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'material_id'">
                  {{ resolveMaterialLabel(record.material_id) }}
                </template>
                <template v-else-if="column.key === 'plot_id'">
                  {{ resolvePlotLabel(record.plot_id) }}
                </template>
                <template v-else-if="column.key === 'sample_type'">
                  <Tag color="purple">{{ record.sample_type || '-' }}</Tag>
                </template>
                <template v-else-if="column.key === 'action'">
                  <Button size="small" type="link" @click="openBioSampleFlow(record)">
                    {{ $t('breeding.detail.viewExperiment') }}
                  </Button>
                </template>
                <template v-else-if="column.key === 'status'">
                  <Tag :color="statusColor(record.status)">{{ record.status || $t('breeding.detail.unknown') }}</Tag>
                </template>
              </template>
            </Table>
          </TabPane>

          <TabPane key="omics" :tab="$t('breeding.detail.omics')">
            <div class="omics-section">
              <div class="section-title">{{ $t('breeding.detail.omicsExperiments') }}</div>
              <Table
                :columns="assayColumns"
                :data-source="filteredAssayRows"
                :loading="assaysLoading"
                :pagination="false"
                :scroll="{ x: 1000 }"
                row-key="id"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'biosample_id'">
                    {{ resolveBioSampleLabel(record.biosample_id) }}
                  </template>
                  <template v-else-if="column.key === 'assay_type'">
                    <Tag color="cyan">{{ record.assay_type }}</Tag>
                  </template>
                  <template v-else-if="column.key === 'action'">
                    <Button size="small" type="link" @click="openAssayFlow(record)">
                      {{ $t('breeding.detail.viewFile') }}
                    </Button>
                  </template>
                  <template v-else-if="column.key === 'status'">
                    <Tag :color="statusColor(record.status)">{{ record.status || $t('breeding.detail.unknown') }}</Tag>
                  </template>
                </template>
              </Table>
            </div>

            <div class="omics-section">
              <div class="section-title">{{ $t('breeding.detail.dataFiles') }}</div>
              <Table
                :columns="dataFileColumns"
                :data-source="filteredDataFileRows"
                :loading="dataFilesLoading"
                :pagination="false"
                :scroll="{ x: 1200 }"
                row-key="id"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'assay_id'">
                    {{ resolveAssayLabel(record.assay_id) }}
                  </template>
                  <template v-else-if="column.key === 'file_role'">
                    <Tag color="geekblue">{{ record.file_role }}</Tag>
                  </template>
                  <template v-else-if="column.key === 'dataset_ref'">
                    {{ formatDatasetRef(record) }}
                  </template>
                  <template v-else-if="column.key === 'action'">
                    <Button size="small" type="link" @click="openDataFileFlow(record)">
                      {{ $t('breeding.detail.locateChain') }}
                    </Button>
                  </template>
                  <template v-else-if="column.key === 'status'">
                    <Tag :color="statusColor(record.status)">{{ record.status || $t('breeding.detail.unknown') }}</Tag>
                  </template>
                </template>
              </Table>
            </div>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  </Page>
</template>

<style scoped lang="less">
.program-detail-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero-card {
  background:
    radial-gradient(circle at top right, rgba(22, 119, 255, 0.12), transparent 36%),
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

.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.hero-description {
  max-width: 880px;
  margin: 0;
  color: #516074;
  line-height: 1.7;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.focus-toolbar {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
  padding: 16px;
  border-radius: 12px;
  background:
    radial-gradient(circle at left top, rgba(22, 119, 255, 0.08), transparent 42%),
    linear-gradient(135deg, #f9fbff 0%, #f5f7fb 100%);
}

.focus-heading {
  max-width: 480px;
}

.focus-title {
  color: #13213a;
  font-size: 16px;
  font-weight: 700;
}

.focus-description {
  margin-top: 4px;
  color: #6a778b;
  line-height: 1.7;
}

.focus-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.focus-summary-grid {
  display: grid;
  grid-template-columns: 2fr repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.focus-summary-card {
  background:
    linear-gradient(135deg, #13213a 0%, #1e3252 100%);
}

.focus-summary-eyebrow {
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.focus-summary-title {
  margin-top: 10px;
  color: #fff;
  font-size: 20px;
  font-weight: 700;
}

.focus-summary-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.stat-label {
  color: #6a778b;
  font-size: 13px;
}

.stat-value {
  margin-top: 8px;
  color: #13213a;
  font-size: 28px;
  font-weight: 700;
}

.stat-value-sm {
  font-size: 22px;
}

.meta-json {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.material-detail-card {
  margin-top: 16px;
  background:
    radial-gradient(circle at top right, rgba(22, 119, 255, 0.08), transparent 38%),
    linear-gradient(135deg, #fbfdff 0%, #f7f9fc 100%);
}

.material-detail-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.material-detail-eyebrow {
  color: #1677ff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.material-detail-title {
  margin-top: 8px;
  color: #13213a;
  font-size: 22px;
  font-weight: 700;
}

.material-detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.material-detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.material-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.material-detail-grid + .material-detail-grid {
  margin-top: 16px;
}

.material-detail-panel {
  padding: 16px;
  border-radius: 12px;
  background: #fff;
  box-shadow: inset 0 0 0 1px rgba(19, 33, 58, 0.06);
}

.material-detail-panel-title {
  margin-bottom: 12px;
  color: #13213a;
  font-size: 15px;
  font-weight: 700;
}

.pedigree-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pedigree-item {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-radius: 10px;
  background: #f8fbff;
}

.pedigree-role {
  flex: 0 0 auto;
  min-width: 36px;
  color: #1677ff;
  font-size: 12px;
  font-weight: 700;
}

.pedigree-main {
  flex: 1 1 auto;
  min-width: 0;
}

.pedigree-name {
  color: #13213a;
  font-weight: 600;
}

.pedigree-accession {
  color: #6a778b;
  font-size: 12px;
}

.material-kv-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.material-kv-item {
  display: flex;
  gap: 12px;
}

.material-kv-label {
  flex: 0 0 auto;
  min-width: 72px;
  color: #6a778b;
  font-size: 13px;
}

.material-kv-value {
  color: #13213a;
  line-height: 1.7;
  word-break: break-word;
}

.material-summary-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.material-summary-item {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-radius: 10px;
  background: #f8fbff;
}

.material-summary-main {
  min-width: 0;
}

.material-summary-title {
  color: #13213a;
  font-weight: 600;
}

.material-summary-subtitle {
  color: #6a778b;
  font-size: 12px;
}

.material-summary-stats {
  display: flex;
  gap: 12px;
  color: #516074;
  font-size: 13px;
  white-space: nowrap;
}

.material-chip-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.material-sample-chip {
  padding: 12px 14px;
  border-radius: 10px;
  background: #f8fbff;
}

.material-sample-code {
  color: #13213a;
  font-weight: 700;
}

.material-sample-meta {
  margin-top: 6px;
  color: #6a778b;
  font-size: 13px;
}

.material-omics-summary {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.material-omics-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.material-omics-label {
  color: #516074;
  font-size: 13px;
  font-weight: 600;
}

.material-empty-hint,
.material-empty-inline {
  color: #6a778b;
  line-height: 1.7;
}

.overview-section-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.overview-panel {
  min-height: 100%;
}

.overview-panel-title {
  margin-bottom: 12px;
  color: #13213a;
  font-size: 16px;
  font-weight: 700;
}

.overview-focus-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.overview-focus-name {
  color: #13213a;
  font-size: 20px;
  font-weight: 700;
}

.overview-focus-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.overview-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.overview-empty-hint {
  color: #6a778b;
  line-height: 1.8;
}

.overview-chip-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.overview-chip {
  padding: 14px;
  border: 1px solid #d8e2f0;
  border-radius: 12px;
  background: #fbfdff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.overview-chip:hover {
  border-color: #8bb9ff;
  box-shadow: 0 10px 24px rgba(19, 33, 58, 0.08);
  transform: translateY(-1px);
}

.overview-chip-code {
  display: block;
  color: #1677ff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.overview-chip-name {
  display: block;
  margin-top: 6px;
  color: #13213a;
  font-size: 16px;
  font-weight: 700;
}

.overview-chip-meta {
  display: block;
  margin-top: 8px;
  color: #6a778b;
  font-size: 13px;
}

.overview-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.overview-list-item {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-radius: 10px;
  background: #f8fbff;
}

.overview-list-main {
  min-width: 0;
}

.overview-list-title {
  color: #13213a;
  font-weight: 600;
}

.overview-list-subtitle {
  color: #6a778b;
  font-size: 12px;
}

.overview-list-stats {
  display: flex;
  gap: 12px;
  color: #516074;
  font-size: 13px;
  white-space: nowrap;
}

.overview-summary-block {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.overview-summary-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.overview-summary-title {
  color: #516074;
  font-size: 13px;
  font-weight: 600;
}

.overview-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pedigree-overview-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.pedigree-overview-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pedigree-overview-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 32px minmax(0, 1.5fr);
  gap: 12px;
  align-items: center;
  padding: 14px;
  border-radius: 12px;
  background: #f8fbff;
}

.pedigree-overview-child {
  min-width: 0;
}

.pedigree-overview-code {
  color: #1677ff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.pedigree-overview-name {
  margin-top: 6px;
  color: #13213a;
  font-weight: 700;
}

.pedigree-overview-arrow {
  color: #9aa7b8;
  font-size: 18px;
  text-align: center;
}

.pedigree-overview-parents {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.pedigree-parent-chip {
  padding: 10px 12px;
  border: 1px solid #d8e2f0;
  border-radius: 10px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.pedigree-parent-chip:hover {
  border-color: #8bb9ff;
  box-shadow: 0 8px 20px rgba(19, 33, 58, 0.08);
}

.pedigree-parent-role {
  display: block;
  color: #6a778b;
  font-size: 12px;
}

.pedigree-parent-name {
  display: block;
  margin-top: 4px;
  color: #13213a;
  font-weight: 600;
}

.pedigree-parent-ref {
  display: block;
  margin-top: 4px;
  color: #6a778b;
  font-size: 12px;
}

.source-file-list,
.assumption-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-file-item,
.assumption-item {
  line-height: 1.7;
}

.source-file-key {
  display: inline-block;
  min-width: 120px;
  color: #6a778b;
  font-weight: 600;
  text-transform: uppercase;
}

.source-file-value {
  color: #13213a;
  word-break: break-word;
}

.cell-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.omics-section + .omics-section {
  margin-top: 24px;
}

.section-title {
  margin-bottom: 12px;
  color: #13213a;
  font-size: 16px;
  font-weight: 600;
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .focus-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .overview-section-grid {
    grid-template-columns: 1fr;
  }

  .material-detail-grid {
    grid-template-columns: 1fr;
  }

  .pedigree-overview-item {
    grid-template-columns: 1fr;
  }

  .pedigree-overview-parents {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .focus-toolbar {
    flex-direction: column;
  }

  .focus-actions {
    justify-content: flex-start;
  }

  .focus-summary-grid {
    grid-template-columns: 1fr;
  }

  .overview-chip-grid {
    grid-template-columns: 1fr;
  }

  .overview-list-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .material-detail-header,
  .material-summary-item,
  .material-kv-item,
  .pedigree-item {
    flex-direction: column;
  }

  .material-detail-actions {
    justify-content: flex-start;
  }
}
</style>
