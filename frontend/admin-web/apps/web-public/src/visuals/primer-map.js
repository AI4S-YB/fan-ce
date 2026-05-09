// visuals/primer-map.js — Linear primer pair map on template sequence
import * as d3 from 'd3';
import { debounce } from './blast-helpers';

const MARGIN = { top: 10, right: 20, bottom: 30, left: 60 };

export function createPrimerMap(container, data, _options) {
  render(container, data);
  const onResize = debounce(() => render(container, data), 200);
  window.addEventListener('resize', onResize);
  container._pmResize = onResize;
}

export function updatePrimerMap(container, data, _options) {
  render(container, data);
}

export function destroyPrimerMap(container) {
  if (container._pmResize) window.removeEventListener('resize', container._pmResize);
  container.innerHTML = '';
}

function render(container, data) {
  container.innerHTML = '';

  const { templateLength, pairs } = data;
  if (!pairs || pairs.length === 0) {
    container.innerHTML = '<div style="padding:16px;color:#999;text-align:center;">No primer pairs</div>';
    return;
  }

  // Extract primer positions from sequence — we approximate by looking up
  // the left primer at start of template and right primer near the end.
  // Actually each pair has: left_seq, right_seq, product_size.
  // We need to find positions. For now, we use a heuristic:
  // - Find left primer position in template
  // - Right primer position = left_pos + product_size
  const rows = [];
  for (const p of pairs) {
    const lSeq = p.Left_Primer || p.left || '';
    const rSeq = p.Right_Primer || p.right || '';
    const pSize = +(p.Product_Size || p.product || 0);

    // Find left primer start position in template
    const lPos = data.templateSeq ? data.templateSeq.toUpperCase().indexOf(lSeq.toUpperCase()) : -1;
    const rPos = lPos >= 0 ? lPos + pSize : -1;

    rows.push({
      label: `Pair ${p.Pair || p.pair || ''}`,
      leftSeq: lSeq,
      rightSeq: rSeq,
      leftTm: p.Left_Tm || p.left_tm || '',
      rightTm: p.Right_Tm || p.right_tm || '',
      leftGC: p['Left_GC%'] || p.left_gc || '',
      rightGC: p['Right_GC%'] || p.right_gc || '',
      productSize: pSize,
      leftPos: lPos,
      rightPos: rPos
    });
  }

  const ROW_H = 28;
  const totalH = MARGIN.top + rows.length * ROW_H + MARGIN.bottom;

  const svg = d3.select(container).append('svg')
    .attr('width', '100%')
    .attr('viewBox', `0 0 ${800} ${totalH}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .style('font-family', 'sans-serif')
    .style('font-size', '10px');

  const g = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);
  const width = 800 - MARGIN.left - MARGIN.right;

  // X scale
  const x = d3.scaleLinear().domain([0, templateLength]).range([0, width]);

  // X axis (top)
  g.append('g').call(d3.axisTop(x).ticks(6))
    .selectAll('text').style('font-size', '9px');

  // Template backbone line
  g.append('line')
    .attr('x1', 0).attr('x2', width)
    .attr('y1', -4).attr('y2', -4)
    .attr('stroke', '#aaa').attr('stroke-width', 2);

  g.append('text').attr('x', width / 2).attr('y', -10)
    .attr('text-anchor', 'middle').style('font-size', '9px').style('fill', '#888')
    .text(`Template (${templateLength} bp)`);

  // Draw each pair
  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    const y = i * ROW_H + 6;

    // Product span line
    if (r.leftPos >= 0 && r.rightPos > r.leftPos) {
      g.append('line')
        .attr('x1', x(r.leftPos)).attr('x2', x(r.rightPos))
        .attr('y1', y + 8).attr('y2', y + 8)
        .attr('stroke', '#67c23a').attr('stroke-width', 5)
        .attr('stroke-linecap', 'round').attr('opacity', 0.3);

      // Product size label
      g.append('text')
        .attr('x', x((r.leftPos + r.rightPos) / 2))
        .attr('y', y + 6)
        .attr('text-anchor', 'middle').style('font-size', '8px').style('fill', '#67c23a')
        .text(`${r.productSize}bp`);
    }

    // Left primer arrow
    if (r.leftPos >= 0) {
      g.append('polygon')
        .attr('points', `${x(r.leftPos)},${y} ${x(r.leftPos + 20)},${y + 5} ${x(r.leftPos)},${y + 10}`)
        .attr('fill', '#409eff').attr('opacity', 0.85);
      g.append('text')
        .attr('x', x(r.leftPos) - 4).attr('y', y + 18)
        .attr('text-anchor', 'end').style('font-size', '8px').style('fill', '#409eff')
        .text(`F: ${r.leftTm}°C`);
    }

    // Right primer arrow (reverse direction)
    if (r.rightPos > 0) {
      g.append('polygon')
        .attr('points', `${x(r.rightPos)},${y} ${x(r.rightPos - 20)},${y + 5} ${x(r.rightPos)},${y + 10}`)
        .attr('fill', '#e6a23c').attr('opacity', 0.85);
      g.append('text')
        .attr('x', x(r.rightPos) + 4).attr('y', y + 18)
        .attr('text-anchor', 'start').style('font-size', '8px').style('fill', '#e6a23c')
        .text(`R: ${r.rightTm}°C`);
    }

    // Pair label on left
    g.append('text')
      .attr('x', -8).attr('y', y + 8)
      .attr('text-anchor', 'end').style('font-size', '9px').style('fill', '#666')
      .text(r.label);
  }
}
