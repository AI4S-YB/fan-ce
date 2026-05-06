<script setup lang="ts">
import { ref } from 'vue';
import { useDatasetList, useDatasetDetail, useDatasetQuery } from '@/composables/useDatasets';
import { useRequest } from '@/composables/useRequest';
import SmartSearchBar from '@/components/SmartSearchBar.vue';
import VariantTable from '@/components/VariantTable.vue';
import VariantDensityPlot from '@/components/VariantDensityPlot.vue';
import SampleFilter from '@/components/SampleFilter.vue';

const { items: datasets, load: loadDatasets } = useDatasetList();
const { detail, lineage, load: loadDetail } = useDatasetDetail();
const { queryLoading, queryResult, execute } = useDatasetQuery();

const selectedId = ref<number | null>(null);
const isDraft = ref(false);
const sampleOptions = ref<string[]>([]);
const selectedSamples = ref<string[]>([]);
const searchInfo = ref('');

// Linked genome dataset (via lineage) for gene→region lookup
const linkedGenome = ref<{ id: number; code: string; annoAssetCode: string | null } | null>(null);
const searchBarRef = ref<InstanceType<typeof SmartSearchBar> | null>(null);

// Example chips populated from backend (region + 3 gene IDs)
const exampleRegion = ref<string>('');
const exampleGenes = ref<string[]>([]);

loadDatasets({ dataset_type: 'variome' });

function getAssetCode(): string | undefined {
  return detail.value?.query_entry_asset?.asset_code;
}

async function resolveLinkedGenome() {
  linkedGenome.value = null;
  try {
    const edges = lineage.value || [];
    const genomeEdge = edges.find((e: any) =>
      e.relation_type === 'references' && e.dst_dataset_id && e.dst_dataset_code
    );
    if (!genomeEdge) return;

    const { post } = useRequest();
    const PRE = '/public/dataset';
    const genomeInfo: any = await post(`${PRE}/info`, { id: genomeEdge.dst_dataset_id });
    const annoAsset = (genomeInfo?.assets || []).find(
      (a: any) => a.asset_type === 'functional_annotation' && a.is_query_entry
    );
    linkedGenome.value = {
      id: genomeEdge.dst_dataset_id!,
      code: genomeEdge.dst_dataset_code || genomeInfo?.dataset_code || '',
      annoAssetCode: annoAsset?.asset_code || null,
    };
  } catch (e) {
    console.warn('Failed to resolve linked genome:', e);
  }
}

async function onDatasetSelect(datasetId: number) {
  searchInfo.value = '';
  sampleOptions.value = [];
  selectedSamples.value = [];
  queryResult.value = null;
  linkedGenome.value = null;
  exampleRegion.value = '';
  exampleGenes.value = [];

  await loadDetail(datasetId);
  isDraft.value = detail.value?.lifecycle_state === 'draft';
  const assetCode = getAssetCode();

  await resolveLinkedGenome();

  try {
    const data = await execute(datasetId, 'samples_list', {}, assetCode);
    sampleOptions.value = data?.data?.samples || data?.samples || [];
  } catch (e) {
    console.error('Failed to load samples:', e);
  }

  await loadExamples(datasetId, assetCode);
}

async function loadExamples(datasetId: number, assetCode?: string) {
  try {
    const data = await execute(datasetId, 'region_example', {}, assetCode);
    const inner = data?.data || data;
    const refId = inner?.ref_id || inner?.chrom;
    const pos = inner?.variant_position || inner?.pos;
    if (refId && pos != null) {
      exampleRegion.value = `${refId}:${Math.max(1, pos - 5000)}-${pos + 5000}`;
    }
  } catch (e) {
    console.warn('Failed to load region example:', e);
  }

  if (linkedGenome.value?.annoAssetCode) {
    try {
      const data: any = await execute(
        linkedGenome.value.id,
        'list_genes',
        { page: 1, size: 3 },
        linkedGenome.value.annoAssetCode,
      );
      const genes = data?.data?.items || data?.items || [];
      exampleGenes.value = genes.slice(0, 3).map((g: any) => g.gene_id).filter(Boolean);
    } catch (e) {
      console.warn('Failed to load gene examples:', e);
    }
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

async function resolveGeneToRegion(geneId: string): Promise<string | null> {
  if (!linkedGenome.value?.annoAssetCode) {
    searchInfo.value = `No annotation dataset linked — cannot resolve gene "${geneId}"`;
    return null;
  }
  const data: any = await execute(
    linkedGenome.value.id,
    'search_genes',
    { keyword: geneId, size: 1 },
    linkedGenome.value.annoAssetCode,
  );
  const genes = data?.data?.items || data?.items || [];
  if (genes.length === 0) {
    searchInfo.value = `Gene "${geneId}" not found`;
    return null;
  }
  const gene = genes[0];
  const pad = 5000;
  return `${gene.chrom}:${Math.max(1, gene.start - pad)}-${gene.stop + pad}`;
}

async function handleSearch({ type, value }: { type: string; value: string }) {
  if (!selectedId.value) return;
  const assetCode = getAssetCode();

  if (type === 'gene') {
    searchInfo.value = `Looking up gene: ${value}`;
    const region = await resolveGeneToRegion(value);
    if (!region) return;
    searchInfo.value = `Gene ${value} → ${region}`;
    await execute(selectedId.value, 'query', {
      regions: [region],
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

// Fill the search box when user clicks an example chip
function fillSearch(value: string) {
  searchBarRef.value?.setInput(value);
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
      <SmartSearchBar ref="searchBarRef" placeholder="Search genes, regions, or variant IDs..." @search="handleSearch" />

      <div v-if="searchInfo" style="margin:8px 0;font-size:12px;color:#409eff;">
        {{ searchInfo }}
      </div>

      <!-- Examples row: chips fill the search box -->
      <div v-if="exampleRegion || exampleGenes.length > 0"
        style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0;">
        <span style="font-size:12px;color:#909399;">Examples:</span>
        <el-tag v-if="exampleRegion" size="small" type="info" effect="plain"
          style="cursor:pointer;" @click="fillSearch(exampleRegion)">
          Region: {{ exampleRegion }}
        </el-tag>
        <el-tag v-for="g in exampleGenes" :key="g" size="small" type="success" effect="plain"
          style="cursor:pointer;" @click="fillSearch(g)">
          Gene: {{ g }}
        </el-tag>
      </div>

      <div style="display:flex;gap:8px;align-items:center;margin:12px 0;">
        <SampleFilter v-if="sampleOptions.length > 0" :samples="sampleOptions"
          @update="(v: string[]) => selectedSamples = v" />
      </div>

      <div v-if="linkedGenome" style="font-size:12px;color:#67c23a;margin-top:4px;">
        Gene lookup enabled via {{ linkedGenome.code }}
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
        description="Enter a search query or click an example chip above to get started." />
    </div>
  </div>
</template>
