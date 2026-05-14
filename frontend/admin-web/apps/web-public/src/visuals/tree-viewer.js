// visuals/tree-viewer.js — D3 phylogenetic tree from Newick
import * as d3 from 'd3';
import { debounce } from './blast-helpers';

export function createTreeViewer(container, data, _options) { render(container, data); const onResize = debounce(() => render(container, data), 200); window.addEventListener('resize', onResize); container._treeResize = onResize; }
export function updateTreeViewer(container, data, _options) { render(container, data); }
export function destroyTreeViewer(container) { if (container._treeResize) window.removeEventListener('resize', container._treeResize); container.innerHTML = ''; }

function parseNewick(s) {
  // Use D3's built-in Newick parser via d3.stratify or manual recursive descent
  let i = 0;
  const text = s.trim().replace(/\s/g, '');
  function parse() {
    const children = [];
    let name = '';
    let length = null;
    if (text[i] === '(') {
      i++; // skip '('
      while (text[i] !== ')') {
        children.push(parse());
        if (text[i] === ',') i++;
      }
      i++; // skip ')'
    }
    // Read name (until : or , or ) or end)
    while (i < text.length && text[i] !== ':' && text[i] !== ',' && text[i] !== ')' && text[i] !== ';') {
      name += text[i]; i++;
    }
    if (text[i] === ':') {
      i++;
      let lenStr = '';
      while (i < text.length && text[i] !== ',' && text[i] !== ')' && text[i] !== ';') { lenStr += text[i]; i++; }
      length = parseFloat(lenStr) || null;
    }
    if (text[i] === ';') i++;
    return { name: name || null, length, children: children.length ? children : null };
  }
  if (text.startsWith('(')) return parse();
  return null;
}

function render(container, data) {
  container.innerHTML = '';
  const text = typeof data === 'string' ? data : (data.tree || data.content || '');
  const rootData = parseNewick(text);
  if (!rootData) { container.innerHTML = '<div style="padding:16px;color:#999;text-align:center;">Invalid Newick format</div>'; return; }

  const root = d3.hierarchy(rootData, d => d.children || null);
  const leafCount = root.leaves().length;
  const leafHeight = 20;
  const totalH = Math.max(200, leafCount * leafHeight + 40);
  const totalW = 600;

  const svg = d3.select(container).append('svg')
    .attr('width', '100%').attr('viewBox', `0 0 ${totalW} ${totalH}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .style('font-family', 'sans-serif').style('font-size', '10px');

  const g = svg.append('g').attr('transform', 'translate(10,20)');

  const maxDepth = d3.max(root.descendants(), d => d.depth) || 1;
  const treeLayout = d3.tree().size([totalH - 40, totalW - 60]);
  treeLayout(root);

  // Links
  g.selectAll('.link').data(root.links()).enter().append('path')
    .attr('d', d => `M${d.source.y},${d.source.x}H${d.target.y}V${d.target.x}`)
    .attr('fill', 'none').attr('stroke', '#999').attr('stroke-width', 1);

  // Nodes
  g.selectAll('.node').data(root.descendants()).enter().append('circle')
    .attr('cx', d => d.y).attr('cy', d => d.x).attr('r', 2).attr('fill', d => d.children ? '#666' : '#409eff');

  // Labels
  g.selectAll('.label').data(root.leaves()).enter().append('text')
    .attr('x', d => d.y + 6).attr('y', d => d.x + 3).style('font-size', '9px').style('fill', '#333')
    .text(d => d.data.name || '');
}
