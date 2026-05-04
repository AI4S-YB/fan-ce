<script setup lang="ts">
import { computed, inject, type Ref } from 'vue';
import type { PublicDatasetDetail } from '@/types/dataset';
import { renderMarkdown } from '@/composables/useMarkdown';

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

const descriptionHtml = computed(() => {
  if (!detail?.value?.description_md) return '';
  return renderMarkdown(detail.value.description_md);
});
</script>

<template>
  <div v-loading="loading">
    <template v-if="detail">
      <!-- Genome Attributes first -->
      <div v-if="detail.extra_json" style="margin-bottom: 20px;">
        <h3>Genome Attributes</h3>
        <el-table :data="extraJsonRows" size="small" border>
          <el-table-column prop="key" label="Attribute" width="220" />
          <el-table-column prop="value" label="Value" />
        </el-table>
      </div>

      <!-- Genome Description as rendered HTML -->
      <div v-if="detail.description_md" style="margin-bottom: 20px;">
        <h3>Genome Description</h3>
        <div
          class="markdown-body"
          v-html="descriptionHtml"
          style="background: #fafafa; padding: 20px; border-radius: 4px; font-size: 14px; line-height: 1.8;"
        />
      </div>
    </template>

    <el-empty v-else description="No genome info" />
  </div>
</template>

<style>
.markdown-body h1 { font-size: 20px; margin: 16px 0 8px; border-bottom: 1px solid #e5e5e5; padding-bottom: 6px; }
.markdown-body h2 { font-size: 17px; margin: 14px 0 6px; }
.markdown-body h3 { font-size: 15px; margin: 12px 0 4px; }
.markdown-body p { margin: 8px 0; }
.markdown-body ul, .markdown-body ol { margin: 8px 0; padding-left: 24px; }
.markdown-body li { margin: 4px 0; }
.markdown-body strong { font-weight: 600; }
.markdown-body code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 13px; }
.markdown-body pre { background: #282c34; color: #abb2bf; padding: 16px; border-radius: 4px; overflow-x: auto; }
.markdown-body pre code { background: none; padding: 0; color: inherit; }
.markdown-body a { color: #409eff; }
.markdown-body table { border-collapse: collapse; width: 100%; margin: 8px 0; }
.markdown-body th, .markdown-body td { border: 1px solid #ddd; padding: 8px; text-align: left; }
.markdown-body th { background: #f5f5f5; }
.markdown-body blockquote { border-left: 3px solid #409eff; padding: 8px 16px; color: #666; margin: 8px 0; }
</style>
