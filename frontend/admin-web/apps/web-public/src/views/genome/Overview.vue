<script setup lang="ts">
import { computed, provide, watch, type Ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDatasetDetail } from '@/composables/useDatasets';
import type { PublicDatasetDetail } from '@/types/dataset';

const route = useRoute();
const router = useRouter();
const { loading, detail, load } = useDatasetDetail();

const genomeId = computed(() => Number(route.params.id));
watch(() => route.params.id, (id) => { if (id) load(Number(id)); }, { immediate: true });

const activeTab = computed(() => {
  const p = route.path;
  if (p.includes('/search')) return 'search';
  if (p.includes('/tf')) return 'tf';
  if (p.includes('/tools/')) return 'tools';
  return 'home';
});

function navigate(sub: string) { router.push(`/genome/${genomeId.value}/${sub}`); }

function tabStyle(name: string) {
  const isActive = activeTab.value === name;
  return {
    padding: '10px 20px', cursor: 'pointer', fontSize: '14px',
    color: isActive ? '#409eff' : '#606266',
    borderBottom: isActive ? '2px solid #409eff' : '2px solid transparent',
    marginBottom: '-2px', fontWeight: isActive ? '600' : '400',
  };
}

provide<Ref<PublicDatasetDetail | null>>('genomeDetail', detail);
provide<Ref<boolean>>('genomeLoading', loading);
</script>

<template>
  <div v-loading="loading">
    <el-button text @click="router.push('/')">← Back</el-button>

    <template v-if="detail">
      <h2 style="margin:8px 0 4px;">{{ detail.title || detail.dataset_code }}</h2>
      <div style="color:#888;font-size:12px;margin-bottom:12px;">
        <el-tag size="small">{{ detail.dataset_type }}</el-tag>
        <span style="margin-left:6px;">{{ detail.organism || '-' }}</span>
        <span style="margin-left:6px;">v{{ detail.version || '-' }}</span>
      </div>

      <!-- Tab bar -->
      <div style="display:flex;gap:0;border-bottom:2px solid #e5e5e5;margin-bottom:20px;">
        <div :style="tabStyle('home')" @click="navigate('home')">Overview</div>
        <div :style="tabStyle('search')" @click="navigate('search')">Gene Search</div>
        <div :style="tabStyle('tf')" @click="navigate('tf')">Transcription Factors</div>

        <el-dropdown trigger="click" style="display:flex;">
          <div :style="tabStyle('tools')">Tools ▾</div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="navigate('tools/batch')">Batch Query</el-dropdown-item>
              <el-dropdown-item @click="navigate('tools/blast')">BLAST</el-dropdown-item>
              <el-dropdown-item @click="navigate('tools/download')">Download</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <router-view />
    </template>

    <el-empty v-else-if="!loading" description="Genome not found" />
  </div>
</template>
