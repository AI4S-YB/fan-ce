<script setup lang="ts">
import { ref, computed, inject, watch, type Ref } from 'vue';
import { useRouter } from 'vue-router';
import { useDatasetQuery } from '@/composables/useDatasets';
import type { PublicDatasetDetail } from '@/types/dataset';

const router = useRouter();
const detail = inject<Ref<PublicDatasetDetail | null>>('genomeDetail');
const { queryLoading, queryResult, execute } = useDatasetQuery();

const allFamilies = ref<string[]>([]);
const activeTab = ref<'TF' | 'TR' | 'PK'>('TF');

const selectedFamily = ref('');
const geneList = ref<Record<string, unknown>[]>([]);
const geneTotal = ref(0);
const genePage = ref(1);
const pkExpanded = ref<string[]>([]);

// ── iTAK definitive family lists ──

const TF_FAMILIES = new Set([
  'ABI3VP1', 'Alfin-like',
  'AP2', 'AP2/ERF-AP2', 'AP2/ERF-ERF', 'AP2/ERF-RAV',
  'B3', 'B3-ARF', 'BBR-BPC', 'BES1', 'bHLH', 'BSD', 'bZIP',
  'C2C2-CO-like', 'C2C2-Dof', 'C2C2-GATA', 'C2C2-LSD', 'C2C2-YABBY',
  'C2H2', 'C3H', 'CAMTA', 'CPP', 'CSD',
  'DBB', 'DBP', 'DDT',
  'E2F-DP', 'EIL',
  'FAR1',
  'GARP-ARR-B', 'GARP-G2-like', 'GeBP', 'GRAS', 'GRF',
  'HB-BELL', 'HB-HD-ZIP', 'HB-KNOX', 'HB-other', 'HB-PHD', 'HB-WOX',
  'HSF', 'HRT-like',
  'LFY', 'LIM', 'LOB',
  'MADS-MIKC', 'MADS-M-type', 'MYB', 'MYB-related',
  'NAC', 'NF-X1', 'NF-YA', 'NF-YB', 'NF-YC', 'Nin-like', 'NZZ/SPL',
  'OFP', 'Orphans',
  'PLATZ',
  'S1Fa-like', 'SAP', 'SBP', 'SRS', 'STAT',
  'TCP', 'Tify', 'Trihelix', 'TUB',
  'ULT',
  'VOZ',
  'Whirly', 'WRKY',
  'zf-HD',
]);

const TR_FAMILIES = new Set([
  'ARID', 'AUX/IAA',
  'IWS1',
  'Jumonji',
  'LUG',
  'MBF1', 'MED6', 'MED7', 'mTERF',
  'Others',
  'PHD', 'Pseudo ARR-B',
  'RB', 'Rcd1-like',
  'SET', 'SNF2', 'SOH1', 'SWI/SNF-BAF60b', 'SWI/SNF-SWI3',
  'TAZ', 'TRAF',
]);

// PK families recognized by RLK/group prefixes
const PK_GROUP_PREFIXES = [
  'RLK-Pelle', 'AGC', 'CAMK', 'CK1', 'CMGC', 'STE', 'TKL',
  'Group', 'PEK', 'SCY1', 'RGC', 'Alpha', 'PPC', 'PDK', 'Rio', 'WNK', 'Bud32',
];

// Categorize families
const tfFamilies = computed(() => {
  return allFamilies.value.filter(f => TF_FAMILIES.has(f));
});

const trFamilies = computed(() => {
  return allFamilies.value.filter(f => TR_FAMILIES.has(f));
});

const pkFamilies = computed(() => {
  const pk = new Set<string>();
  for (const f of allFamilies.value) {
    if (TF_FAMILIES.has(f) || TR_FAMILIES.has(f)) continue;
    if (PK_GROUP_PREFIXES.some(p => f.startsWith(p))) {
      pk.add(f);
    }
  }
  return [...pk];
});

// PK tree: group by prefix before first underscore
const pkGroups = computed(() => {
  const groups: Record<string, string[]> = {};
  for (const f of pkFamilies.value) {
    const idx = f.indexOf('_');
    const group = idx > 0 ? f.substring(0, idx) : f;
    if (!groups[group]) groups[group] = [];
    groups[group].push(f);
  }
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
});

// Load families from API
async function loadFamilies() {
  const d = detail?.value;
  if (!d?.id) return;
  const assetCode = d.query_entry_asset?.asset_code;
  await execute(d.id, 'list_families', {}, assetCode);
  const result = queryResult.value as any;
  const inner = result?.data || result;
  allFamilies.value = inner?.families || [];
}

watch(() => detail?.value?.id, (id) => { if (id) loadFamilies(); }, { immediate: true });

