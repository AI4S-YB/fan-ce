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
const selectedPlots = ref<string[]>([]);
const exampleLoading = ref(false);

const traitOptions = ref<{ label: string; value: string }[]>([]);
const trialOptions = ref<{ label: string; value: string }[]>([]);
const plotOptions = ref<{ label: string; value: string }[]>([]);

loadDatasets({ dataset_type: 'phenome' });

function getAssetCode(): string | undefined {
  return detail.value?.query_entry_asset?.asset_code;
}

async function runQuery() {
  if (!selectedId.value) return;
  const params: Record<string, unknown> = {};
  if (selectedTraits.value.length) params.traits = selectedTraits.value;
  if (selectedTrials.value.length) params.trial_ids = selectedTrials.value;
  if (selectedPlots.value.length) params.plot_ids = selectedPlots.value;
  await execute(selectedId.value, 'multi_trait_query', params, getAssetCode());
}

async function loadExampleData(datasetId: number) {
  const assetCode = getAssetCode();
  exampleLoading.value = true;
  try {
    // Load traits
    const traitData: any = await execute(datasetId, 'trait_list', { limit: 20 }, assetCode);
    traitOptions.value = (traitData?.data?.items || traitData?.items || []).map((t: any) => ({
      label: t.trait_name || t.name,
      value: String(t.trait_code || t.name),
    }));
    selectedTraits.value = traitOptions.value.slice(0, 3).map(t => t.value);

    // Load trials
    const trialData: any = await execute(datasetId, 'trial_list', {}, assetCode);
    trialOptions.value = (trialData?.data?.items || trialData?.items || []).map((t: any) => ({
      label: t.trial_name || String(t.id),
      value: String(t.id),
    }));
    if (trialOptions.value.length > 0) selectedTrials.value = [trialOptions.value[0].value];

    // Load plots
    const plotData: any = await execute(datasetId, 'plot_list', {}, assetCode);
    plotOptions.value = (plotData?.data?.items || plotData?.items || []).map((p: any) => ({
      label: p.plot_code || p.plot_name || String(p.id),
      value: String(p.id),
    }));

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
  selectedPlots.value = [];
  traitOptions.value = [];
  trialOptions.value = [];
  plotOptions.value = [];
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
    <div v-if="selectedId" style="display: flex; gap: 16px; align-items: flex-end; flex-wrap: wrap; margin-bottom: 16px">
      <div>
        <div style="font-size:12px;color:#888;margin-bottom:4px;">Trait</div>
        <MultiSelectDropdown v-model="selectedTraits" :options="traitOptions" placeholder="Select traits" />
      </div>
      <div>
        <div style="font-size:12px;color:#888;margin-bottom:4px;">Trial</div>
        <MultiSelectDropdown v-model="selectedTrials" :options="trialOptions" placeholder="Select trial" />
      </div>
      <div>
        <div style="font-size:12px;color:#888;margin-bottom:4px;">Plot</div>
        <MultiSelectDropdown v-model="selectedPlots" :options="plotOptions" placeholder="Select plots" />
      </div>
      <el-button type="primary" :loading="queryLoading" @click="runQuery">Query</el-button>
      <el-button :loading="exampleLoading" @click="tryExample">Try Example</el-button>
    </div>
    <DataVisualization :result="queryResult" :loading="queryLoading" />
  </div>
</template>
