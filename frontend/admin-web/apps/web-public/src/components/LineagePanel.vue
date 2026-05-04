<script setup lang="ts">
import type { PublicLineageItem } from '@/types/dataset';

defineProps<{
  lineage: PublicLineageItem[];
}>();

function relationTypeColor(type?: string): string {
  const m: Record<string, string> = {
    references: '#409eff',
    quantified_against: '#67c23a',
    derived_from: '#e6a23c',
    complements: '#9b59b6',
  };
  return m[type || ''] || '#909399';
}

function linkedDataset(item: PublicLineageItem) {
  if (item.direction === 'forward') {
    return {
      title: item.dst_dataset_title || '-',
      type: item.dst_dataset_type,
    };
  }
  return {
    title: item.src_dataset_title || '-',
    type: item.src_dataset_type,
  };
}
</script>

<template>
  <div v-if="lineage.length === 0" style="color: #999; font-size: 13px;">
    No lineage relationships
  </div>
  <el-table v-else :data="lineage" size="small" border>
    <el-table-column prop="relation_type" label="Relation" width="160">
      <template #default="{ row }">
        <el-tag
          :color="relationTypeColor(row.relation_type)"
          effect="dark"
          size="small"
          style="color: #fff;"
        >
          {{ row.relation_type }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="direction" label="Direction" width="100">
      <template #default="{ row }">
        <span>{{ row.direction || '-' }}</span>
      </template>
    </el-table-column>
    <el-table-column label="Linked Dataset">
      <template #default="{ row }">
        <span>{{ linkedDataset(row).title }}</span>
        <el-tag
          v-if="linkedDataset(row).type"
          size="small"
          style="margin-left: 8px;"
        >
          {{ linkedDataset(row).type }}
        </el-tag>
      </template>
    </el-table-column>
  </el-table>
</template>
