<script setup lang="ts">
import { ref, computed, inject, watch, type Ref } from 'vue';
import { useRouter } from 'vue-router';
import { useDatasetQuery } from '@/composables/useDatasets';
import type { PublicDatasetDetail } from '@/types/dataset';
import { ElMessage } from 'element-plus';

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

// PK family → canonical group (iTAK Shiu classification, 9 groups)
const PK_GROUP_ORDER = ['AGC', 'CAMK', 'CK1', 'CMGC', 'RLK-Pelle', 'STE', 'TKL', 'Plant-specific', 'Others'];

function pkGroup(fam: string): string {
  if (fam.startsWith('RLK-Pelle')) return 'RLK-Pelle';
  if (fam.startsWith('AGC')) return 'AGC';
  if (fam.startsWith('CAMK')) return 'CAMK';
  if (fam.startsWith('CK1')) return 'CK1';
  if (fam.startsWith('CMGC')) return 'CMGC';
  if (fam.startsWith('STE')) return 'STE';
  if (fam.startsWith('TKL')) return 'TKL';
  if (fam.startsWith('Group-Pl')) return 'Plant-specific';
  return 'Others';
}

// Checks whether a family name belongs to PK (after TF/TR are excluded)
function isPkFamily(fam: string): boolean {
  return PK_GROUP_ORDER.some(g => pkGroup(fam) === g);
}

// PK family descriptions (full names from iTAK / Shiu classification)
const PK_DESCRIPTIONS: Record<string, string> = {
  'AGC_MAST': 'Microtubule Associated Serine/Threonine Kinase',
  'AGC_NDR': 'Nuclear Dbf2-Related kinases',
  'AGC_PDK1': 'Phosphoinositide-Dependent protein Kinase 1',
  'AGC_PKA-PKG': 'Protein Kinase A / Protein Kinase G (cyclic AMP/cGMP-dependent)',
  'AGC_RSK-2': 'Ribosomal S6 Kinases 2',
  'AGC-Pl': 'AGC Plant-specific',
  'CAMK_AMPK': 'AMP-activated protein kinase',
  'CAMK_CAMKL-CHK1': 'CAMK-Like, Checkpoint Kinase 1',
  'CAMK_CAMKL-LKB': 'CAMK-Like, Liver Kinase B1',
  'CAMK_CDPK': 'Calcium-Dependent Protein Kinases',
  'CAMK_OST1L': 'Open Stomata-like Kinase',
  'CK1_CK1': 'Cell Kinase 1',
  'CK1_CK1-Pl': 'Cell Kinase 1, Plant-specific',
  'CMGC_CDK-CCRK': 'Cyclin Dependent Kinase, Cell Cycle Regulated Kinase',
  'CMGC_CDK-CDK7': 'Cyclin Dependent Kinase subfamily 7',
  'CMGC_CDK-CDK8': 'Cyclin Dependent Kinase subfamily 8',
  'CMGC_CDK-CRK7-CDK9': 'Cyclin Dependent Kinase, cdc2-related kinase 7 / Cyclin-dependent kinase 9',
  'CMGC_CDK-PITSLRE': 'Cyclin Dependent Kinase, PITSLRE',
  'CMGC_CDK-Pl': 'Cyclin Dependent Kinase, Plant-specific',
  'CMGC_CDKL-Cr': 'Cyclin Dependent Kinase Like, C. reinhardtii-specific',
  'CMGC_CK2': 'Cell Kinase 2',
  'CMGC_CLK': 'CDC-Like Kinase (splicing)',
  'CMGC_DYRK-PRP4': 'Dual-specificity Y Regulated Kinase, precursor mRNA processing 4',
  'CMGC_DYRK-YAK': 'Dual-specificity Y Regulated Kinase, YAK subfamily',
  'CMGC_GSK': 'Glycogen Synthase 3 Kinase',
  'CMGC_GSKL': 'Glycogen Synthase 3 Kinase-like',
  'CMGC_MAPK': 'Mitogen Activated Protein Kinase',
  'CMGC_Pl-Tthe': 'CMGC shared between land plants and T. thermophila',
  'CMGC_RCK': 'Ros Cross-hybridizing Kinase',
  'CMGC_SRPK': 'SR Protein Kinase (phosphorylates SR splicing factors)',
  'STE_STE-Pl': 'STE Plant-specific',
  'STE_STE11': 'MAP3K (MAP kinase kinase kinase), homologous to yeast Ste11',
  'STE_STE20-Fray': 'MAP4K, homologous to yeast Ste20, Fray',
  'STE_STE20-Pl': 'MAP4K, homologous to yeast Ste20, Plant-specific',
  'STE_STE20-YSK': 'MAP4K, yeast SPS1/STE20-like kinase',
  'STE_STE7': 'MAP2K (MAP kinase kinase), homologous to yeast Ste7',
  'TKL-Pl-1': 'Plant-specific 1',
  'TKL-Pl-2': 'Plant-specific 2',
  'TKL-Pl-3': 'Plant-specific 3',
  'TKL-Pl-4': 'Plant-specific 4',
  'TKL-Pl-5': 'Plant-specific 5',
  'TKL-Pl-6': 'Plant-specific 6',
  'TKL-Pl-7': 'Plant-specific 7',
  'TKL_CTR1-DRK-1': 'CTR1-DRK-1',
  'TKL_CTR1-DRK-2': 'CTR1-DRK-2',
  'TKL_Gdt': 'Growth-Differentiation Transition',
  'PEK_GCN2': 'Pancreatic eIF2alpha kinase, General Control Non-derepressible',
  'PEK_PEK': 'Pancreatic eIF2alpha kinase',
  'SCY1_SCYL1': 'SCY1-like 1',
  'SCY1_SCYL2': 'SCY1-like 2',
  'Aur': 'Aurora kinases',
  'BUB': 'Mitotic checkpoint kinase BUB1',
  'IRE1': 'Inositol Requiring / ERN (ER-to-nucleus signaling)',
  'NAK': 'Numb-Associated Kinase',
  'NEK': 'NimA-Related Kinase (NRK)',
  'TLK': 'Tousled-like kinase',
  'TTK': 'TTK',
  'ULK_Fused': 'Unc-51 Like Kinase, Fused',
  'ULK_ULK4': 'Unc-51 Like Kinase 4',
  'WEE': 'WEE',
  'WNK_NRBP': 'With No Lysine (K) kinases / nuclear receptor binding protein',
  'Group-Pl-2': 'Group Plant-specific 2',
  'Group-Pl-3': 'Group Plant-specific 3',
  'Group-Pl-4': 'Group Plant-specific 4',
};

