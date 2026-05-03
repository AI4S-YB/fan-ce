# Dataset Metadata System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 8 typed metadata columns across dataset_registry, brd_biosample, brd_assay + trigram full-text search index on description_md.

**Architecture:** Three-layer metadata model — Layer 1 (dataset_registry.description_md with full-text search), Layer 2 (breeding biosample/assay typed SRA columns), Layer 3 (dataset_lineage_edge — no changes). LLM tools inject description_md into context when dataset is found.

**Tech Stack:** Python/FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL with pg_trgm extension, Vue 3 + TypeScript + Ant Design Vue

---

### Task 1: Database Migration

**Files:**
- Create: `backend/api-server/alembic/versions/<hash>_add_metadata_columns.py`
- Modify: `backend/api-server/apps/datasets/models.py:184-204`
- Modify: `backend/api-server/apps/breeding/models.py:353-378` and `:381-401`

- [ ] **Step 1: Add description_md to DatasetRegistry model**

```python
# backend/api-server/apps/datasets/models.py
# In class DatasetRegistry, add after index_summary (line 200):
    description_md = Column(Text, comment="Markdown 格式的数据描述文档")
```

- [ ] **Step 2: Add organism to BreedingBioSample model**

```python
# backend/api-server/apps/breeding/models.py
# In class BreedingBioSample, add after sample_type (line 365):
    organism = Column(String(128), comment="物种")
```

- [ ] **Step 3: Add 6 SRA columns to BreedingAssay model**

```python
# backend/api-server/apps/breeding/models.py
# In class BreedingAssay, add after vendor (line 393):
    library_strategy = Column(String(64), comment="文库策略: WGS, RNA-Seq, ChIP-Seq 等")
    library_source = Column(String(64), comment="文库来源: GENOMIC, TRANSCRIPTOMIC 等")
    library_selection = Column(String(64), comment="文库选择: PolyA, RANDOM, ChIP 等")
    library_layout = Column(String(32), comment="文库布局: SINGLE, PAIRED")
    instrument_model = Column(String(128), comment="仪器型号: HiSeq 4000, NovaSeq 6000 等")
    read_length = Column(Integer, comment="读长 bp")
```

- [ ] **Step 4: Generate Alembic migration**

```bash
cd backend/api-server && .venv/bin/alembic revision --autogenerate -m "add_metadata_columns"
```

- [ ] **Step 5: Verify migration SQL**

```bash
cd backend/api-server && cat alembic/versions/*add_metadata_columns*.py
```

Expected: The upgrade() function should contain `op.add_column` for all 8 columns and `op.create_index` / `op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")`.

- [ ] **Step 6: Add trigram index to migration manually if not auto-generated**

The autogenerate may not detect the need for `pg_trgm`. Add to the migration's `upgrade()`:

```python
op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
op.create_index(
    "ix_dataset_registry_description_md_trgm",
    "dataset_registry",
    ["description_md"],
    postgresql_using="gin",
    postgresql_ops={"description_md": "gin_trgm_ops"},
)
```

- [ ] **Step 7: Apply migration**

```bash
cd backend/api-server && .venv/bin/alembic upgrade head
```

Expected: "Running upgrade ... -> ...add_metadata_columns"

- [ ] **Step 8: Verify columns in database**

```bash
PGPASSWORD=fan_api_dev psql -h 127.0.0.1 -p 5433 -U fan_api -d fan_ce_dev -c "\d dataset_registry" | grep description_md
PGPASSWORD=fan_api_dev psql -h 127.0.0.1 -p 5433 -U fan_api -d fan_ce_dev -c "\d brd_biosample" | grep organism
PGPASSWORD=fan_api_dev psql -h 127.0.0.1 -p 5433 -U fan_api -d fan_ce_dev -c "\d brd_assay" | grep -E "library_strategy|library_source|library_selection|library_layout|instrument_model|read_length"
```

Expected: Each column appears in table schema output.

- [ ] **Step 9: Commit**

