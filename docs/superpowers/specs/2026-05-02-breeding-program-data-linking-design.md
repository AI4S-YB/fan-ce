# Breeding Program Data Linking Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the deprecated `system_project` concept with `brd_program` as the unified project model, and build LLM-driven tools to associate datasets with breeding programs.

**Architecture:** Clean up `system_project` tables/code, redirect project menu to breeding programs, add a new AI tool `link_dataset_to_program` that uses LLM + existing breeding entity context to generate sample-level association mappings (human-reviewed before commit). Dataset detail page gains a "Link to Program" entry point with both manual coarse linking and LLM-driven fine mapping.

**Tech Stack:** FastAPI + PostgreSQL + SQLAlchemy + Alembic (backend), Vue 3 + Pinia + ant-design-x-vue (frontend), tool_registry.py LLM function-calling pattern

---

## Design Decisions

### Data Model

- **Delete:** `system_project` table, `system_project_meta` table, `dataset.project_id` column
- **Keep as-is:** All `brd_*` tables (already in place with full FK/CHECK constraints), `brd_dataset_subject_link`, `brd_dataset_assay_link`, `brd_variant_sample_map`, `brd_phenotype_subject_map`, `dataset_lineage_edge`
- **No new tables:** Current link tables + LLM tool cover requirements for Scope B

### Menu

- Remove "系统管理→项目管理" menu item in bootstrap seed data
- Repoint it to `/breeding/program` (same destination as "项目管理→项目列表")
- Users keep the familiar menu entry but it now manages `brd_program` entities

### LLM Tool: `link_dataset_to_program`

Registered in `tool_registry.py`, following the existing tool pattern.

**Tool flow:**
1. Load context: target program's materials/biosamples/trials + dataset metadata (sample_names, columns, file_format)
2. Pack context + user_instruction into LLM prompt with strict JSON output schema
3. LLM generates association proposals (subject_links + variant_maps + summary)
4. Backend validates all IDs exist in the provided context
5. Return as preview (status=draft) for user review; no DB writes until confirmed

**LLM output schema:**
```json
{
  "subject_links": [
    {
      "dataset_id": 15, "version_id": 1, "asset_id": 1,
      "subject_type": "biosample",
      "subject_id": 3,
      "role": "expression_matrix",
      "confidence": "high",
      "note": "column 'Rose_CvA_rep1' matched to biosample 'Leaf_RNA_2024-03' via material name"
    }
  ],
  "variant_maps": [
    {
      "vcf_sample_name": "Cultivar_A",
      "material_id": 1, "biosample_id": 5,
      "confidence": "medium",
      "note": "fuzzy match on germplasm_accession"
    }
  ],
  "summary": "已匹配 12/15 个样本，3 个无法确定需人工处理"
}
```

**Two execution phases:**
- **Preview:** Tool returns proposals, `mapping_status="draft"`, `mapping_method="llm"`, no DB writes
- **Commit:** User confirms; backend batch-inserts into `brd_dataset_subject_link` and/or `brd_variant_sample_map`; status promoted to `"matched"`

**Audit trail:** Every LLM-generated record carries `mapping_method="llm"`, initial `mapping_status="draft"`, a `confidence` score, and a `note` explaining the matching rationale. This enables direct filtering when debugging query issues.

**Manual fallback:** A simple "Link to Program" button creates a coarse `brd_dataset_subject_link` record with `subject_type="program"` — no LLM needed.

### Frontend

**Dashboard workspace header** (`views/dashboard/workspace/index.vue`):
- `getProjectListApi` → `getBreedingProgramListApi`
- `projectStore.getProjectInfo` → `programStore.getProgramInfo`
- Project count → program count
- Description shows current program name

**Store** (`store/modules/project.ts` → `program.ts`):
- Renamed to `useProgramStore`
- `projectInfo` → `programInfo`, sourced from `brd_program` fields
- Initialized from login response (`/auth/login`) and user info (`/auth/user/info`)

**Dataset detail page:**
- New "关联项目" button
- Flow: select target program → (optional) input natural language instruction → call LLM tool → display preview → confirm commit
- Also a simple "直接关联到 Program" button for coarse linking

**Cleanup:**
- Delete `views/system/project/` pages
- Remove all `getProjectListApi`/`getProjectOptionsApi` calls in favor of breeding program APIs
- Update `bootstrap.py` menu entries

### Backend API Changes

| Endpoint | Change |
|----------|--------|
| `/system/project/*` | Delete all endpoints |
| `/auth/login` | `project`/`project_list` → query `brd_program` instead of `system_project` |
| `/auth/user/info` | Same: `project_list` → active breeding programs |
| `/breeding/program/options` | New: lightweight options list for dropdowns |
| `tool_registry.py` | Register `link_dataset_to_program` tool |

### What's NOT in Scope

- Expression matrix column mapping table (validate with real queries first, add if needed)
- Cross-dataset query view refactoring in program detail page
- Phenotype subject map population (separate follow-up)

---

## File Manifest

### Create
- `backend/api-server/db/versions/<auto>_drop_system_project.py` — Alembic auto-generated migration
- `backend/api-server/apps/breeding/tools.py` — `link_dataset_to_program` tool (function + registration)

### Modify
- `backend/api-server/db/bootstrap.py` — Remove system_project menu, repoint to /breeding/program
- `backend/api-server/apps/services/rbd.py` — Replace system_project queries with brd_program queries
- `backend/api-server/apps/auth/login.py` — Replace system_project with brd_program in login response
- `backend/api-server/apps/auth/menus.py` — Update user info response
- `backend/api-server/apps/datasets/tools.py` — Register new tool
- `backend/api-server/apps/system/api/project.py` — Delete all endpoints
- `backend/api-server/apps/system/routers.py` — Remove project_router
- `frontend/admin-web/apps/web-antd/src/store/modules/project.ts` → `program.ts` — Rename, point to brd_program
- `frontend/admin-web/apps/web-antd/src/store/auth.ts` — Update project references
- `frontend/admin-web/apps/web-antd/src/views/dashboard/workspace/index.vue` — Use program APIs
- `frontend/admin-web/apps/web-antd/src/api/system/project.ts` — Remove
- `frontend/admin-web/apps/web-antd/src/api/breeding/program.ts` — Add options endpoint

### Delete
- `backend/api-server/apps/system/project/` — Entire module
- `backend/api-server/apps/system/project/models.py` — system_project ORM model
- `frontend/admin-web/apps/web-antd/src/views/system/project/` — Page components
- `system_project`, `system_project_meta` tables (via migration)
- `dataset.project_id` column (via migration)
