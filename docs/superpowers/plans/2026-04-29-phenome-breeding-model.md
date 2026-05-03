# Phenome Three-Table Model Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade PhenomeAdapter from flat `phenotype` table to Trial→Plot→Observation three-table model while keeping backward compatibility for old-format datasets.

**Architecture:** Single PhenomeAdapter detects schema at query time — `_is_new_schema()` checks for `trial` table in SQLite. New operations (trial_list, multi_trait_query, etc.) route to three-table queries; old operations (subject_list, subject_detail) route to flat-table queries. Backward compatible: existing datasets skip new ops, new datasets expose full operation set.

**Tech Stack:** Python 3.11, SQLite, sqlalchemy (PostgreSQL), FastAPI

---

## File Map

| File | Role |
|------|------|
| `backend/api-server/apps/datasets/adapters/phenome.py` | Main change — add schema detection, new ops |
| `backend/api-server/apps/datasets/models.py` | Fix PhenomeObservation.value_numeric column type |
| `scripts/migrate_rose_phenome.py` | Already created — demo data migration script |
| `frontend/admin-web/apps/web-antd/src/views/apps/dataset/components/QueryForm.vue` | Add defaultParams for new phenome ops |

---

### Task 1: Fix PostgreSQL value_numeric Column Type

**Files:**
- Modify: `backend/api-server/apps/datasets/models.py:22`

**Why:** `phn_observation.value_numeric` is `varchar` in PostgreSQL but `Float` in SQLAlchemy, causing `Unknown PG numeric type: 1043` error. Must match actual numeric storage.

- [ ] **Step 1: Verify current mismatch**

```python
# Already confirmed: column is varchar in DB, Float in model
# No code change needed for verification
```

- [ ] **Step 2: Generate and run migration**

```bash
cd backend/api-server && alembic revision --autogenerate -m "fix_phenome_observation_value_numeric_type"
```

Review the generated migration to ensure it does:
```python
ALTER TABLE phn_observation ALTER COLUMN value_numeric TYPE double precision USING value_numeric::double precision;
```

- [ ] **Step 3: Run migration**

```bash
cd backend/api-server && alembic upgrade head
```

- [ ] **Step 4: Verify column type**

```bash
python3 -c "
import psycopg2
conn = psycopg2.connect(host='127.0.0.1', port=5433, user='fan_api', password='fan_api_dev', dbname='fan_api_poc_dev')
cur = conn.cursor()
cur.execute(\"SELECT data_type FROM information_schema.columns WHERE table_name='phn_observation' AND column_name='value_numeric';\")
print(cur.fetchone())
"
# Expected: ('double precision',)
```

- [ ] **Step 5: Verify trait_values query works via PostgreSQL path**

```bash
# Query any phenome dataset via the API and confirm no more OID 1043 error
```

---

### Task 2: Add Schema Detection to PhenomeAdapter

**Files:**
- Modify: `backend/api-server/apps/datasets/adapters/phenome.py:30-38`

Add a method to detect whether the SQLite file uses old flat `phenotype` table or new `trial/plot/observation` three-table schema.

- [ ] **Step 1: Add `_is_new_schema` method**

```python
def _is_new_schema(self, file_path: str) -> bool:
    """Return True if the SQLite file has trial/plot/observation tables."""
    tables = self._list_tables(file_path)
    return "trial" in tables and "plot" in tables and "observation" in tables
```

Add this method right after `_list_tables` (line ~33) in `phenome.py`.

- [ ] **Step 2: Test detection on old file**

```python
# The old rose_phenotype_test.xlsx was imported as flat table
# Not a .db file, so detection returns False — handled by describe() fallback
```

- [ ] **Step 3: Test detection on new file**

```bash
python3 -c "
import sqlite3
db = sqlite3.connect('/Users/kentnf/projects/data/test_data/phenotype/rose_phenotype_v2.db')
tables = [r[0] for r in db.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]
print(tables)
"
# Expected: ['trial', 'plot', 'observation']
```

---

### Task 3: Implement New describe() with Real Examples

