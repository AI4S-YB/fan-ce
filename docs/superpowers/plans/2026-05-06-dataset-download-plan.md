# Dataset File Download Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Add downloadable flag to files, download API, admin toggle UI, public download page.

---

### Task 1: Backend — Model + Migration

**Files:**
- Modify: `apps/datasets/models.py` — add `is_downloadable` to `AssetFile`
- Create: Alembic migration
- Modify: `apps/datasets/schemas.py` — add to update schema

Add `is_downloadable = Column(Boolean, default=False, comment="是否允许公开下载")` to AssetFile model. Generate migration. Add `is_downloadable: Optional[bool] = None` to `AssetFileUpdateRequest`.

### Task 2: Backend — Public Download API

**Files:**
- Modify: `apps/datasets/api/public.py` — add 2 endpoints

1. `GET /public/dataset/{dataset_code}/downloads` — query asset_file with is_downloadable=true for the dataset
2. `GET /public/dataset/{dataset_code}/download/{file_id}` — resolve file path, return FileResponse

### Task 3: Admin-Web — Download Toggle

**Files:**
- Modify: `AssetPanel.vue` — add switch in each file row + edit modal
- Modify: `api/apps/dataset.ts` — add is_downloadable to types

### Task 4: Public-Web — Download Page

**Files:**
- Modify: `Tools.vue` Download tab — fetch and display downloadable files
- Create: `composables/useDownloads.ts` — download API functions

### Task 5: Build + Verify
