<script setup lang="ts">
import { inject, type Ref } from 'vue';
import type { PublicDatasetDetail } from '@/types/dataset';

const detail = inject<Ref<PublicDatasetDetail | null>>('genomeDetail');

function downloadUrl(file: { id?: number; storage_uri?: string; local_path?: string }): string {
  const base = `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/public/dataset`;
  if (file.storage_uri) return file.storage_uri;
  if (file.local_path) return file.local_path;
  return `${base}/file/${file.id}/download`;
}

function formatSize(bytes?: number): string {
  if (!bytes) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}
</script>

<template>
  <div>
    <template v-if="detail">
      <!-- Primary File -->
      <div v-if="detail.file" style="margin-bottom: 20px;">
        <h3>Primary File</h3>
        <el-table :data="[detail.file]" size="small" border>
          <el-table-column prop="name" label="File Name" min-width="250">
            <template #default="{ row }">
              <a :href="downloadUrl(row)" target="_blank" rel="noopener">
                {{ row.name || row.path || 'download' }}
              </a>
            </template>
          </el-table-column>
          <el-table-column label="Size" width="120">
            <template #default="{ row }">
              {{ formatSize(row.size) }}
            </template>
          </el-table-column>
          <el-table-column prop="type" label="Type" width="120" />
        </el-table>
      </div>

      <!-- Assets -->
      <div v-if="detail.assets?.length">
        <h3>Assets &amp; Files</h3>
        <div v-for="asset in detail.assets" :key="asset.id" style="margin-bottom: 16px;">
          <h4 style="margin: 0 0 8px; font-size: 14px;">
            {{ asset.asset_name || asset.asset_code || `Asset #${asset.id}` }}
            <el-tag
              v-if="asset.is_query_entry"
              size="small"
              type="success"
              style="margin-left: 6px;"
            >
              Query Entry
            </el-tag>
            <el-tag
              v-if="asset.is_required"
              size="small"
              type="danger"
              style="margin-left: 4px;"
            >
              Required
            </el-tag>
          </h4>

          <template v-if="asset.files?.length">
            <el-table :data="asset.files" size="small" border>
              <el-table-column label="File Name" min-width="250">
                <template #default="{ row }">
                  <a :href="downloadUrl(row)" target="_blank" rel="noopener">
                    {{ row.file_name || row.storage_uri || `file-${row.id}` }}
                  </a>
                </template>
              </el-table-column>
              <el-table-column prop="file_format" label="Format" width="100" />
              <el-table-column prop="file_role" label="Role" width="120" />
              <el-table-column label="Size" width="120">
                <template #default="{ row }">
                  {{ formatSize(row.file_size) }}
                </template>
              </el-table-column>
            </el-table>
          </template>
          <div v-else style="color: #999; font-size: 13px; padding: 8px 0;">
            No files in this asset.
          </div>
        </div>
      </div>

      <el-empty v-if="!detail.file && !detail.assets?.length" description="No download files available" />
    </template>
  </div>
</template>
