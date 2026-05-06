# Genotype Page Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 3-input genotype page with a unified smart search + per-sample genotype display.

**Architecture:** Single search box auto-detects gene/region/variant-ID input. Backend gains `query_by_id` for direct variant ID lookup. Frontend gains SmartSearchBar, VariantTable (expandable per-sample rows), SampleFilter, and VariantDensityPlot components.

**Tech Stack:** Vue 3 + TypeScript + Element Plus + ECharts (existing), bcftools (existing backend)

---

### Task 1: Backend — query_by_id operation in variant adapter

**Files:**
- Modify: `backend/api-server/apps/datasets/adapters/variant.py`

- [ ] **Step 1: Add `query_by_id` operation**

In `variant.py`, add to `describe()` supported_operations and examples:
```python
"supported_operations": ["region_example", "samples_list", "query", "query_by_id"],
"examples": {
    ...
    "query_by_id": {"operation": "query_by_id", "params": {"variant_ids": ["Cla97Chr04_15442323"]}},
},
```

- [ ] **Step 2: Add `query_by_id` branch in `execute()`**

After the `query` operation block (line ~150), add:
```python
if operation == "query_by_id":
    variant_ids: List[str] = params.get("variant_ids") or []
    if not variant_ids:
        raise HTTPException(status_code=400, detail="variant_ids is required")
    id_filter = " || ".join(f'ID="{vid}"' for vid in variant_ids)
    cmd = ["bcftools", "view", "-i", id_filter, file_path]
    result_proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result_proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"bcftools query_by_id failed: {result_proc.stderr}")
    output = result_proc.stdout
    count = sum(1 for line in output.split("\n") if line and not line.startswith("#"))
    file_id = f"{uuid.uuid4()}.vcf.gz"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    final_path = f"{DOWNLOAD_DIR}/{file_id}"
    shutil.copyfile(file_path, final_path)
    return {
        "adapter": self.adapter_name,
        "operation": operation,
        "dataset_id": dataset_payload["id"],
        "data": {
            "count": count,
            "size": len(output.encode()),
            "preview": output if len(output.encode()) <= 1024 * 1024 else None,
            "download_url": f"{DOWNLOAD_BASE_URL}/{file_id}",
        },
    }
```

- [ ] **Step 3: Restart backend and verify**

```bash
bash scripts/dev/start-backend.sh
```

Verify via curl:
```bash
# Test with ds-21 (Rose Variome)
curl -s "http://localhost:8002/api/v1/dataset/query/execute" \
  -H "Content-Type: application/json" \
  -d '{"dataset_id":22, "operation":"query_by_id", "params":{"variant_ids":["Cla97Chr04_15442323"]}}' \
  | python -m json.tool | head -20
```

- [ ] **Step 4: Commit**

```bash
git add backend/api-server/apps/datasets/adapters/variant.py
git commit -m "feat: add query_by_id operation to variant adapter for variant ID lookup"
```

---

### Task 2: Frontend — SmartSearchBar component

**Files:**
- Create: `frontend/admin-web/apps/web-public/src/components/SmartSearchBar.vue`

- [ ] **Step 1: Create component with props/emits**

```vue
<script setup lang="ts">
import { ref, computed } from 'vue';

const props = defineProps<{
  placeholder?: string;
}>();

const emit = defineEmits<{
  search: [payload: { type: 'gene' | 'region' | 'variant_id'; value: string }];
}>();

const input = ref('');

const detectedType = computed<'gene' | 'region' | 'variant_id' | null>(() => {
  const v = input.value.trim();
  if (!v) return null;
  // Region: chr:start-end or chr:start
  if (/^[a-zA-Z0-9_]+:\d+(-\d+)?$/.test(v)) return 'region';
  // Variant ID: chrom_pos (underscore with digits on both sides)
  if (/^[a-zA-Z0-9_]+_\d+$/.test(v)) return 'variant_id';
  // Gene ID: alphanumeric, may contain dots
  if (/^[a-zA-Z0-9._]+$/.test(v) && v.length >= 3) return 'gene';
  return null;
});

const typeLabel = computed(() => {
  switch (detectedType.value) {
    case 'gene': return 'Gene';
    case 'region': return 'Region';
    case 'variant_id': return 'Variant ID';
    default: return '';
  }
});

function onSubmit() {
  const v = input.value.trim();
  if (!v || !detectedType.value) return;
  emit('search', { type: detectedType.value, value: v });
}
</script>

<template>
  <div>
    <el-input
      v-model="input"
      :placeholder="placeholder || 'Search genes, regions, or variant IDs...'"
      size="large"
      clearable
      @keyup.enter="onSubmit"
    >
      <template #prepend>
        <el-tag v-if="detectedType" size="small" effect="plain">{{ typeLabel }}</el-tag>
        <span v-else style="color:#bbb;">Type...</span>
      </template>
      <template #append>
        <el-button :disabled="!detectedType" @click="onSubmit">Go</el-button>
      </template>
    </el-input>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/admin-web/apps/web-public/src/components/SmartSearchBar.vue
git commit -m "feat: add SmartSearchBar component with input type auto-detection"
```

