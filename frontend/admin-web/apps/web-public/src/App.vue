<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useDatasetList } from '@/composables/useDatasets';
import AiFloatingButton from './components/AiChatDrawer/AiFloatingButton.vue';
import AiChatDrawer from './components/AiChatDrawer/index.vue';

const router = useRouter();
const chatVisible = ref(false);

const { items: genomes, load: loadGenomes } = useDatasetList();
onMounted(() => loadGenomes({ dataset_type: 'genome' }));

function goGenome(id: number) { router.push(`/genome/${id}`); }
</script>
<template>
  <div id="public-portal">
    <header class="portal-header">
      <router-link to="/" class="logo">Rose Database</router-link>

      <el-dropdown class="nav-dropdown">
        <span class="nav-link active">Genomes ▾</span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item v-for="g in genomes" :key="g.id" @click="goGenome(g.id)">
              {{ g.title || g.dataset_code }}
              <span style="color:#999;font-size:11px;margin-left:4px;">{{ g.organism }}</span>
            </el-dropdown-item>
            <el-dropdown-item divided>
              <router-link to="/" style="color:#409eff;font-size:12px;">View all genomes →</router-link>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <nav class="nav-links">
        <router-link to="/germplasm">Germplasm</router-link>
        <router-link to="/genotype">Genotype</router-link>
        <router-link to="/phenotype">Phenotype</router-link>
        <router-link to="/expression">Expression</router-link>
      </nav>

      <div style="flex:1;" />

      <el-dropdown class="nav-dropdown">
        <span class="nav-link">Tools ▾</span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="router.push('/tools/batch')">Batch Sequence Retrieval</el-dropdown-item>
            <el-dropdown-item @click="router.push('/tools/blast')">BLAST</el-dropdown-item>
            <el-dropdown-item @click="router.push('/tools/download')">Downloads</el-dropdown-item>
            <el-dropdown-item divided disabled>Primer Design <small>(soon)</small></el-dropdown-item>
            <el-dropdown-item disabled>GO Enrichment <small>(soon)</small></el-dropdown-item>
            <el-dropdown-item disabled>Sequence Converter <small>(soon)</small></el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </header>

    <main class="main-content">
      <router-view />
    </main>

    <footer class="portal-footer">
      China Agricultural University — Rose Database &copy; 2024-2026
    </footer>

    <AiFloatingButton @click="chatVisible = true" />
    <AiChatDrawer v-model:visible="chatVisible" />
  </div>
</template>

<style>
body { margin: 0; font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; }
#public-portal a { color: #606266; text-decoration: none; }
#public-portal a:hover { color: #409eff; }
#public-portal .router-link-active { color: #409eff; font-weight: 600; }

.portal-header {
  background: #fff; border-bottom: 1px solid #e5e5e5;
  padding: 0 24px; display: flex; align-items: center;
  height: 52px; gap: 0;
}
.logo { font-size: 18px; font-weight: 700; color: #303133 !important; margin-right: 10px; }
.logo:hover { color: #409eff !important; }
.nav-dropdown { margin: 0 4px; }
.nav-link { font-size: 14px; cursor: pointer; color: #606266; padding: 8px 6px; }
.nav-link:hover { color: #409eff; }
.nav-links { display: flex; gap: 16px; font-size: 14px; margin-left: 12px; }
.main-content { max-width: 1200px; margin: 0 auto; padding: 24px; min-height: 80vh; }
.portal-footer { border-top: 1px solid #e5e5e5; padding: 16px; text-align: center; color: #999; font-size: 12px; }
</style>