**Files:**
- Modify: `backend/api-server/apps/datasets/adapters/phenome.py:131-150`

Replace the current `describe()` with schema-aware version that extracts real example data for both old and new schemas.

- [ ] **Step 1: Write the new describe()**

```python
def describe(self, dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
    file_path = self.require_file_path(dataset_payload)
    fmt = str(dataset_payload.get("query_profile", {}).get("file_format") or "").lower()

    if not self._is_new_schema(file_path):
        # -- Old flat phenotype table path --
        table_name = self._require_phenotype_table(file_path)
        trait_columns = self._get_trait_columns(file_path, table_name)

        example_subject_id = ""
        example_trait_name = ""
        example_trait_search = "花瓣"

        try:
            rows = query_sqlite(
                file_path,
                f"SELECT ID FROM {self._quote_identifier(table_name)} ORDER BY ID ASC LIMIT 1",
            )
            if rows and rows[0].get("ID") is not None:
                example_subject_id = str(rows[0]["ID"])
        except Exception:
            pass

        if trait_columns:
            example_trait_name = str(trait_columns[0].get("name") or "")
            if example_trait_name:
                example_trait_search = example_trait_name

        return {
            "adapter": self.adapter_name,
            "display_name": self.display_name,
            "dataset_type": dataset_payload.get("dataset_type"),
            "file_format": dataset_payload.get("query_profile", {}).get("file_format"),
            "supported_operations": ["dataset_summary", "trait_list", "trait_search",
                                     "subject_list", "subject_detail", "trait_values"],
            "query_entrypoints": ["/api/v1/dataset/query/execute"],
            "examples": {
                "dataset_summary": {"operation": "dataset_summary", "params": {}},
                "trait_list": {"operation": "trait_list", "params": {"limit": 20}},
                "trait_search": {"operation": "trait_search", "params": {"keyword": example_trait_search, "limit": 20}},
                "subject_list": {"operation": "subject_list", "params": {"limit": 20}},
                "subject_detail": {"operation": "subject_detail", "params": {"subject_id": example_subject_id}},
                "trait_values": {"operation": "trait_values", "params": {"trait": example_trait_name, "limit": 20}},
            },
        }

    # -- New three-table path --
    example_trial_id = ""
    example_plot_id = ""
    example_trait_code = ""
    example_trait_codes: list = []
    example_plot_ids: list = []

    try:
        rows = query_sqlite(file_path, "SELECT id FROM trial ORDER BY id ASC LIMIT 1")
        if rows:
            example_trial_id = str(rows[0]["id"])
    except Exception:
        pass

    try:
        rows = query_sqlite(file_path, "SELECT id, plot_code FROM plot ORDER BY id ASC LIMIT 5")
        if rows:
            example_plot_id = str(rows[0]["id"])
            example_plot_ids = [str(r["id"]) for r in rows]
    except Exception:
        pass

    try:
        rows = query_sqlite(
            file_path,
            "SELECT DISTINCT trait_code FROM observation WHERE value_numeric IS NOT NULL ORDER BY trait_code ASC LIMIT 3",
        )
        if rows:
            example_trait_code = str(rows[0]["trait_code"])
            example_trait_codes = [str(r["trait_code"]) for r in rows]
    except Exception:
        pass

    return {
        "adapter": self.adapter_name,
        "display_name": self.display_name,
        "dataset_type": dataset_payload.get("dataset_type"),
        "file_format": fmt,
        "supported_operations": [
            "trial_list", "trial_detail", "trait_list", "trait_search",
            "plot_list", "plot_detail", "trait_values", "multi_trait_query",
        ],
        "query_entrypoints": ["/api/v1/dataset/query/execute"],
        "examples": {
            "trial_list": {"operation": "trial_list", "params": {}},
            "trial_detail": {"operation": "trial_detail", "params": {"trial_id": example_trial_id}},
            "trait_list": {"operation": "trait_list", "params": {"limit": 20}},
            "trait_search": {"operation": "trait_search", "params": {"keyword": example_trait_code, "limit": 20}},
            "plot_list": {"operation": "plot_list", "params": {"trial_id": example_trial_id, "limit": 20}},
            "plot_detail": {"operation": "plot_detail", "params": {"plot_id": example_plot_id}},
            "trait_values": {"operation": "trait_values", "params": {"trait": example_trait_code, "limit": 20}},
            "multi_trait_query": {
                "operation": "multi_trait_query",
                "params": {
                    "trait_codes": example_trait_codes[:2],
                    "plot_ids": example_plot_ids[:3],
                },
            },
        },
    }
```

