<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { getCollapsed, setCollapsed } from '@/visuals/blast-helpers';

const props = defineProps<{ data: any }>();

const container = ref<HTMLElement>();
const collapsed = ref(getCollapsed('tree-viewer'));
let rendered = false;

function toggle() { collapsed.value = !collapsed.value; setCollapsed('tree-viewer', collapsed.value); }

async function render() {
  if (!container.value || rendered) return;
  const text = props.data?.content || (typeof props.data === 'string' ? props.data : '');
  if (!text || !text.trim().startsWith('(')) return;
  rendered = true;

  // Wait for DOM to settle (container is visible via v-show)
  await new Promise(r => requestAnimationFrame(r));

  const el = container.value;
  el.innerHTML = '';

  try {
    const { phylotree } = await import('phylotree');
    const tree = new phylotree(text.trim());
    const renderOptions: Record<string, any> = {
      container: '#' + (el.id || (el.id = 'tree-' + Date.now())),
      width: (el.clientWidth || 700) - 20,
      height: Math.max(200, (text.match(/,/g) || []).length * 18 + 60),
      'left-offset': 10,
    };
    tree.render(renderOptions);
  } catch (e) {
    console.warn('TreeViewer render failed:', e);
    el.innerHTML = '<div style="padding:20px;color:#999;text-align:center;">Tree visualization unavailable.</div>';
    rendered = false;
  }
}

onMounted(() => { if (!collapsed.value) render(); });
onUnmounted(() => { container.value && (container.value.innerHTML = ''); });
watch(() => props.data, () => { rendered = false; if (!collapsed.value) render(); });
watch(collapsed, (c) => { if (!c && container.value) { rendered = false; render(); } });
</script>

<template>
  <div class="blast-viz-section">
    <div class="blast-viz-header" @click="toggle" style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 0;font-weight:600;font-size:13px;user-select:none;">
      <span>{{ collapsed ? '▶' : '▼' }} Phylogenetic Tree</span>
    </div>
    <div v-show="!collapsed" ref="container" class="blast-viz-body" style="overflow-x:auto;" />
  </div>
</template>
