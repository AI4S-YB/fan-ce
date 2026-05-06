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
const familyCounts = ref<Record<string, number>>({});

async function selectFamily(fam: string) {
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

function backToFamilies() {
  selectedFamily.value = '';
  geneList.value = [];
}
</script>

<template>
  <div style="display:flex;gap:20px;">
    <!-- Left: Family List -->
    <div style="width:220px;flex-shrink:0;">
      <h4 style="margin:0 0 8px;">TF Families</h4>
      <div style="border:1px solid #e5e5e5;border-radius:4px;max-height:600px;overflow-y:auto;">
        <div
          v-for="fam in tfFamilies"
          :key="fam"
          @click="selectFamily(fam)"
          :style="{
            padding:'10px 14px',cursor:'pointer',fontSize:'13px',
            background: selectedFamily === fam ? '#ecf5ff' : '#fff',
            color: selectedFamily === fam ? '#409eff' : '#606266',
            borderBottom:'1px solid #f0f0f0',
            display:'flex',justifyContent:'space-between',alignItems:'center',
          }"
        >
          <span>{{ fam }}</span>
          <span v-if="familyCounts[fam]" style="font-size:11px;color:#999;">{{ familyCounts[fam] }}</span>
        </div>
      </div>
    </div>

    <!-- Right: Gene List or Family Overview -->
    <div style="flex:1;" v-loading="queryLoading">
      <template v-if="!selectedFamily">
        <h4>Transcription Factor Families</h4>
        <p style="color:#888;font-size:13px;margin-bottom:16px;">
          Select a TF family from the left panel to browse its member genes.
          Data is sourced from the functional annotation database (InterPro, Pfam).
        </p>
        <el-empty description="Select a family to view genes" :image-size="80" />
      </template>

      <template v-else>
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
          <el-button text size="small" @click="backToFamilies">← All Families</el-button>
          <h4 style="margin:0;">{{ selectedFamily }}</h4>
          <span style="color:#888;font-size:12px;">{{ geneTotal }} genes</span>
        </div>

        <el-table :data="geneList" size="small" border stripe v-if="geneList.length > 0">
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
    </div>
  </div>
</template>
