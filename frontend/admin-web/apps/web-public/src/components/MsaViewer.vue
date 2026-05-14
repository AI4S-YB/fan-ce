<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { createMsaViewer, updateMsaViewer, destroyMsaViewer } from '@/visuals/msa-viewer';
import { getCollapsed, setCollapsed } from '@/visuals/blast-helpers';

const props = defineProps<{ data: any }>();
const container = ref<HTMLElement>();
const collapsed = ref(getCollapsed('msa-viewer'));

function toggle() { collapsed.value = !collapsed.value; setCollapsed('msa-viewer', collapsed.value); }
onMounted(() => { if (container.value && !collapsed.value) createMsaViewer(container.value, props.data); });
onUnmounted(() => { if (container.value) destroyMsaViewer(container.value); });
watch(() => props.data, (d) => { if (container.value && !collapsed.value) updateMsaViewer(container.value, d); }, { deep: true });
watch(collapsed, (c) => { if (container.value) { if (c) destroyMsaViewer(container.value); else createMsaViewer(container.value, props.data); } });
</script>

<template>
  <div class="blast-viz-section">
    <div class="blast-viz-header" @click="toggle" style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 0;font-weight:600;font-size:13px;user-select:none;">
      <span>{{ collapsed ? '▶' : '▼' }} Multiple Sequence Alignment</span>
    </div>
    <div v-show="!collapsed" ref="container" class="blast-viz-body" />
  </div>
</template>
