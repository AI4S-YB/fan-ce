// visuals/grna-track.js — gRNA target sites + PAM track on target sequence
import * as d3 from 'd3';
import { debounce } from './blast-helpers';

const MARGIN = { top: 20, right: 20, bottom: 30, left: 120 };

export function createGrnaTrack(container, data, _options) {
  render(container, data);
  const onResize = debounce(() => render(container, data), 200);
  window.addEventListener('resize', onResize);
  container._gtResize = onResize;
}

export function updateGrnaTrack(container, data, _options) {
  render(container, data);
}

export function destroyGrnaTrack(container) {
  if (container._gtResize) window.removeEventListener('resize', container._gtResize);
  container.innerHTML = '';
}

function render(container, data) {
  container.innerHTML = '';

  const { targetLength, sites } = data;
  if (!sites || sites.length === 0) {
    container.innerHTML = '<div style="padding:16px;color:#999;text-align:center;">No gRNA target sites found</div>';
    return;
  }

  const ROW_H = 20;
  const totalH = MARGIN.top + sites.length * ROW_H + MARGIN.bottom;

  const svg = d3.select(container).append('svg')
    .attr('width', '100%')
    .attr('viewBox', `0 0 ${800} ${totalH}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .style('font-family', 'sans-serif')
    .style('font-size', '10px');

  const g = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);
  const width = 800 - MARGIN.left - MARGIN.right;

  const x = d3.scaleLinear().domain([0, targetLength]).range([0, width]);

  // Target backbone line
  g.append('line')
    .attr('x1', 0).attr('x2', width)
    .attr('y1', -8).attr('y2', -8)
    .attr('stroke', '#aaa').attr('stroke-width', 2);

  g.append('text').attr('x', width / 2).attr('y', -14)
    .attr('text-anchor', 'middle').style('font-size', '9px').style('fill', '#888')
    .text(`Target (${targetLength} bp)`);

  // X axis at bottom
  const lastY = sites.length * ROW_H;
  g.append('g').attr('transform', `translate(0,${lastY})`)
    .call(d3.axisBottom(x).ticks(6))
    .selectAll('text').style('font-size', '9px');

  // Draw each gRNA site
  for (let i = 0; i < sites.length; i++) {
    const s = sites[i];
    const pos = +(s.Position || s.position || 0);
    const seq = s.gRNA_Sequence || s.sequence || '';
    const pam = s.PAM || s.pam || '';
    const gc = s.GC_Content || s.gc || '';
    const len = +(s.Length || s.length || 20);
    const y = i * ROW_H;

    // gRNA binding region (green)
    const gStart = pos;
    const gEnd = pos + len;
    g.append('rect')
      .attr('x', x(gStart)).attr('y', y + 2)
      .attr('width', Math.max(1, x(gEnd) - x(gStart)))
      .attr('height', ROW_H - 4)
      .attr('fill', '#67c23a').attr('opacity', 0.7).attr('rx', 2);

    // gRNA sequence label (truncated if needed)
    const label = seq.length > 18 ? seq.slice(0, 15) + '…' : seq;
    g.append('text')
      .attr('x', x(gStart) + 2).attr('y', y + ROW_H / 2 + 3)
      .style('font-size', '7px').style('fill', '#fff')
      .text(label);

    // PAM site (orange)
    const pamEnd = gEnd + pam.length;
    g.append('rect')
      .attr('x', x(gEnd)).attr('y', y + 4)
      .attr('width', Math.max(2, x(pamEnd) - x(gEnd)))
      .attr('height', ROW_H - 8)
      .attr('fill', '#e6a23c').attr('opacity', 0.85).attr('rx', 1);

    // PAM label
    g.append('text')
      .attr('x', x(gEnd) + 1).attr('y', y + ROW_H / 2 + 3)
      .style('font-size', '6px').style('fill', '#fff')
      .text(pam);

    // Position label on left
    g.append('text')
      .attr('x', -6).attr('y', y + ROW_H / 2 + 3)
      .attr('text-anchor', 'end').style('font-size', '9px').style('fill', '#666')
      .text(`${pos}`);

    // GC content on right
    g.append('text')
      .attr('x', width + 6).attr('y', y + ROW_H / 2 + 3)
      .attr('text-anchor', 'start').style('font-size', '8px').style('fill', '#888')
      .text(gc);
  }
}
