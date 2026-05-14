// visuals/msa-viewer.js — D3 SVG MSA alignment viewer
import * as d3 from 'd3';

const CHAR_W = 14;
const CHAR_H = 20;
const LABEL_W = 160;
const TOP_MARGIN = 24;
const COLORS = {
  A:'#a0d0ff', G:'#a0d0ff', I:'#a0d0ff', L:'#a0d0ff', M:'#a0d0ff', V:'#a0d0ff',
  F:'#a0ffd0', W:'#a0ffd0', Y:'#a0ffd0',
  D:'#ffa0a0', E:'#ffa0a0',
  R:'#ffd0a0', K:'#ffd0a0', H:'#ffd0e0',
  S:'#ffe8a0', T:'#ffe8a0', N:'#ffe8a0', Q:'#ffe8a0',
  C:'#ffff80',
  P:'#d0d0d0',
  '-':'#ffffff',
};

export function createMsaViewer(c, d) { render(c, d); }
export function updateMsaViewer(c, d) { render(c, d); }
export function destroyMsaViewer(c) { c.innerHTML = ''; }

function parseFasta(text) {
  const seqs = []; let cur = null;
  for (const line of text.split('\n')) {
    const t = line.trim();
    if (!t) continue;
    if (t.startsWith('>')) { cur = { header: t.slice(1).trim(), sequence: '' }; seqs.push(cur); }
    else if (cur) cur.sequence += t.replace(/\s/g, '').toUpperCase();
  }
  return seqs.filter(s => s.sequence.length > 0);
}

function render(container, data) {
  container.innerHTML = '';
  const text = typeof data === 'string' ? data : (data?.alignment || data?.content || '');
  const seqs = parseFasta(text);
  if (seqs.length === 0) {
    container.innerHTML = '<div style="padding:24px;color:#999;text-align:center;">No alignment data</div>';
    return;
  }

  const maxLen = d3.max(seqs, s => s.sequence.length) || 0;
  const H = TOP_MARGIN + seqs.length * CHAR_H + 24;
  const W = LABEL_W + maxLen * CHAR_W + 40;

  // Wrapper for horizontal scroll
  const wrap = document.createElement('div');
  wrap.style.cssText = 'overflow-x:auto;max-width:100%;position:relative;';
  container.appendChild(wrap);

  const svg = d3.select(wrap).append('svg')
    .attr('width', Math.max(800, W)).attr('height', H).style('display', 'block');

  const g = svg.append('g').attr('transform', `translate(${LABEL_W},${TOP_MARGIN})`);

  // Column position numbers (every 10)
  for (let ci = 0; ci < maxLen; ci += 10) {
    g.append('text').attr('x', ci * CHAR_W + 2).attr('y', -8)
      .style('font-size', '9px').style('fill', '#999').style('font-family', 'monospace')
      .text(ci + 1);
  }

  // Consensus
  const consY = seqs.length * CHAR_H + 4;
  for (let ci = 0; ci < maxLen; ci++) {
    const counts = {};
    for (const s of seqs) { const c = s.sequence[ci] || '-'; counts[c] = (counts[c] || 0) + 1; }
    const cons = Math.max(...Object.values(counts)) / seqs.length;
    g.append('rect').attr('x', ci * CHAR_W + 1).attr('y', consY).attr('width', CHAR_W - 2).attr('height', 8)
      .attr('fill', cons > 0.9 ? '#f5b041' : cons > 0.6 ? '#f0e68c' : '#e0e0e0').attr('rx', 1);
  }

  // Rows
  for (let ri = 0; ri < seqs.length; ri++) {
    const s = seqs[ri];
    const baseY = ri * CHAR_H;

    // Label (fixed, outside scroll)
    svg.append('text').attr('x', LABEL_W - 8).attr('y', TOP_MARGIN + baseY + CHAR_H - 5)
      .attr('text-anchor', 'end').style('font-size', '11px').style('fill', '#333').style('font-family', 'monospace')
      .text(s.header.length > 22 ? s.header.slice(0, 21) + '…' : s.header)
      .append('title').text(s.header);

    // Alternating row background
    if (ri % 2 === 0) {
      g.append('rect').attr('x', 0).attr('y', baseY).attr('width', maxLen * CHAR_W).attr('height', CHAR_H)
        .attr('fill', '#fafafa');
    }

    // Render residues as text (much faster for large alignments)
    for (let ci = 0; ci < s.sequence.length; ci++) {
      const ch = s.sequence[ci] || '-';
      g.append('rect').attr('x', ci * CHAR_W + 1).attr('y', baseY + 2)
        .attr('width', CHAR_W - 2).attr('height', CHAR_H - 4).attr('fill', COLORS[ch.toUpperCase()] || '#f0f0f0').attr('rx', 2);
      g.append('text').attr('x', ci * CHAR_W + CHAR_W / 2).attr('y', baseY + CHAR_H - 5)
        .attr('text-anchor', 'middle').style('font-size', '11px').style('fill', '#222').style('font-family', 'monospace')
        .text(ch);
    }
  }
}
