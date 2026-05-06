<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useDatasetList } from '@/composables/useDatasets';
import { useRequest } from '@/composables/useRequest';
import AiFloatingButton from './components/AiChatDrawer/AiFloatingButton.vue';
import AiChatDrawer from './components/AiChatDrawer/index.vue';

const router = useRouter();
const chatVisible = ref(false);
const { get } = useRequest();

interface SiteInfo {
  site_name: string;
  site_title: string;
  logo_text: string;
  filing_no: string;
  contact_email: string;
  footer_copyright: string;
}

const siteInfo = ref<SiteInfo>({
  site_name: 'Rose Database',
  site_title: 'Rose Genomics Data Platform',
  logo_text: 'Rose DB',
  filing_no: '',
  contact_email: '',
  footer_copyright: '',
});

async function loadSiteInfo() {
  try {
    const data = await get<SiteInfo>('/public/site-info');
    if (data && data.site_name) {
      siteInfo.value = data;
      if (data.site_title) {
        document.title = data.site_title;
      }
    }
  } catch {
    // use defaults
  }
}

const { items: genomes, load: loadGenomes } = useDatasetList();
onMounted(() => {
  loadGenomes({ dataset_type: 'genome' });
  loadSiteInfo();
});

function goGenome(id: number) {
  console.log('goGenome called with id:', id);
  router.push(`/genome/${id}`);
}
</script>
<template>
  <div id="public-portal">
    <header class="portal-header">
      <router-link to="/" class="logo">{{ siteInfo.logo_text || siteInfo.site_name }}</router-link>

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

      <el-dropdown class="nav-dropdown">
        <span class="nav-link">Community ▾</span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="router.push('/community/news')">News</el-dropdown-item>
            <el-dropdown-item @click="router.push('/community/conferences')">Conferences</el-dropdown-item>
            <el-dropdown-item divided disabled>Links <small>(soon)</small></el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </header>

    <main class="main-content">
      <router-view />
    </main>

    <footer class="portal-footer">
      <span>{{ siteInfo.footer_copyright || siteInfo.site_name }}</span>
      <span v-if="siteInfo.filing_no" class="footer-divider">|</span>
      <a v-if="siteInfo.filing_no" href="https://beian.miit.gov.cn/" target="_blank" rel="noopener">{{ siteInfo.filing_no }}</a>
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
.portal-footer a { color: #999; text-decoration: none; }
.portal-footer a:hover { color: #409eff; }
.footer-divider { margin: 0 8px; }
</style>