---

### Task 3: Frontend — SampleFilter component

**Files:**
- Create: `frontend/admin-web/apps/web-public/src/components/SampleFilter.vue`

- [ ] **Step 1: Create SampleFilter component**

```vue
<script setup lang="ts">
import { ref, watch } from 'vue';

const props = defineProps<{
  samples: string[];
  loading?: boolean;
}>();

const emit = defineEmits<{
  update: [selected: string[]];
}>();

const expanded = ref(false);
const selected = ref<string[]>([]);
const searchText = ref('');

const filteredSamples = computed(() => {
  const q = searchText.value.toLowerCase();
  if (!q) return props.samples;
  return props.samples.filter(s => s.toLowerCase().includes(q));
});

watch(selected, (v) => emit('update', v), { deep: true });

function selectAll() { selected.value = [...props.samples]; }
function clearAll() { selected.value = []; }
</script>

<template>
  <div>
    <el-button text size="small" @click="expanded = !expanded">
      {{ expanded ? '▲' : '▼' }} Samples ({{ samples.length }})
    </el-button>
    <div v-if="expanded" style="margin-top:8px;padding:12px;background:#fafafa;border-radius:6px;">
      <el-input v-model="searchText" placeholder="Filter samples..." size="small" style="margin-bottom:8px;" clearable />
      <div style="margin-bottom:4px;">
        <el-button text size="small" @click="selectAll">Select All</el-button>
        <el-button text size="small" @click="clearAll">Clear</el-button>
        <span style="color:#888;font-size:12px;">{{ selected.length }} selected</span>
      </div>
      <el-select v-model="selected" multiple :filter-method="() => {}" style="width:100%;" collapse-tags collapse-tags-tooltip>
        <el-option v-for="s in filteredSamples" :key="s" :label="s" :value="s" />
      </el-select>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/admin-web/apps/web-public/src/components/SampleFilter.vue
git commit -m "feat: add SampleFilter component with multi-select and search"
```

---

### Task 4: Frontend — VariantTable component

**Files:**
- Create: `frontend/admin-web/apps/web-public/src/components/VariantTable.vue`

- [ ] **Step 1: Create VariantTable with expandable per-sample rows**

