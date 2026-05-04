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
</script>

<template>
  <div v-loading="queryLoading" class="gene-info">
    <div class="gene-nav">
      <el-button text @click="backToSearch">← Back to Search</el-button>
    </div>
    <div v-if="errorMsg" class="gene-error">{{ errorMsg }}</div>

    <template v-if="gene">
      <!-- Header -->
      <div class="gene-header">
        <h2 class="gene-title">{{ gene.gene_id }}</h2>
        <div class="gene-subtitle">
          <span class="gene-locus">{{ gene.chrom }}:{{ (gene.start as number)?.toLocaleString() }}-{{ (gene.stop as number)?.toLocaleString() }}</span>
          <span class="gene-strand">{{ gene.strand === '+' ? '(+) Forward' : '(-) Reverse' }}</span>
          <span v-if="canonicalTranscript" class="gene-transcript">Canonical: <code>{{ canonicalTranscript }}</code></span>
        </div>
        <p class="gene-desc">{{ gene.description || 'No description available' }}</p>
        <div v-if="gene.family" class="gene-family">
          <el-tag type="success" size="small">{{ gene.family }}</el-tag>
        </div>
      </div>

      <!-- Quick stats -->
      <div class="gene-stats">
        <div class="stat-item"><span class="stat-val">{{ transcriptCount }}</span><span class="stat-label">Transcripts</span></div>
        <div class="stat-item"><span class="stat-val">{{ annotationCounts.go || 0 }}</span><span class="stat-label">GO</span></div>
        <div class="stat-item"><span class="stat-val">{{ annotationCounts.kegg || 0 }}</span><span class="stat-label">KEGG</span></div>
        <div class="stat-item"><span class="stat-val">{{ annotationCounts.interpro || 0 }}</span><span class="stat-label">InterPro</span></div>
        <div class="stat-item"><span class="stat-val">{{ blastHits.length }}</span><span class="stat-label">BLAST</span></div>
      </div>

      <!-- Location -->
      <div class="gene-section">
        <h3>Genomic Location</h3>
        <table class="gene-table">
          <tr><th>Chromosome</th><td>{{ gene.chrom }}</td><th>Start</th><td>{{ (gene.start as number)?.toLocaleString() }}</td></tr>
          <tr><th>End</th><td>{{ (gene.stop as number)?.toLocaleString() }}</td><th>Strand</th><td>{{ gene.strand }}</td></tr>
          <tr><th>Transcripts</th><td>{{ transcriptCount }}</td><th>Canonical</th><td><code v-if="canonicalTranscript">{{ canonicalTranscript }}</code><span v-else>-</span></td></tr>
        </table>
      </div>

      <!-- BLAST -->
      <div v-if="blastHits.length > 0" class="gene-section">
        <h3>BLAST Homology ({{ blastHits.length }} hits)</h3>
        <el-table :data="blastHits" size="small" border stripe max-height="500">
          <el-table-column prop="_db" label="DB" width="70" />
          <el-table-column prop="Hit_id" label="Subject ID" width="180" show-overflow-tooltip />
          <el-table-column prop="Hit_def" label="Description" min-width="280" show-overflow-tooltip />
          <el-table-column label="E-value" width="100" sortable sort-by="Hit_hsps.Hsp.Hsp_evalue">
            <template #default="{ row }">{{ row.Hit_hsps?.Hsp?.Hsp_evalue || '-' }}</template>
          </el-table-column>
          <el-table-column label="Identity" width="70">
            <template #default="{ row }">{{ row.Hit_hsps?.Hsp?.Hsp_identity || '-' }}</template>
          </el-table-column>
          <el-table-column label="Score" width="70">
            <template #default="{ row }">{{ row.Hit_hsps?.Hsp?.Hsp_bit_score || '-' }}</template>
          </el-table-column>
        </el-table>
      </div>

      <!-- GO -->
      <div v-if="annotations.go?.length" class="gene-section">
        <h3>GO Terms ({{ annotations.go.length }})</h3>
        <el-table :data="annotations.go" size="small" border stripe>
          <el-table-column prop="term_id" label="Accession" width="140">
            <template #default="{ row }">
              <a :href="'https://amigo.geneontology.org/amigo/term/' + row.term_id" target="_blank" style="color:#409eff;">{{ row.term_id }}</a>
            </template>
          </el-table-column>
          <el-table-column prop="term_name" label="Term" min-width="300" />
          <el-table-column prop="term_type" label="Type" width="100" />
        </el-table>
      </div>

      <!-- KEGG -->
      <div v-if="annotations.kegg?.length" class="gene-section">
        <h3>KEGG Pathways ({{ annotations.kegg.length }})</h3>
        <el-table :data="annotations.kegg" size="small" border stripe>
          <el-table-column prop="term_id" label="Pathway ID" width="140" />
          <el-table-column prop="term_name" label="Pathway" min-width="300" />
        </el-table>
      </div>
    </template>

    <el-empty v-else-if="!queryLoading && !errorMsg" description="Gene not found" />
  </div>
</template>

<style scoped>
.gene-info { font-size: 14px; }
.gene-nav { margin-bottom: 12px; }
.gene-error { color: #f56c6c; margin: 8px 0; padding: 8px 12px; background: #fef0f0; border-radius: 4px; }
.gene-header { margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #e5e5e5; }
.gene-title { margin: 0 0 6px; font-size: 20px; font-weight: 700; color: #303133; }
.gene-subtitle { font-size: 13px; color: #888; margin-bottom: 8px; display: flex; gap: 16px; }
.gene-locus { font-family: monospace; }
.gene-strand { color: #409eff; }
.gene-transcript code { background: #f0f0f0; padding: 1px 6px; border-radius: 3px; font-size: 12px; }
.gene-desc { margin: 8px 0 4px; color: #555; line-height: 1.6; }
.gene-family { margin-top: 4px; }
.gene-stats { display: flex; gap: 16px; margin-bottom: 20px; }
.stat-item { flex: 1; background: #f5f7fa; border-radius: 6px; padding: 12px; text-align: center; }
.stat-val { display: block; font-size: 22px; font-weight: 700; color: #409eff; }
.stat-label { display: block; font-size: 11px; color: #999; margin-top: 2px; }
.gene-section { margin-bottom: 24px; }
.gene-section h3 { font-size: 15px; margin: 0 0 8px; color: #303133; }
.gene-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.gene-table th { background: #f5f7fa; padding: 8px 12px; text-align: right; width: 100px; color: #888; font-weight: 500; border: 1px solid #e5e5e5; }
.gene-table td { padding: 8px 12px; border: 1px solid #e5e5e5; font-family: monospace; }
</style>
