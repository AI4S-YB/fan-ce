<script setup lang="ts">
import { computed, inject, ref, watch, type Ref } from 'vue';
import { useDatasetQuery } from '@/composables/useDatasets';
import type { PublicDatasetDetail } from '@/types/dataset';

const detail = inject<Ref<PublicDatasetDetail | null>>('genomeDetail');
const { queryLoading, queryResult, execute } = useDatasetQuery();

const errorMsg = ref('');
const debugInfo = ref('');

// Search filters
const searchMode = ref('keyword');
const keyword = ref('');
const geneId = ref('');
const chrom = ref('');
const start = ref('');
const end = ref('');
const page = ref(1);
const pageSize = ref(20);

const rows = computed(() => {
  const result = queryResult.value;
  if (!result) return [];
  const inner = (result as any).data;
  return (inner?.items || inner?.rows || result.rows || result.items || []) as Record<string, unknown>[];
});

const total = computed(() => {
  const r = queryResult.value as any;
  return r?.data?.total ?? r?.total ?? 0;
});

// Auto-load gene list when genome detail is ready
watch(() => detail?.value?.id, (id) => {
  debugInfo.value = 'detail.id = ' + String(id) + ', detail = ' + (detail ? 'present' : 'undefined');
  console.log('GeneSearch watcher: id=', id, 'detail=', detail);
  if (id) {
    page.value = 1;
    doQuery();
  }
}, { immediate: true });

async function doQuery() {
  const d = detail?.value;
  if (!d?.id) return;
  const assetCode = d.query_entry_asset?.asset_code;
  debugInfo.value = 'querying dataset=' + d.id + ' asset=' + assetCode;

  const params: Record<string, unknown> = { page: page.value, size: pageSize.value };
  if (searchMode.value === 'keyword' && keyword.value) params.keyword = keyword.value;
  else if (searchMode.value === 'gene_id' && geneId.value) params.gene_id = geneId.value;
  else if (searchMode.value === 'range') {
    if (chrom.value) params.chrom = chrom.value;
    if (start.value) params.start = Number(start.value);
    if (end.value) params.end = Number(end.value);
  }

  errorMsg.value = '';
  try {
    await execute(d.id, 'search_genes', params as Record<string, unknown>, assetCode);
    debugInfo.value = 'query done, rows=' + rows.value.length + ' total=' + total.value;
  } catch (e: any) {
    errorMsg.value = 'Query failed: ' + (e?.message || String(e));
    console.error('doQuery error:', e);
  }
}
</script>

<template>
  <div>
    <!-- Debug info -->
    <div v-if="debugInfo" style="background:#f0f7ff;padding:4px 12px;border-radius:4px;font-size:11px;color:#888;margin-bottom:8px;">{{ debugInfo }}</div>
    <div v-if="errorMsg" style="background:#fef0f0;padding:8px 12px;border-radius:4px;font-size:12px;color:#f56c6c;margin-bottom:8px;">{{ errorMsg }}</div>
    <!-- Search Controls -->
    <div style="margin-bottom: 16px;">
      <el-radio-group v-model="searchMode" size="small" style="margin-bottom: 12px;">
        <el-radio-button value="keyword">Keyword</el-radio-button>
        <el-radio-button value="gene_id">Gene ID</el-radio-button>
        <el-radio-button value="range">Chromosome Range</el-radio-button>
      </el-radio-group>
    </div>

    <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px;">
      <template v-if="searchMode === 'keyword'">
        <el-input
          v-model="keyword"
          placeholder="Search by gene name or description..."
          clearable
          style="width: 320px;"
          @keyup.enter="onSearch"
        />
      </template>
      <template v-else-if="searchMode === 'gene_id'">
        <el-input
          v-model="geneId"
          placeholder="Enter gene ID..."
          clearable
          style="width: 240px;"
          @keyup.enter="onSearch"
        />
      </template>
      <template v-else>
        <el-input
          v-model="chrom"
          placeholder="Chromosome (e.g. Chr1)"
          style="width: 150px;"
        />
        <el-input
          v-model="start"
          placeholder="Start"
          type="number"
          style="width: 120px;"
        />
        <span style="line-height: 32px;">-</span>
        <el-input
          v-model="end"
          placeholder="End"
          type="number"
          style="width: 120px;"
        />
      </template>
      <el-button type="primary" :loading="queryLoading" @click="onSearch">
        Search
      </el-button>
    </div>

    <!-- Results Table -->
    <div v-loading="queryLoading">
      <el-empty v-if="!queryLoading && rows.length === 0" description="No results found" />

      <template v-if="rows.length > 0">
        <el-table :data="rows" size="small" border stripe>
          <el-table-column prop="gene_id" label="Gene ID" width="160" />
          <el-table-column prop="chrom" label="Chr" width="100" />
          <el-table-column prop="start" label="Start" width="100" />
          <el-table-column prop="stop" label="End" width="100" />
          <el-table-column prop="strand" label="Strand" width="80" />
          <el-table-column prop="description" label="Description" min-width="200">
            <template #default="{ row }">
              <span>{{ row.description || row.gene_name || '-' }}</span>
            </template>
          </el-table-column>
        </el-table>

        <div style="margin-top: 12px; text-align: right;">
          <el-pagination
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            small
            @current-change="onPageChange"
            @size-change="(s: number) => { pageSize = s; onSearch(); }"
          />
        </div>
      </template>
    </div>
  </div>
</template>