- [ ] **Step 2: Check no syntax errors**

```bash
python3 -c "compile(open('/Users/kentnf/projects/omicsagent/odata/backend/api-server/apps/datasets/adapters/phenome.py').read(), 'phenome.py', 'exec'); print('OK')"
```

- [ ] **Step 3: Restart backend and verify describe response**

```bash
# After registering the new .db file as the dataset's asset, call:
curl -s -X POST http://127.0.0.1:8001/api/v1/dataset/version/query/capabilities \
  -H "Content-Type: application/json" \
  -d '{"version_id": 24}' | python3 -m json.tool
# Expected: supported_operations includes trial_list, multi_trait_query, etc.
```

---

### Task 4: Implement New Query Operations (execute)

**Files:**
- Modify: `backend/api-server/apps/datasets/adapters/phenome.py:152-402`

Add new query methods and route in `execute()`.

- [ ] **Step 1: Add `_query_trial_list` method**

```python
def _query_trial_list(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    limit = int(params.get("limit") or 100)
    rows = query_sqlite(
        file_path,
        "SELECT id, trial_name, location, year, season, trial_type, design_type FROM trial ORDER BY id ASC LIMIT ?",
        (limit,),
    )
    return {"items": rows, "count": len(rows)}
```

- [ ] **Step 2: Add `_query_trial_detail` method**

```python
def _query_trial_detail(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    trial_id = params.get("trial_id")
    if not trial_id:
        raise HTTPException(status_code=400, detail="trial_id is required")
    rows = query_sqlite(file_path, "SELECT * FROM trial WHERE id = ?", (trial_id,))
    if not rows:
        raise HTTPException(status_code=404, detail=f"trial not found: {trial_id}")
    plot_count = query_sqlite(
        file_path, "SELECT COUNT(*) AS cnt FROM plot WHERE trial_id = ?", (trial_id,)
    )[0]["cnt"]
    trait_count = query_sqlite(
        file_path,
        "SELECT COUNT(DISTINCT trait_code) AS cnt FROM observation o JOIN plot p ON p.id = o.plot_id WHERE p.trial_id = ?",
        (trial_id,),
    )[0]["cnt"]
    return {"trial": dict(rows[0]), "plot_count": plot_count, "trait_count": trait_count}
```

- [ ] **Step 3: Add `_query_plot_list` method**

```python
def _query_plot_list(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    trial_id = params.get("trial_id")
    limit = int(params.get("limit") or 100)
    if trial_id:
        rows = query_sqlite(
            file_path,
            "SELECT id, plot_code, subject_name, subject_name_cn, block, rep, germplasm_id FROM plot WHERE trial_id = ? ORDER BY id ASC LIMIT ?",
            (trial_id, limit),
        )
    else:
        rows = query_sqlite(
            file_path,
            "SELECT id, plot_code, subject_name, subject_name_cn, block, rep, germplasm_id FROM plot ORDER BY id ASC LIMIT ?",
            (limit,),
        )
    return {"items": rows, "count": len(rows)}
```

- [ ] **Step 4: Add `_query_plot_detail` method**

```python
def _query_plot_detail(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    plot_id = params.get("plot_id")
    if not plot_id:
        raise HTTPException(status_code=400, detail="plot_id is required")
    rows = query_sqlite(file_path, "SELECT * FROM plot WHERE id = ?", (plot_id,))
    if not rows:
        raise HTTPException(status_code=404, detail=f"plot not found: {plot_id}")
    obs_rows = query_sqlite(
        file_path,
        "SELECT trait_code, value_numeric, value_text, value_category, timepoint, is_missing FROM observation WHERE plot_id = ? ORDER BY trait_code",
        (plot_id,),
    )
    return {"plot": dict(rows[0]), "observations": obs_rows, "observation_count": len(obs_rows)}
```

