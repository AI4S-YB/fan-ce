<script setup lang="ts">
import { computed, ref } from 'vue';
import type { QueryResult } from '@/types/dataset';

const props = defineProps<{
  result: QueryResult | null;
  loading?: boolean;
}>();

const mode = ref<'table' | 'heatmap'>('table');

const rows = computed(() => props.result?.rows || props.result?.items || []);

const columns = computed(() => {
  if (rows.value.length === 0) return [];
  return Object.keys(rows.value[0]).map((k) => ({ prop: k, label: k }));
});
</script>

<template>
  <div>
    <el-radio-group
      v-model="mode"
      size="small"
      style="margin-bottom: 8px;"
    >
      <el-radio-button value="table">Table</el-radio-button>
      <el-radio-button value="heatmap">Heatmap</el-radio-button>
    </el-radio-group>

    <div v-if="mode === 'table'">
      <el-table
        :data="rows"
        border
        size="small"
        v-loading="loading"
        max-height="500"
        stripe
      >
        <el-table-column
          v-for="col in columns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          min-width="120"
          show-overflow-tooltip
        />
      </el-table>
      <div
        v-if="result?.total"
        style="margin-top: 8px; color: #888; font-size: 13px;"
      >
        {{ result.total }} rows
      </div>
    </div>

    <div
      v-else
      style="text-align: center; padding: 40px; color: #999;"
    >
      Heatmap view — requires ECharts. Coming soon.
    </div>

    <el-empty
      v-if="!loading && rows.length === 0"
      description="No results"
    />
  </div>
</template>
