<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useDatasetList, useDatasetDetail, useDatasetQuery } from '@/composables/useDatasets';
import MultiSelectDropdown from '@/components/MultiSelectDropdown.vue';
import DataVisualization from '@/components/DataVisualization/index.vue';
import type { QueryCapabilities } from '@/types/dataset';

const { items: datasets, load: loadDatasets } = useDatasetList();
const { detail, load: loadDetail } = useDatasetDetail();
const { queryLoading, queryResult, loadCapabilities, execute } = useDatasetQuery();

const selectedId = ref<number | null>(null);
const caps = ref<QueryCapabilities | null>(null);
const selectedTrait = ref('');
const selectedPlots = ref<string[]>([]);
const selectedBlock = ref<number | null>(null);
const exampleLoading = ref(false);

const traitOptions = ref<{ label: string; value: string }[]>([]);
const plotOptions = ref<{ label: string; value: string; _block: number }[]>([]);

loadDatasets({ dataset_type: 'phenome' });

function getAssetCode(): string | undefined {
  return detail.value?.query_entry_asset?.asset_code;
}

const filteredPlotOptions = computed(() => {
  if (!selectedBlock.value) return plotOptions.value;
  return plotOptions.value.filter(p => p._block === selectedBlock.value);
});

async function runQuery() {
  if (!selectedId.value || !selectedTrait.value) return;
  const params: Record<string, unknown> = { trait: selectedTrait.value, limit: 100 };
  if (selectedPlots.value.length) params.plot_ids = selectedPlots.value;
  await execute(selectedId.value, 'trait_values', params, getAssetCode());
}

async function loadExampleData(datasetId: number) {
  const assetCode = getAssetCode();
  exampleLoading.value = true;
  try {
    const traitData: any = await execute(datasetId, 'trait_list', { limit: 20 }, assetCode);
    traitOptions.value = (traitData?.data?.items || traitData?.items || []).map((t: any) => ({
      label: t.trait_name || t.name,
      value: String(t.trait_code || t.name),
    }));
    if (traitOptions.value.length > 0) selectedTrait.value = traitOptions.value[0].value;

    const plotData: any = await execute(datasetId, 'plot_list', { limit: 100 }, assetCode);
    const rawPlots = plotData?.data?.items || plotData?.items || [];
    plotOptions.value = rawPlots.map((p: any) => ({
      label: `${p.subject_name_cn || p.subject_name} (${p.plot_code})`,
      value: String(p.id),
      _block: p.block,
    }));
    selectedPlots.value = plotOptions.value.slice(0, 6).map(p => p.value);

    if (selectedTrait.value) await runQuery();
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
  selectedTrait.value = '';
  selectedPlots.value = [];
  traitOptions.value = [];
  plotOptions.value = [];
  selectedBlock.value = null;
});
</script>

<template>
  <div>
    <h2>Phenotype Query</h2>

    <div style="margin-bottom:16px;">
      <el-select v-model="selectedId" placeholder="Select phenome dataset" style="width:360px;">
        <el-option v-for="ds in datasets" :key="ds.id" :label="ds.title || ds.dataset_code" :value="ds.id" />
      </el-select>
    </div>

    <div v-if="selectedId" style="background:#fafafa;border:1px solid #e5e5e5;border-radius:6px;padding:20px;margin-bottom:16px;">
      <div style="display:flex;gap:24px;flex-wrap:wrap;">
        <div style="display:flex;flex-direction:column;gap:16px;min-width:220px;">
          <div>
            <div style="font-size:13px;font-weight:500;color:#606266;margin-bottom:6px;">Trait</div>
            <el-select v-model="selectedTrait" placeholder="Select trait" style="width:100%;" filterable @change="runQuery">
              <el-option v-for="t in traitOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
          </div>
          <div>
            <div style="font-size:13px;font-weight:500;color:#606266;margin-bottom:6px;">Block</div>
            <el-select v-model="selectedBlock" placeholder="All blocks" clearable style="width:100%;">
              <el-option label="Block 1" :value="1" />
              <el-option label="Block 2" :value="2" />
            </el-select>
          </div>
        </div>

        <div style="flex:1;min-width:300px;">
          <div style="font-size:13px;font-weight:500;color:#606266;margin-bottom:6px;">Cultivars ({{ filteredPlotOptions.length }})</div>
          <MultiSelectDropdown v-model="selectedPlots" :options="filteredPlotOptions" placeholder="Select cultivars" />
          <div style="display:flex;gap:8px;margin-top:12px;">
            <el-button type="primary" :loading="queryLoading" @click="runQuery">Query</el-button>
            <el-button :loading="exampleLoading" @click="tryExample">Try Example</el-button>
          </div>
        </div>
      </div>
    </div>

    <DataVisualization :result="queryResult" :loading="queryLoading" show-export />
  </div>
</template>
