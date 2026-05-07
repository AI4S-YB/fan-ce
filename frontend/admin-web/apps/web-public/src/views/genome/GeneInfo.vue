<script setup lang="ts">
import { ref, inject, watch, nextTick, type Ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDatasetQuery } from '@/composables/useDatasets';
import { useRequest } from '@/composables/useRequest';
import type { PublicDatasetDetail } from '@/types/dataset';

declare var FeatureViewer: any;

const route = useRoute();
const router = useRouter();
const detail = inject<Ref<PublicDatasetDetail | null>>('genomeDetail');
const { queryLoading, queryResult, execute } = useDatasetQuery();

const geneId = ref(route.query.gene_id as string || '');
const gene = ref<Record<string, any> | null>(null);
const exons = ref<any[]>([]);
const canonicalId = ref('');
const annotationCounts = ref<Record<string, number>>({});

const blastByDb = ref<Record<string, any[]>>({});
const interpro = ref<any[]>([]);
const goTerms = ref<any[]>([]);
const keggPathways = ref<any[]>([]);
const families = ref<any[]>([]);

const geneSeq = ref('');
const mrnaSeq = ref('');
const cdsSeq = ref('');
const proteinSeq = ref('');
const activeSeq = ref('');

const activeName = ref('1');
const dialogVisible = ref(false);
const dialogContent = ref<any>({});
const hit = ref<any>({});
const errorMsg = ref('');

watch(() => route.query.gene_id, (id) => {
  if (id) { geneId.value = String(id); loadGeneDetail(); }
}, { immediate: true });

function parseGeneData(result: any) {
  const inner = result?.data || result;
  const g = inner?.gene;
  if (!g) return;
  gene.value = g;
  canonicalId.value = inner?.canonical_transcript_id || '';
  annotationCounts.value = inner?.annotation_counts || {};
  exons.value = inner?.exons || [];

  const ann = inner?.annotations || {};
  const blastData = ann?.blast || {};
  const dbMap: Record<string, any[]> = {};
  for (const [db, hitList] of Object.entries(blastData)) {
    dbMap[db] = Array.isArray(hitList) ? hitList : [];
  }
  blastByDb.value = dbMap;

  const ipr = ann?.interpro;
  if (ipr && typeof ipr === 'object' && !Array.isArray(ipr) && ipr.matches_format) {
    interpro.value = ipr.matches_format;
  } else if (Array.isArray(ipr) && ipr.length > 0 && ipr[0]?.matches_format) {
    interpro.value = ipr[0].matches_format;
  } else if (Array.isArray(ipr)) {
    interpro.value = ipr;
  } else {
    interpro.value = [];
  }

  const goData = ann?.go;
  if (Array.isArray(goData) && goData.length > 0 && goData[0]?.terms) {
    goTerms.value = goData[0].terms;
  } else if (Array.isArray(goData)) {
    goTerms.value = goData;
  } else {
    goTerms.value = [];
  }

  const keggData = ann?.kegg;
  if (Array.isArray(keggData)) {
    keggPathways.value = keggData;
  } else {
    keggPathways.value = [];
  }

  const fam = ann?.family;
  if (fam && !Array.isArray(fam) && fam.family) {
    families.value = Array.isArray(fam.family) ? fam.family : [fam.family];
  } else if (Array.isArray(fam) && fam.length > 0 && fam[0]?.family) {
    families.value = fam[0].family;
  } else if (Array.isArray(fam)) {
    families.value = fam;
  } else {
    families.value = [];
  }
}

async function loadGeneDetail() {
  const d = detail?.value;
  if (!d?.id || !geneId.value) return;
  errorMsg.value = '';
  try {
    await execute(d.id, 'gene_function_summary', { gene_id: geneId.value }, d.query_entry_asset?.asset_code);
    parseGeneData(queryResult.value);
    await nextTick();
    if (exons.value.length > 0) tryRenderStructure();
  } catch (e: any) {
    errorMsg.value = 'Failed: ' + (e?.message || String(e));
  }
}

watch(queryResult, (result) => {
  if (result) parseGeneData(result);
});

