<script setup lang="ts">
import { ref, computed, inject, watch, onMounted, type Ref } from 'vue';
import { useRoute } from 'vue-router';
import type { PublicDatasetDetail } from '@/types/dataset';
import { useDatasetList, useDownloads } from '@/composables/useDatasets';
import { useRequest } from '@/composables/useRequest';

const route = useRoute();
const tool = computed(() => route.params.tool as string);
const detail = inject<Ref<PublicDatasetDetail | null>>('genomeDetail', ref(null));

const hasGenome = computed(() => !!detail?.value);

// Batch sequence retrieval
const geneIds = ref('');
const seqType = ref('gene');
const enableUpstream = ref(false);
const enableDownstream = ref(false);
const upstream = ref(2000);
const downstream = ref(1000);
const seqLoading = ref(false);
const seqResults = ref<any[]>([]);
const seqTruncated = ref(false);
const seqDownloadUrl = ref('');
const seqError = ref('');
const exampleLoading = ref(false);

function buildSequenceType(): string {
  if (seqType.value === 'gene') {
    const parts = ['gene'];
    if (enableUpstream.value) parts.push('up');
    if (enableDownstream.value) parts.push('down');
    return parts.join('_');
  }
  return seqType.value;
}

async function retrieveSequences() {
  const inputList = geneIds.value.split('\n').map(s => s.trim()).filter(Boolean);
  if (inputList.length === 0) { seqError.value = 'Please enter at least one input'; return; }
  if (!detail?.value?.id) { seqError.value = 'No genome dataset selected'; return; }

  seqLoading.value = true;
  seqError.value = '';
  seqResults.value = [];
  seqTruncated.value = false;
  seqDownloadUrl.value = '';

  try {
    const { post } = useRequest();
    const data: any = await post('/public/dataset/sequence/batch', {
      dataset_id: detail.value.id,
      sequence_type: buildSequenceType(),
      upstream: upstream.value,
      downstream: downstream.value,
      inputs: inputList,
    });
    seqResults.value = data?.sequences || [];
    seqTruncated.value = data?.truncated || false;
    seqDownloadUrl.value = data?.download_url || '';
  } catch (e: any) {
    seqError.value = e?.message || 'Sequence retrieval failed';
  } finally {
    seqLoading.value = false;
  }
}