```bash
git -C /Users/kentnf/projects/omicsagent/odata add backend/api-server/apps/datasets/models.py backend/api-server/apps/breeding/models.py backend/api-server/alembic/versions/
git -C /Users/kentnf/projects/omicsagent/odata commit -m "feat: add metadata columns to dataset_registry, brd_biosample, brd_assay"
```

---

### Task 2: Pydantic Schemas Update

**Files:**
- Modify: `backend/api-server/apps/datasets/schemas.py:24-37`
- Modify: `backend/api-server/apps/breeding/schemas.py:230-269`

- [ ] **Step 1: Add description_md to DatasetUpdateRequest**

```python
# backend/api-server/apps/datasets/schemas.py
# In class DatasetUpdateRequest, add after extra_json:
    description_md: Optional[str] = None
```

- [ ] **Step 2: Add organism to BreedingBioSampleCreateRequest and UpdateRequest**

```python
# backend/api-server/apps/breeding/schemas.py
# In BreedingBioSampleCreateRequest, add after sample_type:
    organism: Optional[str] = None
```

UpdateRequest inherits from CreateRequest, so no separate change needed.

- [ ] **Step 3: Add 6 SRA columns to BreedingAssayCreateRequest and UpdateRequest**

```python
# backend/api-server/apps/breeding/schemas.py
# In BreedingAssayCreateRequest, add after vendor:
    library_strategy: Optional[str] = None
    library_source: Optional[str] = None
    library_selection: Optional[str] = None
    library_layout: Optional[str] = None
    instrument_model: Optional[str] = None
    read_length: Optional[int] = None
```

UpdateRequest inherits from CreateRequest, no separate change needed.

- [ ] **Step 4: Update BreedingAssayListRequest to support new filter fields**

```python
# backend/api-server/apps/breeding/schemas.py
# In BreedingAssayListRequest, add after platform:
    library_strategy: Optional[str] = None
    instrument_model: Optional[str] = None
```

- [ ] **Step 5: Commit**

```bash
git -C /Users/kentnf/projects/omicsagent/odata add backend/api-server/apps/datasets/schemas.py backend/api-server/apps/breeding/schemas.py
git -C /Users/kentnf/projects/omicsagent/odata commit -m "feat: add metadata fields to dataset and breeding Pydantic schemas"
```

---

### Task 3: Backend API — Dataset Update + Full-Text Search

**Files:**
- Modify: `backend/api-server/apps/datasets/api/dataset.py`
- Modify: `backend/api-server/apps/datasets/services.py`
- Modify: `backend/api-server/apps/datasets/tools.py`

- [ ] **Step 1: Add description_md to dataset update endpoint**

Read the current `dataset.py` update endpoint to find where fields are mapped. Add `description_md` to the update payload.

```python
# In the dataset update handler, add alongside other field assignments:
if request.description_md is not None:
    dataset.description_md = request.description_md
```

- [ ] **Step 2: Add full-text search to dataset list API**

In the `list_datasets` service method or API endpoint, add support for a `keyword` query parameter that searches `description_md` via trigram:

```python
# In datasets/services.py list_datasets method, add keyword search:
if getattr(request_data, 'keyword', None):
    keyword = request_data.keyword.strip()
    query = query.filter(
        DatasetRegistry.description_md.ilike(f'%{keyword}%')
    )
```

- [ ] **Step 3: Add keyword parameter to DatasetListRequest schema**

```python
# backend/api-server/apps/datasets/schemas.py
# In class DatasetListRequest, add:
    keyword: Optional[str] = None
```

- [ ] **Step 4: Update LLM tool to inject description_md into context**

In `_resolve_datasets` or in the tool functions, add `description_md` to the dataset info dict returned to LLM:

```python
# In dataset_domain_service.get_dataset or _resolve_datasets, ensure response includes:
"description_md": dataset.get("description_md") or ""
```

- [ ] **Step 5: Commit**

```bash
git -C /Users/kentnf/projects/omicsagent/odata add backend/api-server/apps/datasets/
git -C /Users/kentnf/projects/omicsagent/odata commit -m "feat: add description_md CRUD and full-text search to dataset API"
```

