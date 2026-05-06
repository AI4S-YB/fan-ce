<script setup lang="ts">
import { computed, ref, watch, onMounted, nextTick } from 'vue';
import * as echarts from 'echarts';
import type { QueryResult } from '@/types/dataset';

const props = defineProps<{
  result: QueryResult | null;
  loading?: boolean;
  precision?: number;
}>();

const mode = ref<'table' | 'heatmap'>('table');
const chartRef = ref<HTMLElement>();
let chartInst: echarts.ECharts | null = null;

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

function buildHeatmap() {
  if (!chartRef.value || rows.value.length === 0) return;
  if (!chartInst) {
    chartInst = echarts.init(chartRef.value);
  }

  const cols = columns.value.filter(c => c.prop !== 'gene');
  const geneCol = rows.value.map(r => r['gene'] || r['gene_id'] || '');

  const data: [number, number, number][] = [];
  let maxVal = 0;
  rows.value.forEach((row, yi) => {
    cols.forEach((col, xi) => {
      const v = Number(row[col.prop]) || 0;
      if (v > maxVal) maxVal = v;
      data.push([xi, yi, v]);
    });
  });

  chartInst.setOption({
    tooltip: {
      formatter: (p: any) => `${cols[p.data[0]]?.label} × ${geneCol[p.data[1]]}<br/>Value: ${p.data[2]}`,
    },
    grid: { left: 120, right: 40, top: 40, bottom: 80 },
    xAxis: {
      type: 'category',
      data: cols.map(c => c.label),
      axisLabel: { rotate: 45, fontSize: 11 },
    },
    yAxis: {
      type: 'category',
      data: geneCol,
      axisLabel: { fontSize: 11 },
    },
    visualMap: {
      min: 0,
      max: maxVal || 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#f0f9ff', '#409eff', '#003d80'] },
    },
    series: [{
      type: 'heatmap',
      data,
      label: { show: false },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' },
      },
    }],
  }, true);
}

watch([mode, rows], ([m]) => {
  if (m === 'heatmap') {
    nextTick(() => buildHeatmap());
  }
});

watch(() => props.result, () => {
  if (mode.value === 'heatmap') nextTick(() => buildHeatmap());
});
</script>

<template>
  <div>
    <el-radio-group v-model="mode" size="small" style="margin-bottom: 8px;">
      <el-radio-button value="table">Table</el-radio-button>
      <el-radio-button value="heatmap">Heatmap</el-radio-button>
    </el-radio-group>

    <div v-if="mode === 'table'">
      <el-table :data="rows" border size="small" v-loading="loading" max-height="500" stripe>
        <el-table-column v-for="col in columns" :key="col.prop" :prop="col.prop" :label="col.label" min-width="120" show-overflow-tooltip />
      </el-table>
      <div v-if="result?.total" style="margin-top: 8px; color: #888; font-size: 13px;">{{ result.total }} rows</div>
    </div>

    <div v-else>
      <div ref="chartRef" style="width:100%;height:500px;" />
    </div>

    <el-empty v-if="!loading && rows.length === 0" description="No results" />
  </div>
</template>
