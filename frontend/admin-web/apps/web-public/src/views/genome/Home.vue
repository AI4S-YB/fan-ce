<script setup lang="ts">
import { computed, inject, type Ref } from 'vue';
import type { PublicDatasetDetail } from '@/types/dataset';

const detail = inject<Ref<PublicDatasetDetail | null>>('genomeDetail');
const loading = inject<Ref<boolean>>('genomeLoading', { value: false } as Ref<boolean>);

const extraJsonRows = computed(() => {
  if (!detail?.value?.extra_json) return [];
  try {
    return Object.entries(JSON.parse(detail.value.extra_json)).map(([k, v]) => ({
      key: k,
      value: String(v),
    }));
  } catch {
    return [];
  }
});
</script>

<template>
  <div v-loading="loading">
    <template v-if="detail">
      <div v-if="detail.description_md" style="margin-bottom: 20px;">
        <h3>Genome Description</h3>
        <pre
          style="background: #f5f7fa; padding: 16px; border-radius: 4px; white-space: pre-wrap; font-size: 13px; line-height: 1.6;"
        >{{ detail.description_md }}</pre>
      </div>

      <div v-if="detail.extra_json" style="margin-bottom: 20px;">
        <h3>Genome Attributes</h3>
        <el-table :data="extraJsonRows" size="small" border>
          <el-table-column prop="key" label="Attribute" width="200" />
          <el-table-column prop="value" label="Value" />
        </el-table>
      </div>
    </template>

    <el-empty v-else description="No genome info" />
  </div>
</template>
