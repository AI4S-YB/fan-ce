<script setup lang="ts">
import { ref, computed } from 'vue';
import { useDatasetList } from '@/composables/useDatasets';

const { loading, items, load } = useDatasetList();
const keyword = ref('');

load({ dataset_type: 'germplasm' });

const filtered = computed(() => {
  if (!keyword.value) return items.value;
  const kw = keyword.value.toLowerCase();
  return items.value.filter(
    (item) =>
      (item.title || '').toLowerCase().includes(kw) ||
      (item.organism || '').toLowerCase().includes(kw),
  );
});

const detailVisible = ref(false);
const selectedItem = ref<any>(null);

function showDetail(item: any) {
  selectedItem.value = item;
  detailVisible.value = true;
}
</script>

<template>
  <div>
    <h2>Germplasm Browser</h2>
    <div style="margin-bottom: 16px">
      <el-input
        v-model="keyword"
        placeholder="Search germplasm..."
        clearable
        style="width: 400px"
      />
    </div>
    <el-table
      :data="filtered"
      border
      size="small"
      v-loading="loading"
      style="cursor: pointer"
      @row-click="showDetail"
    >
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="title" label="Name" />
      <el-table-column prop="organism" label="Species" width="180" />
      <el-table-column prop="version" label="Version" width="120" />
      <el-table-column prop="dataset_type" label="Type" width="120" />
    </el-table>
    <div style="margin-top: 8px; color: #888; font-size: 13px">
      {{ filtered.length }} germplasm records
    </div>

    <!-- Detail Drawer -->
    <el-drawer
      v-model="detailVisible"
      title="Germplasm Detail"
      size="500px"
    >
      <template v-if="selectedItem">
        <el-descriptions border :column="1" size="small">
          <el-descriptions-item label="ID">
            {{ selectedItem.id }}
          </el-descriptions-item>
          <el-descriptions-item label="Name">
            {{ selectedItem.title || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="Species">
            {{ selectedItem.organism || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="Type">
            {{ selectedItem.dataset_type }}
          </el-descriptions-item>
          <el-descriptions-item label="Version">
            {{ selectedItem.version || '-' }}
          </el-descriptions-item>
        </el-descriptions>
        <div
          v-if="selectedItem.description_md"
          style="margin-top: 16px"
        >
          <h4>Description</h4>
          <pre
            style="
              background: #f5f7fa;
              padding: 12px;
              border-radius: 4px;
              white-space: pre-wrap;
              font-size: 12px;
            "
          >{{ selectedItem.description_md }}</pre>
        </div>
      </template>
    </el-drawer>
  </div>
</template>
