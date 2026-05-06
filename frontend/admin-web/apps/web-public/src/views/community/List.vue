<script setup lang="ts">
import { ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useRequest } from '@/composables/useRequest';

const route = useRoute();
const { get } = useRequest();
const loading = ref(false);
const items = ref<any[]>([]);

const type = ref(route.params.type as string);
const typeLabel = ref('');

watch(() => route.params.type, (t) => {
  type.value = t as string;
  loadItems();
}, { immediate: true });

async function loadItems() {
  loading.value = true;
  try {
    const typeMap: Record<string, string> = { news: '1', conferences: '2' };
    const labelMap: Record<string, string> = { news: 'News', conferences: 'Conferences' };
    typeLabel.value = labelMap[type.value] || type.value;
    const newsType = typeMap[type.value] || '1';
    const data: any = await get(`/public/news?type=${newsType}`);
    items.value = data || [];
  } finally {
    loading.value = false;
  }
}
</script>
<template>
  <div>
    <h2>{{ typeLabel }}</h2>
    <div v-loading="loading">
      <div v-if="items.length === 0 && !loading" style="text-align:center;padding:40px;color:#999;">
        No {{ typeLabel.toLowerCase() }} available.
      </div>
      <div v-for="item in items" :key="item.id" style="padding:16px 0;border-bottom:1px solid #f0f0f0;">
        <h4 style="margin:0 0 4px;font-size:15px;">{{ item.title }}</h4>
        <p style="margin:0 0 6px;color:#666;font-size:13px;line-height:1.6;">{{ item.content }}</p>
        <div style="color:#999;font-size:11px;">
          <span v-if="item.author">{{ item.author }}</span>
          <span v-if="item.create_time" style="margin-left:8px;">{{ new Date(item.create_time * 1000).toLocaleDateString() }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
