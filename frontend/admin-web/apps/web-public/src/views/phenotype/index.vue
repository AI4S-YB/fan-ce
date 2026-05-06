<script setup lang="ts">
import { ref, watch } from 'vue';
import { useDatasetList, useDatasetDetail, useDatasetQuery } from '@/composables/useDatasets';
import MultiSelectDropdown from '@/components/MultiSelectDropdown.vue';
import DataVisualization from '@/components/DataVisualization/index.vue';
import type { QueryCapabilities } from '@/types/dataset';

const { items: datasets, load: loadDatasets } = useDatasetList();
const { detail, load: loadDetail } = useDatasetDetail();
const { queryLoading, queryResult, loadCapabilities, execute } = useDatasetQuery();

const selectedId = ref<number | null>(null);
const caps = ref<QueryCapabilities | null>(null);
const selectedTraits = ref<string[]>([]);
const selectedTrials = ref<string[]>([]);
const exampleLoading = ref(false);
const traitOptions = ref<{ label: string; value: string }[]>([]);
const trialOptions = ref<{ label: string; value: string }[]>([]);
const exampleHint = ref('');

loadDatasets({ dataset_type: 'phenome' });

function getAssetCode(): string | undefined {
  return detail.value?.query_entry_asset?.asset_code;
}

async function runQuery() {
  if (!selectedId.value || !selectedTraits.value.length) return;
  const params: Record<string, unknown> = {};
  if (selectedTraits.value.length) params.traits = selectedTraits.value;
  if (selectedTrials.value.length) params.trial_ids = selectedTrials.value;
  await execute(selectedId.value, 'multi_trait_query', params, getAssetCode());
}

async function loadExampleData(datasetId: number) {
  const assetCode = getAssetCode();
  exampleLoading.value = true;
  exampleHint.value = '';
  try {
    // Load traits
    const traitData: any = await execute(datasetId, 'trait_list', { limit: 20 }, assetCode);
    const traits = (traitData?.data?.items || traitData?.items || []).map((t: any) => ({
      label: t.trait_name || t.name,
      value: String(t.trait_code || t.name),
    }));
    traitOptions.value = traits;
    const pickedTraits = traits.slice(0, 3);
    selectedTraits.value = pickedTraits.map((t: any) => t.value);

    // Load trials
    const trialData: any = await execute(datasetId, 'trial_list', {}, assetCode);
    const trials = (trialData?.data?.items || trialData?.items || []).map((t: any) => ({
      label: t.trial_name || String(t.id),
      value: String(t.id),
    }));
    trialOptions.value = trials;
    if (trials.length > 0) selectedTrials.value = [trials[0].value];

    // Show hint with what was selected
    const traitNames = pickedTraits.map((t: any) => t.label).join(', ');
    const trialName = trials[0]?.label || '';
    exampleHint.value = `Example: ${traitNames}${trialName ? ' · Trial: ' + trialName : ''}`;

    if (selectedTraits.value.length) await runQuery();
  } finally {
    exampleLoading.value = false;
  }
}

async function tryExample() {
  if (!selectedId.value) return;
  await loadExampleData(selectedId.value);
}

watch(selectedId, async (id) => {
  if (!id) return;
  caps.value = await loadCapabilities(id);
  await loadDetail(id);
  selectedTraits.value = [];
  selectedTrials.value = [];
  traitOptions.value = [];
  trialOptions.value = [];
  exampleHint.value = '';
});
</script>

<template>
  <div>
    <h2>Phenotype Query</h2>
    <div style="display: flex; gap: 12px; margin-bottom: 16px">
      <el-select v-model="selectedId" placeholder="Select phenome dataset" style="width: 360px">
        <el-option v-for="ds in datasets" :key="ds.id" :label="ds.title || ds.dataset_code" :value="ds.id" />
      </el-select>
    </div>
    <div v-if="selectedId" style="display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; margin-bottom: 16px">
      <MultiSelectDropdown v-model="selectedTraits" :options="traitOptions" placeholder="e.g. 花瓣长, 花瓣宽" />
      <MultiSelectDropdown v-model="selectedTrials" :options="trialOptions" placeholder="Select trial" />
      <el-button type="primary" :loading="queryLoading" @click="runQuery">Query</el-button>
      <el-button :loading="exampleLoading" @click="tryExample">Try Example</el-button>
    </div>
    <div v-if="exampleHint" style="font-size:12px;color:#67c23a;margin-bottom:12px;">{{ exampleHint }}</div>
    <DataVisualization :result="queryResult" :loading="queryLoading" />
  </div>
</template>
