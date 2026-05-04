# Public Database Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new public database frontend (`apps/web-public`) — Vue 3 + Element Plus + ECharts, 7 pages, all data via Dataset public API.

**Architecture:** Independent Vite app in admin-web monorepo. Lightweight — no vben framework, no auth. Three-step query pattern: Select Dataset → Capabilities → Execute.

**Tech Stack:** Vue 3.5, Element Plus 2.9, ECharts 5.6, Pinia 3.0, Vite 6.3 — all already in pnpm workspace catalog.

---

### Task 1: Scaffold New App

**Files:**
- Create: `frontend/admin-web/apps/web-public/package.json`
- Create: `frontend/admin-web/apps/web-public/vite.config.ts`
- Create: `frontend/admin-web/apps/web-public/tsconfig.json`
- Create: `frontend/admin-web/apps/web-public/index.html`
- Create: `frontend/admin-web/apps/web-public/src/main.ts`
- Create: `frontend/admin-web/apps/web-public/src/App.vue`
- Create: `frontend/admin-web/apps/web-public/src/router/index.ts`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "@fan-ce/web-public",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1 --port 5677",
    "build": "vue-tsc && vite build",
    "preview": "vite preview --host 127.0.0.1 --port 5678"
  },
  "dependencies": {
    "vue": "catalog:",
    "vue-router": "catalog:",
    "pinia": "catalog:",
    "element-plus": "catalog:",
    "echarts": "catalog:",
    "axios": "catalog:",
    "@vueuse/core": "catalog:"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "catalog:",
    "typescript": "catalog:",
    "vite": "catalog:"
  }
}
```

- [ ] **Step 2: Create vite.config.ts**

```typescript
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5677,
    proxy: {
      '/api/v1': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "jsx": "preserve",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "noEmit": true,
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.vue"]
}
```

- [ ] **Step 4: Create index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><title>Rose Database</title></head>
  <body><div id="app"></div><script type="module" src="/src/main.ts"></script></body>
</html>
```

- [ ] **Step 5: Create src/main.ts**

```typescript
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import App from './App.vue';
import router from './router';

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.use(ElementPlus);
app.mount('#app');
```

- [ ] **Step 6: Create src/App.vue**

```vue
<script setup lang="ts">
import Header from './components/layout/Header.vue';
import Footer from './components/layout/Footer.vue';
</script>
<template>
  <Header />
  <main style="max-width:1200px;margin:0 auto;padding:20px;min-height:80vh;">
    <router-view />
  </main>
  <Footer />
</template>
```

- [ ] **Step 7: Create src/router/index.ts** (all 7 routes, lazy-loaded)

```typescript
import { createRouter, createWebHistory } from 'vue-router';

const routes = [
  { path: '/', component: () => import('@/views/home/index.vue') },
  { path: '/dataset/:id', component: () => import('@/views/dataset/Detail.vue') },
  { path: '/genome/:id', component: () => import('@/views/genome/Overview.vue'), children: [
    { path: '', redirect: to => ({ path: 'home', query: to.query }) },
    { path: 'home', component: () => import('@/views/genome/Home.vue') },
    { path: 'search', component: () => import('@/views/genome/Search.vue') },
    { path: 'batch', component: () => import('@/views/genome/BatchQuery.vue') },
    { path: 'blast', component: () => import('@/views/genome/Blast.vue') },
    { path: 'download', component: () => import('@/views/genome/Download.vue') },
    { path: 'geneinfo', component: () => import('@/views/genome/GeneInfo.vue') },
  ]},
  { path: '/expression', component: () => import('@/views/expression/index.vue') },
  { path: '/genotype', component: () => import('@/views/genotype/index.vue') },
  { path: '/germplasm', component: () => import('@/views/germplasm/index.vue') },
  { path: '/phenotype', component: () => import('@/views/phenotype/index.vue') },
];

export default createRouter({ history: createWebHistory(), routes });
```

- [ ] **Step 8: Install deps and verify dev server starts**

```bash
cd frontend/admin-web && pnpm install && cd apps/web-public && pnpm dev
```

Expected: Vite starts on port 5677, `curl http://127.0.0.1:5677` returns 200.

- [ ] **Step 9: Commit**

```bash
git add frontend/admin-web/apps/web-public/ && git commit -m "feat: scaffold public database frontend app"
```

---

### Task 2: HTTP Client + Dataset API Composables

**Files:**
- Create: `src/composables/useRequest.ts`
- Create: `src/composables/useDatasets.ts`
- Create: `src/types/dataset.ts`

- [ ] **Step 1: Create src/types/dataset.ts** — TypeScript interfaces

