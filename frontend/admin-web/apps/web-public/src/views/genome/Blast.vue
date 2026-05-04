<script setup lang="ts">
import { computed, inject, ref, type Ref } from 'vue';
import { useDatasetQuery } from '@/composables/useDatasets';
import type { PublicDatasetDetail } from '@/types/dataset';

const detail = inject<Ref<PublicDatasetDetail | null>>('genomeDetail');
const { queryLoading, queryResult, execute } = useDatasetQuery();

const querySeq = ref('');

const rows = computed(() => {
  const result = queryResult.value;
  if (!result) return [];
  return (result.rows || result.items || []) as Record<string, unknown>[];
});

async function onBlast() {
  const datasetId = detail?.value?.id;
  if (!datasetId || !querySeq.value.trim()) return;

  await execute(datasetId, 'blast', {
    sequence: querySeq.value,
  });
}
</script>

<template>
  <div>
    <p style="font-size: 13px; color: #888; margin-bottom: 8px;">
      Enter a query sequence in FASTA format for BLAST alignment against this genome.
    </p>

    <div style="margin-bottom: 16px;">
      <el-input
        v-model="querySeq"
        type="textarea"
        :rows="8"
        placeholder=">query&#10;ATGGCGTACCCATACGATGTTCCAGATTACGCTTCTTCTCGTTA..."
      />
    </div>

    <el-button
      type="primary"
      :loading="queryLoading"
      :disabled="!querySeq.trim()"
      @click="onBlast"
      style="margin-bottom: 16px;"
    >
      Run BLAST
    </el-button>

    <div v-loading="queryLoading">
      <el-empty v-if="!queryLoading && rows.length === 0 && queryResult !== null" description="No hits found" />

      <template v-if="rows.length > 0">
        <el-table :data="rows" size="small" border stripe>
          <el-table-column prop="target_id" label="Target ID" width="160" />
          <el-table-column prop="identity" label="Identity (%)" width="110" />
          <el-table-column prop="alignment_length" label="Align Length" width="120" />
          <el-table-column prop="mismatches" label="Mismatches" width="110" />
          <el-table-column prop="gap_opens" label="Gap Opens" width="100" />
          <el-table-column prop="evalue" label="E-value" width="100" />
          <el-table-column prop="bit_score" label="Bit Score" width="100" />
          <el-table-column prop="q_start" label="Q Start" width="80" />
          <el-table-column prop="q_end" label="Q End" width="80" />
          <el-table-column prop="t_start" label="T Start" width="80" />
          <el-table-column prop="t_end" label="T End" width="80" />
        </el-table>

        <div v-if="queryResult?.total" style="margin-top: 8px; color: #888; font-size: 13px;">
          Total hits: {{ queryResult.total }}
        </div>
      </template>
    </div>
  </div>
</template>