---

### Task 4: Backend API — Breeding BioSample & Assay Update

**Files:**
- Modify: `backend/api-server/apps/breeding/api/core.py`

- [ ] **Step 1: Add organism to biosample CRUD**

Read `core.py` to find biosample create/update handlers. Add `organism` field mapping:

```python
# In biosample create:
biosample.organism = request.organism

# In biosample update:
if request.organism is not None:
    biosample.organism = request.organism
```

- [ ] **Step 2: Add 6 SRA columns to assay CRUD**

```python
# In assay create:
assay.library_strategy = request.library_strategy
assay.library_source = request.library_source
assay.library_selection = request.library_selection
assay.library_layout = request.library_layout
assay.instrument_model = request.instrument_model
assay.read_length = request.read_length

# In assay update, wrap each with "if request.xxx is not None:"
```

- [ ] **Step 3: Add filter support for list endpoints**

In biosample list: add organism filter.
In assay list: add library_strategy and instrument_model filters (matching the ListRequest schemas).

- [ ] **Step 4: Commit**

```bash
git -C /Users/kentnf/projects/omicsagent/odata add backend/api-server/apps/breeding/
git -C /Users/kentnf/projects/omicsagent/odata commit -m "feat: add organism and SRA fields to breeding biosample/assay APIs"
```

---

### Task 5: Frontend — Dataset description_md Editor

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/views/apps/dataset/Detail.vue`
- Modify: `frontend/admin-web/apps/web-antd/src/api/apps/dataset.ts`
- Modify: `frontend/admin-web/apps/web-antd/src/locales/langs/zh-CN/dataset.json`
- Modify: `frontend/admin-web/apps/web-antd/src/locales/langs/en-US/dataset.json`

- [ ] **Step 1: Add description_md to frontend API types**

```typescript
// frontend/admin-web/apps/web-antd/src/api/apps/dataset.ts
// In DatasetItem interface, add:
description_md?: string;

// In DatasetUpdateParams interface, add:
description_md?: string;
```

- [ ] **Step 2: Add markdown editor to dataset Detail page**

In `Detail.vue`, add a textarea or markdown editor section for `description_md`. Use Ant Design's `Input.TextArea` with `autoSize` for simple editing:

```vue
<!-- In Detail.vue template, add a card section for description: -->
<a-card :title="$t('dataset.detail.descriptionMd')" style="margin-top: 16px;">
  <a-textarea
    v-model:value="form.description_md"
    :placeholder="$t('dataset.detail.descriptionMdPlaceholder')"
    :auto-size="{ minRows: 6, maxRows: 20 }"
    @change="handleDescriptionChange"
  />
</a-card>
```

- [ ] **Step 3: Add debounced auto-save for description_md**

```typescript
// In Detail.vue script:
import { debounce } from 'lodash-es';

const handleDescriptionChange = debounce(async () => {
  await updateDatasetApi({ id: datasetId.value, description_md: form.description_md });
  createMessage.success($t('dataset.detail.descriptionSaved'));
}, 2000);
```

- [ ] **Step 4: Add i18n labels**

```json
// zh-CN/dataset.json add:
"detail.descriptionMd": "数据说明文档 (Markdown)",
"detail.descriptionMdPlaceholder": "用 Markdown 格式描述数据集内容，例如：\n# 数据集概述\n- 物种：...\n- 实验设计：...",
"detail.descriptionSaved": "数据说明已保存"

// en-US/dataset.json add:
"detail.descriptionMd": "Data Description (Markdown)",
"detail.descriptionMdPlaceholder": "Describe the dataset in Markdown, e.g.:\n# Overview\n- Species: ...\n- Experimental design: ...",
"detail.descriptionSaved": "Description saved"
```

- [ ] **Step 5: Commit**

```bash
git -C /Users/kentnf/projects/omicsagent/odata add frontend/
git -C /Users/kentnf/projects/omicsagent/odata commit -m "feat: add description_md markdown editor to dataset detail page"
```

---

### Task 6: Frontend — Breeding BioSample & Assay Forms

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/views/breeding/` (biosample form components)
- Modify: `frontend/admin-web/apps/web-antd/src/api/breeding/` (API types)

