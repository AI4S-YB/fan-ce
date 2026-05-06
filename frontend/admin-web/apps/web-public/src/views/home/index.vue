<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useDatasetList } from '@/composables/useDatasets';
import { useRequest } from '@/composables/useRequest';

const router = useRouter();
const { loading, items, total, load } = useDatasetList();
const { get } = useRequest();

const keyword = ref('');
const typeFilter = ref('');

// ── News section ──
const newsItems = ref<any[]>([]);
async function loadNews() {
  try { newsItems.value = await get('/public/news?type=1'); } catch { /* optional */ }
}
onMounted(() => { loadNews(); });

const typeOptions = [
  { value: 'genome', label: 'Genome' },
  { value: 'transcriptome', label: 'Transcriptome' },
  { value: 'variome', label: 'Variome' },
  { value: 'phenome', label: 'Phenome' },
  { value: 'annotation', label: 'Annotation' },
  { value: 'interaction', label: 'Interaction' },
  { value: 'signal', label: 'Signal' },
];

const typeLabelMap: Record<string, string> = {
  genome: 'Genome',
  transcriptome: 'Transcriptome',
  variome: 'Variome',
  phenome: 'Phenome',
  annotation: 'Annotation',
  interaction: 'Interaction',
  signal: 'Signal',
};

const typeColorMap: Record<string, string> = {
  genome: '#67c23a',
  transcriptome: '#409eff',
  variome: '#e6a23c',
  phenome: '#f56c6c',
};

function typeLabel(type?: string): string {
  return typeLabelMap[type || ''] || type || '-';
}

function typeColor(type?: string): string {
  return typeColorMap[type || ''] || '#909399';
}

function onSearch() {
  const params: Record<string, unknown> = {};
  if (keyword.value) params.keyword = keyword.value;
  if (typeFilter.value) params.dataset_type = typeFilter.value;
  load(params);
}

onMounted(() => {
  load({});
});
</script>

<template>
  <div>
    <!-- News Section -->
    <div v-if="newsItems.length > 0" style="margin-bottom:32px;padding-bottom:20px;border-bottom:1px solid #e5e5e5;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3 style="margin:0;font-size:16px;">News & Updates</h3>
        <router-link to="/community/news" style="font-size:13px;color:#409eff;">View all →</router-link>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:12px;">
        <div v-for="item in newsItems.slice(0, 3)" :key="item.id" style="padding:12px 16px;background:#f9fafb;border-radius:6px;">
          <h4 style="margin:0 0 4px;font-size:14px;">{{ item.title }}</h4>
          <p style="margin:0 0 4px;color:#666;font-size:12px;line-height:1.5;">{{ (item.content || '').substring(0, 120) }}{{ item.content?.length > 120 ? '...' : '' }}</p>
          <span style="color:#999;font-size:11px;">{{ item.create_time ? new Date(item.create_time * 1000).toLocaleDateString() : '' }}</span>
        </div>
      </div>
    </div>

    <!-- Search & Filter -->
    <div style="display:flex;gap:12px;margin-bottom:24px;">
      <el-input
        v-model="keyword"
        placeholder="Search datasets..."
        clearable
        style="width:400px;"
        @input="onSearch"
      />
      <el-select
        v-model="typeFilter"
        placeholder="All types"
        clearable
        style="width:180px;"
        @change="onSearch"
      >
        <el-option
          v-for="t in typeOptions"
          :key="t.value"
          :label="t.label"
          :value="t.value"
        />
      </el-select>
    </div>

    <!-- Loading / Empty / Cards -->
    <div v-loading="loading">
      <el-empty
        v-if="!loading && items.length === 0"
        description="No datasets found"
      />
      <div
        v-else
        style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;"
      >
        <el-card
          v-for="item in items"
          :key="item.id"
          shadow="hover"
          style="cursor:pointer;"
          @click="router.push('/dataset/' + item.id)"
        >
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <h3 style="margin:0 0 8px;font-size:16px;">
              {{ item.title || item.dataset_code }}
            </h3>
            <el-tag
              :color="typeColor(item.dataset_type)"
              effect="dark"
              size="small"
              style="color:#fff;"
            >
              {{ typeLabel(item.dataset_type) }}
            </el-tag>
          </div>
          <div style="color:#888;font-size:13px;">
            <div v-if="item.organism">{{ item.organism }}</div>
            <div>Version: {{ item.version || '-' }}</div>
          </div>
        </el-card>
      </div>
      <div
        v-if="total > 0"
        style="text-align:center;margin-top:16px;color:#999;"
      >
        {{ total }} datasets
      </div>
    </div>
  </div>
</template>
