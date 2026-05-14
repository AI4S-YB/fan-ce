<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

const props = defineProps<{
  currentDatasetId?: number;
  currentDatasetTitle?: string;
}>();

const emit = defineEmits<{
  (e: 'use', ids: string[], genomeId: number): void;
}>();

const GENE_SETS_KEY = 'fan_gene_sets';
const geneSets = ref<any[]>([]);

function loadGeneSets() {
  try {
    const raw = JSON.parse(localStorage.getItem(GENE_SETS_KEY) || '[]');
    const cutoff = Math.floor(Date.now() / 1000) - 30 * 24 * 3600;
    geneSets.value = raw.filter((s: any) => s.createdAt > cutoff);
  } catch { geneSets.value = []; }
}

function deleteGeneSet(id: string) {
  geneSets.value = geneSets.value.filter((s: any) => s.id !== id);
  localStorage.setItem(GENE_SETS_KEY, JSON.stringify(geneSets.value));
}

function useGeneSet(gs: any) {
  const items = gs.genes || [];
  const isOld = typeof items[0] === 'string';
  const ids: string[] = isOld
    ? items
    : items.map((g: any) => g.gene_id || '');
  emit('use', ids, gs.genomeId || 0);
}

const displayedSets = computed(() => {
  return geneSets.value.map(gs => ({
    ...gs,
    compatible: !props.currentDatasetId || gs.genomeId === props.currentDatasetId,
  }));
});

onMounted(loadGeneSets);
</script>

<template>
  <div v-if="displayedSets.length > 0" style="margin-bottom:12px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;padding:8px 12px;">
    <div style="font-size:12px;font-weight:600;color:#166534;margin-bottom:6px;">Gene Sets</div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;">
      <div v-for="gs in displayedSets" :key="gs.id"
        :title="gs.compatible ? '' : 'From ' + (gs.genomeTitle || 'another genome') + ' — not compatible with ' + (currentDatasetTitle || 'current dataset')"
        style="display:flex;align-items:center;gap:4px;padding:3px 8px;border-radius:3px;font-size:11px;border:1px solid #ddd;background:#fff;"
        :style="{ opacity: gs.compatible ? 1 : 0.4, cursor: gs.compatible ? 'pointer' : 'not-allowed' }">
        <span v-if="gs.compatible" @click="useGeneSet(gs)" style="font-weight:500;">{{ gs.name }}</span>
        <span v-else style="font-weight:500;">{{ gs.name }}</span>
        <span v-if="gs.compatible" @click="useGeneSet(gs)" style="color:#888;">({{ gs.genes?.length || 0 }})</span>
        <span v-else style="color:#aaa;">({{ gs.genes?.length || 0 }})</span>
        <span @click.stop="deleteGeneSet(gs.id)" style="color:#ccc;cursor:pointer;font-size:12px;">×</span>
      </div>
    </div>
  </div>
</template>
