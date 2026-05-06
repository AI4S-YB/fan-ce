<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue';
import * as echarts from 'echarts';
import type { QueryResult } from '@/types/dataset';

const props = defineProps<{
  result: QueryResult | null;
  loading?: boolean;
  precision?: number;
  showExport?: boolean;
}>();

const emit = defineEmits<{ normalize: [method: string] }>();

const mode = ref<'table' | 'bar' | 'line' | 'heatmap'>('table');
const chartRef = ref<HTMLElement>();
let chartInst: echarts.ECharts | null = null;
const normalizeMethod = ref('raw');

const rows = computed(() => {
  const raw = props.result?.rows || props.result?.items || [];
  if (props.precision == null) return raw;
  return raw.map(row => {
    const r: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(row)) {
      r[k] = typeof v === 'number' ? Number(v.toFixed(props.precision)) : v;
    }
    return r;
  });
});

const columns = computed(() => {
  if (rows.value.length === 0) return [];
  return Object.keys(rows.value[0]).map((k) => ({ prop: k, label: k }));
});

const numCols = computed(() => columns.value.filter(c => c.prop !== 'gene' && c.prop !== 'gene_id'));

function ensureChart() {
  if (!chartRef.value) return null;
  if (!chartInst) chartInst = echarts.init(chartRef.value);
  return chartInst;
}

function buildBarChart() {
  const chart = ensureChart();
  if (!chart || rows.value.length === 0) return;
  const genes = rows.value.map(r => String(r['gene'] || r['gene_id'] || ''));
  const series = numCols.value.map(col => ({
    name: col.label, type: 'bar' as const,
    data: rows.value.map(r => Number(r[col.prop]) || 0),
  }));
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: numCols.value.map(c => c.label), top: 0 },
    grid: { left: 60, right: 20, top: 40, bottom: 80 },
    xAxis: { type: 'category', data: genes, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value' },
    series,
  }, true);
}

function buildLineChart() {
  const chart = ensureChart();
  if (!chart || rows.value.length === 0) return;
  const genes = rows.value.map(r => String(r['gene'] || r['gene_id'] || ''));
  const series = numCols.value.map(col => ({
    name: col.label, type: 'line' as const,
    data: rows.value.map(r => Number(r[col.prop]) || 0),
    smooth: true,
  }));
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: numCols.value.map(c => c.label), top: 0 },
    grid: { left: 60, right: 20, top: 40, bottom: 80 },
    xAxis: { type: 'category', data: genes, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value' },
    series,
  }, true);
}

function buildHeatmap() {
  const chart = ensureChart();
  if (!chart || rows.value.length === 0) return;
  const geneCol = rows.value.map(r => String(r['gene'] || r['gene_id'] || ''));
  const data: [number, number, number][] = [];
  let maxVal = 0;
  rows.value.forEach((row, yi) => {
    numCols.value.forEach((col, xi) => {
      const v = Number(row[col.prop]) || 0;
      if (v > maxVal) maxVal = v;
      data.push([xi, yi, v]);
    });
  });
  chart.setOption({
    tooltip: { formatter: (p: any) => `${numCols.value[p.data[0]]?.label} × ${geneCol[p.data[1]]}<br/>Value: ${p.data[2]}` },
    grid: { left: 120, right: 40, top: 20, bottom: 80 },
    xAxis: { type: 'category', data: numCols.value.map(c => c.label), axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'category', data: geneCol, axisLabel: { fontSize: 10 } },
    visualMap: { min: 0, max: maxVal || 1, calculable: true, orient: 'horizontal', left: 'center', bottom: 0, inRange: { color: ['#f0f9ff', '#409eff', '#003d80'] } },
    series: [{ type: 'heatmap', data, label: { show: false } }],
  }, true);
}

watch([mode, rows], ([m]) => {
  if (m === 'bar') nextTick(() => buildBarChart());
  else if (m === 'line') nextTick(() => buildLineChart());
  else if (m === 'heatmap') nextTick(() => buildHeatmap());
});

watch(() => props.result, () => {
  if (mode.value === 'bar') nextTick(() => buildBarChart());
  else if (mode.value === 'line') nextTick(() => buildLineChart());
  else if (mode.value === 'heatmap') nextTick(() => buildHeatmap());
});

function exportCSV() {
  if (rows.value.length === 0) return;
  const cols = columns.value;
  const header = cols.map(c => c.label).join(',');
  const body = rows.value.map(r => cols.map(c => r[c.prop] ?? '').join(',')).join('\n');
  const blob = new Blob([header + '\n' + body], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'expression_data.csv'; a.click();
  URL.revokeObjectURL(a.href);
}
</script>

<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:8px;">
      <el-radio-group v-model="mode" size="small">
        <el-radio-button value="table">Table</el-radio-button>
        <el-radio-button value="bar">Bar</el-radio-button>
        <el-radio-button value="line">Line</el-radio-button>
        <el-radio-button value="heatmap">Heatmap</el-radio-button>
      </el-radio-group>
      <div style="display:flex;gap:8px;align-items:center;">
        <el-select v-model="normalizeMethod" size="small" style="width:110px;" @change="(v: string) => emit('normalize', v)">
          <el-option label="Raw" value="raw" />
          <el-option label="log2(x+1)" value="log2" />
          <el-option label="Z-score" value="zscore" />
        </el-select>
        <el-button v-if="showExport !== false" size="small" @click="exportCSV">CSV</el-button>
      </div>
    </div>

    <div v-if="mode === 'table'">
      <el-table :data="rows" border size="small" v-loading="loading" max-height="500" stripe>
        <el-table-column v-for="col in columns" :key="col.prop" :prop="col.prop" :label="col.label" min-width="120" show-overflow-tooltip />
      </el-table>
      <div v-if="result?.total" style="margin-top:8px;color:#888;font-size:13px;">{{ result.total }} rows</div>
    </div>

    <div v-else>
      <div ref="chartRef" style="width:100%;height:450px;" />
    </div>

    <el-empty v-if="!loading && rows.length === 0" description="No results" />
  </div>
</template>