function pkDesc(fam: string): string {
  return PK_DESCRIPTIONS[fam] || '';
}

// Categorize families
const tfFamilies = computed(() => allFamilies.value.filter(f => TF_FAMILIES.has(f)));
const trFamilies = computed(() => allFamilies.value.filter(f => TR_FAMILIES.has(f)));

const pkFamilies = computed(() => {
  return allFamilies.value.filter(f => !TF_FAMILIES.has(f) && !TR_FAMILIES.has(f) && isPkFamily(f));
});

// PK tree: group by canonical group, ordered by PK_GROUP_ORDER
const pkGroups = computed(() => {
  const groups: Record<string, string[]> = {};
  for (const f of pkFamilies.value) {
    const g = pkGroup(f);
    if (!groups[g]) groups[g] = [];
    groups[g].push(f);
  }
  // Sort members within each group
  for (const g of Object.keys(groups)) groups[g].sort();
  // Order groups by canonical order
  return PK_GROUP_ORDER.filter(g => groups[g]).map(g => [g, groups[g]]);
});

// Expand / Collapse all PK groups
function expandAllPk() {
  pkExpanded.value = pkGroups.value.map(([g]) => g as string);
}
function collapseAllPk() {
  pkExpanded.value = [];
}

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

// ── Gene set selection ──
const tableRef = ref<any>(null);
const selectedGenes = ref<any[]>([]);
const showGeneSetDialog = ref(false);
const geneSetName = ref('');

function handleSelectionChange(rows: any[]) { selectedGenes.value = rows; }
function selectAll() { if (tableRef.value) tableRef.value.toggleAllSelection(); }
function deselectAll() { if (tableRef.value) tableRef.value.clearSelection(); }
function openGeneSetDialog() { geneSetName.value = ''; showGeneSetDialog.value = true; }

