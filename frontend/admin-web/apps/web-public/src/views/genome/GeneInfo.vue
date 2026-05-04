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
const annotationCounts = ref<Record<string, number>>({});
const annotations = ref<Record<string, any>>({});
const transcriptCount = ref(0);
const canonicalTranscript = ref('');
const blastHits = ref<any[]>([]);
const errorMsg = ref('');

watch(() => route.query.gene_id, (id) => {
  if (id) { geneId.value = String(id); loadGeneDetail(); }
}, { immediate: true });

function parseResult(result: any) {
  if (!result) return;
  const inner = result?.data || result;
  const g = inner?.gene;
  if (!g) return;
  gene.value = g;
  annotationCounts.value = inner?.annotation_counts || {};
  annotations.value = inner?.annotations || {};
  transcriptCount.value = inner?.transcript_count || 0;
  canonicalTranscript.value = inner?.canonical_transcript_id || '';
  const blastData = inner?.annotations?.blast || {};
  const hits: any[] = [];
  Object.entries(blastData).forEach(([db, hitList]: [string, any]) => {
    (Array.isArray(hitList) ? hitList : []).forEach((h: any) => hits.push({ ...h, _db: db }));
  });
  blastHits.value = hits;
}

watch(queryResult, (result) => parseResult(result));

async function loadGeneDetail() {
  const d = detail?.value;
  if (!d?.id || !geneId.value) return;
  const assetCode = d.query_entry_asset?.asset_code;
  errorMsg.value = '';
  try {
    await execute(d.id, 'gene_function_summary', { gene_id: geneId.value }, assetCode);
    parseResult(queryResult.value);
  } catch (e: any) {
    errorMsg.value = 'Failed: ' + (e?.message || String(e));
  }
}

function backToSearch() {
  const path = router.currentRoute.value.path.replace('/geneinfo', '/search');
  router.push({ path, query: {} });
}

function fmtEvalue(v: any): string {
  if (v === undefined || v === null) return '-';
  return String(v);
}
</script>

<template>
  <div v-loading="queryLoading">
    <el-button text @click="backToSearch">← Back to Search</el-button>
    <div v-if="errorMsg" style="color:#f56c6c;margin:8px 0;">{{ errorMsg }}</div>

    <template v-if="gene">
      <h3 style="margin-bottom:4px;">{{ gene.gene_id }}</h3>
      <div style="color:#888;font-size:13px;margin-bottom:16px;">
        <el-tag size="small">{{ gene.chrom }}</el-tag>
        <span style="margin-left:8px;">{{ gene.strand === '+' ? 'Forward' : 'Reverse' }} strand</span>
        <span style="margin-left:8px;" v-if="canonicalTranscript">Canonical: {{ canonicalTranscript }}</span>
      </div>

      <el-descriptions border :column="2" size="small" style="margin-bottom:16px;">
        <el-descriptions-item label="Gene ID">{{ gene.gene_id }}</el-descriptions-item>
        <el-descriptions-item label="Chromosome">{{ gene.chrom }}</el-descriptions-item>
        <el-descriptions-item label="Start">{{ (gene.start as number)?.toLocaleString() }}</el-descriptions-item>
        <el-descriptions-item label="End">{{ (gene.stop as number)?.toLocaleString() }}</el-descriptions-item>
        <el-descriptions-item label="Strand">{{ gene.strand }}</el-descriptions-item>
        <el-descriptions-item label="Transcripts">{{ transcriptCount }}</el-descriptions-item>
        <el-descriptions-item label="Description" :span="2">{{ gene.description || '-' }}</el-descriptions-item>
        <el-descriptions-item v-if="gene.family" label="Family" :span="2">{{ gene.family }}</el-descriptions-item>
      </el-descriptions>

      <h4 v-if="Object.keys(annotationCounts).length">Annotation Summary</h4>
      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px;">
        <el-tag v-for="(count, db) in annotationCounts" :key="db" type="info">{{ db }}: {{ count }}</el-tag>
      </div>

      <div v-if="blastHits.length > 0" style="margin-bottom:20px;">
        <h4>BLAST Hits ({{ blastHits.length }})</h4>
        <el-table :data="blastHits" size="small" border stripe max-height="400">
          <el-table-column prop="_db" label="DB" width="80" />
          <el-table-column prop="Hit_id" label="Hit ID" width="180" show-overflow-tooltip />
          <el-table-column prop="Hit_def" label="Definition" min-width="250" show-overflow-tooltip />
          <el-table-column label="E-value" width="100">
            <template #default="{ row }">{{ fmtEvalue(row.Hit_hsps?.Hsp?.Hsp_evalue) }}</template>
          </el-table-column>
          <el-table-column label="Identity" width="80">
            <template #default="{ row }">{{ row.Hit_hsps?.Hsp?.Hsp_identity || '-' }}</template>
          </el-table-column>
          <el-table-column label="Align Len" width="80">
            <template #default="{ row }">{{ row.Hit_hsps?.Hsp?.['Hsp_align-len'] || '-' }}</template>
          </el-table-column>
        </el-table>
      </div>

      <div v-if="annotations.go?.length" style="margin-bottom:16px;">
        <h4>GO Terms</h4>
        <el-table :data="annotations.go" size="small" border stripe>
          <el-table-column prop="term_id" label="GO ID" width="140" />
          <el-table-column prop="term_name" label="Term" />
          <el-table-column prop="term_type" label="Type" width="120" />
        </el-table>
      </div>

      <div v-if="annotations.kegg?.length" style="margin-bottom:16px;">
        <h4>KEGG Pathways</h4>
        <el-table :data="annotations.kegg" size="small" border stripe>
          <el-table-column prop="term_id" label="KEGG ID" width="140" />
          <el-table-column prop="term_name" label="Pathway" />
        </el-table>
      </div>
    </template>

    <el-empty v-else-if="!queryLoading && !errorMsg" description="Gene not found" />
  </div>
</template>
