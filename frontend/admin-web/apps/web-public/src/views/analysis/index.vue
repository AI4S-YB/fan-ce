<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRequest } from '@/composables/useRequest';

const { get } = useRequest();

interface ToolInfo {
  tool_id: string; display_name: string; description: string;
  category: string; version: string;
}

const tools = ref<ToolInfo[]>([]);
const loading = ref(true);

onMounted(async () => {
  try {
    tools.value = await get('/analysis/tools');
  } catch { /* ignore */ }
  finally { loading.value = false; }
});
</script>

<template>
  <div style="max-width:900px;margin:0 auto;padding:24px 16px;">
    <h2 style="margin:0 0 4px;">Analysis Tools</h2>
    <p style="color:#888;font-size:13px;margin:0 0 20px;">Select a tool to start a new analysis</p>

    <div v-loading="loading">
      <div v-if="tools.length === 0 && !loading" style="text-align:center;padding:60px;color:#999;">
        No analysis tools available
      </div>

      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;">
        <router-link
          v-for="t in tools"
          :key="t.tool_id"
          :to="'/analysis/' + t.tool_id"
          style="display:block;padding:16px;background:#f9fafb;border:1px solid #e5e5e5;border-radius:8px;text-decoration:none;color:#303133;transition:all .2s;"
          onmouseover="this.style.borderColor='#409eff';this.style.boxShadow='0 2px 8px rgba(64,158,255,0.1)'"
          onmouseout="this.style.borderColor='#e5e5e5';this.style.boxShadow='none'"
        >
          <h4 style="margin:0 0 4px;font-size:14px;">{{ t.display_name }}</h4>
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
            <span style="font-size:11px;color:#909399;background:#f0f0f0;padding:1px 6px;border-radius:3px;">{{ t.category }}</span>
            <span style="font-size:11px;color:#c0c4cc;">v{{ t.version }}</span>
          </div>
          <p style="margin:0;color:#888;font-size:12px;line-height:1.4;">{{ t.description }}</p>
        </router-link>
      </div>
    </div>
  </div>
</template>
