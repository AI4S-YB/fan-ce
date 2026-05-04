<script setup lang="ts">
import { ref } from 'vue';
import { useDatasetList, useDatasetQuery } from '@/composables/useDatasets';
import DataVisualization from '@/components/DataVisualization/index.vue';

const { items: datasets, load: loadDatasets } = useDatasetList();
const { queryLoading, queryResult, execute } = useDatasetQuery();

const selectedId = ref<number | null>(null);
const chrom = ref('chr1');
const start = ref('1');
const end = ref('100000');

loadDatasets({ dataset_type: 'variome' });

async function runQuery() {
  if (!selectedId.value) return;
  await execute(selectedId.value, 'variant_query', {
    chrom: chrom.value,
    start: Number(start.value),
    end: Number(end.value),
  });
}

function fillExample() {
  chrom.value = 'chr1';
  start.value = '1';
  end.value = '100000';
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
        placeholder="Chromosome"
        style="width: 140px"
      />
      <el-input
        v-model="start"
        placeholder="Start"
        style="width: 120px"
        type="number"
      />
      <el-input
        v-model="end"
        placeholder="End"
        style="width: 120px"
        type="number"
      />
      <el-button text size="small" @click="fillExample"> Example </el-button>
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
