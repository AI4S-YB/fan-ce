# Public Database Frontend Design

> **Date:** 2026-05-04
> **Status:** Approved

## Goal

Build a new public database frontend (`apps/web-public`) that combines our Dataset center, lineage graph, and LLM chat capabilities with fan-db-ui's academic visual design. All data access goes through the Dataset public API layer.

## Architecture

**Location:** `frontend/admin-web/apps/web-public/` — independent Vite app inside the admin-web pnpm monorepo.

**Tech Stack:** Vue 3.5 + TypeScript + Element Plus 2.9 + ECharts 5.6 + Pinia 3.0 + Vite 6.3. All dependencies already in pnpm workspace catalog.

**Key decisions:**
- No vben framework — lightweight, no admin layouts or access control
- No auth interceptor — all API endpoints are public (`/api/v1/public/*`)
- Element Plus, not Ant Design — matching fan-db-ui's visual style
- Chinese only in v1 — i18n can be added later via `@vben/locales`

**Security:** FRP tunnel exposes only this app's port (5677). Admin web (5666) and backend (8002) remain internal.

## Pages (7 routes)

| Route | Page | Data Source |
|-------|------|-------------|
| `/` | Home — dataset catalog with search | `POST /public/dataset/list` |
| `/dataset/:id` | Dataset Detail — overview, lineage, files | `POST /public/dataset/info` + lineage |
| `/genome/:id` | Genome Browser — tabs: home, search, batch, blast, download, gene | `POST /public/dataset/query/execute` |
| `/expression` | Expression Query — gene × sample matrix + heatmap | `POST /public/dataset/query/execute` |
| `/genotype` | Variant Query — region-based, VCF download | `POST /public/dataset/query/execute` |
| `/germplasm` | Germplasm Browse — search, detail modals, knowledge graph | `POST /public/dataset/query/execute` |
| `/phenotype` | Phenotype Query — trait × sample + heatmap | `POST /public/dataset/query/execute` |

## Data Flow: Three-Step Pattern

Every query page follows the same pattern:

1. **Select Dataset + Version** — `DatasetSelector` component filters by `dataset_type`, emits selected `{dataset_id, version_id}`
2. **Discover Capabilities** — `POST /public/dataset/query/capabilities` returns available operations, filter options (chromosomes, genes, samples, traits)
3. **Execute Query** — `POST /public/dataset/query/execute` with `{operation, params}`, returns rows + total + download URL

No direct calls to basis API. All data access through the Dataset public query layer.

## Shared Components

| Component | Purpose | Used By |
|-----------|---------|---------|
| `DatasetSelector` | Dataset type → dataset → version cascade selector | All query pages |
| `DataVisualization` | Table ↔ ECharts heatmap toggle | Expression, Phenotype, Genotype |
| `CompositeSearchForm` | Gene search: keyword / gene_id / chrom range | Genome Search |
| `MultiSelectDropdown` | Searchable multi-select for samples/genes/traits | Expression, Phenotype, Genotype |
| `LineagePanel` | Dataset relationship graph from `dataset_lineage_edge` | Dataset Detail |
| `AiChatDrawer` | Floating LLM chat, auto-injects `description_md` + `extra_json` | Global (all pages) |

## Project Structure

```
apps/web-public/
├── package.json          # @fan-ce/web-public
├── vite.config.ts        # proxy /api/v1 → backend, port 5677
├── tsconfig.json
├── index.html
└── src/
    ├── main.ts           # createApp + router + pinia
    ├── App.vue           # Header + RouterView + Footer
    ├── router/index.ts   # flat routes, 7 pages
    ├── composables/
    │   ├── useRequest.ts # Axios instance, base URL from env
    │   └── useDatasets.ts# dataset list, info, capabilities, query
    ├── components/
    │   ├── layout/       # Header.vue, Footer.vue
    │   ├── DatasetSelector.vue
    │   ├── DataVisualization/
    │   ├── CompositeSearchForm.vue
    │   ├── MultiSelectDropdown.vue
    │   ├── LineagePanel.vue
    │   ├── AiChatDrawer/
    │   └── ui/           # AcademicCard, AcademicTag
    └── views/
        ├── home/index.vue
        ├── dataset/Detail.vue
        ├── genome/       # Overview, Search, BatchQuery, Blast, Download, GeneInfo
        ├── expression/index.vue
        ├── genotype/index.vue
        ├── germplasm/index.vue
        └── phenotype/index.vue
```

## Out of Scope (v1)

- User authentication / login
- Multi-tenant / tenant config system
- i18n internationalization
- Admin management features (handled by admin-web)
- Data upload / registration (handled by admin-web)
