<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { createTreeViewer, updateTreeViewer, destroyTreeViewer } from '@/visuals/tree-viewer';
import { getCollapsed, setCollapsed } from '@/visuals/blast-helpers';

const props = defineProps<{ data: any }>();
const container = ref<HTMLElement>();
const collapsed = ref(getCollapsed('tree-viewer'));

function toggle() { collapsed.value = !collapsed.value; setCollapsed('tree-viewer', collapsed.value); }
onMounted(() => { if (container.value && !collapsed.value) createTreeViewer(container.value, props.data); });
onUnmounted(() => { if (container.value) destroyTreeViewer(container.value); });
watch(() => props.data, (d) => { if (container.value && !collapsed.value) updateTreeViewer(container.value, d); }, { deep: true });
watch(collapsed, (c) => { if (container.value) { if (c) destroyTreeViewer(container.value); else createTreeViewer(container.value, props.data); } });
</script>
<template>
  <div class="blast-viz-section">
    <div class="blast-viz-header" @click="toggle" style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 0;font-weight:600;font-size:13px;user-select:none;">
      <span>{{ collapsed ? '▶' : '▼' }} Phylogenetic Tree</span>
    </div>
    <div v-show="!collapsed" ref="container" class="blast-viz-body"></div>
  </div>
</template>
