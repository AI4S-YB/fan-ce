<script setup lang="ts">
import { ref, watch } from 'vue';
import { useDatasetList, useDatasetQuery } from '@/composables/useDatasets';
import MultiSelectDropdown from '@/components/MultiSelectDropdown.vue';
import DataVisualization from '@/components/DataVisualization/index.vue';
import type { QueryCapabilities } from '@/types/dataset';

const { items: datasets, load: loadDatasets } = useDatasetList();
const { queryLoading, queryResult, loadCapabilities, execute } =
  useDatasetQuery();

const selectedId = ref<number | null>(null);
const caps = ref<QueryCapabilities | null>(null);
const selectedTraits = ref<string[]>([]);
const selectedSamples = ref<string[]>([]);

loadDatasets({ dataset_type: 'phenome' });

watch(selectedId, async (id) => {
  if (!id) return;
  caps.value = await loadCapabilities(id);
  selectedTraits.value = [];
  selectedSamples.value = [];
});

async function runQuery() {
  if (!selectedId.value) return;
  await execute(selectedId.value, 'phenotype_query', {
    traits: selectedTraits.value,
    samples: selectedSamples.value,
  });
}
</script>

<template>
  <div>
    <h2>Phenotype Query</h2>
    <div style="display: flex; gap: 12px; margin-bottom: 16px">
      <el-select
        v-model="selectedId"
        placeholder="Select phenome dataset"
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
        align-items: flex-end;
        flex-wrap: wrap;
        margin-bottom: 16px;
      "
    >
      <MultiSelectDropdown
        v-model="selectedTraits"
        :options="
          (caps?.filter_options?.traits || []).map((t: string) => ({
            label: t,
            value: t,
          }))
        "
        placeholder="Traits"
      />
      <MultiSelectDropdown
        v-model="selectedSamples"
        :options="
          (caps?.filter_options?.samples || []).map((s: string) => ({
            label: s,
            value: s,
          }))
        "
        placeholder="Samples"
      />
      <el-button type="primary" :loading="queryLoading" @click="runQuery">
        Query
      </el-button>
    </div>
    <DataVisualization :result="queryResult" :loading="queryLoading" />
  </div>
</template>