```vue
<script setup lang="ts">
import { ref, computed } from 'vue';
import type { QueryResult } from '@/types/dataset';

const props = defineProps<{
  result: QueryResult | null;
  loading?: boolean;
}>();

const expandedRows = ref<Set<number>>(new Set());

interface VariantRow {
  chrom: string;
  pos: number;
  ref: string;
  alt: string;
  qual: string;
  genotypes: { sample: string; gt: string }[];
}

const variants = computed<VariantRow[]>(() => {
  const preview = (props.result as any)?.preview;
  if (!preview) return [];
  const lines = preview.split('\n').filter((l: string) => l && !l.startsWith('#'));
  // Determine sample count from header
  const headerLine = preview.split('\n').find((l: string) => l.startsWith('#CHROM'));
  const sampleNames = headerLine ? headerLine.split('\t').slice(9) : [];

  return lines.map((line: string) => {
    const fields = line.split('\t');
    const genotypes = sampleNames.map((name: string, i: number) => ({
      sample: name,
      gt: fields[9 + i] ? fields[9 + i].split(':')[0] : './.',
    }));
    return {
      chrom: fields[0],
      pos: Number(fields[1]),
      ref: fields[3],
      alt: fields[4],
      qual: fields[5],
      genotypes,
    };
  });
});

function toggleRow(idx: number) {
  const s = new Set(expandedRows.value);
  s.has(idx) ? s.delete(idx) : s.add(idx);
  expandedRows.value = s;
}

function alleleDisplay(gt: string, ref: string, alt: string): string {
  return gt.replace(/0/g, ref).replace(/1/g, alt).replace('|', '/');
}
</script>

<template>
  <div>
    <el-table :data="variants" border size="small" v-loading="loading" max-height="600" stripe
      @expand-change="(row: any, rows: any) => toggleRow(variants.indexOf(row))">
      <el-table-column type="expand">
        <template #default="{ row }">
          <el-table :data="row.genotypes" border size="small" max-height="300">
            <el-table-column prop="sample" label="Sample" min-width="140" />
            <el-table-column label="Allele" min-width="120">
              <template #default="{ row: gr }">
                {{ alleleDisplay(gr.gt, row.ref, row.alt) }}
              </template>
            </el-table-column>
          </el-table>
        </template>
      </el-table-column>
      <el-table-column prop="chrom" label="Chrom" width="120" />
      <el-table-column prop="pos" label="Position" width="120" sortable />
      <el-table-column prop="ref" label="Ref" width="80" />
      <el-table-column prop="alt" label="Alt" width="80" />
      <el-table-column prop="qual" label="Qual" width="80" />
    </el-table>
    <el-empty v-if="!loading && variants.length === 0" description="No variants found" />
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/admin-web/apps/web-public/src/components/VariantTable.vue
git commit -m "feat: add VariantTable with expandable per-sample genotype rows"
```

---

### Task 5: Frontend — VariantDensityPlot component

**Files:**
- Create: `frontend/admin-web/apps/web-public/src/components/VariantDensityPlot.vue`

- [ ] **Step 1: Create density plot using ECharts**

```vue
<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue';
import * as echarts from 'echarts';

const props = defineProps<{
  variants: { chrom: string; pos: number }[];
  loading?: boolean;
}>();

const chartRef = ref<HTMLElement>();
let chartInst: echarts.ECharts | null = null;

const bins = computed(() => {
  if (props.variants.length === 0) return { categories: [], data: [] };
  const chroms = [...new Set(props.variants.map(v => v.chrom))];
  const data: [string, number, number][] = [];

  for (const chrom of chroms) {
    const positions = props.variants.filter(v => v.chrom === chrom).map(v => v.pos);
    if (positions.length === 0) continue;
    const maxPos = Math.max(...positions);
    const windowSize = Math.max(100000, Math.floor(maxPos / 100));

    for (let start = 0; start <= maxPos; start += windowSize) {
      const count = positions.filter(p => p >= start && p < start + windowSize).length;
      if (count > 0) {
        const mid = (start + start + windowSize) / 2;
        data.push([chrom, mid, count]);
      }
    }
  }
  return data;
});

function buildChart() {
  if (!chartRef.value || bins.value.length === 0) return;
  if (!chartInst) chartInst = echarts.init(chartRef.value);

  const chroms = [...new Set(bins.value.map(b => b[0]))];
  const series = chroms.map(chrom => ({
    name: chrom,
    type: 'scatter' as const,
    data: bins.value.filter(b => b[0] === chrom).map(b => [b[1], b[2]]),
    symbolSize: (val: number[]) => Math.max(3, Math.sqrt(val[1]) * 2),
  }));

  chartInst.setOption({
    tooltip: { formatter: (p: any) => `${p.seriesName}<br/>Pos: ${p.data[0].toLocaleString()}<br/>Variants: ${p.data[1]}` },
    legend: { data: chroms, top: 0 },
    grid: { left: 80, right: 20, top: 40, bottom: 40 },
    xAxis: { type: 'value', name: 'Position', axisLabel: { formatter: (v: number) => (v / 1e6).toFixed(1) + 'M' } },
    yAxis: { type: 'value', name: 'Variant Count' },
    series,
  }, true);
}

watch(() => props.variants, () => nextTick(() => {
  if (chartInst) { chartInst.dispose(); chartInst = null; }
  buildChart();
}), { deep: true });
</script>

<template>
  <div>
    <div ref="chartRef" style="width:100%;height:300px;" />
    <el-empty v-if="!loading && variants.length === 0" description="No data for plot" />
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/admin-web/apps/web-public/src/components/VariantDensityPlot.vue
git commit -m "feat: add VariantDensityPlot with per-chromosome scatter density"
```

