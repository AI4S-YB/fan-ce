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

// Batch
const geneIds = ref('');
const seqType = ref('genome');

// BLAST
const querySeq = ref('');

// ── Downloads ──
const { loading: dlLoading, files: dlFiles, loadDownloads, downloadUrl } = useDownloads();
const dsCode = computed(() => detail?.value?.dataset_code || '');

// Genome-scoped downloads
watch([tool, dsCode], ([t, code]) => {
  console.log('Tools watcher:', t, code, 'hasGenome:', hasGenome.value, 'detail:', !!detail?.value);
  if (t === 'download' && code && hasGenome.value) {
    console.log('Loading downloads for', code);
    loadDownloads(code);
  }
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
        <el-input v-model="geneIds" type="textarea" :rows="6" placeholder="Enter gene IDs, one per line..." style="margin-bottom:12px;" />
        <el-select v-model="seqType" style="width:160px;margin-right:8px;">
          <el-option label="Genome" value="genome" />
          <el-option label="mRNA" value="mrna" />
          <el-option label="CDS" value="cds" />
          <el-option label="Protein" value="protein" />
        </el-select>
        <el-button type="primary">Retrieve</el-button>
        <div style="margin-top:12px;color:#888;font-size:13px;">Results will appear here</div>
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