- [ ] **Step 1: Add organism, SRA fields to frontend API types**

```typescript
// In breeding API types files:
// BreedingBioSample interface add:
organism?: string;

// BreedingAssay interface add:
library_strategy?: string;
library_source?: string;
library_selection?: string;
library_layout?: string;
instrument_model?: string;
read_length?: number;
```

- [ ] **Step 2: Add organism field to biosample form**

Find the biosample create/edit modal component. Add an `organism` input field (following the existing pattern for `sample_type` or `tissue_type`):

```vue
<a-form-item :label="$t('breeding.biosample.organism')">
  <a-input v-model:value="form.organism" placeholder="e.g. Homo sapiens, Rosa chinensis" />
</a-form-item>
```

- [ ] **Step 3: Add 6 SRA fields to assay form**

Find the assay create/edit modal component. Add the 6 SRA fields:

```vue
<a-form-item :label="$t('breeding.assay.libraryStrategy')">
  <a-select v-model:value="form.library_strategy" placeholder="Select strategy">
    <a-select-option value="WGS">WGS</a-select-option>
    <a-select-option value="RNA-Seq">RNA-Seq</a-select-option>
    <a-select-option value="ChIP-Seq">ChIP-Seq</a-select-option>
    <!-- ... -->
  </a-select>
</a-form-item>
<a-form-item :label="$t('breeding.assay.libraryLayout')">
  <a-select v-model:value="form.library_layout">
    <a-select-option value="SINGLE">Single-end</a-select-option>
    <a-select-option value="PAIRED">Paired-end</a-select-option>
  </a-select>
</a-form-item>
<!-- library_source, library_selection as text inputs -->
<!-- instrument_model as text input -->
<!-- read_length as number input -->
```

- [ ] **Step 4: Add i18n labels for new fields**

```json
// zh-CN/breeding.json
"biosample.organism": "物种",
"assay.libraryStrategy": "文库策略",
"assay.librarySource": "文库来源",
"assay.librarySelection": "文库选择",
"assay.libraryLayout": "文库布局",
"assay.instrumentModel": "仪器型号",
"assay.readLength": "读长 (bp)"
```

- [ ] **Step 5: Commit**

```bash
git -C /Users/kentnf/projects/omicsagent/odata add frontend/
git -C /Users/kentnf/projects/omicsagent/odata commit -m "feat: add organism and SRA fields to breeding biosample and assay forms"
```

---

### Task 7: Integration Verification

**Files:** None new

- [ ] **Step 1: Verify backend API — dataset description_md**

```bash
# Update description_md on a dataset
curl -s -X POST http://127.0.0.1:8002/api/v1/dataset/update \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"id": 1, "description_md": "# Test\n- species: human\n- type: RNA-seq"}'

# Search by keyword
curl -s "http://127.0.0.1:8002/api/v1/dataset/list?keyword=RNA-seq" \
  -H "Authorization: Bearer <token>"
```

Expected: Search returns dataset with matching description_md.

- [ ] **Step 2: Verify backend API — breeding biosample organism**

```bash
curl -s -X POST http://127.0.0.1:8002/api/v1/breeding/biosample/update \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"id": 1, "organism": "Rosa chinensis"}'
```

- [ ] **Step 3: Verify backend API — breeding assay SRA fields**

```bash
curl -s -X POST http://127.0.0.1:8002/api/v1/breeding/assay/update \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"id": 1, "library_strategy": "RNA-Seq", "library_layout": "PAIRED", "read_length": 150}'
```

- [ ] **Step 4: Verify frontend build**

```bash
cd frontend/admin-web && pnpm build:antd 2>&1 | tail -5
```

Expected: Build completes without errors.

- [ ] **Step 5: Commit any fixes and final verification**

```bash
git -C /Users/kentnf/projects/omicsagent/odata commit -m "chore: integration verification for metadata system"
```
