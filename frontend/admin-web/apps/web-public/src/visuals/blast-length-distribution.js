// visuals/blast-length-distribution.js — Stacked histogram of hit lengths
import * as d3 from 'd3';
import { evalueToColor, formatTick, debounce } from './blast-helpers';

const MARGIN = { top: 10, right: 20, bottom: 30, left: 60 };
const HEIGHT = 180;

export function createLengthDist(container, data, _options) {
  render(container, data);

  const onResize = debounce(() => render(container, data), 200);
  window.addEventListener('resize', onResize);
  container._ldResize = onResize;
}

export function updateLengthDist(container, data, _options) {
  render(container, data);
}

export function destroyLengthDist(container) {
  if (container._ldResize) window.removeEventListener('resize', container._ldResize);
  container.innerHTML = '';
}

function render(container, data) {
  container.innerHTML = '';

  const { length: qLen, type: qType, hits } = data;
  if (!hits || hits.length === 0) return;

  const maxE = Math.max(...hits.flatMap(h => h.hsps.map(hsp => hsp.evalue || 1e-100)));
  const hitLengths = hits.map(h => h.length).filter(l => l > 0);

  if (hitLengths.length === 0) {
    container.innerHTML = '<div style="padding:16px;color:#999;text-align:center;">No length data</div>';
    return;
  }

  const innerH = HEIGHT - MARGIN.top - MARGIN.bottom;
  const svg = d3.select(container).append('svg')
    .attr('width', '100%')
    .attr('viewBox', `0 0 ${800} ${HEIGHT}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .style('font-family', 'sans-serif')
    .style('font-size', '10px');

  const g = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);
  const width = 800 - MARGIN.left - MARGIN.right;

  const x = d3.scaleLinear()
    .domain([0, d3.max(hitLengths) || 1])
    .range([0, width]).nice();

  const bins = d3.bin().domain(x.domain()).thresholds(15)(hitLengths);

  const y = d3.scaleLinear()
    .domain([0, d3.max(bins, d => d.length) || 1])
    .range([innerH, 0]).nice();

  // X axis
  g.append('g').attr('transform', `translate(0,${innerH})`)
    .call(d3.axisBottom(x).tickFormat(d => formatTick(d, qType)).ticks(5));

  // Y axis
  g.append('g').call(d3.axisLeft(y).ticks(4));

  // Bars — each hit contributes height=1, stacked, colored by E-value
  for (const bin of bins) {
    const binHits = hits.filter(h => {
      const l = h.length;
      return l != null && l >= (bin.x0 || 0) && l < (bin.x1 || Infinity);
    });

    const sorted = [...binHits].sort((a, b) => {
      const aE = Math.max(...(a.hsps || []).map(h => h.evalue || 0));
      const bE = Math.max(...(b.hsps || []).map(h => h.evalue || 0));
      return bE - aE;
    });

    let cumY = innerH;
    for (const hit of sorted) {
      const barH = 1;
      const eVal = Math.max(...(hit.hsps || []).map(h => h.evalue || 0));
      g.append('rect')
        .attr('x', x(bin.x0 || 0) + 1)
        .attr('y', cumY - barH)
        .attr('width', Math.max(1, x(bin.x1 || 0) - x(bin.x0 || 0) - 2))
        .attr('height', barH)
        .attr('fill', evalueToColor(eVal, maxE))
        .append('title')
        .text(`${hit.id}: ${hit.length} aa, E=${eVal}`);
      cumY -= barH;
    }
  }

  // Query reference line
  g.append('line')
    .attr('x1', x(qLen))
    .attr('x2', x(qLen))
    .attr('y1', 0)
    .attr('y2', innerH)
    .attr('stroke', '#e66000')
    .attr('stroke-dasharray', '4,2')
    .attr('stroke-width', 1);

  g.append('text')
    .attr('x', x(qLen) + 4)
    .attr('y', 10)
    .style('fill', '#e66000')
    .style('font-size', '9px')
    .text('Query');
}
