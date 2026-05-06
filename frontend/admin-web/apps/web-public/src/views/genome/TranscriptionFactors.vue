<script setup lang="ts">
import { ref, inject, type Ref } from 'vue';
import { useRouter } from 'vue-router';
import { useDatasetQuery } from '@/composables/useDatasets';
import type { PublicDatasetDetail } from '@/types/dataset';

const router = useRouter();
const detail = inject<Ref<PublicDatasetDetail | null>>('genomeDetail');
const { queryLoading, queryResult, execute } = useDatasetQuery();

const tfFamilies = [
  'AP2/ERF', 'ARF', 'bHLH', 'bZIP', 'C2H2', 'C3H', 'Dof', 'GATA',
  'GRAS', 'HSF', 'LOB', 'MADS', 'MYB', 'NAC', 'NF-Y', 'SBP',
  'TCP', 'Trihelix', 'WRKY', 'ZF-HD',
];

const selectedFamily = ref('');
const geneList = ref<Record<string, unknown>[]>([]);
const geneTotal = ref(0);
const genePage = ref(1);

async function selectFamily(fam: string) {
  if (selectedFamily.value === fam) {
    selectedFamily.value = '';
    geneList.value = [];
    return;
  }
  selectedFamily.value = fam;
  genePage.value = 1;
  await loadGenes();
}

async function loadGenes() {
  const d = detail?.value;
  if (!d?.id || !selectedFamily.value) return;
  const assetCode = d.query_entry_asset?.asset_code;
  await execute(d.id, 'search_genes', {
    family: selectedFamily.value,
    page: genePage.value,
    size: 20,
  }, assetCode);
  const result = queryResult.value as any;
  const inner = result?.data || result;
  geneList.value = inner?.items || [];
  geneTotal.value = inner?.total || 0;
}

async function onGenePageChange(p: number) {
  genePage.value = p;
  await loadGenes();
}

function goToGene(geneId: string) {
  router.push({
    path: router.currentRoute.value.path.replace(/\/tf$/, '/geneinfo'),
    query: { gene_id: geneId },
  });
}
</script>

<template>
  <div>
    <h4 style="margin:0 0 12px;">Transcription Factor Families</h4>
    <p style="color:#888;font-size:13px;margin-bottom:12px;">
      Click a family to browse its member genes. Data sourced from functional annotation (InterPro, Pfam).
    </p>

    <!-- Family tag cloud -->
    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;">
      <el-tag
        v-for="fam in tfFamilies"
        :key="fam"
        :type="selectedFamily === fam ? 'primary' : 'info'"
        :effect="selectedFamily === fam ? 'dark' : 'plain'"
        size="large"
        style="cursor:pointer;font-size:13px;"
        @click="selectFamily(fam)"
      >
        {{ fam }}
      </el-tag>
    </div>

    <!-- Gene list for selected family -->
    <template v-if="selectedFamily">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <el-button text size="small" @click="selectFamily(selectedFamily)">← Back</el-button>
        <h4 style="margin:0;">{{ selectedFamily }}</h4>
        <span style="color:#888;font-size:12px;">{{ geneTotal }} genes</span>
      </div>

      <el-table :data="geneList" size="small" border stripe v-loading="queryLoading" v-if="geneList.length > 0">
        <el-table-column prop="gene_id" label="Gene ID" width="180">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="goToGene(row.gene_id)">
              {{ row.gene_id }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column prop="chrom" label="Chr" width="100" />
        <el-table-column prop="start" label="Start" width="100" />
        <el-table-column prop="stop" label="End" width="100" />
        <el-table-column prop="strand" label="Strand" width="70" />
        <el-table-column prop="description" label="Description" min-width="200" show-overflow-tooltip />
      </el-table>

      <el-empty v-else-if="!queryLoading" description="No genes found for this family" />

      <div v-if="geneTotal > 20" style="margin-top:12px;text-align:right;">
        <el-pagination
          v-model:current-page="genePage"
          :page-size="20"
          :total="geneTotal"
          layout="prev, pager, next"
          small
          @current-change="onGenePageChange"
        />
      </div>
    </template>

    <el-empty v-else description="Select a TF family above to view member genes" :image-size="60" />
  </div>
</template>