// Gene list
async function selectFamily(fam: string) {
  if (selectedFamily.value === fam) { selectedFamily.value = ''; geneList.value = []; return; }
  selectedFamily.value = fam;
  genePage.value = 1;
  await loadGenes();
}

async function loadGenes() {
  const d = detail?.value;
  if (!d?.id || !selectedFamily.value) return;
  const assetCode = d.query_entry_asset?.asset_code;
  await execute(d.id, 'search_genes', { family: selectedFamily.value, page: genePage.value, size: 20 }, assetCode);
  const result = queryResult.value as any;
  const inner = result?.data || result;
  geneList.value = inner?.items || [];
  geneTotal.value = inner?.total || 0;
}

async function onGenePageChange(p: number) { genePage.value = p; await loadGenes(); }

function goToGene(geneId: string) {
  router.push({ path: router.currentRoute.value.path.replace(/\/tf$/, '/geneinfo'), query: { gene_id: geneId } });
}

function currentFamilies() {
  if (activeTab.value === 'TF') return tfFamilies.value;
  if (activeTab.value === 'TR') return trFamilies.value;
  return [];
}

const tabStyle = (t: string) => ({
  padding: '8px 20px', cursor: 'pointer', fontSize: '14px', fontWeight: activeTab.value === t ? '600' : '400',
  color: activeTab.value === t ? '#409eff' : '#606266',
  borderBottom: activeTab.value === t ? '2px solid #409eff' : '2px solid transparent',
});
</script>

<template>
  <div>
    <!-- Tab bar -->
    <div style="display:flex;gap:0;border-bottom:2px solid #e5e5e5;margin-bottom:20px;">
      <div :style="tabStyle('TF')" @click="activeTab = 'TF'">Transcription Factors ({{ tfFamilies.length }})</div>
      <div :style="tabStyle('TR')" @click="activeTab = 'TR'">Transcriptional Regulators ({{ trFamilies.length }})</div>
      <div :style="tabStyle('PK')" @click="activeTab = 'PK'">Protein Kinases ({{ pkFamilies.length }})</div>
    </div>

    <!-- TF / TR: tag cloud -->
    <template v-if="activeTab === 'TF' || activeTab === 'TR'">
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:20px;max-height:400px;overflow-y:auto;padding:8px 0;">
        <el-tag
          v-for="fam in currentFamilies()"
          :key="fam"
          :type="selectedFamily === fam ? 'primary' : 'info'"
          :effect="selectedFamily === fam ? 'dark' : 'plain'"
          size="default"
          style="cursor:pointer;font-size:12px;"
          @click="selectFamily(fam)"
        >
          {{ fam }} ({{ fam === selectedFamily && geneTotal ? geneTotal : '' }})
        </el-tag>
      </div>
    </template>

    <!-- PK: grouped tree -->
    <template v-if="activeTab === 'PK'">
      <div style="margin-bottom:20px;">
        <el-collapse v-model="pkExpanded">
          <el-collapse-item v-for="[group, members] in pkGroups" :key="group" :title="`${group}  (${members.length})`" :name="group">
            <div style="display:flex;flex-wrap:wrap;gap:6px;padding:8px 0;">
              <el-tag
                v-for="fam in members"
                :key="fam"
                :type="selectedFamily === fam ? 'primary' : 'info'"
                :effect="selectedFamily === fam ? 'dark' : 'plain'"
                size="default"
                style="cursor:pointer;font-size:12px;"
                @click="selectFamily(fam)"
              >
                {{ fam }}
              </el-tag>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </template>

    <!-- Gene list for selected family -->
    <template v-if="selectedFamily">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <el-button text size="small" @click="selectFamily(selectedFamily)">← Close</el-button>
        <h4 style="margin:0;">{{ selectedFamily }}</h4>
        <span style="color:#888;font-size:12px;">{{ geneTotal }} genes</span>
      </div>

      <el-table :data="geneList" size="small" border stripe v-loading="queryLoading" v-if="geneList.length > 0">
        <el-table-column prop="gene_id" label="Gene ID" width="180">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="goToGene(row.gene_id)">{{ row.gene_id }}</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="chrom" label="Chr" width="100" />
        <el-table-column prop="start" label="Start" width="100" />
        <el-table-column prop="stop" label="End" width="100" />
        <el-table-column prop="strand" label="Strand" width="70" />
        <el-table-column prop="description" label="Description" min-width="200" show-overflow-tooltip />
      </el-table>

      <el-empty v-else-if="!queryLoading" description="No genes found" />

      <div v-if="geneTotal > 20" style="margin-top:12px;text-align:right;">
        <el-pagination v-model:current-page="genePage" :page-size="20" :total="geneTotal" layout="prev, pager, next" small @current-change="onGenePageChange" />
      </div>
    </template>
  </div>
</template>