async function loadSequences(datasetId: number) {
  const { post } = useRequest();
  const tid = canonicalId.value || geneId.value;
  try {
    const r: any = await post('/public/dataset/sequence/batch', {
      dataset_id: datasetId, sequence_type: 'gene', inputs: [geneId.value],
    });
    geneSeq.value = r?.sequences?.[0]?.sequence || '';
  } catch { /* ignore */ }
  try {
    const r: any = await post('/public/dataset/sequence/batch', {
      dataset_id: datasetId, sequence_type: 'mrna', inputs: [tid],
    });
    mrnaSeq.value = r?.sequences?.[0]?.sequence || '';
  } catch { /* ignore */ }
  try {
    const r: any = await post('/public/dataset/sequence/batch', {
      dataset_id: datasetId, sequence_type: 'protein', inputs: [tid],
    });
    proteinSeq.value = r?.sequences?.[0]?.sequence || '';
  } catch { /* ignore */ }
  cdsSeq.value = mrnaSeq.value;
}

async function tabHandleClick(tab: any) {
  const name = typeof tab === 'string' ? tab : tab?.name || tab?.props?.name;
  if (name === '2' && !geneSeq.value && detail?.value?.id) {
    await loadSequences(detail.value.id);
  }
  if (name === '1') {
    await nextTick();
    tryRenderStructure();
  }
}

function tryRenderStructure() {
  const container = document.getElementById('struc_view');
  if (!container || exons.value.length === 0) return;
  const g = gene.value;
  if (!g) return;
  container.innerHTML = '';
  const start = (g.start as number) || 1;
  const stop = (g.stop as number) || 1;
  const geneLen = stop - start + 1;
  const pad = Math.min(150, start - 1);
  const seq = 'N'.repeat(pad + geneLen + pad);

  const fv = new FeatureViewer(seq, '#struc_view', {
    showAxis: true, showSequence: true, brushActive: true,
    toolbar: true, bubbleHelp: true, zoomMax: 20,
  });
  const exonFeatures = exons.value.filter((e: any) => e.feature_type === 'exon');
  exonFeatures.forEach((e: any) => {
    fv.addFeature({
      x: (e.start as number) - start + 1 + pad,
      y: (e.stop as number) - start + 1 + pad,
      fillColor: '#409eff',
      strokeColor: '#337ecc',
      shape: 'rect',
      height: 12,
    });
  });
}

function formatLocation(loc: any): string {
  if (!loc) return '-';
  if (typeof loc === 'string') return loc;
  if (Array.isArray(loc)) {
    return loc.map((l: any) =>
      `${l.start || ''}-${l.end || ''}${l.score ? ' (score:' + l.score + ')' : ''}`
    ).join('; ');
  }
  if (typeof loc === 'object') {
    return `${loc.start || ''}-${loc.end || ''}${loc.score ? ' (score:' + loc.score + ')' : ''}`;
  }
  return String(loc);
}

function formatKO(orthology: any): string {
  if (!orthology) return '';
  return Array.isArray(orthology) ? orthology.join(', ') : String(orthology);
}

function backToSearch() {
  const path = router.currentRoute.value.path.replace('/geneinfo', '/search');
  router.push({ path, query: {} });
}

function openAlignment(db: string, row: any) {
  dialogContent.value = { database: db, ...row };
  hit.value = row;
  dialogVisible.value = true;
}

function getBlastLink(accession: string, db: string): string {
  const d = db.toLowerCase();
  if (d.includes('nr')) return `https://www.ncbi.nlm.nih.gov/protein/${accession}`;
  if (d.includes('swiss') || d.includes('trembl')) return `https://www.uniprot.org/uniprot/${accession}`;
  if (d.includes('tair')) return `https://www.arabidopsis.org/servlets/Search?type=general&search_action=detail&method=1&show_obsolete=F&name=${accession}&sub_type=gene&SEARCH_EXACT=4&SEARCH_CONTAINS=1`;
  return '#';
}

function getFamilyLabel(type: string): string {
  if (type === 'TF') return 'Transcription Factor';
  if (type === 'TR') return 'Transcriptional Regulator';
  if (type === 'PK') return 'Protein Kinase';
  return type;
}
</script>

