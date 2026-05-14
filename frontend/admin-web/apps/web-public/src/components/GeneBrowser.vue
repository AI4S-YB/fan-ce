<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue';
import * as d3 from 'd3';

const props = defineProps<{
  seqName: string;
  seq: string;
  start: number;
  stop: number;
  exons: any[];
  geneId: string;
}>();

const container = ref<HTMLElement>();

function render() {
  if (!container.value || !props.exons.length) return;
  const el = container.value;
  el.innerHTML = '';

  const strand = props.exons[0]?.strand === '-' ? -1 : 1;
  const geneLen = props.stop - props.start + 1;
  const pad = Math.max(100, geneLen * 0.3);
  const totalLen = geneLen + pad * 2;
  const margin = { top: 8, right: 30, bottom: 24, left: 30 };
  const w = Math.max(600, el.clientWidth - 10);
  const h = 130;

  const svg = d3.select(el).append('svg')
    .attr('width', w).attr('height', h)
    .attr('viewBox', `0 0 ${w} ${h}`)
    .style('font-family', '-apple-system, Helvetica Neue, Arial, sans-serif');

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);
  const plotW = w - margin.left - margin.right;
  const scaleX = (pos: number) => (pos - props.start + pad) / totalLen * plotW;

  const exonFeatures = props.exons.filter((e: any) => e.feature_type === 'exon');
  const cdsFeatures = props.exons.filter((e: any) => e.feature_type === 'CDS');
  const centerY = 55;

  // ── Gene body line (introns as thin lines, exons as thick bars) ──
  const sortedExons = [...exonFeatures].sort((a: any, b: any) => a.start - b.start);

  // Intron lines between exons
  for (let i = 0; i < sortedExons.length - 1; i++) {
    const curEnd = scaleX(sortedExons[i].stop);
    const nextStart = scaleX(sortedExons[i + 1].start);
    g.append('line')
      .attr('x1', curEnd).attr('x2', nextStart)
      .attr('y1', centerY).attr('y2', centerY)
      .attr('stroke', '#bbb').attr('stroke-width', 1.5);
    // Chevron mark in middle of intron
    const mid = (curEnd + nextStart) / 2;
    g.append('polyline')
      .attr('points', `${mid - 4},${centerY - 3} ${mid},${centerY} ${mid - 4},${centerY + 3}`)
      .attr('fill', 'none').attr('stroke', '#ccc').attr('stroke-width', 1);
  }

  // Exon boxes (tall, colored, rounded)
  const exonBoxes = g.selectAll('.exon-box').data(exonFeatures).enter();
  exonBoxes.append('rect')
    .attr('x', (d: any) => scaleX(d.start))
    .attr('y', centerY - 12)
    .attr('width', (d: any) => Math.max(4, scaleX(d.stop) - scaleX(d.start)))
    .attr('height', 24)
    .attr('fill', '#5b9bd5').attr('rx', 4);

  // CDS fill inside exon boxes (slightly darker)
  g.selectAll('.cds-fill').data(cdsFeatures).enter()
    .append('rect')
    .attr('x', (d: any) => scaleX(d.start) + 1)
    .attr('y', centerY - 10)
    .attr('width', (d: any) => Math.max(2, scaleX(d.stop) - scaleX(d.start) - 2))
    .attr('height', 20)
    .attr('fill', '#3b7fc4').attr('rx', 3);

  // Exon borders
  exonBoxes.append('rect')
    .attr('x', (d: any) => scaleX(d.start))
    .attr('y', centerY - 12)
    .attr('width', (d: any) => Math.max(4, scaleX(d.stop) - scaleX(d.start)))
    .attr('height', 24)
    .attr('fill', 'none').attr('stroke', '#3a6ea5').attr('stroke-width', 1).attr('rx', 4);

  // Strand arrow head at gene end
  const arrowX = strand > 0 ? scaleX(props.stop) + 6 : scaleX(props.start) - 6;
  const arrowDir = strand > 0 ? 1 : -1;
  g.append('polygon')
    .attr('points', `${arrowX},${centerY} ${arrowX - 8 * arrowDir},${centerY - 6} ${arrowX - 8 * arrowDir},${centerY + 6}`)
    .attr('fill', '#5b9bd5');

  // ── Gene name + strand ──
  g.append('text')
    .attr('x', plotW / 2).attr('y', 18)
    .attr('text-anchor', 'middle').style('font-size', '13px').style('font-weight', '600').style('fill', '#303133')
    .text(`${props.geneId}  (${geneLen.toLocaleString()} bp, ${strand > 0 ? '+' : '-'} strand)`);

  // ── Position ruler ──
  const rulerY = 82;
  g.append('line').attr('x1', 0).attr('x2', plotW).attr('y1', rulerY).attr('y2', rulerY)
    .attr('stroke', '#ddd').attr('stroke-width', 1);

  // Tick marks every ~200bp or 1/5 of gene length
  const tickInterval = geneLen > 1000 ? Math.ceil(geneLen / 500) * 100 : Math.ceil(geneLen / 5 / 100) * 100;
  for (let pos = Math.ceil(props.start / tickInterval) * tickInterval; pos <= props.stop; pos += tickInterval) {
    const tx = scaleX(pos);
    g.append('line').attr('x1', tx).attr('x2', tx).attr('y1', rulerY - 4).attr('y2', rulerY + 4)
      .attr('stroke', '#bbb').attr('stroke-width', 0.5);
    g.append('text').attr('x', tx).attr('y', rulerY + 16)
      .attr('text-anchor', 'middle').style('font-size', '9px').style('fill', '#999')
      .text(pos.toLocaleString());
  }

  // Scale bar
  const barY = 108;
  g.append('line').attr('x1', 0).attr('x2', plotW).attr('y1', barY).attr('y2', barY)
    .attr('stroke', '#ddd').attr('stroke-width', 1);

  // ── Legend ──
  g.append('rect').attr('x', 0).attr('y', barY + 4).attr('width', 12).attr('height', 8)
    .attr('fill', '#5b9bd5').attr('rx', 2);
  g.append('text').attr('x', 16).attr('y', barY + 12)
    .style('font-size', '10px').style('fill', '#888').text('Exon');
  g.append('rect').attr('x', 56).attr('y', barY + 4).attr('width', 12).attr('height', 8)
    .attr('fill', '#3b7fc4').attr('rx', 2);
  g.append('text').attr('x', 72).attr('y', barY + 12)
    .style('font-size', '10px').style('fill', '#888').text('CDS');
  g.append('line').attr('x1', 110).attr('x2', 125).attr('y1', barY + 8).attr('y2', barY + 8)
    .attr('stroke', '#bbb').attr('stroke-width', 1);
  g.append('text').attr('x', 130).attr('y', barY + 12)
    .style('font-size', '10px').style('fill', '#888').text('Intron');

  // Tooltips for exons
  exonBoxes.append('title').text((d: any) => `Exon: ${(d.start as number).toLocaleString()} – ${(d.stop as number).toLocaleString()} (${(d.stop - d.start + 1).toLocaleString()} bp)`);
}

onMounted(() => nextTick(render));
watch(() => props.exons, () => nextTick(render), { deep: true });
</script>

<template>
  <div ref="container" style="min-height:130px;width:100%;overflow-x:auto;" />
</template>
