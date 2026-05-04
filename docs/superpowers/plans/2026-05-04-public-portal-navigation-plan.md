# Public Portal — Navigation & Genome Detail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure public portal navigation with Genomes dropdown, genome internal tabs (Overview, Gene Search, TF, Tools), and global Tools menu.

**Architecture:** Header links to modules; genome internal page has its own tab bar with dropdown menus. Tools are accessible both globally and scoped to a genome.

---

### Task 1: Restructure Header Navigation

**Files:**
- Modify: `src/App.vue` — complete header rewrite
- Modify: `src/router/index.ts` — add new routes

- [ ] **Step 1: Rewrite header in App.vue**

Replace current `el-menu` with custom navigation bar:

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useDatasetList } from '@/composables/useDatasets';
import AiFloatingButton from './components/AiChatDrawer/AiFloatingButton.vue';
import AiChatDrawer from './components/AiChatDrawer/index.vue';

const router = useRouter();
const chatVisible = ref(false);

// Load genome list for dropdown
const { items: genomes, load: loadGenomes } = useDatasetList();
onMounted(() => loadGenomes({ dataset_type: 'genome' }));

function goGenome(id: number) { router.push(`/genome/${id}`); }
</script>
<template>
  <div id="public-portal">
    <header style="background:#fff;border-bottom:1px solid #e5e5e5;padding:0 24px;display:flex;align-items:center;height:52px;gap:0;">
      <router-link to="/" style="font-size:18px;font-weight:700;text-decoration:none;color:#303133;margin-right:24px;">Rose Database</router-link>
      
      <!-- Genomes dropdown -->
      <el-dropdown style="margin-right:16px;">
        <span style="font-size:14px;cursor:pointer;color:#409eff;">Genomes ▾</span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item v-for="g in genomes" :key="g.id" @click="goGenome(g.id)">
              {{ g.title || g.dataset_code }}
              <span style="color:#999;font-size:11px;">{{ g.organism }}</span>
            </el-dropdown-item>
            <el-dropdown-item divided>
              <router-link to="/" style="color:#409eff;">View all genomes...</router-link>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <nav style="display:flex;gap:20px;font-size:14px;">
        <router-link to="/germplasm">Germplasm</router-link>
        <router-link to="/genotype">Genotype</router-link>
        <router-link to="/phenotype">Phenotype</router-link>
        <router-link to="/expression">Expression</router-link>
      </nav>

      <div style="flex:1;" />

      <!-- Tools dropdown -->
      <el-dropdown style="margin-right:16px;">
        <span style="font-size:14px;cursor:pointer;color:#409eff;">Tools ▾</span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="router.push('/tools/batch')">Batch Sequence Retrieval</el-dropdown-item>
            <el-dropdown-item @click="router.push('/tools/blast')">BLAST</el-dropdown-item>
            <el-dropdown-item @click="router.push('/tools/download')">Genome Downloads</el-dropdown-item>
            <el-dropdown-item divided disabled>Primer Design <small>(coming soon)</small></el-dropdown-item>
            <el-dropdown-item disabled>GO Enrichment <small>(coming soon)</small></el-dropdown-item>
            <el-dropdown-item disabled>Sequence Converter <small>(coming soon)</small></el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </header>
    <main style="max-width:1200px;margin:0 auto;padding:24px;min-height:80vh;">
      <router-view />
    </main>
    <footer style="border-top:1px solid #e5e5e5;padding:16px;text-align:center;color:#999;font-size:12px;">
      China Agricultural University — Rose Database &copy; 2024-2026
    </footer>
    <AiFloatingButton @click="chatVisible = true" />
    <AiChatDrawer v-model:visible="chatVisible" />
  </div>