```typescript
export interface PublicDatasetItem {
  id: number; dataset_code?: string; title?: string;
  dataset_type?: string; organism?: string; version?: string;
  lifecycle_state?: string; visibility?: string;
  description_md?: string; extra_json?: string;
}
export interface PublicDatasetDetail extends PublicDatasetItem {
  query_profile?: { file_format?: string; query_engine?: string };
  query_entry_asset?: { asset_code?: string };
  assets?: PublicAssetItem[];
  current_version?: { id: number; version?: string };
  lineage?: PublicLineageItem[];
}
export interface PublicAssetItem {
  id: number; asset_code?: string; asset_name?: string;
  asset_type?: string; file_format?: string; is_query_entry?: boolean;
  files?: PublicAssetFileItem[];
}
export interface PublicAssetFileItem {
  id: number; file_role?: string; file_name?: string;
  file_format?: string; file_size?: number;
}
export interface PublicLineageItem {
  id: number; relation_type?: string; direction?: string;
  src_dataset_title?: string; src_dataset_type?: string;
  dst_dataset_title?: string; dst_dataset_type?: string;
}
export interface QueryCapabilities {
  operations?: string[];
  filter_options?: Record<string, string[]>;
}
export interface QueryResult {
  rows: Record<string, unknown>[]; total: number; download_url?: string;
}
```

- [ ] **Step 2: Create src/composables/useRequest.ts**

```typescript
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const client = axios.create({ baseURL: API_BASE });

// Response unwrap: backend returns { code: 2000, data: ... }
client.interceptors.response.use(res => {
  const body = res.data;
  if (body?.code === 2000 && body.data !== undefined) return body.data;
  return body;
});

export function useRequest() {
  return { get: client.get, post: client.post };
}
```

- [ ] **Step 3: Create src/composables/useDatasets.ts**

```typescript
import { ref } from 'vue';
import { useRequest } from './useRequest';
import type { PublicDatasetItem, PublicDatasetDetail, QueryCapabilities, QueryResult } from '@/types/dataset';

const { post } = useRequest();
const pre = '/public/dataset';

export function useDatasets() {
  const listLoading = ref(false);
  const listData = ref<PublicDatasetItem[]>([]);
  const listTotal = ref(0);

  async function loadList(params: Record<string, unknown> = {}) {
    listLoading.value = true;
    try {
      const data = await post(`${pre}/list`, { page: 1, size: 50, ...params });
      listData.value = data?.items || data?.dataList || [];
      listTotal.value = data?.total || 0;
    } finally { listLoading.value = false; }
  }

  return { listLoading, listData, listTotal, loadList };
}

export function useDatasetDetail() {
  const { post } = useRequest();
  const loading = ref(false);
  const detail = ref<PublicDatasetDetail | null>(null);

  async function load(id: number) {
    loading.value = true;
    try { detail.value = await post(`${pre}/info`, { id }); }
    finally { loading.value = false; }
  }

  return { loading, detail, load };
}

export function useDatasetQuery() {
  const { post } = useRequest();
  const queryLoading = ref(false);
  const queryResult = ref<QueryResult | null>(null);

  async function capabilities(datasetId: number, versionId?: number): Promise<QueryCapabilities> {
    return post(`${pre}/query/capabilities`, { dataset_id: datasetId, version_id: versionId });
  }

  async function execute(datasetId: number, operation: string, params: Record<string, unknown>, versionId?: number) {
    queryLoading.value = true;
    try {
      queryResult.value = await post(`${pre}/query/execute`, {
        dataset_id: datasetId, version_id: versionId, operation, params,
      });
    } finally { queryLoading.value = false; }
  }

  return { queryLoading, queryResult, capabilities, execute };
}
```

- [ ] **Step 4: Commit**

---

### Task 3: Layout + Home Page

**Files:**
- Create: `src/components/layout/Header.vue`
- Create: `src/components/layout/Footer.vue`
- Create: `src/views/home/index.vue`

- [ ] **Step 1: Header.vue** — Logo/title left, nav links (Genome, Expression, Genotype, Germplasm, Phenotype) right. Use Element Plus `el-menu` horizontal mode.
- [ ] **Step 2: Footer.vue** — Simple centered footer with institution info.
- [ ] **Step 3: Home page** — Dataset catalog cards with search bar. Filter by dataset_type. Each card shows title, organism, type tag, version. Click → navigate to `/dataset/:id`.
- [ ] **Step 4: Commit**

---

### Task 4: Dataset Detail Page

**Files:**
- Create: `src/views/dataset/Detail.vue`
- Create: `src/components/LineagePanel.vue`