---

### Task 6: Frontend — Rewrite genotype/index.vue

**Files:**
- Modify: `frontend/admin-web/apps/web-public/src/views/genotype/index.vue`
- Modify: `frontend/admin-web/apps/web-public/src/composables/useDatasets.ts` (if needed for new operation)

- [ ] **Step 1: Rewrite the page with all new components integrated**

```vue
<script setup lang="ts">
import { ref } from 'vue';
import { useDatasetList, useDatasetDetail, useDatasetQuery } from '@/composables/useDatasets';
import SmartSearchBar from '@/components/SmartSearchBar.vue';
import VariantTable from '@/components/VariantTable.vue';
import VariantDensityPlot from '@/components/VariantDensityPlot.vue';
import SampleFilter from '@/components/SampleFilter.vue';

const { items: datasets, load: loadDatasets } = useDatasetList();
const { detail, load: loadDetail } = useDatasetDetail();
const { queryLoading, queryResult, execute } = useDatasetQuery();

const selectedId = ref<number | null>(null);
const isDraft = ref(false);
const sampleOptions = ref<string[]>([]);
const selectedSamples = ref<string[]>([]);

// Parsed search result info
const searchInfo = ref<string>('');

loadDatasets({ dataset_type: 'variome' });

function getAssetCode(): string | undefined {
  return detail.value?.query_entry_asset?.asset_code;
}

async function onDatasetSelect(datasetId: number) {
  searchInfo.value = '';
  sampleOptions.value = [];
  selectedSamples.value = [];
  await loadDetail(datasetId);
  isDraft.value = detail.value?.lifecycle_state === 'draft';
  const assetCode = getAssetCode();

  // Load samples
  try {
    const data = await execute(datasetId, 'samples_list', {}, assetCode);
    sampleOptions.value = data?.data?.samples || data?.samples || [];
  } catch (e) {
    console.error('Failed to load samples:', e);
  }
}

async function handleSearch({ type, value }: { type: string; value: string }) {
  if (!selectedId.value) return;
  const assetCode = getAssetCode();

  if (type === 'gene') {
    searchInfo.value = `Searching gene: ${value}`;
    // TODO (Task 7): resolve gene to region via annotation adapter
    // For now, pass as-is to region query
    await execute(selectedId.value, 'query', {
      regions: [value],
      include_samples: selectedSamples.value.length > 0 ? selectedSamples.value : undefined,
    }, assetCode);
  } else if (type === 'region') {
    searchInfo.value = `Region: ${value}`;
    await execute(selectedId.value, 'query', {
      regions: [value],
      include_samples: selectedSamples.value.length > 0 ? selectedSamples.value : undefined,
    }, assetCode);
  } else if (type === 'variant_id') {
    searchInfo.value = `Variant ID: ${value}`;
    await execute(selectedId.value, 'query_by_id', {
      variant_ids: [value],
    }, assetCode);
  }
}

async function tryExample() {
  if (!selectedId.value) return;
  const assetCode = getAssetCode();
  try {
    const data = await execute(selectedId.value, 'region_example', {}, assetCode);
    if (data?.ref_id && data?.variant_position != null) {
      const region = `${data.ref_id}:${Math.max(1, data.variant_position - 5000)}-${data.variant_position + 5000}`;
      await handleSearch({ type: 'region', value: region });
    }
  } catch (e) {
    console.error('Failed to load example:', e);
  }
}
</script>

<template>
  <div>
    <h2>Genotype Query</h2>

    <div style="margin-bottom:16px;">
      <el-select v-model="selectedId" placeholder="Select variome dataset" style="width:360px;"
        @change="onDatasetSelect">
        <el-option v-for="ds in datasets" :key="ds.id" :label="ds.title || ds.dataset_code" :value="ds.id" />
      </el-select>
    </div>

    <el-alert v-if="isDraft" title="Dataset is in draft state" type="warning" :closable="false" show-icon
      style="margin-bottom:16px;">
      This dataset may be incomplete or missing required index files.
    </el-alert>

    <div v-if="selectedId">
      <SmartSearchBar placeholder="Search genes, regions, or variant IDs..." @search="handleSearch" />

      <div v-if="searchInfo" style="margin:8px 0;font-size:12px;color:#409eff;">
        {{ searchInfo }}
      </div>

      <div style="display:flex;gap:8px;align-items:center;margin:12px 0;">
        <SampleFilter v-if="sampleOptions.length > 0" :samples="sampleOptions"
          @update="(v: string[]) => selectedSamples = v" />
        <el-button text size="small" @click="tryExample">Try Example</el-button>
      </div>

      <!-- Result tabs -->
      <div v-if="queryResult" style="margin-top:16px;">
        <el-tabs type="border-card">
          <el-tab-pane label="Table">
            <VariantTable :result="queryResult" :loading="queryLoading" />
          </el-tab-pane>
          <el-tab-pane label="Density Plot">
            <VariantDensityPlot :variants="[]" :loading="queryLoading" />
          </el-tab-pane>
        </el-tabs>

        <div v-if="queryResult?.download_url" style="margin-top:12px;">
          <el-button type="success">Download VCF</el-button>
        </div>
      </div>

      <el-empty v-if="!queryLoading && !queryResult" description="Enter a search query to find variants" />
    </div>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/admin-web/apps/web-public/src/views/genotype/index.vue
git commit -m "feat: rewrite genotype page with smart search, sample filter, and variant table"
```

