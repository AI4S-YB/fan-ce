<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue';
import * as echarts from 'echarts';

const props = defineProps<{
  variants: { chrom: string; pos: number }[];
  loading?: boolean;
}>();

const chartRef = ref<HTMLElement>();
let chartInst: echarts.ECharts | null = null;

const bins = computed(() => {
  if (props.variants.length === 0) return [];
  const chroms = [...new Set(props.variants.map(v => v.chrom))];
  const data: { chrom: string; pos: number; count: number }[] = [];

  for (const chrom of chroms) {
    const positions = props.variants.filter(v => v.chrom === chrom).map(v => v.pos);
    if (positions.length === 0) continue;
    const maxPos = Math.max(...positions);
    const windowSize = Math.max(100000, Math.floor(maxPos / 100));

    for (let start = 0; start <= maxPos; start += windowSize) {
      const count = positions.filter(p => p >= start && p < start + windowSize).length;
      if (count > 0) {
        data.push({ chrom, pos: (start + start + windowSize) / 2, count });
      }
    }
  }
  return data;
});

watch(() => props.variants, () => {
  nextTick(() => {
    if (chartInst) { chartInst.dispose(); chartInst = null; }
    buildChart();
  });
}, { deep: true });

function buildChart() {
  if (!chartRef.value || bins.value.length === 0) return;
  chartInst = echarts.init(chartRef.value);

  const chroms = [...new Set(bins.value.map(b => b.chrom))];
  const series = chroms.map(chrom => ({
    name: chrom,
    type: 'scatter' as const,
    data: bins.value.filter(b => b.chrom === chrom).map(b => [b.pos, b.count]),
    symbolSize: (val: number[]) => Math.max(3, Math.sqrt(val[1]) * 2),
  }));

  chartInst.setOption({
    tooltip: {
      formatter: (p: any) => `${p.seriesName}<br/>Pos: ${p.data[0].toLocaleString()}<br/>Variants: ${p.data[1]}`,
    },
    legend: { data: chroms, top: 0 },
    grid: { left: 80, right: 20, top: 40, bottom: 40 },
    xAxis: { type: 'value', name: 'Position', axisLabel: { formatter: (v: number) => (v / 1e6).toFixed(1) + 'M' } },
    yAxis: { type: 'value', name: 'Variant Count' },
    series,
  }, true);
}
</script>

<template>
  <div>
    <div ref="chartRef" style="width:100%;height:300px;" />
    <el-empty v-if="!loading && variants.length === 0" description="No data for plot" />
  </div>
</template>
