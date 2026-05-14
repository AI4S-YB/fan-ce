<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import * as d3 from 'd3';
import { getCollapsed, setCollapsed } from '@/visuals/blast-helpers';

const props = defineProps<{ data: any }>();

const container = ref<HTMLElement>();
const collapsed = ref(getCollapsed('tree-viewer'));
let rendered = false;

function toggle() { collapsed.value = !collapsed.value; setCollapsed('tree-viewer', collapsed.value); }

function parseNewick(s: string): any {
  let i = 0;
  const text = s.trim().replace(/\s/g, '');
  function parse(): any {
    const children: any[] = [];
    let name = '';
    let length: number | null = null;
    if (text[i] === '(') {
      i++;
      while (text[i] !== ')') { children.push(parse()); if (text[i] === ',') i++; }
      i++;
    }
    while (i < text.length && !':,);'.includes(text[i])) { name += text[i]; i++; }
    if (text[i] === ':') { i++; let s = ''; while (i < text.length && !',);'.includes(text[i])) { s += text[i]; i++; } length = parseFloat(s) || null; }
    if (text[i] === ';') i++;
    return { name: name || null, length, children: children.length ? children : null };
  }
  return text.startsWith('(') ? parse() : null;
}

function render() {
  if (!container.value || rendered) return;
  const text = props.data?.content || (typeof props.data === 'string' ? props.data : '');
  if (!text?.trim().startsWith('(')) return;
  rendered = true;

  const el = container.value;
  el.innerHTML = '';
  const rootData = parseNewick(text);
  if (!rootData) { el.innerHTML = '<div style="padding:20px;color:#999;text-align:center;">Invalid Newick format</div>'; rendered = false; return; }

  const root = d3.hierarchy(rootData, d => d.children || null);
  const leaves = root.leaves();
  const leafH = 22;
  const labelMaxLen = d3.max(leaves, (d: any) => (d.data.name || '').length) || 10;
  const labelArea = labelMaxLen * 8 + 40;
  const h = Math.max(200, leaves.length * leafH + 40);
  const w = Math.max(el.clientWidth || 600, h + labelArea);

  const svg = d3.select(el).append('svg').attr('width', w).attr('height', h).style('font-family', 'sans-serif');
  const g = svg.append('g').attr('transform', 'translate(20,20)');

  const treeLayout = d3.cluster().size([h - 40, w - labelArea - 20]);
  treeLayout(root);

  // Links
  g.selectAll('path').data(root.links()).enter().append('path')
    .attr('d', (d: any) => `M${d.source.y},${d.source.x}C${d.source.y + 50},${d.source.x} ${d.target.y - 50},${d.target.x} ${d.target.y},${d.target.x}`)
    .attr('fill', 'none').attr('stroke', '#bbb').attr('stroke-width', 1.5);

  // Internal nodes
  g.selectAll('.inode').data(root.descendants().filter((d: any) => d.children)).enter()
    .append('circle').attr('cx', (d: any) => d.y).attr('cy', (d: any) => d.x).attr('r', 2.5).attr('fill', '#888');

  // Leaf nodes + labels
  const leafG = g.selectAll('.leaf').data(leaves).enter().append('g');
  leafG.append('circle').attr('cx', (d: any) => d.y).attr('cy', (d: any) => d.x).attr('r', 3.5).attr('fill', '#409eff');
  leafG.append('text').attr('x', (d: any) => d.y + 8).attr('y', (d: any) => d.x + 4)
    .style('font-size', '11px').style('fill', '#333')
    .text((d: any) => d.data.name || '');
}

onMounted(() => { if (!collapsed.value) nextTick(render); });
onUnmounted(() => { rendered = false; });
watch(() => props.data, () => { rendered = false; if (!collapsed.value) nextTick(render); });
watch(collapsed, (c) => { if (!c && container.value) { rendered = false; nextTick(render); } });
</script>

<template>
  <div class="blast-viz-section">
    <div class="blast-viz-header" @click="toggle" style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 0;font-weight:600;font-size:13px;user-select:none;">
      <span>{{ collapsed ? '▶' : '▼' }} Phylogenetic Tree</span>
    </div>
    <div v-show="!collapsed" ref="container" class="blast-viz-body" style="overflow-x:auto;" />
  </div>
</template>
