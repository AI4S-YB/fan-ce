<script setup lang="ts">
import { ref, computed, inject, watch, type Ref } from 'vue';
import { useRoute } from 'vue-router';
import type { PublicDatasetDetail } from '@/types/dataset';
import { useDownloads } from '@/composables/useDatasets';

const route = useRoute();
const tool = computed(() => route.params.tool as string);
const detail = inject<Ref<PublicDatasetDetail | null>>('genomeDetail', ref(null));

const hasGenome = computed(() => !!detail?.value);

// Batch
const geneIds = ref('');
const seqType = ref('genome');

// BLAST
const querySeq = ref('');

// Downloads
const { loading: dlLoading, files: dlFiles, loadDownloads, downloadUrl } = useDownloads();
const dsCode = computed(() => detail?.value?.dataset_code || '');

watch([tool, dsCode], ([t, code]) => {
  console.log('Tools watcher:', t, code, 'detail keys:', Object.keys(detail?.value || {}));
  if (t === 'download' && code) {
    console.log('Calling loadDownloads for', code);
    loadDownloads(code);
  }
});
</script>
<template>
  <div>
    <div v-if="!hasGenome">
      <h3>Select a genome to use this tool</h3>
      <p style="color:#888;font-size:13px;">
        <router-link to="/">Browse genomes</router-link> and select one first.
      </p>
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
