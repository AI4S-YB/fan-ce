<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { createKablammo, updateKablammo, destroyKablammo } from '@/visuals/blast-kablammo';
import { getCollapsed, setCollapsed } from '@/visuals/blast-helpers';

const props = defineProps<{ data: { id: string; length: number; hsps: any[] }; seqType?: string }>();
const emit = defineEmits<{ (e: 'hsp-click', hsp: any, index: number): void }>();

const container = ref<HTMLElement>();
const collapsed = ref(getCollapsed('kablammo'));
const opts = computed(() => ({ onHspClick: (hsp: any, idx: number) => emit('hsp-click', hsp, idx), seqType: props.seqType }));

function toggle() {
  collapsed.value = !collapsed.value;
  setCollapsed('kablammo', collapsed.value);
}

onMounted(() => {
  if (container.value && !collapsed.value) createKablammo(container.value, props.data, opts.value);
});

onUnmounted(() => {
  if (container.value) destroyKablammo(container.value);
});

watch(() => props.data, (d) => {
  if (container.value && !collapsed.value) updateKablammo(container.value, d, opts.value);
}, { deep: true });

watch(collapsed, (c) => {
  if (container.value) {
    if (c) destroyKablammo(container.value);
    else createKablammo(container.value, props.data, opts.value);
  }
});
</script>

<template>
  <div class="blast-viz-section">
    <div class="blast-viz-header" @click="toggle" style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 0;font-weight:600;font-size:13px;user-select:none;">
      <span>{{ collapsed ? '▶' : '▼' }} Pairwise Alignment — {{ data.id }}</span>
    </div>
    <div v-show="!collapsed" ref="container" class="blast-viz-body" style="height:170px;"></div>
  </div>
</template>