</template>
```

### Task 2: Restructure Genome Overview + Tab Bar

**Files:**
- Modify: `src/views/genome/Overview.vue` — add dropdown tab bar
- Create: `src/views/genome/TranscriptionFactors.vue`
- Create: `src/views/genome/Tools.vue` — tool switcher page
- Modify: `src/router/index.ts` — update genome child routes

- [ ] **Step 1: Update router**

```typescript
{
  path: '/genome/:id',
  component: () => import('@/views/genome/Overview.vue'),
  children: [
    { path: '', redirect: (to: any) => ({ path: 'home', query: to.query }) },
    { path: 'home', component: () => import('@/views/genome/Home.vue') },
    { path: 'search', component: () => import('@/views/genome/GeneSearch.vue') },
    { path: 'tf', component: () => import('@/views/genome/TranscriptionFactors.vue') },
    { path: 'tools/:tool', component: () => import('@/views/genome/Tools.vue') },
  ],
},
// Standalone tools route
{ path: '/tools/:tool', component: () => import('@/views/genome/Tools.vue') },
```

- [ ] **Step 2: Rewrite genome Overview.vue tab bar**

Replace `el-tabs` with a custom tab bar that supports dropdown menus:

```vue
<script setup lang="ts">
import { ref, computed, provide, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDatasetDetail } from '@/composables/useDatasets';
import type { PublicDatasetDetail } from '@/types/dataset';

const route = useRoute();
const router = useRouter();
const { loading, detail, load } = useDatasetDetail();

const genomeId = computed(() => Number(route.params.id));
watch(() => route.params.id, (id) => load(Number(id)), { immediate: true });
provide('genomeDetail', detail);
provide('genomeLoading', loading);

const activeTab = computed(() => {
  const path = route.path;
  if (path.endsWith('/search')) return 'search';
  if (path.endsWith('/tf')) return 'tf';
  if (path.includes('/tools/')) return 'tools';
  return 'home';
});

function navigate(path: string) {
  router.push(`/genome/${genomeId.value}${path}`);
}
</script>
<template>
  <div v-loading="loading">
    <el-button text @click="router.push('/')">← Back</el-button>
    <template v-if="detail">
      <h2 style="margin:8px 0 4px;">{{ detail.title || detail.dataset_code }}</h2>
      <div style="color:#888;font-size:12px;margin-bottom:12px;">
        <el-tag size="small">{{ detail.dataset_type }}</el-tag>
        {{ detail.organism }} &nbsp; v{{ detail.version }}
      </div>
      
      <!-- Tab bar with dropdowns -->
      <div style="display:flex;gap:0;border-bottom:2px solid #e5e5e5;margin-bottom:20px;">
        <div @click="navigate('/home')" :style="tabStyle('home')">Overview</div>
        
        <el-dropdown trigger="click" style="display:flex;">
          <div :style="tabStyle('search')">Gene Search ▾</div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="navigate('/search')">Search Genes</el-dropdown-item>
              <el-dropdown-item @click="navigate('/tf')">Transcription Factors</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-dropdown trigger="click" style="display:flex;">
          <div :style="tabStyle('tools')">Tools ▾</div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="navigate('/tools/batch')">Batch Query</el-dropdown-item>
              <el-dropdown-item @click="navigate('/tools/blast')">BLAST</el-dropdown-item>
              <el-dropdown-item @click="navigate('/tools/download')">Download</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      
      <router-view />
    </template>
  </div>
</template>
<script lang="ts">
function tabStyle(active: string) {
  const isActive = (this as any).activeTab === active;
  return {
    padding: '10px 20px', cursor: 'pointer', fontSize: '14px',
    color: isActive ? '#409eff' : '#606266',
    borderBottom: isActive ? '2px solid #409eff' : '2px solid transparent',
    marginBottom: '-2px', fontWeight: isActive ? '600' : '400',
  };
}
</script>
```

IMPORTANT: Convert the Options API `tabStyle` function to Composition API. Use a function that returns a computed style object.

### Task 3: Create Transcription Factors Page

**Files:**
- Create: `src/views/genome/TranscriptionFactors.vue`

- [ ] Design: Left panel (TF family list) + Right panel (member table). Uses `useDatasetQuery()` to fetch TF data from functional_annotation asset. Query operation: `gene_search` with family filter.

### Task 4: Create Tools Page (Tool Switcher)

**Files:**
- Create: `src/views/genome/Tools.vue`

- [ ] Reads `:tool` from route params. Renders the appropriate tool component (BatchQuery / Blast / Download). Reuses existing components from old genome tabs where possible.

### Task 5: Clean Up Old Routes & Pages

- [ ] Remove old genome child routes no longer needed
- [ ] Remove or repurpose old BatchQuery/Blast/Download/GeneInfo pages into Tools.vue sub-components
- [ ] Verify no broken imports

### Task 6: Build Verification

- [ ] `pnpm build` passes with no TypeScript errors
- [ ] Dev server serves all routes
- [ ] Header navigation works (dropdowns, links)
- [ ] Genome tabs switch correctly
- [ ] Commit