function saveGeneSet() {
  if (!geneSetName.value.trim() || selectedGenes.value.length === 0) return;
  try {
    const sets = JSON.parse(localStorage.getItem('fan_gene_sets') || '[]');
    const genes = selectedGenes.value.map((r: any) => ({
      gene_id: r.gene_id || '',
      canonical_transcript: r.canonical_transcript || r.gene_id || '',
    }));
    const detailData = detail?.value;
    sets.unshift({
      id: crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2),
      name: geneSetName.value.trim(),
      genes,
      genomeId: detailData?.id || 0,
      genomeTitle: detailData?.title || detailData?.dataset_code || '',
      createdAt: Math.floor(Date.now() / 1000),
    });
    if (sets.length > 20) sets.length = 20;
    localStorage.setItem('fan_gene_sets', JSON.stringify(sets));
    showGeneSetDialog.value = false;
    ElMessage.success(`Gene set "${geneSetName.value}" saved (${genes.length} genes)`);
  } catch { /* ignore */ }
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
          {{ fam }}
        </el-tag>
      </div>
    </template>

    <!-- PK: tree with descriptions -->
    <template v-if="activeTab === 'PK'">
      <div style="display:flex;gap:8px;margin-bottom:12px;">
        <el-button size="small" text @click="expandAllPk">Expand All</el-button>
        <el-button size="small" text @click="collapseAllPk">Collapse All</el-button>
      </div>
      <div style="margin-bottom:20px;">
        <el-collapse v-model="pkExpanded">
          <el-collapse-item v-for="[group, members] in pkGroups" :key="group" :name="group">
            <template #title>
              <span style="font-weight:600;">{{ group }}</span>
              <span style="color:#909399;margin-left:8px;">({{ members.length }})</span>
            </template>
            <div style="font-size:13px;line-height:2;">
              <div v-for="fam in members" :key="fam"
                style="padding:2px 0;cursor:pointer;"
                :style="{ color: selectedFamily === fam ? '#409eff' : '#303133', fontWeight: selectedFamily === fam ? '600' : '400' }"
                @click="selectFamily(fam)">
                {{ fam }}
                <span v-if="pkDesc(fam)" style="color:#909399;font-size:12px;"> — {{ pkDesc(fam) }}</span>
              </div>
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
        <span v-if="pkDesc(selectedFamily)" style="color:#909399;font-size:12px;">— {{ pkDesc(selectedFamily) }}</span>
        <span style="color:#888;font-size:12px;">{{ geneTotal }} genes</span>
      </div>

      <div v-if="geneList.length > 0" style="margin-bottom:8px;display:flex;gap:8px;align-items:center;">
        <el-button size="small" @click="selectAll">Select All</el-button>
        <el-button size="small" @click="deselectAll">Clear</el-button>
        <el-button v-if="selectedGenes.length > 0" type="success" size="small" @click="openGeneSetDialog">
          Save as Gene Set ({{ selectedGenes.length }} genes)
        </el-button>
      </div>

      <el-table ref="tableRef" :data="geneList" size="small" border stripe v-loading="queryLoading" v-if="geneList.length > 0" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="40" />
        <el-table-column prop="gene_id" label="Gene ID" width="180">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="goToGene(row.gene_id)">{{ row.gene_id }}</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="chrom" label="Chr" width="100" />
        <el-table-column prop="start" label="Start" width="100" />
        <el-table-column prop="stop" label="End" width="100" />
        <el-table-column prop="strand" label="Strand" width="70" />
        <el-table-column prop="canonical_transcript" label="Canonical Transcript" width="180" show-overflow-tooltip />
        <el-table-column prop="description" label="Description" min-width="200" show-overflow-tooltip />
      </el-table>

      <el-empty v-else-if="!queryLoading" description="No genes found" />

      <div v-if="geneTotal > 20" style="margin-top:12px;text-align:right;">
        <el-pagination v-model:current-page="genePage" :page-size="20" :total="geneTotal" layout="prev, pager, next" small @current-change="onGenePageChange" />
      </div>
    </template>

    <el-dialog v-model="showGeneSetDialog" title="Save Gene Set" width="400px">
      <el-input v-model="geneSetName" placeholder="Gene set name..." maxlength="100" />
      <p style="color:#888;font-size:12px;margin-top:4px;">{{ selectedGenes.length }} genes will be saved</p>
      <template #footer>
        <el-button @click="showGeneSetDialog = false">Cancel</el-button>
        <el-button type="primary" @click="saveGeneSet" :disabled="!geneSetName.trim()">Save</el-button>
      </template>
    </el-dialog>
  </div>
</template>
