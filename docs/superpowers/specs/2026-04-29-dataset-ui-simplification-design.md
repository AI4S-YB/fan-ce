# Dataset Center UI Simplification Design

> **Goal:** Simplify the over-engineered, cramped Dataset detail pages (Overview, Version Workbench, Data Browse) in admin-web by moving from Drawer-overlay to independent route pages, eliminating overlapping content, and reducing query complexity.

**Architecture:** Replace the 7884-line monolithic `index.vue` (two wide Drawers + 5 tabs + 17 sub-tabs) with three clean route pages: List, Detail (merged overview + version management), and Query (simplified data browse). Pages use full-width layout instead of right-side Drawers.

**Tech Stack:** Vue 3 + Ant Design Vue + TypeScript + Vite, existing API layer (`/admin/dataset/*` endpoints).

---

## Current State (Problems)

The current dataset center is a single 7884-line component (`apps/web-antd/src/views/apps/dataset/index.vue`) containing:

1. **Dataset List** — main page table with 4 action buttons (版本工作台, 数据浏览, 概览, 删除)
2. **概览 Drawer** (1180px) — 9 content blocks: Identity, Version Summary (6 cards), Health (2 cards), Version Snapshot, Reference Status, Asset Overview, Recent Tasks, Publish Summary, System Info
3. **版本工作台 Drawer** (1040px/920px) — toolbar + descriptions + version summary cards + version table + 5 tabs:
   - 总览 Tab: 7 sub-blocks, heavily overlapping with 概览 Drawer (7/8 blocks are duplicates)
   - 资产 Tab: Asset CRUD + file CRUD
   - 血缘 Tab: Lineage list + CRUD
   - 查询 Tab: Query execution with 4 data-type-specific sub-panels (17 sub-tabs total)
   - 演进 Tab: Publish history table
4. **数据浏览** — confirmed to be the same code path as 版本工作台 Query Tab (calls `openVersionQueryWorkspace()`)

### Root Causes of Complexity

- **Overlapping layers:** 概览 Drawer and 版本工作台"总览" Tab have 7/8 identical content blocks
- **Over-designed query:** 4 data types × multiple sub-tabs × per-operation dynamic forms = excessive nesting
- **Cramped Drawers:** 1040-1180px drawers with dense multi-column grids, cards, and tables
- **Monolithic file:** Single component handles list, two drawers, five tabs, queries, modals, and forms

---

## Target Design: 3-Page Structure

### Page 1: `/dataset` — Dataset List

Route: existing `/dataset` (keep current route)

**Changes from current:**
- Remove "查询适配器" column (moved to detail page)
- Merge 4 action buttons into 3: **详情**, **数据查询**, **删除**
  - 详情 → `/dataset/:id`
  - 数据查询 → `/dataset/:id/query`
  - 删除 → confirm modal (unchanged)

### Page 2: `/dataset/:id` — Detail & Management Workbench

New route, full-width page. Merges overview + version management into one vertically-scrollable page.

**Section 1: Header (always visible)**
- Dataset identity: title/dataset_code, type, organism, assembly, file_format
- Lifecycle + visibility tags
- Action buttons: 数据查询 (→ query page), 删除

**Section 2: Status Bar (single row)**
- Replaces the 2-3 "health cards" from both drawers
- Query entry status (configured/missing), current version, default public version, reference binding status
- Version mismatch warning (when current != default public)

**Section 3: Version Table**
- Version list with columns: radio, version, lifecycle, release_state, visibility, asset count, operations
- Operations: activate, release, set default public, withdraw (context-dependent)
- "新建版本" button in toolbar

**Section 4 & 5: Selected Version — Assets & Lineage (side by side)**
- Shown when a version is selected in the version table
- **Assets panel (left):** Asset cards with file details. Operations: add asset, edit, register file, delete asset. Filter by keyword/asset_code.
- **Lineage panel (right):** Lineage records with relation type, direction, linked version. Operations: add lineage, open linked version, delete.

**Section 6: Publish History (collapsed by default)**
- `<details>` element, shows publish records table only when expanded

**Section 7: System Info (collapsed by default)**
- `<details>` element, shows: dataset ID, code, create/update time, source file path

### Page 3: `/dataset/:id/query` — Data Query

New route, full-width page. Replaces both 数据浏览 and 版本工作台"查询"Tab.

**Layout: Two columns**
- **Left column (360px):** Query configuration panel
  - File accessibility indicator
  - Operation selector (dropdown, populated from adapter capabilities)
  - Dynamic parameter form (renders based on selected operation)
  - Execute / Load Example buttons

- **Right column (flex):** Results panel
  - Result summary (row count, data type if applicable)
  - Tabular or structured result display
  - Copy JSON / Download CSV buttons

**Key simplification:** Remove the 4 data-type-specific sub-tab groups (Genome 5 tabs, Expression 3 tabs, Variant 3 tabs, Phenome 6 tabs). Instead:
- Auto-select the most common operation for the dataset type on page load (e.g., expression → matrix_slice, variant → query)
- User freely switches operations via the dropdown
- Parameter form dynamically renders appropriate fields for the selected operation

### Deletion

Remains a simple confirm modal on the list page and detail page. No separate page needed.

---

## Removed Content

| Removed | Reason |
|---------|--------|
| 概览 Drawer (entire) | Merged into detail page Header + Status Bar |
| 版本工作台 Drawer (entire) | Converted to full-width route page |
| 总览 Tab (entire) | 7/8 blocks duplicate with 概览; key info moved to detail page header |
| 演进 Tab (standalone) | Moved to collapsed section on detail page |
| 数据浏览 as separate entry | Same as query page |
| Health "cards" (query health, reference health, asset health) | Replaced by single status bar row |
| Recent workflow tasks (概览 block G) | Not needed on management page |
| 17 data-type sub-tabs in query | Replaced by operation dropdown + dynamic form |
| query_adapter column in list | Moved to detail page (reduces list width) |
| "查询入口资产" card in overview | Merged into status bar |

---

## File Changes

### New Files

- `apps/web-antd/src/views/apps/dataset/Detail.vue` — Detail & Management Workbench page
- `apps/web-antd/src/views/apps/dataset/Query.vue` — Data Query page
- `apps/web-antd/src/views/apps/dataset/components/VersionTable.vue` — Version list + operations
- `apps/web-antd/src/views/apps/dataset/components/AssetPanel.vue` — Asset cards + file management
- `apps/web-antd/src/views/apps/dataset/components/LineagePanel.vue` — Lineage records + CRUD
- `apps/web-antd/src/views/apps/dataset/components/QueryForm.vue` — Dynamic query parameter form

### Modified Files

- `apps/web-antd/src/views/apps/dataset/index.vue` — Remove drawers, simplify to list-only, update action buttons
- Route configuration — Add `/dataset/:id` and `/dataset/:id/query` routes (currently routes are dynamically loaded via `generateRoutesByBackend`; may need backend menu items or frontend static route entries)
- `apps/web-antd/src/api/apps/dataset.ts` — No API changes needed; may extract shared composables

### Removed

- None (the old index.vue is refactored in-place, not deleted)

---

## Backward Compatibility

- All existing API endpoints unchanged (`/admin/dataset/*`)
- The list page keeps the same filter/search/pagination behavior
- Version operations (activate, release, withdraw, set-default-public) unchanged
- Asset/lineage CRUD operations unchanged
- Query execution unchanged

---

## Non-Goals

- Changing backend API structure
- Modifying portal-web dataset pages
- Adding new data types or query operations
- Changing the dataset data model