<template>
  <div v-loading="queryLoading" class="geneinfo-wrapper">
    <div class="gene-nav">
      <el-button text @click="backToSearch">← Back to Search</el-button>
    </div>
    <div v-if="errorMsg" class="gene-error">{{ errorMsg }}</div>

    <template v-if="gene">
      <h3>Gene: {{ geneId }}</h3>
      <el-divider />
      <el-tabs v-model="activeName" type="border-card" @tab-click="tabHandleClick">

        <el-tab-pane label="Overview" name="1">
          <el-descriptions :column="1">
            <el-descriptions-item label="Gene ID">{{ gene.gene_id }}</el-descriptions-item>
            <el-descriptions-item label="Description">{{ gene.description || '-' }}</el-descriptions-item>
            <el-descriptions-item label="Location">{{ gene.chrom }}:{{ (gene.start as number) - 1 }}-{{ gene.stop }}</el-descriptions-item>
            <el-descriptions-item label="Strand">({{ gene.strand }})</el-descriptions-item>
          </el-descriptions>
          <h4>Gene Structure</h4>
          <div id="struc_view" style="min-height:80px;">
            <div v-if="exons.length === 0" style="color:#999;font-size:12px;padding:12px;">No structural annotation available</div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="Sequence" name="2">
          <el-collapse v-model="activeSeq" accordion>
            <el-collapse-item :title="'Gene sequence (' + geneSeq.length + ' bp)'" name="gene">
              <pre class="seq-pre">{{ geneSeq || 'Click Sequence tab to load' }}</pre>
            </el-collapse-item>
            <el-collapse-item :title="'mRNA (' + mrnaSeq.length + ' bp)'" name="mrna">
              <pre class="seq-pre">{{ mrnaSeq || 'Click Sequence tab to load' }}</pre>
            </el-collapse-item>
            <el-collapse-item :title="'CDS (' + cdsSeq.length + ' bp)'" name="cds">
              <pre class="seq-pre">{{ cdsSeq || 'Click Sequence tab to load' }}</pre>
            </el-collapse-item>
            <el-collapse-item :title="'Protein (' + proteinSeq.length + ' aa)'" name="protein">
              <pre class="seq-pre">{{ proteinSeq || 'Click Sequence tab to load' }}</pre>
            </el-collapse-item>
          </el-collapse>
        </el-tab-pane>

        <el-tab-pane label="BLAST" name="3">
          <div v-if="Object.keys(blastByDb).length === 0" style="padding:20px;color:#999;">No BLAST data available</div>
          <div v-for="(hits, db) in blastByDb" :key="db" style="margin-bottom:24px;">
            <h4>BLAST of {{ geneId }} vs. {{ db.replace('blast_', '').replace(/_/g, ' ') }} Database</h4>
            <el-table v-if="hits.length > 0" :data="hits" stripe size="small">
              <el-table-column prop="Hit_accession" label="Accession" width="150">
                <template #default="{ row: r }">
                  <el-link :href="getBlastLink(r.Hit_accession, db)" target="_blank" type="primary" :underline="false">
                    {{ r.Hit_accession }}
                  </el-link>
                </template>
              </el-table-column>
              <el-table-column prop="Hit_def" label="Description" min-width="350" show-overflow-tooltip />
              <el-table-column label="E-value" width="120">
                <template #default="{ row: r }">{{ r.Hit_hsps?.Hsp?.Hsp_evalue || '-' }}</template>
              </el-table-column>
              <el-table-column label="Identity" width="100">
                <template #default="{ row: r }">{{ r.Hit_hsps?.Hsp?.Hsp_identity || '-' }}</template>
              </el-table-column>
              <el-table-column label="Alignment" width="100">
                <template #default="{ row: r }">
                  <el-link type="primary" :underline="false" @click="openAlignment(db, r)">Show</el-link>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <el-tab-pane label="Domain" name="4">
          <el-table v-if="interpro.length > 0" :data="interpro" stripe size="small">
            <el-table-column label="IPR Term" width="120">
              <template #default="{ row: r }">
                <el-link v-if="r.ipr_term && r.ipr_term !== 'None' && r.ipr_term !== 'none'" :href="'https://www.ebi.ac.uk/interpro/entry/InterPro/' + r.ipr_term" target="_blank" type="primary" :underline="false">
                  {{ r.ipr_term }}
                </el-link>
                <span v-else>{{ r.ipr_term || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="ipr_desc" label="IPR Description" min-width="200" show-overflow-tooltip />
            <el-table-column prop="source_lib" label="Source" width="100" />
            <el-table-column label="Source Term" width="120">
              <template #default="{ row: r }">
                <el-link v-if="r.source_term" :href="'https://www.ebi.ac.uk/interpro/entry/' + r.source_lib?.toLowerCase() + '/' + r.source_term" target="_blank" type="primary" :underline="false">
                  {{ r.source_term }}
                </el-link>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="source_desc" label="Source Name" min-width="180" show-overflow-tooltip />
            <el-table-column label="Location" width="200">
              <template #default="{ row: r }">{{ formatLocation(r.location) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="No domain annotations available" />
        </el-tab-pane>

        <el-tab-pane label="Gene Ontology" name="5">
          <div v-if="goTerms.length > 0">
            <h4>Gene Ontology Terms</h4>
            <el-table :data="goTerms" stripe size="small">
              <el-table-column label="Term" width="180">
                <template #default="{ row: r }">
                  <el-link :href="'http://amigo.geneontology.org/amigo/term/' + r.term" target="_blank" type="primary" :underline="false">
                    {{ r.term }}
                  </el-link>
                </template>
              </el-table-column>
              <el-table-column prop="name" label="Name" min-width="300" show-overflow-tooltip />
              <el-table-column prop="namespace" label="Namespace" width="200" />
            </el-table>
          </div>
          <el-empty v-else description="No GO annotations available" />
        </el-tab-pane>

        <el-tab-pane label="KEGG Pathways" name="6">
          <div v-if="keggPathways.length > 0">
            <h4>KEGG Pathway Annotations</h4>
            <el-table :data="keggPathways" stripe size="small">
              <el-table-column label="Pathway ID" width="120">
                <template #default="{ row: r }">
                  <el-link :href="'https://www.kegg.jp/entry/' + r.pathway" target="_blank" type="primary" :underline="false">
                    {{ r.pathway }}
                  </el-link>
                </template>
              </el-table-column>
              <el-table-column prop="description" label="Pathway" min-width="300" show-overflow-tooltip />
              <el-table-column label="KEGG Orthology" width="200">
                <template #default="{ row: r }">{{ formatKO(r.orthology) }}</template>
              </el-table-column>
            </el-table>
          </div>
          <el-empty v-else description="No KEGG pathway annotations available" />
        </el-tab-pane>

        <el-tab-pane label="TFS/TRs/PKs" name="7">
          <div v-if="families.length > 0">
            <h4>Gene Families</h4>
            <el-button v-for="(term, i) in families" :key="i" type="primary" style="margin:4px;">
              {{ term.name }} ({{ getFamilyLabel(term.type) }})
            </el-button>
          </div>
          <el-empty v-else description="No gene family annotations available" />
        </el-tab-pane>

      </el-tabs>

      <el-dialog v-model="dialogVisible" :title="'BLAST alignment — ' + (hit.Hit_accession || '')" width="50%">
        <div v-if="hit.Hit_hsps?.Hsp">
          <p>Match: {{ hit.Hit_accession }} ({{ hit.Hit_def }})</p>
          <p><b>HSP</b> Score: {{ hit.Hit_hsps.Hsp.Hsp_score }}, E-value: {{ hit.Hit_hsps.Hsp.Hsp_evalue }}, Identity: {{ hit.Hit_hsps.Hsp.Hsp_identity }}</p>
          <pre class="alignment-pre">Query:  {{ hit.Hit_hsps.Hsp.Hsp_qseq }}
            {{ hit.Hit_hsps.Hsp.Hsp_midline }}
Sbjct:  {{ hit.Hit_hsps.Hsp.Hsp_hseq }}</pre>
        </div>
      </el-dialog>
    </template>

    <el-empty v-else-if="!queryLoading && !errorMsg" description="Gene not found" />
  </div>
</template>

<style scoped>
.geneinfo-wrapper { font-size: 14px; }
.gene-nav { margin-bottom: 12px; }
.gene-error { color: #f56c6c; margin: 8px 0; padding: 8px 12px; background: #fef0f0; border-radius: 4px; }
.seq-pre { word-break: break-all; font-family: 'Lucida Console', Monaco, monospace; font-size: 12px; white-space: pre-wrap; max-height: 400px; overflow: auto; background: #f5f5f5; padding: 8px; border-radius: 4px; }
.alignment-pre { font-family: 'Lucida Console', Monaco, monospace; font-size: 12px; white-space: pre; overflow-x: auto; background: #f5f5f5; padding: 12px; border-radius: 4px; }
</style>
