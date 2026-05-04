<script setup lang="ts">
import { onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDatasetDetail } from '@/composables/useDatasets';
import LineagePanel from '@/components/LineagePanel.vue';
import type { PublicDatasetDetail } from '@/types/dataset';

const route = useRoute();
const router = useRouter();
const { loading, detail, lineage, load } = useDatasetDetail();

onMounted(() => load(Number(route.params.id)));
watch(
  () => route.params.id,
  (id) => load(Number(id)),
);

function typeColor(t?: string): string {
  const m: Record<string, string> = {
    genome: '#67c23a',
    transcriptome: '#409eff',
    variome: '#e6a23c',
    phenome: '#f56c6c',
  };
  return m[t || ''] || '#909399';
}

function parseExtraJson(detail: PublicDatasetDetail): Record<string, string> {
  try {
    return JSON.parse(detail.extra_json || '{}');
  } catch {
    return {};
  }
}
</script>

<template>
  <div v-loading="loading">
    <el-button text @click="router.push('/')" style="margin-bottom: 16px;">
      ← Back
    </el-button>

    <template v-if="detail">
      <!-- Header -->
      <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
        <h2 style="margin: 0;">{{ detail.title || detail.dataset_code }}</h2>
        <el-tag>{{ detail.dataset_code }}</el-tag>
        <el-tag
          :color="typeColor(detail.dataset_type)"
          effect="dark"
          style="color: #fff;"
        >
          {{ detail.dataset_type }}
        </el-tag>
        <el-tag>{{ detail.lifecycle_state }}</el-tag>
        <el-tag>{{ detail.visibility }}</el-tag>
      </div>

      <!-- Metadata -->
      <el-descriptions border :column="2" size="small" style="margin-bottom: 20px;">
        <el-descriptions-item label="Organism">
          {{ detail.organism || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="Version">
          {{ detail.version || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="File Format">
          {{ detail.query_profile?.file_format || detail.file?.type || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="Query Engine">
          {{ detail.query_profile?.query_engine || '-' }}
        </el-descriptions-item>
        <el-descriptions-item
          v-if="detail.file?.size"
          label="File Size"
        >
          {{ (detail.file.size / 1024 / 1024).toFixed(1) }} MB
        </el-descriptions-item>
      </el-descriptions>

      <!-- Description MD -->
      <div v-if="detail.description_md" style="margin-bottom: 20px;">
        <h3>Data Description</h3>
        <pre
          style="background: #f5f7fa; padding: 16px; border-radius: 4px; white-space: pre-wrap; font-size: 13px; line-height: 1.6;"
        >{{ detail.description_md }}</pre>
      </div>

      <!-- Extra JSON Attributes -->
      <div v-if="detail.extra_json" style="margin-bottom: 20px;">
        <h3>Structured Attributes</h3>
        <el-table
          :data="
            Object.entries(parseExtraJson(detail)).map(([k, v]) => ({
              key: k,
              value: String(v),
            }))
          "
          size="small"
          border
        >
          <el-table-column prop="key" label="Key" width="200" />
          <el-table-column prop="value" label="Value" />
        </el-table>
      </div>

      <!-- Assets -->
      <div v-if="detail.assets?.length" style="margin-bottom: 20px;">
        <h3>Assets ({{ detail.assets.length }})</h3>
        <el-table :data="detail.assets" size="small" border>
          <el-table-column prop="asset_code" label="Code" width="160" />
          <el-table-column prop="asset_name" label="Name" />
          <el-table-column prop="asset_type" label="Type" width="140" />
          <el-table-column prop="file_format" label="Format" width="100" />
          <el-table-column label="Files" width="60">
            <template #default="{ row }">
              <span v-if="row.files?.length">{{ row.files.length }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Version Info -->
      <div
        style="margin-bottom: 20px; font-size: 13px; color: #888;"
      >
        <span>Current: <strong>{{ detail.current_version?.version || '-' }}</strong></span>
        <span style="margin-left: 16px;">Public: <strong>{{ detail.default_public_version?.version || '-' }}</strong></span>
        <span style="margin-left: 16px;">Versions: <strong>{{ detail.version_count ?? 0 }}</strong></span>
      </div>

      <!-- Lineage -->
      <div style="margin-bottom: 20px;">
        <h3>Lineage</h3>
        <LineagePanel :lineage="lineage" />
      </div>
    </template>
  </div>
</template>
