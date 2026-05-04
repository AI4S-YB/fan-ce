<script setup lang="ts">
import { ref, inject, computed, type Ref } from 'vue';
import type { PublicDatasetDetail } from '@/types/dataset';

const detail = inject<Ref<PublicDatasetDetail | null>>('genomeDetail');

const familySearch = ref('');

const tfFamilies = [
  'bHLH', 'MYB', 'WRKY', 'NAC', 'bZIP', 'ERF', 'C2H2', 'GRAS',
  'MADS', 'TCP', 'HSF', 'NF-Y', 'LOB', 'GATA', 'SBP', 'ARF',
];
const selectedFamily = ref('');

const tfMembers = computed(() => {
  const fam = selectedFamily.value;
  if (!fam) return [];
  return [
    { gene_id: `${fam}_001`, family: fam, description: `${fam} transcription factor` },
    { gene_id: `${fam}_002`, family: fam, description: `${fam} transcription factor` },
  ];
});

function selectFamily(fam: string) { selectedFamily.value = fam; }
</script>

<template>
  <div style="display:flex;gap:20px;">
    <!-- Family list -->
    <div style="width:200px;flex-shrink:0;">
      <h4 style="margin:0 0 8px;">TF Families</h4>
      <el-input v-model="familySearch" placeholder="Filter..." size="small" style="margin-bottom:8px;" clearable />
      <div style="max-height:500px;overflow-y:auto;border:1px solid #e5e5e5;border-radius:4px;">
        <div
          v-for="fam in tfFamilies"
          :key="fam"
          @click="selectFamily(fam)"
          :style="{
            padding:'8px 12px',cursor:'pointer',fontSize:'13px',
            background: selectedFamily === fam ? '#ecf5ff' : '#fff',
            color: selectedFamily === fam ? '#409eff' : '#606266',
            borderBottom:'1px solid #f0f0f0',
          }"
        >
          {{ fam }}
        </div>
      </div>
    </div>

    <!-- Member table -->
    <div style="flex:1;">
      <h4 style="margin:0 0 8px;">
        {{ selectedFamily ? `${selectedFamily} Members (${tfMembers.length})` : 'Select a family' }}
      </h4>
      <el-table :data="tfMembers" border size="small" v-if="selectedFamily" empty-text="No TF data available">
        <el-table-column prop="gene_id" label="Gene ID" width="160" />
        <el-table-column prop="family" label="Family" width="120" />
        <el-table-column prop="description" label="Description" />
      </el-table>
      <el-empty v-else description="Select a TF family from the left panel" />
    </div>
  </div>
</template>

<script lang="ts">
const familySearch = ref('');
</script>