---

### Task 7: Frontend — Gene-to-region resolution via annotation adapter

**Files:**
- Modify: `frontend/admin-web/apps/web-public/src/views/genotype/index.vue`
- Modify: `frontend/admin-web/apps/web-public/src/composables/useDatasets.ts`

- [ ] **Step 1: Add `searchGenes` to useDatasets composable**

In `useDatasets.ts`, add a helper:
```typescript
async function searchGenes(datasetId: number, keyword: string, assetCode?: string): Promise<{gene_id: string; chrom: string; start: number; stop: number} | null> {
  const result: any = await execute(datasetId, 'search_genes', { keyword, size: 1 }, assetCode);
  const genes = result?.data?.items || result?.items || result?.data?.genes || result?.genes || [];
  return genes.length > 0 ? genes[0] : null;
}
```

- [ ] **Step 2: Resolve gene to region in handleSearch**

In genotype/index.vue, when `type === 'gene'`, first look up the gene:
```typescript
if (type === 'gene') {
  searchInfo.value = `Searching gene: ${value}`;
  // Resolve gene -> region via annotation adapter
  const gene = await searchGenes(selectedId.value, value, undefined);  // annotation asset_code needed
  if (gene) {
    const region = `${gene.chrom}:${Math.max(1, gene.start - 5000)}-${gene.stop + 5000}`;
    searchInfo.value = `Gene ${gene.gene_id} → ${region}`;
    await execute(selectedId.value, 'query', {
      regions: [region],
      include_samples: selectedSamples.value.length > 0 ? selectedSamples.value : undefined,
    }, assetCode);
  } else {
    searchInfo.value = `Gene "${value}" not found`;
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/admin-web/apps/web-public/src/views/genotype/index.vue
git add frontend/admin-web/apps/web-public/src/composables/useDatasets.ts
git commit -m "feat: resolve gene to region via annotation adapter in genotype page"
```

---

### Task 8: Integration verification

- [ ] **Step 1: Build and check for type errors**

```bash
cd frontend/admin-web && pnpm -F web-public build 2>&1 | tail -20
```

- [ ] **Step 2: Start servers and test all three input types**

```bash
bash scripts/dev/start-backend.sh
bash scripts/dev/start-admin-web.sh
```

Test in browser at `http://localhost:5668/genotype`:
1. Select Rose Variome dataset
2. Try Example — verify results appear
3. Type a gene ID — verify gene→region resolution label shows
4. Type a region `Chr04:15442000-15443000` — verify variant table
5. Type a variant ID — verify query_by_id path works
6. Expand a variant row — verify per-sample genotypes display
7. Select samples filter — verify only selected samples in results

- [ ] **Step 3: Commit any fixes**

```bash
git add . && git commit -m "fix: integration fixes for genotype page"
```
