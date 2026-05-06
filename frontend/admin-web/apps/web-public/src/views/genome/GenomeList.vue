<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useDatasetList } from '@/composables/useDatasets';

const router = useRouter();
const { loading, items, load } = useDatasetList();

onMounted(() => {
  load({ dataset_type: 'genome' });
});

function goGenome(id: number) {
  router.push(`/genome/${id}`);
}
</script>

<template>
  <div>
    <h2>Genomes</h2>

    <div v-loading="loading">
      <el-empty v-if="!loading && items.length === 0" description="No genome datasets found" />
      <div v-else style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;">
        <el-card v-for="item in items" :key="item.id" shadow="hover" style="cursor:pointer;"
          @click="goGenome(item.id)">
          <h3 style="margin:0 0 8px;font-size:16px;">
            {{ item.title || item.dataset_code }}
          </h3>
          <div style="color:#888;font-size:13px;">
            <div v-if="item.organism">{{ item.organism }}</div>
            <div>Version: {{ item.version || '-' }}</div>
          </div>
          <div v-if="item.description_md" style="margin-top:8px;color:#666;font-size:12px;line-height:1.5;">
            {{ (item.description_md || '').substring(0, 150) }}{{ item.description_md?.length > 150 ? '...' : '' }}
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>
