// visuals/msa-viewer.js — D3 SVG MSA alignment viewer
import * as d3 from 'd3';
import { debounce } from './blast-helpers';

const CHAR_W = 10;
const CHAR_H = 16;
const LEFT_MARGIN = 150;
const TOP_MARGIN = 10;
const COLORS = {
  A: '#80a0f0', G: '#80a0f0', I: '#80a0f0', L: '#80a0f0', M: '#80a0f0', V: '#80a0f0', // aliphatic
  F: '#80f0a0', W: '#80f0a0', Y: '#80f0a0', // aromatic
  D: '#f08080', E: '#f08080', // acidic
  R: '#f0a080', K: '#f0a080', // basic
  S: '#f0e080', T: '#f0e080', N: '#f0e080', Q: '#f0e080', // polar
  C: '#80f0f0', // cysteine
  H: '#f080e0', // histidine
  P: '#c0c0c0', // proline
  '-': '#ffffff', // gap
};

export function createMsaViewer(container, data, _options) { render(container, data); const onResize = debounce(() => render(container, data), 200); window.addEventListener('resize', onResize); container._msaResize = onResize; }
export function updateMsaViewer(container, data, _options) { render(container, data); }
export function destroyMsaViewer(container) { if (container._msaResize) window.removeEventListener('resize', container._msaResize); container.innerHTML = ''; }

function parseFasta(text) {
  const seqs = [];
  let current = null;
  for (const line of text.split('\n')) {
    const t = line.trim();
    if (!t) continue;
    if (t.startsWith('>')) { current = { header: t.slice(1), sequence: '' }; seqs.push(current); }
    else if (current) { current.sequence += t.replace(/\s/g, ''); }
  }
  return seqs.filter(s => s.sequence.length > 0);
}

function colorForChar(c) {
  const uc = (c || '-').toUpperCase();
  return COLORS[uc] || '#f0f0f0';
}

function render(container, data) {
  container.innerHTML = '';
  const text = typeof data === 'string' ? data : (data.alignment || data.content || '');
  const seqs = parseFasta(text);
  if (seqs.length === 0) { container.innerHTML = '<div style="padding:16px;color:#999;text-align:center;">No alignment data</div>'; return; }

  const maxLen = d3.max(seqs, s => s.sequence.length) || 0;
  const width = LEFT_MARGIN + maxLen * CHAR_W + 20;
  const height = TOP_MARGIN + seqs.length * CHAR_H + 10;

  const svg = d3.select(container).append('svg')
    .attr('width', '100%').attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMinYMid meet')
    .style('font-family', 'monospace').style('font-size', '10px');

  const g = svg.append('g').attr('transform', `translate(${LEFT_MARGIN},${TOP_MARGIN})`);

  // Consensus bar (conservation %)
  const consY = seqs.length * CHAR_H + 4;
  for (let ci = 0; ci < maxLen; ci++) {
    const counts = {};
    for (const s of seqs) { const c = s.sequence[ci] || '-'; counts[c] = (counts[c] || 0) + 1; }
    const maxCount = d3.max(Object.values(counts)) || 1;
    const cons = maxCount / seqs.length;
    g.append('rect').attr('x', ci * CHAR_W).attr('y', consY).attr('width', CHAR_W - 1).attr('height', 6)
      .attr('fill', d3.interpolateYlOrRd(cons)).attr('opacity', 0.8);
  }

  // Sequence rows
  for (let ri = 0; ri < seqs.length; ri++) {
    const s = seqs[ri];
    // Label
    g.append('text').attr('x', -6).attr('y', ri * CHAR_H + CHAR_H - 4).attr('text-anchor', 'end')
      .style('font-size', '9px').style('fill', '#333').text(s.header.length > 18 ? s.header.slice(0, 17) + '…' : s.header)
      .append('title').text(s.header);

    // Residue rects
    for (let ci = 0; ci < s.sequence.length; ci++) {
      g.append('rect').attr('x', ci * CHAR_W).attr('y', ri * CHAR_H + 1).attr('width', CHAR_W - 1).attr('height', CHAR_H - 2)
        .attr('fill', colorForChar(s.sequence[ci])).attr('rx', 1)
        .append('title').text(`${s.header} pos ${ci + 1}: ${s.sequence[ci]}`);
    }
  }
}