- [ ] **Step 1: Detail.vue** — Shows dataset metadata (title, organism, type, lifecycle, visibility), description_md rendered as markdown, extra_json as key-value table, assets/files table, version list. Back button to home.
- [ ] **Step 2: LineagePanel.vue** — Calls `GET /public/dataset/{code}/lineage`. Renders upstream/downstream edges as a simple table with relation type, direction, linked dataset name.
- [ ] **Step 3: Commit**

---

### Task 5: Genome Browser Pages

**Files:**
- Create: `src/views/genome/Overview.vue`
- Create: `src/views/genome/Home.vue`
- Create: `src/views/genome/Search.vue`
- Create: `src/views/genome/BatchQuery.vue`
- Create: `src/views/genome/Blast.vue`
- Create: `src/views/genome/Download.vue`
- Create: `src/views/genome/GeneInfo.vue`
- Create: `src/components/CompositeSearchForm.vue`

- [ ] **Step 1: Overview.vue** — Parent with `DatasetSelector` (type=genome). After selection, shows tab navigation (Home, Search, Batch Query, Blast, Download). Uses `router-view` for children, passes dataset info via `provide/inject`.
- [ ] **Step 2: Home.vue** — Genome stats cards (genome size, gene count, BUSCO, N50). Display `description_md` and key extra_json attributes.
- [ ] **Step 3: Search.vue** — `CompositeSearchForm` + results table with pagination. Gene ID click → navigate to GeneInfo.
- [ ] **Step 4: BatchQuery.vue** — Gene ID list textarea + sequence type selector (genome/mRNA/CDS/protein). Query button → table of sequences with download.
- [ ] **Step 5: Blast.vue** — Sequence input textarea + BLAST button → results table.
- [ ] **Step 6: Download.vue** — File list from assets, with download links.
- [ ] **Step 7: GeneInfo.vue** — Single gene detail (gene ID, chrom, position, strand, description, transcripts).
- [ ] **Step 8: Commit**

---

### Task 6: Expression Query Page

**Files:**
- Create: `src/views/expression/index.vue`
- Create: `src/components/DataVisualization/index.vue`
- Create: `src/components/MultiSelectDropdown.vue`

- [ ] **Step 1: index.vue** — `DatasetSelector` (type=transcriptome). On select → fetch capabilities → populate gene multi-select + sample multi-select + matrix type dropdown. Query button → `DataVisualization`.
- [ ] **Step 2: DataVisualization/index.vue** — Tab toggle: Table (el-table with sortable columns, pagination) | Heatmap (ECharts heatmap with row/col labels, color scale). Props: `columns, rows, heatmapData, loading`.
- [ ] **Step 3: MultiSelectDropdown.vue** — Wraps `el-select` with `multiple`, `filterable`, "Select All" / "Clear" actions.
- [ ] **Step 4: Commit**

---

### Task 7: Genotype + Phenotype + Germplasm Pages

**Files:**
- Create: `src/views/genotype/index.vue`
- Create: `src/views/phenotype/index.vue`
- Create: `src/views/germplasm/index.vue`

- [ ] **Step 1: genotype/index.vue** — `DatasetSelector` (type=variome). Chromosome + position range inputs. Quick-fill example button. Query → `DataVisualization` + VCF download link.
- [ ] **Step 2: phenotype/index.vue** — `DatasetSelector` (type=phenome). Trait multi-select + sample multi-select. Query → `DataVisualization`.
- [ ] **Step 3: germplasm/index.vue** — `DatasetSelector` (type=germplasm). Searchable table with keyword filter. Click row → detail modal (attributes, relationships, knowledge graph).
- [ ] **Step 4: Commit**

---

### Task 8: AiChatDrawer

**Files:**
- Create: `src/components/AiChatDrawer/index.vue`
- Create: `src/components/AiChatDrawer/AiFloatingButton.vue`

- [ ] **Step 1: AiFloatingButton.vue** — Fixed position floating button (bottom-right). Click → toggle drawer.
- [ ] **Step 2: AiChatDrawer/index.vue** — Slide-out drawer with chat interface. Context-aware: reads current route, if on dataset page → auto-injects `description_md` + `extra_json` into system prompt. Calls backend LLM API (existing agent endpoint). Renders markdown responses.
- [ ] **Step 3: Commit**

---

### Task 9: Polish + Build Verification

- [ ] **Step 1:** Add loading states (el-skeleton) to all pages
- [ ] **Step 2:** Add error handling (el-alert) for API failures
- [ ] **Step 3:** Verify `pnpm build` passes for web-public
- [ ] **Step 4:** Verify dev server on port 5677 serves all 7 pages
- [ ] **Step 5:** Add `dev:public` and `build:public` scripts to admin-web root package.json
- [ ] **Step 6:** Commit
