// visuals/blast-kablammo.js — Pairwise alignment polygon view (per hit)
import * as d3 from 'd3';
import { formatTick, debounce } from './blast-helpers';

const MARGIN = { top: 20, right: 20, bottom: 30, left: 60 };
const HEIGHT = 150;

export function createKablammo(container, data, _options) {
  render(container, data);

  const onResize = debounce(() => render(container, data), 200);
  window.addEventListener('resize', onResize);
  container._kabResize = onResize;
}

export function updateKablammo(container, data, _options) {
  render(container, data);
}

export function destroyKablammo(container) {
  if (container._kabResize) {
    window.removeEventListener('resize', container._kabResize);
  }
  container.innerHTML = '';
}

function render(container, data) {
  container.innerHTML = '';

  const { id: hitId, length: sLen, hsps } = data;
  if (!hsps || hsps.length === 0) return;

  const qLen = Math.max(...hsps.map(h => h.qEnd), 0);
  const subjectLen = sLen || Math.max(...hsps.map(h => h.sEnd), 0);
  const maxBitScore = Math.max(...hsps.map(h => h.bitScore || 0), 1);

  const innerH = HEIGHT - MARGIN.top - MARGIN.bottom;

  const svg = d3.select(container).append('svg')
    .attr('width', '100%')
    .attr('viewBox', `0 0 ${800} ${HEIGHT}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .style('font-family', 'sans-serif')
    .style('font-size', '10px');

  const g = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);

  const width = 800 - MARGIN.left - MARGIN.right;

  // Query axis (top)
  const xQ = d3.scaleLinear().domain([0, qLen]).range([0, width]);
  g.append('g').call(d3.axisTop(xQ).tickFormat(d => formatTick(d, 'amino_acid')).ticks(5))
    .selectAll('text').style('font-size', '9px');

  // Subject axis (bottom)
  const xS = d3.scaleLinear().domain([0, subjectLen]).range([0, width]);
  g.append('g').attr('transform', `translate(0,${innerH})`)
    .call(d3.axisBottom(xS).tickFormat(d => formatTick(d, 'amino_acid')).ticks(5))
    .selectAll('text').style('font-size', '9px');

  // Labels
  g.append('text').attr('x', -50).attr('y', -8).style('font-size', '10px').style('font-weight', '600').text('Query');
  g.append('text').attr('x', -50).attr('y', innerH + 20).style('font-size', '10px').style('font-weight', '600').text(hitId);

  // Draw HSP polygons (top-to-bottom trapezoids)
  for (const hsp of hsps) {
    const opacity = (hsp.bitScore || 0) / maxBitScore;
    const points = [
      [xQ(hsp.qStart), 0],
      [xQ(hsp.qEnd), 0],
      [xS(hsp.sEnd), innerH],
      [xS(hsp.sStart), innerH],
    ];

    g.append('polygon')
      .attr('points', points.map(p => p.join(',')).join(' '))
      .attr('fill', `rgba(199, 79, 20, ${Math.max(0.1, opacity * 0.7)})`)
      .attr('stroke', 'rgba(199, 79, 20, 0.5)')
      .attr('stroke-width', 0.5)
      .on('mouseenter', function () {
        d3.select(this).raise().attr('stroke-width', 1.5);
      })
      .on('mouseleave', function () {
        d3.select(this).attr('stroke-width', 0.5);
      })
      .append('title')
      .text(`Q: ${hsp.qStart}-${hsp.qEnd} | S: ${hsp.sStart}-${hsp.sEnd} | Score: ${hsp.bitScore}`);
  }
}
