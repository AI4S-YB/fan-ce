<script setup lang="ts">
import { ref, watch } from 'vue';
import { useDatasetList, useDatasetQuery } from '@/composables/useDatasets';
import MultiSelectDropdown from '@/components/MultiSelectDropdown.vue';
import DataVisualization from '@/components/DataVisualization/index.vue';
import type { PublicDatasetItem, QueryCapabilities } from '@/types/dataset';

const { items: datasets, load: loadDatasets } = useDatasetList();
const { queryLoading, queryResult, loadCapabilities, execute } =
  useDatasetQuery();

const selectedDatasetId = ref<number | null>(null);
const selectedVersionId = ref<number | undefined>();
const caps = ref<QueryCapabilities | null>(null);
const selectedGenes = ref<string[]>([]);
const selectedSamples = ref<string[]>([]);
const selectedType = ref('count');

// Load transcriptome datasets on mount
loadDatasets({ dataset_type: 'transcriptome' });

// When dataset changes, load capabilities
watch(selectedDatasetId, async (id) => {
  if (!id) return;
  caps.value = await loadCapabilities(id, undefined, selectedVersionId.value);
  selectedGenes.value = [];
  selectedSamples.value = [];
});

async function runQuery() {
  if (!selectedDatasetId.value) return;
  await execute(
    selectedDatasetId.value,
    'expression_query',
    {
      genes: selectedGenes.value,
      samples: selectedSamples.value,
      type: selectedType.value,
    },
    undefined,
    selectedVersionId.value,
  );
}
</script>

<template>
  <div>
    <h2>Expression Query</h2>

    <!-- Dataset selector -->
    <div
      style="display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap;"
    >
      <el-select
        v-model="selectedDatasetId"
        placeholder="Select transcriptome dataset"
        style="width: 360px;"
      >
        <el-option
          v-for="ds in datasets"
          :key="ds.id"
          :label="ds.title || ds.dataset_code"
          :value="ds.id"
        />
      </el-select>
    </div>

    <!-- Filters -->
    <div
      v-if="selectedDatasetId"
      style="display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; margin-bottom: 16px;"
    >
      <MultiSelectDropdown
        v-model="selectedGenes"
        :options="
          (caps?.filter_options?.genes || []).map((g) => ({
            label: g,
            value: g,
          }))
        "
        placeholder="Select genes"
      />
      <MultiSelectDropdown
        v-model="selectedSamples"
        :options="
          (caps?.filter_options?.samples || []).map((s) => ({
            label: s,
            value: s,
          }))
        "
        placeholder="Select samples"
      />
      <el-select v-model="selectedType" style="width: 140px;">
        <el-option label="Count" value="count" />
        <el-option label="FPKM" value="fpkm" />
        <el-option label="TPM" value="tpm" />
      </el-select>
      <el-button
        type="primary"
        :loading="queryLoading"
        @click="runQuery"
      >
        Query
      </el-button>
    </div>

    <!-- Results -->
    <DataVisualization :result="queryResult" :loading="queryLoading" />
  </div>
</template>
