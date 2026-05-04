<script setup lang="ts">
import { ref, computed, inject, type Ref } from 'vue';
import { useRoute } from 'vue-router';
import type { PublicDatasetDetail } from '@/types/dataset';

const route = useRoute();
const tool = computed(() => route.params.tool as string);
const detail = inject<Ref<PublicDatasetDetail | null>>('genomeDetail', ref(null));

const hasGenome = computed(() => !!detail?.value);

// Batch
const geneIds = ref('');
const seqType = ref('genome');

// BLAST
const querySeq = ref('');
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
        <el-table :data="detail?.assets || []" border size="small" v-if="detail?.assets?.length">
          <el-table-column prop="asset_code" label="Asset" width="180" />
          <el-table-column prop="asset_name" label="Name" />
          <el-table-column prop="file_format" label="Format" width="100" />
          <el-table-column label="Files" width="80">
            <template #default="{ row }">{{ row.files?.length || 0 }}</template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="No download files available" />
      </div>

      <el-empty v-else :description="`Unknown tool: ${tool}`" />
    </template>
  </div>
</template>
