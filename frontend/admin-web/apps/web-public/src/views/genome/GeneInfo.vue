<script setup lang="ts">
import { computed, inject, watch, type Ref } from 'vue';
import { useRoute } from 'vue-router';
import { useDatasetQuery } from '@/composables/useDatasets';
import type { PublicDatasetDetail } from '@/types/dataset';

const route = useRoute();
const detail = inject<Ref<PublicDatasetDetail | null>>('genomeDetail');
const { queryLoading, queryResult, execute } = useDatasetQuery();

const geneIdParam = computed(() => route.query.gene_id as string);

const geneData = computed(() => {
  const rows = queryResult.value?.rows || queryResult.value?.items;
  if (rows && rows.length > 0) return rows[0] as Record<string, unknown>;
  return null;
});

// Auto-load gene info when route query or detail changes
watch(
  () => [route.query.gene_id, detail?.value?.id] as const,
  ([gid, did]) => {
    if (gid && did) {
      execute(did, 'gene_search', { gene_id: gid as string });
    }
  },
  { immediate: true },
);
</script>

<template>
  <div v-loading="queryLoading">
    <template v-if="geneData">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="Gene ID">
          {{ geneData.gene_id || geneIdParam || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="Gene Name">
          {{ geneData.gene_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="Chromosome">
          {{ geneData.chrom || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="Strand">
          {{ geneData.strand || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="Start">
          {{ geneData.start ?? '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="End">
          {{ geneData.end ?? '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="Type">
          {{ geneData.gene_type || geneData.type || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="Source">
          {{ geneData.source || '-' }}
        </el-descriptions-item>

        <!-- Transcripts -->
        <template v-if="geneData.transcripts">
          <el-descriptions-item label="Transcripts" :span="2">
            <pre
              style="margin: 0; font-size: 12px; max-height: 200px; overflow: auto; white-space: pre-wrap;"
            >{{ typeof geneData.transcripts === 'string' ? geneData.transcripts : JSON.stringify(geneData.transcripts, null, 2) }}</pre>
          </el-descriptions-item>
        </template>

        <!-- Description -->
        <template v-if="geneData.description">
          <el-descriptions-item label="Description" :span="2">
            {{ geneData.description }}
          </el-descriptions-item>
        </template>
      </el-descriptions>

      <!-- Sequence -->
      <div v-if="geneData.sequence || geneData.seq" style="margin-top: 20px;">
        <h3>Sequence</h3>
        <pre
          style="background: #f5f7fa; padding: 16px; border-radius: 4px; white-space: pre-wrap; font-size: 12px; line-height: 1.6; font-family: monospace; max-height: 300px; overflow: auto;"
        >{{ geneData.sequence || geneData.seq }}</pre>
      </div>
    </template>

    <el-empty v-else-if="!queryLoading" description="No gene selected" />
  </div>
</template>
