<script setup lang="ts">
import { ref, watch } from 'vue';
import { useDatasetList, useDatasetDetail, useDatasetQuery } from '@/composables/useDatasets';
import MultiSelectDropdown from '@/components/MultiSelectDropdown.vue';
import DataVisualization from '@/components/DataVisualization/index.vue';
import type { QueryCapabilities } from '@/types/dataset';

const { items: datasets, load: loadDatasets } = useDatasetList();
const { detail, load: loadDetail } = useDatasetDetail();
const { queryLoading, queryResult, loadCapabilities, execute } = useDatasetQuery();

const selectedDatasetId = ref<number | null>(null);
const selectedVersionId = ref<number | undefined>();
const caps = ref<QueryCapabilities | null>(null);
const selectedGenesText = ref('');
const selectedSamples = ref<string[]>([]);
const selectedType = ref('count');
const exampleLoading = ref(false);
const sampleOptions = ref<{ label: string; value: string }[]>([]);

loadDatasets({ dataset_type: 'transcriptome' });

function getAssetCode(): string | undefined {
  return detail.value?.query_entry_asset?.asset_code;
}

async function runQuery() {
  if (!selectedDatasetId.value) return;
  const geneList = selectedGenesText.value.split(/[\n,;\s]+/).map(s => s.trim()).filter(Boolean);
  if (!geneList.length) return;
  const result: any = await execute(selectedDatasetId.value, 'matrix_slice', {
    genes: geneList,
    samples: selectedSamples.value,
    data_type: selectedType.value,
  }, getAssetCode(), selectedVersionId.value);

  const data = result?.data || result;
  const genes: string[] = data?.genes || [];
  const samples: string[] = data?.samples || [];
  const rawMatrix: number[][] = data?.matrix || [];
  if (genes.length && samples.length) {
    const rows = buildRows(rawMatrix, genes, samples, 'raw');
    (queryResult as any)._raw = { genes, samples, matrix: rawMatrix };
    queryResult.value = { rows, total: rows.length } as any;
  }
}

function buildRows(matrix: number[][], genes: string[], samples: string[], norm: string): Record<string, unknown>[] {
  let m = matrix.map(row => [...row]);
  if (norm === 'log2') {
    m = m.map(row => row.map(v => v > 0 ? Math.log2(v + 1) : 0));
  } else if (norm === 'zscore') {
    m = m.map(row => {
      const mean = row.reduce((a, b) => a + b, 0) / row.length;
      const std = Math.sqrt(row.reduce((a, b) => a + (b - mean) ** 2, 0) / row.length) || 1;
      return row.map(v => (v - mean) / std);
    });
  }
  return genes.map((gene, i) => {
    const row: Record<string, unknown> = { gene };
    samples.forEach((s, j) => { row[s] = m[i]?.[j] ?? null; });
    return row;
  });
}

function handleNormalize(method: string) {
  const raw = (queryResult as any)._raw;
  if (!raw) return;
  const rows = buildRows(raw.matrix, raw.genes, raw.samples, method);
  queryResult.value = { rows, total: rows.length } as any;
}

async function loadExampleData(datasetId: number) {
  const assetCode = getAssetCode();
  exampleLoading.value = true;
  try {
    const geneData: any = await execute(datasetId, 'genes_list', { max_records: 30 }, assetCode);
    const rawGenes = geneData?.data?.genes || geneData?.genes || geneData?.data?.items || geneData?.items || [];
    selectedGenesText.value = rawGenes.slice(0, 20).map((g: any) => String(g)).join('\n');

    const sampleData: any = await execute(datasetId, 'samples_list', { max_records: 50 }, assetCode);
    const rawSamples = sampleData?.data?.samples || sampleData?.samples || sampleData?.data?.items || sampleData?.items || [];
    sampleOptions.value = rawSamples.map((s: any) => ({ label: String(s), value: String(s) }));
    selectedSamples.value = sampleOptions.value.slice(0, 5).map(s => s.value);

    if (selectedGenesText.value.trim()) await runQuery();
  } finally {
    exampleLoading.value = false;
  }
}

async function tryExample() {
  if (!selectedDatasetId.value) return;
  await loadExampleData(selectedDatasetId.value);
}

watch(selectedDatasetId, async (id) => {
  if (!id) return;
  caps.value = await loadCapabilities(id, undefined, selectedVersionId.value);
  await loadDetail(id);
  selectedGenesText.value = '';
  selectedSamples.value = [];
  sampleOptions.value = [];
});
</script>

<template>
  <div>
    <h2>Expression Query</h2>

    <!-- Dataset selector -->
    <div style="margin-bottom:16px;">
      <el-select v-model="selectedDatasetId" placeholder="Select transcriptome dataset" style="width:360px;">
        <el-option v-for="ds in datasets" :key="ds.id" :label="ds.title || ds.dataset_code" :value="ds.id" />
      </el-select>
    </div>

    <!-- Query form -->
    <div v-if="selectedDatasetId" style="background:#fafafa;border:1px solid #e5e5e5;border-radius:6px;padding:20px;margin-bottom:16px;">
      <div style="display:flex;gap:24px;flex-wrap:wrap;">
        <!-- Left: Genes -->
        <div style="flex:1;min-width:280px;">
          <div style="font-size:13px;font-weight:500;color:#606266;margin-bottom:6px;">Genes</div>
          <el-input
            v-model="selectedGenesText"
            type="textarea"
            :rows="8"
            placeholder="Enter gene IDs, one per line..."
            style="font-family:monospace;font-size:12px;"
          />
          <div style="font-size:11px;color:#bbb;margin-top:4px;">One gene ID per line, supports comma/space separation</div>
        </div>

        <!-- Right: Samples + Data Type + Actions -->
        <div style="display:flex;flex-direction:column;gap:16px;min-width:260px;">
          <div>
            <div style="font-size:13px;font-weight:500;color:#606266;margin-bottom:6px;">Samples</div>
            <MultiSelectDropdown v-model="selectedSamples" :options="sampleOptions" placeholder="Select samples" />
          </div>
          <div>
            <div style="font-size:13px;font-weight:500;color:#606266;margin-bottom:6px;">Data Type</div>
            <el-select v-model="selectedType" style="width:100%;">
              <el-option label="Count" value="count" />
              <el-option label="FPKM" value="fpkm" />
              <el-option label="TPM" value="tpm" />
            </el-select>
          </div>
          <div style="display:flex;gap:8px;margin-top:auto;">
            <el-button type="primary" :loading="queryLoading" @click="runQuery">Query</el-button>
            <el-button :loading="exampleLoading" @click="tryExample">Try Example</el-button>
          </div>
        </div>
      </div>
    </div>

    <DataVisualization :result="queryResult" :loading="queryLoading" :precision="selectedType === 'fpkm' ? 2 : undefined" show-export @normalize="handleNormalize" />
  </div>
</template>
