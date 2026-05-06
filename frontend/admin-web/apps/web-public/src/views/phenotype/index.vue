<script setup lang="ts">
import { ref, watch } from 'vue';
import { useDatasetList, useDatasetDetail, useDatasetQuery } from '@/composables/useDatasets';
import DataVisualization from '@/components/DataVisualization/index.vue';
import type { QueryCapabilities } from '@/types/dataset';

const { items: datasets, load: loadDatasets } = useDatasetList();
const { detail, load: loadDetail } = useDatasetDetail();
const { queryLoading, queryResult, loadCapabilities, execute } = useDatasetQuery();

const selectedId = ref<number | null>(null);
const caps = ref<QueryCapabilities | null>(null);
const selectedTrait = ref('');
const selectedTimepoint = ref('');
const limit = ref(20);
const exampleLoading = ref(false);

const traitOptions = ref<{ label: string; value: string }[]>([]);
const timepointOptions = ref<{ label: string; value: string }[]>([]);

loadDatasets({ dataset_type: 'phenome' });

function getAssetCode(): string | undefined {
  return detail.value?.query_entry_asset?.asset_code;
}

async function runQuery() {
  if (!selectedId.value || !selectedTrait.value) return;
  const params: Record<string, unknown> = { trait: selectedTrait.value, limit: limit.value };
  if (selectedTimepoint.value) params.timepoint = selectedTimepoint.value;
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
    if (traitOptions.value.length > 0) {
      selectedTrait.value = traitOptions.value[0].value;
      await runQuery();
    }
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
  selectedTimepoint.value = '';
  traitOptions.value = [];
  timepointOptions.value = [];
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
        <el-select v-model="selectedTrait" placeholder="Select trait" style="width: 200px;" filterable>
          <el-option v-for="t in traitOptions" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
      </div>
      <div>
        <div style="font-size:12px;color:#888;margin-bottom:4px;">Timepoint</div>
        <el-input v-model="selectedTimepoint" placeholder="e.g. day7" style="width: 140px;" clearable />
      </div>
      <div>
        <div style="font-size:12px;color:#888;margin-bottom:4px;">Limit</div>
        <el-input-number v-model="limit" :min="1" :max="200" style="width: 120px;" />
      </div>
      <el-button type="primary" :loading="queryLoading" @click="runQuery">Query</el-button>
      <el-button :loading="exampleLoading" @click="tryExample">Try Example</el-button>
    </div>
    <DataVisualization :result="queryResult" :loading="queryLoading" />
  </div>
</template>
