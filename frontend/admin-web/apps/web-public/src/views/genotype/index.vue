<script setup lang="ts">
import { ref } from 'vue';
import { useDatasetList, useDatasetDetail, useDatasetQuery } from '@/composables/useDatasets';
import SmartSearchBar from '@/components/SmartSearchBar.vue';
import VariantTable from '@/components/VariantTable.vue';
import VariantDensityPlot from '@/components/VariantDensityPlot.vue';
import SampleFilter from '@/components/SampleFilter.vue';

const { items: datasets, load: loadDatasets } = useDatasetList();
const { detail, load: loadDetail } = useDatasetDetail();
const { queryLoading, queryResult, execute } = useDatasetQuery();

const selectedId = ref<number | null>(null);
const isDraft = ref(false);
const sampleOptions = ref<string[]>([]);
const selectedSamples = ref<string[]>([]);
const searchInfo = ref('');

loadDatasets({ dataset_type: 'variome' });

function getAssetCode(): string | undefined {
  return detail.value?.query_entry_asset?.asset_code;
}

async function onDatasetSelect(datasetId: number) {
  searchInfo.value = '';
  sampleOptions.value = [];
  selectedSamples.value = [];
  queryResult.value = null;

  await loadDetail(datasetId);
  isDraft.value = detail.value?.lifecycle_state === 'draft';
  const assetCode = getAssetCode();

  try {
    const data = await execute(datasetId, 'samples_list', {}, assetCode);
    sampleOptions.value = data?.data?.samples || data?.samples || [];
  } catch (e) {
    console.error('Failed to load samples:', e);
  }
}

function getVariantList(): { chrom: string; pos: number }[] {
  const preview = queryResult.value?.data?.preview || queryResult.value?.preview || '';
  if (!preview) return [];
  return preview.split('\n')
    .filter((l: string) => l && !l.startsWith('#'))
    .map((line: string) => {
      const fields = line.split('\t');
      return { chrom: fields[0], pos: Number(fields[1]) };
    })
    .filter((v: { chrom: string; pos: number }) => v.chrom && !isNaN(v.pos));
}

async function handleSearch({ type, value }: { type: string; value: string }) {
  if (!selectedId.value) return;
  const assetCode = getAssetCode();

  if (type === 'gene') {
    searchInfo.value = `Looking up gene: ${value}`;
    // Gene→region via annotation adapter — see Task 7
    // For now, query the genome's annotation linked to this variome
    await execute(selectedId.value, 'query', {
      regions: [value],
      include_samples: selectedSamples.value.length > 0 ? selectedSamples.value : undefined,
    }, assetCode);
  } else if (type === 'region') {
    searchInfo.value = `Region: ${value}`;
    await execute(selectedId.value, 'query', {
      regions: [value],
      include_samples: selectedSamples.value.length > 0 ? selectedSamples.value : undefined,
    }, assetCode);
  } else if (type === 'variant_id') {
    searchInfo.value = `Variant ID: ${value}`;
    await execute(selectedId.value, 'query_by_id', {
      variant_ids: [value],
    }, assetCode);
  }
}

async function tryExample() {
  if (!selectedId.value) return;
  const assetCode = getAssetCode();
  try {
    const data = await execute(selectedId.value, 'region_example', {}, assetCode);
    const inner = data?.data || data;
    const refId = inner?.ref_id || inner?.chrom;
    const pos = inner?.variant_position || inner?.pos;
    if (refId && pos != null) {
      const region = `${refId}:${Math.max(1, pos - 5000)}-${pos + 5000}`;
      searchInfo.value = `Example region: ${region}`;
      await execute(selectedId.value, 'query', {
        regions: [region],
        include_samples: selectedSamples.value.length > 0 ? selectedSamples.value : undefined,
      }, assetCode);
    }
  } catch (e) {
    console.error('Failed to load example:', e);
  }
}

</script>

<template>
  <div>
    <h2>Genotype Query</h2>

    <div style="margin-bottom:16px;">
      <el-select v-model="selectedId" placeholder="Select variome dataset" style="width:360px;"
        @change="onDatasetSelect">
        <el-option v-for="ds in datasets" :key="ds.id" :label="ds.title || ds.dataset_code" :value="ds.id" />
      </el-select>
    </div>

    <el-alert v-if="isDraft" title="Dataset is in draft state" type="warning" :closable="false" show-icon
      style="margin-bottom:16px;">
      Query results may not be available until the dataset is fully registered.
    </el-alert>

    <div v-if="selectedId">
      <SmartSearchBar placeholder="Search genes, regions, or variant IDs..." @search="handleSearch" />

      <div v-if="searchInfo" style="margin:8px 0;font-size:12px;color:#409eff;">
        {{ searchInfo }}
      </div>

      <div style="display:flex;gap:8px;align-items:center;margin:12px 0;">
        <SampleFilter v-if="sampleOptions.length > 0" :samples="sampleOptions"
          @update="(v: string[]) => selectedSamples = v" />
        <el-button text size="small" @click="tryExample">Try Example</el-button>
      </div>

      <div v-if="queryResult" style="margin-top:16px;">
        <div style="color:#888;font-size:13px;margin-bottom:8px;">
          Found {{ queryResult?.data?.count || queryResult?.count || 0 }} variants
          <span v-if="queryResult?.data?.sample_count"> in {{ queryResult.data.sample_count }} samples</span>
        </div>

        <el-tabs type="border-card">
          <el-tab-pane label="Table">
            <VariantTable :result="queryResult" :loading="queryLoading" />
          </el-tab-pane>
          <el-tab-pane label="Density Plot">
            <VariantDensityPlot :variants="getVariantList()" :loading="queryLoading" />
          </el-tab-pane>
        </el-tabs>

        <div v-if="queryResult?.data?.download_url || queryResult?.download_url" style="margin-top:12px;">
          <el-button type="success">Download VCF</el-button>
        </div>
      </div>

      <el-empty v-if="!queryLoading && !queryResult"
        description="Enter a search query to find variants. Try clicking 'Try Example' for demo data." />
    </div>
  </div>
</template>
