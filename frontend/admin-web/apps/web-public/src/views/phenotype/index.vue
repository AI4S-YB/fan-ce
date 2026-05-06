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
const selectedSamples = ref<string[]>([]);
const exampleLoading = ref(false);

loadDatasets({ dataset_type: 'phenome' });

function getAssetCode(): string | undefined {
  return detail.value?.query_entry_asset?.asset_code;
}

/** Extract string names from a query result row set. */
function extractNames(result: any): string[] {
  const rows = result?.rows || result?.items || [];
  if (!rows.length) return [];
  const first = rows[0];
  if (typeof first === 'string') return rows;
  const key =
    Object.keys(first).find((k) =>
      ['trait', 'name', 'subject', 'sample', 'id', 'value', 'label'].includes(
        k.toLowerCase(),
      ),
    ) || Object.keys(first)[0];
  return rows.map((r: any) => (typeof r === 'string' ? r : String(r[key] ?? ''))).filter(Boolean);
}

async function runQuery() {
  if (!selectedId.value) return;
  await execute(
    selectedId.value,
    'phenotype_query',
    {
      traits: selectedTraits.value,
      samples: selectedSamples.value,
    },
    getAssetCode(),
  );
}

async function autoLoadExample(datasetId: number) {
  const ops = caps.value?.operations ?? [];
  if (!ops.includes('trait_list') && !ops.includes('subject_list')) return;

  const assetCode = getAssetCode();
  exampleLoading.value = true;
  try {
    if (ops.includes('trait_list')) {
      await execute(datasetId, 'trait_list', { limit: 5 }, assetCode);
      const traits = extractNames(queryResult.value);
      selectedTraits.value = traits.slice(0, 3);
    }

    if (ops.includes('subject_list')) {
      await execute(datasetId, 'subject_list', { limit: 5 }, assetCode);
      const subjects = extractNames(queryResult.value);
      selectedSamples.value = subjects.slice(0, 3);
    }

    // Run the actual phenotype query with the auto-selected values
    if (selectedTraits.value.length || selectedSamples.value.length) {
      await runQuery();
    }
  } finally {
    exampleLoading.value = false;
  }
}

async function tryExample() {
  if (!selectedId.value) return;
  await autoLoadExample(selectedId.value);
}

watch(selectedId, async (id) => {
  if (!id) return;
  caps.value = await loadCapabilities(id);
  await loadDetail(id);
  selectedTraits.value = [];
  selectedSamples.value = [];

  // Auto-load example traits + subjects and show results immediately
  await autoLoadExample(id);
});
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
        placeholder="e.g. flower diameter, petal number"
      />
      <MultiSelectDropdown
        v-model="selectedSamples"
        :options="
          (caps?.filter_options?.samples || []).map((s: string) => ({
            label: s,
            value: s,
          }))
        "
        placeholder="e.g. select 1-5 samples"
      />
      <el-button type="primary" :loading="queryLoading" @click="runQuery">
        Query
      </el-button>
      <el-button :loading="exampleLoading" @click="tryExample">
        Try Example
      </el-button>
    </div>
    <DataVisualization :result="queryResult" :loading="queryLoading" />
  </div>
</template>