function downloadAllSequences() {
  const fasta = seqResults.value
    .filter((item: any) => item.sequence)
    .map((item: any) => `${item.header}\n${item.sequence}`)
    .join('\n');
  if (!fasta) return;
  const blob = new Blob([fasta + '\n'], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'sequences.fasta';
  a.click();
  URL.revokeObjectURL(url);
}

async function loadBatchExample() {
  if (!detail?.value?.id) return;
  exampleLoading.value = true;
  try {
    const { post } = useRequest();
    const data: any = await post('/public/dataset/query/execute', {
      id: detail.value.id,
      operation: 'list_genes',
      params: { page: 1, size: 5 },
    });
    const items = data?.data?.items || data?.items || [];

    if (seqType.value === 'genome') {
      // Build example coordinate strings from chromosome names
      const chroms = [...new Set(items.map((item: any) => String(item.chrom || '')).filter(Boolean))] as string[];;
      const examples = chroms.slice(0, 3).map((c: string) => `${c}:1000-5000`);
      if (examples.length > 0) geneIds.value = examples.join('\n');
    } else if (seqType.value === 'mrna' || seqType.value === 'protein') {
      // Use transcript IDs for mRNA/protein FASTA lookup
      const tids = items.map((item: any) => item.canonical_transcript || '').filter(Boolean);
      if (tids.length > 0) geneIds.value = tids.join('\n');
    } else {
      // Gene mode: use gene IDs
      const ids = items.map((item: any) => item.gene_id || '').filter(Boolean);
      if (ids.length > 0) {
        geneIds.value = ids.join('\n');
        upstream.value = 2000;
        downstream.value = 1000;
      }
    }
  } finally {
    exampleLoading.value = false;
  }
}

// BLAST
const querySeq = ref('');

// ── Downloads ──
const { loading: dlLoading, files: dlFiles, loadDownloads, downloadUrl } = useDownloads();
const dsCode = computed(() => detail?.value?.dataset_code || '');

// Genome-scoped downloads
watch([tool, dsCode], ([t, code]) => {
  if (t === 'download' && code && hasGenome.value) loadDownloads(code);
});

// ── Site-wide downloads (standalone /tools/download) ──
const { items: allDatasets, load: loadAllDatasets } = useDatasetList();
const siteDownloads = ref<{ dataset: any; files: any[] }[]>([]);
const siteLoading = ref(false);

async function loadSiteDownloads() {
  siteLoading.value = true;
  siteDownloads.value = [];
  const { get } = useRequest();
  try {
    await loadAllDatasets({});
    const results: { dataset: any; files: any[] }[] = [];
    for (const ds of allDatasets.value) {
      const code = ds.dataset_code;
      if (!code) continue;
      try {
        const data: any = await get(`/public/dataset/${code}/downloads`);
        const files = data?.files || [];
        if (files.length > 0) {
          results.push({ dataset: ds, files });
        }
      } catch { /* skip */ }
    }
    siteDownloads.value = results;
  } finally {
    siteLoading.value = false;
  }
}

// Load site-wide downloads when standalone download page mounts
watch(tool, (t) => {
  if (t === 'download' && !hasGenome.value) loadSiteDownloads();
});
onMounted(() => {
  if (tool.value === 'download' && !hasGenome.value) loadSiteDownloads();
});

function siteDownloadUrl(datasetCode: string, fileId: number) {
  return `/api/v1/public/dataset/${datasetCode}/download/${fileId}`;
}
</script>
<template>
  <div>
    <div v-if="!hasGenome">
      <!-- Standalone tools -->
      <div v-if="tool === 'download'">
        <h2>Site Downloads</h2>
        <p style="color:#888;font-size:13px;margin-bottom:16px;">
          Browse downloadable files from all public datasets.
        </p>
        <div v-loading="siteLoading">
          <div v-if="siteDownloads.length === 0 && !siteLoading" style="text-align:center;padding:40px;color:#999;">
            No downloadable files available at this time.
          </div>
          <div v-for="item in siteDownloads" :key="item.dataset.id" style="margin-bottom:24px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
              <router-link :to="'/dataset/' + item.dataset.id" style="font-size:16px;font-weight:600;color:#409eff;text-decoration:none;">
                {{ item.dataset.title || item.dataset.dataset_code }}
              </router-link>
              <el-tag size="small">{{ item.dataset.dataset_type }}</el-tag>
              <span style="color:#888;font-size:12px;">{{ item.files.length }} file(s)</span>
            </div>
            <el-table :data="item.files" border size="small">
              <el-table-column prop="file_name" label="File" min-width="240" />
              <el-table-column prop="file_format" label="Format" width="100" />
              <el-table-column label="Size" width="120">
                <template #default="{ row }">
                  {{ row.file_size ? (row.file_size / 1024 / 1024).toFixed(1) + ' MB' : '-' }}
                </template>
              </el-table-column>
              <el-table-column label="" width="100">
                <template #default="{ row }">
                  <el-button type="primary" size="small" tag="a" :href="siteDownloadUrl(item.dataset.dataset_code, row.id)">
                    Download
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>

      <el-empty v-else :description="`Unknown tool: ${tool}`" />
    </div>

    <template v-else>
      <div v-if="tool === 'batch'">
        <h3>Batch Sequence Retrieval</h3>
        <p style="color:#888;font-size:13px;margin-bottom:16px;">
          Retrieve sequences by gene ID or genomic coordinates from this genome dataset.
        </p>

        <!-- Sequence Type -->
        <div style="margin-bottom:12px;">
          <div style="font-weight:500;margin-bottom:4px;">Sequence Type</div>
          <el-radio-group v-model="seqType">
            <el-radio value="genome">Genome (by coordinates)</el-radio>
            <el-radio value="mrna">mRNA (by gene ID)</el-radio>
            <el-radio value="protein">Protein (by gene ID)</el-radio>
            <el-radio value="gene">Gene (by gene ID)</el-radio>
          </el-radio-group>
        </div>

        <!-- Upstream / Downstream -->
        <div v-if="seqType === 'gene'" style="margin-bottom:12px;display:flex;gap:16px;align-items:center;flex-wrap:wrap;">
          <el-checkbox v-model="enableUpstream">Upstream</el-checkbox>
          <el-input-number v-model="upstream" :min="1" :max="3000" :disabled="!enableUpstream" size="small" style="width:140px;" /> bp
          <el-checkbox v-model="enableDownstream" style="margin-left:8px;">Downstream</el-checkbox>
          <el-input-number v-model="downstream" :min="1" :max="3000" :disabled="!enableDownstream" size="small" style="width:140px;" /> bp
        </div>

        <!-- Input -->
        <div style="margin-bottom:12px;">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">
            <span style="font-weight:500;">
              {{ seqType === 'genome' ? 'Coordinates (one per line, e.g. Chr1A:1000-5000)' :
                 seqType === 'mrna' || seqType === 'protein' ? 'Transcript IDs (one per line)' :
                 'Gene IDs (one per line)' }}
            </span>
            <el-button size="small" type="primary" plain :loading="exampleLoading" @click="loadBatchExample">
              Try Example
            </el-button>
          </div>
          <el-input
            v-model="geneIds"
            type="textarea"
            :rows="8"
            :placeholder="seqType === 'genome' ? 'Chr1A:1000000-1005000\nChr2B:2000000-2005000' : seqType === 'mrna' || seqType === 'protein' ? 'SAM1A000100.1\nSAM1A000200.1' : 'SAM1A000100\nSAM1A000200'"
            style="font-family:monospace;font-size:13px;"
          />
        </div>

        <el-button type="primary" :loading="seqLoading" @click="retrieveSequences" style="margin-bottom:16px;">
          Retrieve
        </el-button>

        <!-- Results -->
        <div v-if="seqResults.length > 0 || seqError" style="margin-top:16px;">
          <div v-if="seqError" style="color:red;margin-bottom:12px;">{{ seqError }}</div>
          <div v-if="seqTruncated" style="background:#fff3cd;padding:12px;border-radius:4px;margin-bottom:12px;">
            Result exceeds 1MB.
            <el-button v-if="seqDownloadUrl" size="small" type="primary" tag="a" :href="seqDownloadUrl">
              Download sequences.fasta
            </el-button>
          </div>
          <div v-if="!seqTruncated && seqResults.some((r: any) => r.sequence)" style="margin-bottom:12px;">
            <el-button size="small" @click="downloadAllSequences">Download All (.fasta)</el-button>
          </div>
          <div v-for="item in seqResults" :key="item.input" style="margin-bottom:16px;">
            <div v-if="item.error" style="color:#e6a23c;font-size:12px;margin-bottom:4px;">
              {{ item.input }}: {{ item.error }}
            </div>
            <template v-else>
              <div style="font-weight:600;font-size:13px;color:#409eff;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center;">
                <span>{{ item.header }}</span>
                <span style="color:#999;font-weight:400;">{{ item.length?.toLocaleString() }} bp</span>
              </div>
              <pre v-if="item.sequence" style="background:#f5f5f5;padding:8px;border-radius:4px;font-size:12px;max-height:200px;overflow:auto;white-space:pre-wrap;word-break:break-all;">{{ item.sequence }}</pre>
            </template>
          </div>
        </div>
      </div>

      <div v-else-if="tool === 'blast'">
        <h3>BLAST</h3>
        <el-input v-model="querySeq" type="textarea" :rows="6" placeholder="Paste query sequence in FASTA format..." style="margin-bottom:12px;" />
        <el-button type="primary">Run BLAST</el-button>
        <div style="margin-top:12px;color:#888;font-size:13px;">Results will appear here</div>
      </div>

      <div v-else-if="tool === 'download'">
        <h3>Downloads</h3>
        <el-table :data="dlFiles" border size="small" v-loading="dlLoading" v-if="dlFiles.length > 0">
          <el-table-column prop="file_name" label="File" min-width="200" />
          <el-table-column prop="file_format" label="Format" width="100" />
          <el-table-column label="Size" width="120">
            <template #default="{ row }">
              {{ row.file_size ? (row.file_size / 1024 / 1024).toFixed(1) + ' MB' : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="Download" width="120">
            <template #default="{ row }">
              <el-button type="primary" size="small" tag="a" :href="downloadUrl(dsCode, row.id)">
                Download
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else-if="!dlLoading" description="No downloadable files available" />
      </div>

      <el-empty v-else :description="`Unknown tool: ${tool}`" />
    </template>
  </div>
</template>
