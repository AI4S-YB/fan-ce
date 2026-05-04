<script setup lang="ts">
import { provide, ref, watch, type Ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDatasetDetail } from '@/composables/useDatasets';
import type { PublicDatasetDetail } from '@/types/dataset';

const route = useRoute();
const router = useRouter();
const { loading, detail, load } = useDatasetDetail();

const activeTab = ref('home');

// Load genome detail on mount and when id changes
watch(
  () => route.params.id,
  (id) => {
    if (id) load(Number(id));
  },
  { immediate: true },
);

// Sync activeTab from route path
watch(
  () => route.path,
  (path) => {
    const seg = path.split('/').pop();
    if (seg && !Number.isNaN(Number(seg))) {
      activeTab.value = 'home';
    } else if (seg) {
      activeTab.value = seg;
    }
  },
  { immediate: true },
);

function onTabClick(paneName: string) {
  router.push({ path: `/genome/${Number(route.params.id)}/${paneName}` });
}

provide<Ref<PublicDatasetDetail | null>>('genomeDetail', detail);
provide<Ref<boolean>>('genomeLoading', loading);
</script>

<template>
  <div v-loading="loading">
    <el-button text @click="router.push('/')">← Back to Catalog</el-button>

    <template v-if="detail">
      <h2 style="margin: 12px 0 4px;">
        {{ detail.title || detail.dataset_code }}
      </h2>
      <div style="color: #888; font-size: 13px; margin-bottom: 16px;">
        <el-tag size="small">{{ detail.dataset_type }}</el-tag>
        <span style="margin-left: 8px;">{{ detail.organism || '-' }}</span>
        <span style="margin-left: 8px;">v{{ detail.version || '-' }}</span>
      </div>

      <el-tabs v-model="activeTab" @tab-click="onTabClick(activeTab)">
        <el-tab-pane label="Home" name="home" />
        <el-tab-pane label="Gene Search" name="search" />
        <el-tab-pane label="Batch Query" name="batch" />
        <el-tab-pane label="BLAST" name="blast" />
        <el-tab-pane label="Download" name="download" />
      </el-tabs>

      <router-view />
    </template>

    <el-empty v-else-if="!loading" description="Genome not found" />
  </div>
</template>