- [ ] **Step 5: Add `_query_trait_values_new` method**

```python
def _query_trait_values_new(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    trait_code = params.get("trait") or params.get("trait_name") or params.get("trait_code")
    if not trait_code:
        raise HTTPException(status_code=400, detail="trait is required")
    trial_id = params.get("trial_id")
    timepoint = params.get("timepoint")
    limit = int(params.get("limit") or 200)

    sql = """
    SELECT p.plot_code, p.subject_name, p.subject_name_cn, o.value_numeric, o.value_text,
           o.value_category, o.timepoint, o.is_missing
    FROM observation o JOIN plot p ON p.id = o.plot_id
    WHERE o.trait_code = ?
    """
    args: list = [trait_code]

    if trial_id:
        sql += " AND p.trial_id = ?"
        args.append(trial_id)
    if timepoint:
        sql += " AND o.timepoint = ?"
        args.append(timepoint)

    sql += " ORDER BY p.id ASC LIMIT ?"
    args.append(limit)

    rows = query_sqlite(file_path, sql, tuple(args))
    items = []
    non_missing = 0
    for r in rows:
        if not r.get("is_missing"):
            non_missing += 1
        items.append({
            "plot_code": r.get("plot_code"),
            "subject_name": r.get("subject_name_cn") or r.get("subject_name"),
            "value_numeric": r.get("value_numeric"),
            "value_text": r.get("value_text"),
            "value_category": r.get("value_category"),
            "timepoint": r.get("timepoint"),
        })
    return {"trait": trait_code, "items": items, "count": len(items), "non_missing_count": non_missing}
```

- [ ] **Step 6: Add `_query_multi_trait` method**

```python
def _query_multi_trait(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    trait_codes = params.get("trait_codes") or []
    plot_ids = params.get("plot_ids") or []
    if not trait_codes or not plot_ids:
        raise HTTPException(status_code=400, detail="trait_codes and plot_ids are required")

    placeholders_t = ",".join("?" * len(trait_codes))
    placeholders_p = ",".join("?" * len(plot_ids))

    sql = f"""
    SELECT p.plot_code, p.subject_name, p.subject_name_cn, o.trait_code,
           o.value_numeric, o.value_text, o.timepoint, o.is_missing
    FROM observation o JOIN plot p ON p.id = o.plot_id
    WHERE o.trait_code IN ({placeholders_t}) AND o.plot_id IN ({placeholders_p})
    ORDER BY p.id, o.trait_code
    """
    rows = query_sqlite(file_path, sql, tuple(trait_codes + plot_ids))

    # Build plot × trait matrix
    matrix: Dict[str, Dict[str, Any]] = {}
    plot_info: Dict[str, str] = {}
    for r in rows:
        pid = str(r["plot_code"] or r["plot_id"])
        tc = str(r["trait_code"])
        if pid not in matrix:
            matrix[pid] = {}
            plot_info[pid] = str(r.get("subject_name_cn") or r.get("subject_name") or "")
        matrix[pid][tc] = r.get("value_numeric") if r.get("value_numeric") is not None else r.get("value_text")

    return {
        "trait_codes": trait_codes,
        "plot_ids": list(plot_info.keys()),
        "plot_names": plot_info,
        "matrix": matrix,
        "count": len(rows),
    }
```

- [ ] **Step 7: Route new operations in execute()**

Add at the top of `execute()`, after `file_path` and `table_name` resolution:

```python
def execute(self, dataset_payload: Dict[str, Any], operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
    file_path = self.require_file_path(dataset_payload)

    if self._is_new_schema(file_path):
        return self._execute_new(file_path, operation, params, dataset_payload)

    # -- Existing old-path code below (unchanged) --
    table_name = self._require_phenotype_table(file_path)
    ...
```

- [ ] **Step 8: Add `_execute_new` dispatch**

