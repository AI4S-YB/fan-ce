<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { createElement } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MSAViewer } from 'react-msa-viewer';
import { getCollapsed, setCollapsed } from '@/visuals/blast-helpers';

const props = defineProps<{ data: any }>();

const container = ref<HTMLElement>();
const collapsed = ref(getCollapsed('msa-viewer'));
let root: Root | null = null;
let rendered = false;

function toggle() { collapsed.value = !collapsed.value; setCollapsed('msa-viewer', collapsed.value); }

function render() {
  if (!container.value || rendered) return;
  const text = props.data?.content || (typeof props.data === 'string' ? props.data : '');
  if (!text) return;
  rendered = true;

  // Parse FASTA sequences
  const seqs: { name: string; sequence: string }[] = [];
  let current: { name: string; sequence: string } | null = null;
  for (const line of text.split('\n')) {
    const t = line.trim();
    if (!t) continue;
    if (t.startsWith('>')) { current = { name: t.slice(1).split(' ')[0], sequence: '' }; seqs.push(current); }
    else if (current) { current.sequence += t.replace(/\s/g, '').toUpperCase(); }
  }
  if (seqs.length === 0) return;

  // Clean up previous root
  if (root) { root.unmount(); root = null; }

  try {
    const el = createElement(MSAViewer, {
      sequences: seqs,
      height: Math.min(600, seqs.length * 20 + 100),
    });
    root = createRoot(container.value);
    root.render(el);
  } catch (e) {
    console.warn('MSAViewer render failed:', e);
    rendered = false;
  }
}

onMounted(render);
onUnmounted(() => { if (root) { root.unmount(); root = null; } });
watch(() => props.data, () => { rendered = false; render(); });
watch(collapsed, (c) => { if (!c && container.value) { rendered = false; render(); } });
</script>

<template>
  <div class="blast-viz-section">
    <div class="blast-viz-header" @click="toggle" style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 0;font-weight:600;font-size:13px;user-select:none;">
      <span>{{ collapsed ? '▶' : '▼' }} Multiple Sequence Alignment</span>
    </div>
    <div v-show="!collapsed" ref="container" class="blast-viz-body" style="overflow-x:auto;" />
  </div>
</template>
