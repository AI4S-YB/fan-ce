// visuals/blast-hits-overview.js — Linear HSP coverage map along query sequence
import * as d3 from 'd3';
import { evalueToColor, formatTick, debounce } from './blast-helpers';

const MARGIN = { top: 10, right: 20, bottom: 30, left: 200 };
const ROW_HEIGHT = 14;
const MAX_INITIAL = 20;

export function createHitsOverview(container, data, _options) {
  const state = { collapsed: false, showAll: false };
  container._blastState = state;

  render(container, data, state);

  const onResize = debounce(() => render(container, data, state), 200);
  window.addEventListener('resize', onResize);
  container._blastResize = onResize;
}

export function updateHitsOverview(container, data, _options) {
  render(container, data, container._blastState || { collapsed: false, showAll: false });
}

export function destroyHitsOverview(container) {
  if (container._blastResize) {
    window.removeEventListener('resize', container._blastResize);
  }
  container.innerHTML = '';
}

function render(container, data, state) {
  container.innerHTML = '';

  const { name, length: qLen, type: qType, hits } = data;
  if (!hits || hits.length === 0) {
    container.innerHTML = '<div style="padding:16px;color:#999;text-align:center;">No hits to display</div>';
    return;
  }

  const displayHits = state.showAll ? hits : hits.slice(0, MAX_INITIAL);
  const totalH = MARGIN.top + displayHits.length * ROW_HEIGHT + MARGIN.bottom;

  const maxE = Math.max(...hits.flatMap(h => h.hsps.map(hsp => hsp.evalue || 1e-100)));

  const svg = d3.select(container).append('svg')
    .attr('width', '100%')
    .attr('viewBox', `0 0 ${800} ${totalH}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .style('font-family', 'sans-serif')
    .style('font-size', '11px');

  const g = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);

  const width = 800 - MARGIN.left - MARGIN.right;

  const x = d3.scaleLinear().domain([0, qLen]).range([0, width]);

  const y = d3.scaleBand()
    .domain(d3.range(displayHits.length))
    .range([0, displayHits.length * ROW_HEIGHT])
    .paddingInner(0.2);

  const xAxis = d3.axisBottom(x).tickFormat(d => formatTick(d, qType)).ticks(5);
  g.append('g').attr('transform', `translate(0,${displayHits.length * ROW_HEIGHT})`).call(xAxis)
    .selectAll('text').style('font-size', '10px');

  g.selectAll('.hit-label')
    .data(displayHits)
    .enter().append('text')
    .attr('class', 'hit-label')
    .attr('x', -6)
    .attr('y', (_, i) => (y(i) || 0) + y.bandwidth() / 2)
    .attr('dy', '0.3em')
    .attr('text-anchor', 'end')
    .style('font-size', '10px')
    .text(d => d.id.length > 25 ? d.id.slice(0, 25) + '…' : d.id)
    .append('title').text(d => `${d.id}: ${d.def}`);

  for (let i = 0; i < displayHits.length; i++) {
    const hit = displayHits[i];
    const bandY = y(i) || 0;
    const h = y.bandwidth();

    g.selectAll(null)
      .data(hit.hsps)
      .enter().append('rect')
      .attr('x', d => x(d.qStart))
      .attr('y', bandY + 2)
      .attr('width', d => Math.max(1, x(d.qEnd) - x(d.qStart)))
      .attr('height', h - 4)
      .attr('fill', d => evalueToColor(d.evalue, maxE))
      .attr('rx', 1)
      .append('title')
      .text(d => `Query ${d.qStart}-${d.qEnd} | Subject ${d.sStart}-${d.sEnd} | E=${d.evalue}`);

    if (hit.hsps.length > 1) {
      const sorted = [...hit.hsps].sort((a, b) => a.qStart - b.qStart);
      for (let j = 0; j < sorted.length - 1; j++) {
        g.append('line')
          .attr('x1', x(sorted[j].qEnd))
          .attr('y1', bandY + h / 2)
          .attr('x2', x(sorted[j + 1].qStart))
          .attr('y2', bandY + h / 2)
          .attr('stroke', '#ccc')
          .attr('stroke-width', 0.5);
      }
    }
  }

  const btnDiv = document.createElement('div');
  btnDiv.style.cssText = 'text-align:center;margin-top:8px;';
  if (hits.length > MAX_INITIAL) {
    const btn = document.createElement('button');
    btn.textContent = state.showAll ? `Show First ${MAX_INITIAL}` : `View All ${hits.length} Hits`;
    btn.style.cssText = 'padding:4px 16px;font-size:12px;cursor:pointer;';
    btn.addEventListener('click', () => {
      state.showAll = !state.showAll;
      render(container, data, state);
    });
    btnDiv.appendChild(btn);
  }
  container.appendChild(btnDiv);

  const legendDiv = document.createElement('div');
  legendDiv.style.cssText = 'display:flex;align-items:center;gap:6px;font-size:11px;padding:0 200px;color:#666;';
  legendDiv.innerHTML = '<span>Weaker</span><div style="width:120px;height:10px;background:linear-gradient(to right, hsl(20,82%,85%), hsl(20,82%,30%));border-radius:2px;"></div><span>Stronger</span><span style="margin-left:8px;">E-value</span>';
  container.appendChild(legendDiv);
}
