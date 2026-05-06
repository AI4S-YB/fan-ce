<script setup lang="ts">
import { ref } from 'vue';
import { useDatasetList, useDatasetDetail, useDatasetQuery } from '@/composables/useDatasets';
import DataVisualization from '@/components/DataVisualization/index.vue';

const { items: datasets, load: loadDatasets } = useDatasetList();
const { detail, load: loadDetail } = useDatasetDetail();
const { queryLoading, queryResult, capabilities, loadCapabilities, execute } = useDatasetQuery();

const selectedId = ref<number | null>(null);
const chrom = ref('');
const start = ref('');
const end = ref('');

// Real example region fetched from backend via region_example
const exampleRegion = ref<{ chrom: string; start: number; end: number } | null>(null);

loadDatasets({ dataset_type: 'variome' });

function getAssetCode(): string | undefined {
  return detail.value?.query_entry_asset?.asset_code;
}

async function onDatasetSelect(datasetId: number) {
  // Reset state
  exampleRegion.value = null;

  // Load detail to get asset_code
  await loadDetail(datasetId);
  const assetCode = getAssetCode();

  // Load query capabilities
  await loadCapabilities(datasetId, assetCode);

  // Fetch a real variant example region from the backend
  try {
    const data = await execute(datasetId, 'region_example', {}, assetCode);
    if (data?.chrom && data?.pos != null) {
      const pos = Number(data.pos);
      exampleRegion.value = {
        chrom: data.chrom,
        start: Math.max(1, pos - 5000),
        end: pos + 5000,
      };
      // Pre-fill form with real variant data
      chrom.value = exampleRegion.value.chrom;
      start.value = String(exampleRegion.value.start);
      end.value = String(exampleRegion.value.end);
      // Auto-execute query so results appear immediately
      await runQuery();
    }
  } catch (e) {
    console.error('Failed to load region example:', e);
  }
}

async function runQuery() {
  if (!selectedId.value) return;
  await execute(
    selectedId.value,
    'variant_query',
    {
      chrom: chrom.value,
      start: Number(start.value),
      end: Number(end.value),
    },
    getAssetCode(),
  );
}

async function tryExample() {
  if (exampleRegion.value) {
    chrom.value = exampleRegion.value.chrom;
    start.value = String(exampleRegion.value.start);
    end.value = String(exampleRegion.value.end);
    await runQuery();
  }
}
</script>

<template>
  <div>
    <h2>Genotype Query</h2>
    <div
      style="
        display: flex;
        gap: 12px;
        align-items: center;
        margin-bottom: 16px;
        flex-wrap: wrap;
      "
    >
      <el-select
        v-model="selectedId"
        placeholder="Select variome dataset"
        style="width: 360px"
        @change="onDatasetSelect"
      >
        <el-option
          v-for="ds in datasets"
          :key="ds.id"
          :label="ds.title || ds.dataset_code"
          :value="ds.id"
        />
      </el-select>
    </div>
    <div
      v-if="selectedId"
      style="
        display: flex;
        gap: 12px;
        align-items: center;
        margin-bottom: 16px;
        flex-wrap: wrap;
      "
    >
      <el-input
        v-model="chrom"
        placeholder="e.g. Chr1A"
        style="width: 140px"
      />
      <el-input
        v-model="start"
        placeholder="e.g. 100000"
        style="width: 120px"
        type="number"
      />
      <el-input
        v-model="end"
        placeholder="e.g. 200000"
        style="width: 120px"
        type="number"
      />
      <el-button text size="small" @click="tryExample"> Try Example </el-button>
      <el-button type="primary" :loading="queryLoading" @click="runQuery">
        Query
      </el-button>
    </div>
    <DataVisualization :result="queryResult" :loading="queryLoading" />
    <div v-if="queryResult?.download_url" style="margin-top: 12px">
      <el-button type="success">Download VCF</el-button>
    </div>
  </div>
</template>