```python
def _execute_new(self, file_path: str, operation: str, params: Dict[str, Any], dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
    if operation == "trial_list":
        data = self._query_trial_list(file_path, params)
    elif operation == "trial_detail":
        data = self._query_trial_detail(file_path, params)
    elif operation == "trait_list":
        return self._execute_old_trait_list(file_path, params, dataset_payload)
    elif operation == "trait_search":
        return self._execute_old_trait_search(file_path, params, dataset_payload)
    elif operation == "plot_list":
        data = self._query_plot_list(file_path, params)
    elif operation == "plot_detail":
        data = self._query_plot_detail(file_path, params)
    elif operation == "trait_values":
        data = self._query_trait_values_new(file_path, params)
    elif operation == "multi_trait_query":
        data = self._query_multi_trait(file_path, params)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported operation: {operation}")

    return {
        "adapter": self.adapter_name,
        "operation": operation,
        "dataset_id": dataset_payload["id"],
        "data": data,
    }
```

- [ ] **Step 9: Extract old trait_list/trait_search into reusable methods**

Refactor the trait_list and trait_search code in the old `execute()` into `_execute_old_trait_list` and `_execute_old_trait_search` so they can be called from both old-path execute and new-path `_execute_new`.

---

### Task 5: Register Demo Data as New Dataset Version

**Files:**
- Modify: (database records)

Update the dataset_asset record for the phenome dataset to point to the new `rose_phenotype_v2.db` file.

- [ ] **Step 1: Find the current asset record**

```bash
python3 -c "
import psycopg2
conn = psycopg2.connect(host='127.0.0.1', port=5433, user='fan_api', password='fan_api_dev', dbname='fan_api_poc_dev')
cur = conn.cursor()
cur.execute('SELECT id, dataset_version_id, asset_type, file_format, storage_backend FROM dataset_asset WHERE dataset_version_id = 24;')
for r in cur.fetchall(): print(r)
conn.close()
"
```

- [ ] **Step 2: Update or create asset record to point to the new .db file**

The phenome asset should point to `rose_phenotype_v2.db` with `file_format = 'sqlite'` and `query_engine = 'phenome'`.

If the XLSX file is the only asset and is the data source, we need to either:
1. Add a new file asset pointing to the .db, or
2. Register the .db as a derived asset

Check the existing storage_backend and path conventions used by other datasets.

- [ ] **Step 3: Verify the new asset is queryable**

```bash
# Call capabilities endpoint and check new operations appear
```

---

### Task 6: Update Frontend QueryForm Default Params

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/views/apps/dataset/components/QueryForm.vue:28-48`

Add default parameters for new phenome operations (backend examples are primary source, these are fallback).

- [ ] **Step 1: Add new defaultParams entries**

```typescript
const defaultParams: Record<string, Record<string, any>> = {
  // ... existing entries ...
  trial_list: { limit: 20 },
  trial_detail: { trial_id: '' },
  plot_list: { trial_id: '', limit: 20 },
  plot_detail: { plot_id: '' },
  multi_trait_query: { trait_codes: [], plot_ids: [] },
};
```

Add these entries inside the `defaultParams` object, after the existing `subject_detail` entry.

---

### Task 7: End-to-End Verification

- [ ] **Step 1: Restart all services**

```bash
# Backend auto-reloads via uvicorn --reload
# Frontend auto-reloads via Vite HMR
```

- [ ] **Step 2: Test old dataset still works**

1. Open a dataset that uses old flat `phenotype` table
2. Click "载入示例参数" on each operation → should show old operation set with real examples

- [ ] **Step 3: Test new dataset operations**

1. Open dataset 19 (rose phenome with new .db)
2. `trial_list` → should return 1 trial
3. `trial_detail` with trial_id=1 → should show trial info + counts
4. `plot_list` → should return 12 plots
5. `plot_detail` with plot_id=1 → should show plot + 14 observations
6. `trait_values` with trait="花瓣长" → should return 12 values (one per plot)
7. `multi_trait_query` with 2 traits × 3 plots → should return matrix

- [ ] **Step 4: Test example auto-load**

Click "载入示例参数" for each operation → params should populate with real IDs from the data.
