<script setup lang="ts">
import { ref, inject, watch, type Ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDatasetQuery } from '@/composables/useDatasets';
import type { PublicDatasetDetail } from '@/types/dataset';

const route = useRoute();
const router = useRouter();
const detail = inject<Ref<PublicDatasetDetail | null>>('genomeDetail');
const { queryLoading, queryResult, execute } = useDatasetQuery();

const geneId = ref(route.query.gene_id as string || '');
const gene = ref<Record<string, unknown> | null>(null);
const transcripts = ref<Record<string, unknown>[]>([]);
const errorMsg = ref('');

watch(() => route.query.gene_id, (id) => {
  if (id) {
    geneId.value = String(id);
    loadGeneDetail();
  }
}, { immediate: true });

async function loadGeneDetail() {
  const d = detail?.value;
  if (!d?.id || !geneId.value) return;

  const assetCode = d.query_entry_asset?.asset_code;
  errorMsg.value = '';

  try {
    // Load gene detail
    await execute(d.id, 'gene_detail', { gene_id: geneId.value }, assetCode);
    const result = queryResult.value as any;
    const inner = result?.data || result;
    gene.value = inner?.items?.[0] || inner || null;

    // Load transcripts
    await execute(d.id, 'transcript_detail', { gene_id: geneId.value }, assetCode);
    const tResult = queryResult.value as any;
    const tInner = tResult?.data || tResult;
    transcripts.value = tInner?.items || [];
  } catch (e: any) {
    errorMsg.value = 'Failed to load gene: ' + (e?.message || String(e));
  }
}

function backToSearch() {
  router.push({ path: router.currentRoute.value.path.replace('/geneinfo', '/search'), query: {} });
}
</script>

<template>
  <div v-loading="queryLoading">
    <el-button text @click="backToSearch">← Back to Search</el-button>
    <div v-if="errorMsg" style="color:#f56c6c;margin:8px 0;">{{ errorMsg }}</div>

    <template v-if="gene">
      <h3>{{ gene.gene_id }} <el-tag size="small">{{ gene.chrom }}</el-tag></h3>
      <el-descriptions border :column="2" size="small" style="margin-bottom:20px;">
        <el-descriptions-item label="Gene ID">{{ gene.gene_id }}</el-descriptions-item>
        <el-descriptions-item label="Chromosome">{{ gene.chrom }}</el-descriptions-item>
        <el-descriptions-item label="Start">{{ gene.start }}</el-descriptions-item>
        <el-descriptions-item label="End">{{ gene.stop }}</el-descriptions-item>
        <el-descriptions-item label="Strand">{{ gene.strand }}</el-descriptions-item>
        <el-descriptions-item label="Canonical Transcript">{{ gene.canonical_transcript || '-' }}</el-descriptions-item>
        <el-descriptions-item label="Description" :span="2">{{ gene.description || '-' }}</el-descriptions-item>
        <el-descriptions-item v-if="gene.family" label="Family" :span="2">{{ gene.family }}</el-descriptions-item>
      </el-descriptions>

      <!-- Transcripts -->
      <div v-if="transcripts.length > 0">
        <h4>Transcripts ({{ transcripts.length }})</h4>
        <el-table :data="transcripts" size="small" border stripe>
          <el-table-column prop="transcript_id" label="Transcript ID" width="200" />
          <el-table-column prop="chrom" label="Chr" width="100" />
          <el-table-column prop="start" label="Start" width="100" />
          <el-table-column prop="stop" label="End" width="100" />
          <el-table-column prop="strand" label="Strand" width="80" />
          <el-table-column prop="cds_length" label="CDS Length" width="100" />
        </el-table>
      </div>
    </template>

    <el-empty v-else-if="!queryLoading && !errorMsg" description="Gene not found" />
  </div>
</template>
