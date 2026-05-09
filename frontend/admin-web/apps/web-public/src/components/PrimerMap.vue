<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { createPrimerMap, updatePrimerMap, destroyPrimerMap } from '@/visuals/primer-map';
import { getCollapsed, setCollapsed } from '@/visuals/blast-helpers';

const props = defineProps<{ data: { templateLength: number; templateSeq: string; pairs: any[] } }>();

const container = ref<HTMLElement>();
const collapsed = ref(getCollapsed('primer-map'));

function toggle() {
  collapsed.value = !collapsed.value;
  setCollapsed('primer-map', collapsed.value);
}

onMounted(() => {
  if (container.value && !collapsed.value) createPrimerMap(container.value, props.data);
});

onUnmounted(() => {
  if (container.value) destroyPrimerMap(container.value);
});

watch(() => props.data, (d) => {
  if (container.value && !collapsed.value) updatePrimerMap(container.value, d);
}, { deep: true });

watch(collapsed, (c) => {
  if (container.value) {
    if (c) destroyPrimerMap(container.value);
    else createPrimerMap(container.value, props.data);
  }
});
</script>

<template>
  <div class="blast-viz-section">
    <div class="blast-viz-header" @click="toggle" style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 0;font-weight:600;font-size:13px;user-select:none;">
      <span>{{ collapsed ? '▶' : '▼' }} Primer Map</span>
      <span style="font-weight:400;color:#999;font-size:11px;">{{ data.pairs?.length || 0 }} pairs</span>
    </div>
    <div v-show="!collapsed" ref="container" class="blast-viz-body"></div>
  </div>
</template>
