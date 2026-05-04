<script setup lang="ts">
import { computed, inject, ref, type Ref } from 'vue';
import { useDatasetQuery } from '@/composables/useDatasets';
import type { PublicDatasetDetail } from '@/types/dataset';

const detail = inject<Ref<PublicDatasetDetail | null>>('genomeDetail');
const { queryLoading, queryResult, execute } = useDatasetQuery();

const geneList = ref('');
const seqType = ref('genome');
const page = ref(1);
const pageSize = ref(20);

const seqTypeOptions = [
  { label: 'Genome', value: 'genome' },
  { label: 'mRNA', value: 'mrna' },
  { label: 'CDS', value: 'cds' },
  { label: 'Protein', value: 'protein' },
];

const rows = computed(() => {
  const result = queryResult.value;
  if (!result) return [];
  return (result.rows || result.items || []) as Record<string, unknown>[];
});

const total = computed(() => queryResult.value?.total ?? 0);

function toFasta(): string {
  if (rows.value.length === 0) return '';
  return rows.value
    .map((r) => {
      const id = r.gene_id || r.id || '';
      const seq = r.sequence || r.seq || '';
      return `>${id}\n${seq}`;
    })
    .join('\n');
}

async function onQuery() {
  page.value = 1;
  await doQuery();
}

async function onPageChange(p: number) {
  page.value = p;
  await doQuery();
}

async function doQuery() {
  const datasetId = detail?.value?.id;
  if (!datasetId || !geneList.value.trim()) return;

  const ids = geneList.value
    .split(/[\n,;]+/)
    .map((s) => s.trim())
    .filter(Boolean);

  await execute(datasetId, 'batch_query', {
    gene_ids: ids,
    seq_type: seqType.value,
    page: page.value,
    size: pageSize.value,
  });
}

function downloadFasta() {
  const fasta = toFasta();
  if (!fasta) return;
  const blob = new Blob([fasta], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'batch_sequences.fasta';
  a.click();
  URL.revokeObjectURL(url);
}
</script>

<template>
  <div>
    <!-- Query Form -->
    <div style="margin-bottom: 16px;">
      <p style="font-size: 13px; color: #888; margin-bottom: 8px;">
        Enter gene IDs, one per line or separated by commas/semicolons.
      </p>
      <el-input
        v-model="geneList"
        type="textarea"
        :rows="6"
        placeholder="RCHI_00001&#10;RCHI_00002&#10;RCHI_00003"
      />
    </div>

    <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 16px;">
      <el-select v-model="seqType" style="width: 150px;">
        <el-option
          v-for="opt in seqTypeOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
      <el-button type="primary" :loading="queryLoading" :disabled="!geneList.trim()" @click="onQuery">
        Query
      </el-button>
      <el-button v-if="rows.length > 0" @click="downloadFasta">
        Download FASTA
      </el-button>
    </div>

    <!-- Results -->
    <div v-loading="queryLoading">
      <el-empty v-if="!queryLoading && rows.length === 0 && queryResult !== null" description="No results" />

      <template v-if="rows.length > 0">
        <el-table :data="rows" size="small" border stripe>
          <el-table-column prop="gene_id" label="Gene ID" width="160" />
          <el-table-column label="Sequence" min-width="300">
            <template #default="{ row }">
              <pre
                style="margin: 0; font-size: 11px; max-height: 80px; overflow: auto; white-space: pre; font-family: monospace;"
              >{{ (row.sequence || row.seq || '') }}</pre>
            </template>
          </el-table-column>
          <el-table-column prop="length" label="Length" width="80">
            <template #default="{ row }">
              {{ row.length || (row.sequence || row.seq || '').toString().length }}
            </template>
          </el-table-column>
        </el-table>

        <div style="margin-top: 12px; text-align: right;">
          <el-pagination
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            small
            @current-change="onPageChange"
            @size-change="(s: number) => { pageSize = s; onQuery(); }"
          />
        </div>
      </template>
    </div>
  </div>
</template>
