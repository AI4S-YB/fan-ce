<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { createGrnaTrack, updateGrnaTrack, destroyGrnaTrack } from '@/visuals/grna-track';
import { getCollapsed, setCollapsed } from '@/visuals/blast-helpers';

const props = defineProps<{ data: { targetLength: number; sites: any[] } }>();

const container = ref<HTMLElement>();
const collapsed = ref(getCollapsed('grna-track'));

function toggle() {
  collapsed.value = !collapsed.value;
  setCollapsed('grna-track', collapsed.value);
}

onMounted(() => {
  if (container.value && !collapsed.value) createGrnaTrack(container.value, props.data);
});

onUnmounted(() => {
  if (container.value) destroyGrnaTrack(container.value);
});

watch(() => props.data, (d) => {
  if (container.value && !collapsed.value) updateGrnaTrack(container.value, d);
}, { deep: true });

watch(collapsed, (c) => {
  if (container.value) {
    if (c) destroyGrnaTrack(container.value);
    else createGrnaTrack(container.value, props.data);
  }
});
</script>

<template>
  <div class="blast-viz-section">
    <div class="blast-viz-header" @click="toggle" style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 0;font-weight:600;font-size:13px;user-select:none;">
      <span>{{ collapsed ? '▶' : '▼' }} gRNA Target Sites</span>
      <span style="font-weight:400;color:#999;font-size:11px;">{{ data.sites?.length || 0 }} sites</span>
    </div>
    <div v-show="!collapsed" ref="container" class="blast-viz-body"></div>
  </div>
</template>
