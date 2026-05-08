<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { createLengthDist, updateLengthDist, destroyLengthDist } from '@/visuals/blast-length-distribution';
import { getCollapsed, setCollapsed } from '@/visuals/blast-helpers';

const props = defineProps<{ data: { name: string; length: number; type: string; hits: any[] } }>();

const container = ref<HTMLElement>();
const collapsed = ref(getCollapsed('length-dist'));

function toggle() {
  collapsed.value = !collapsed.value;
  setCollapsed('length-dist', collapsed.value);
}

onMounted(() => {
  if (container.value && !collapsed.value) createLengthDist(container.value, props.data);
});

onUnmounted(() => {
  if (container.value) destroyLengthDist(container.value);
});

watch(() => props.data, (d) => {
  if (container.value && !collapsed.value) updateLengthDist(container.value, d);
}, { deep: true });

watch(collapsed, (c) => {
  if (container.value) {
    if (c) destroyLengthDist(container.value);
    else createLengthDist(container.value, props.data);
  }
});
</script>

<template>
  <div class="blast-viz-section">
    <div class="blast-viz-header" @click="toggle" style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 0;font-weight:600;font-size:13px;user-select:none;">
      <span>{{ collapsed ? '▶' : '▼' }} Length Distribution — {{ data.name }}</span>
      <span style="font-weight:400;color:#999;font-size:11px;">{{ data.hits?.length || 0 }} hits</span>
    </div>
    <div v-show="!collapsed" ref="container" class="blast-viz-body"></div>
  </div>
</template>
