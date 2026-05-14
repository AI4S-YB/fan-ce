<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { createHitsOverview, updateHitsOverview, destroyHitsOverview } from '@/visuals/blast-hits-overview';
import { getCollapsed, setCollapsed } from '@/visuals/blast-helpers';

const props = defineProps<{ data: { name: string; length: number; type: string; hits: any[] } }>();
const emit = defineEmits<{ (e: 'hit-click', hit: any): void }>();

const container = ref<HTMLElement>();
const collapsed = ref(getCollapsed('hits-overview'));
const opts = { onHitClick: (hit: any) => emit('hit-click', hit) };

function toggle() {
  collapsed.value = !collapsed.value;
  setCollapsed('hits-overview', collapsed.value);
}

onMounted(() => {
  if (container.value && !collapsed.value) {
    createHitsOverview(container.value, props.data, opts);
  }
});

onUnmounted(() => {
  if (container.value) destroyHitsOverview(container.value);
});

watch(() => props.data, (d) => {
  if (container.value && !collapsed.value) updateHitsOverview(container.value, d, opts);
}, { deep: true });

watch(collapsed, (c) => {
  if (container.value) {
    if (c) destroyHitsOverview(container.value);
    else createHitsOverview(container.value, props.data, opts);
  }
});
</script>

<template>
  <div class="blast-viz-section">
    <div class="blast-viz-header" @click="toggle" style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 0;font-weight:600;font-size:13px;user-select:none;">
      <span>{{ collapsed ? '▶' : '▼' }} HSP Coverage Map — {{ data.name }}</span>
      <span style="font-weight:400;color:#999;font-size:11px;">{{ data.hits?.length || 0 }} hits</span>
    </div>
    <div v-show="!collapsed" ref="container" class="blast-viz-body"></div>
  </div>
</template>

<style scoped>
.blast-viz-body { overflow-x: auto; }
.blast-viz-body :deep(svg) { display: block; }
</style>
