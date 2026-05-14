<script setup lang="ts">
import { computed, inject, ref, watch, type Ref } from 'vue';
import { useRouter } from 'vue-router';
import { useDatasetQuery } from '@/composables/useDatasets';
import type { PublicDatasetDetail } from '@/types/dataset';
import { ElMessage } from 'element-plus';

const detail = inject<Ref<PublicDatasetDetail | null>>('genomeDetail');
const router = useRouter();
const { queryLoading, queryResult, execute } = useDatasetQuery();

const errorMsg = ref('');

// Search filters
const keyword = ref('');
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
  if (id) {
    page.value = 1;
  }
}, { immediate: true });

async function doQuery() {
  const d = detail?.value;
  if (!d?.id) return;
  const assetCode = d.query_entry_asset?.asset_code;

  const params: Record<string, unknown> = { page: page.value, size: pageSize.value };
  if (keyword.value) params.keyword = keyword.value;

  errorMsg.value = '';
  try {
    await execute(d.id, 'search_genes', params as Record<string, unknown>, assetCode);
  } catch (e: any) {
    errorMsg.value = 'Query failed: ' + (e?.message || String(e));
  }
}

async function onSearch() {
  page.value = 1;
  await doQuery();
}

async function onPageChange(p: number) {
  page.value = p;
  await doQuery();
}

function goToGene(geneId: string) {
  router.push({ path: router.currentRoute.value.path.replace(/\/search$/, '/geneinfo'), query: { gene_id: geneId } });
}

const selectedGenes = ref<any[]>([]);
const showGeneSetDialog = ref(false);
const geneSetName = ref('');

function handleSelectionChange(rows: any[]) {
  selectedGenes.value = rows;
}

function openGeneSetDialog() {
  geneSetName.value = '';
  showGeneSetDialog.value = true;
}

function saveGeneSet() {
  if (!geneSetName.value.trim() || selectedGenes.value.length === 0) return;
  try {
    const sets = JSON.parse(localStorage.getItem('fan_gene_sets') || '[]');
    const genes = selectedGenes.value.map((r: any) => r.gene_id || '');
    const detailData = detail?.value;
    sets.unshift({
      id: crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2),
      name: geneSetName.value.trim(),
      genes,
      genomeId: detailData?.id || 0,
      genomeTitle: detailData?.title || detailData?.dataset_code || '',
      createdAt: Math.floor(Date.now() / 1000),
    });
    if (sets.length > 20) sets.length = 20;
    localStorage.setItem('fan_gene_sets', JSON.stringify(sets));
    showGeneSetDialog.value = false;
    ElMessage.success(`Gene set "${geneSetName.value}" saved (${genes.length} genes)`);
  } catch { /* ignore */ }
}
</script>

<template>
  <div>
    <div v-if="errorMsg" style="background:#fef0f0;padding:8px 12px;border-radius:4px;font-size:12px;color:#f56c6c;margin-bottom:8px;">{{ errorMsg }}</div>
    <!-- Search Controls -->
    <div style="display: flex; gap: 8px; margin-bottom: 16px;">
      <el-input
        v-model="keyword"
        placeholder="Search by gene ID, name, or description..."
        clearable
        style="width: 400px;"
        @keyup.enter="onSearch"
      />
      <el-button type="primary" :loading="queryLoading" @click="onSearch">Search</el-button>
    </div>

    <div v-if="selectedGenes.length > 0" style="margin-bottom:8px;">
      <el-button type="success" size="small" @click="openGeneSetDialog">
        Save as Gene Set ({{ selectedGenes.length }} genes)
      </el-button>
    </div>

    <!-- Results Table -->
    <div v-loading="queryLoading">
      <el-empty v-if="!queryLoading && rows.length === 0" description="No results found" />

      <template v-if="rows.length > 0">
        <el-table :data="rows" size="small" border stripe @selection-change="handleSelectionChange">
          <el-table-column type="selection" width="40" />
          <el-table-column prop="gene_id" label="Gene ID" width="160">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="goToGene(row.gene_id)">
                {{ row.gene_id }}
              </el-button>
            </template>
          </el-table-column>
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

    <el-dialog v-model="showGeneSetDialog" title="Save Gene Set" width="400px">
      <el-input v-model="geneSetName" placeholder="Gene set name..." maxlength="100" />
      <p style="color:#888;font-size:12px;margin-top:4px;">{{ selectedGenes.length }} genes will be saved</p>
      <template #footer>
        <el-button @click="showGeneSetDialog = false">Cancel</el-button>
        <el-button type="primary" @click="saveGeneSet" :disabled="!geneSetName.trim()">Save</el-button>
      </template>
    </el-dialog>
  </div>
</template>
