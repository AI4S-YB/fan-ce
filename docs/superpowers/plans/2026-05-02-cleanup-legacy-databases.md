# Clean Up Legacy `databases` Tables — Implementation Plan

> **Goal:** Remove `databases`, `databases_metadata`, `databases_file`, `project_database` tables. Replace with `dataset_registry` + `asset_file`.

> **Strategy:** Refactor `legacy_bridge` to read/write new tables instead of old ones. Keep the bridge interface unchanged so 30+ call sites in `services.py` need minimal or no modification.

---

## Current State

```
databases (5 rows: id, name, user_id, is_public, status, ...)
    ├── databases_metadata (0 rows — empty)
    ├── databases_file (5 rows — only filename refs)
    └── project_database (0 rows — empty)

dataset_registry (5 rows: id, database_id→databases.id, title, lifecycle_state, visibility, ...)
    └── dataset_asset
        └── asset_file (actual files, 30+ rows)
```

### Field Mapping

| databases field | dataset_registry equivalent | Status |
|-----------------|---------------------------|--------|
| `id` | `database_id` (FK back to databases.id) | Need to break FK loop |
| `name` | `title` | Already exists |
| `user_id` | **MISSING** | Need to add `owner_id` |
| `type` | `dataset_type` | Already exists |
| `status` | `lifecycle_state` | Already exists |
| `is_public` | `visibility == 'public'` | Can derive |
| `is_active` | Derived from lifecycle | Can derive |
| `is_delete` | — | Not used, skip |
| `create_time` | `create_time` | Already exists |
| `remark` | `description_md` | Already exists |

### databases_file → Already Replaced

| databases_file field | asset_file equivalent |
|---------------------|----------------------|
| `name` / `file_name` | `file_name` |
| `path` / `url` | `storage_uri` / `local_path` |
| `size` | `file_size` |
| `type` | `file_format` |

---

## Implementation Tasks

### Task 1: Extend dataset_registry with missing permission fields

**Add columns:**
- `owner_id INTEGER` — replaces `databases.user_id`
- `is_public BOOLEAN` — first-class public flag (synchronized from visibility)

**Data migration:**
```sql
UPDATE dataset_registry SET owner_id = d.user_id, is_public = d.is_public
FROM databases d WHERE dataset_registry.database_id = d.id;
```

**Files:**
- Migration: `alembic/versions/xxxx_add_owner_public_to_dataset_registry.py`
- Model: `apps/datasets/models.py` — `DatasetRegistry` +2 columns

### Task 2: Refactor legacy_bridge — get_database → dataset_registry

**Change `get_database()`** to read from `DatasetRegistry` instead of `Databases`:

```python
# OLD: return database_db.get(db=db, id=dataset_id)
# NEW:
registry = db.query(DatasetRegistry).filter(
    DatasetRegistry.database_id == dataset_id
).first()
# Return a SimpleNamespace or dict matching the old Databases interface
return SimpleNamespace(
    id=dataset_id,
    name=registry.title,
    user_id=registry.owner_id,
    is_public=registry.is_public,
    ...
)
```

**Change `list_databases()`** to query `DatasetRegistry`.

**Change `create_database()`** to insert into `DatasetRegistry` (with auto-generated `database_id`).

**Change `update_database()`** to update `DatasetRegistry`.

All callers in `services.py` are unaffected — they only see the bridge interface.

### Task 3: Refactor legacy_bridge — file methods → asset_file

**Replace `get_primary_file()`**: query `asset_file` via `dataset_asset` where `is_query_entry=1`, return primary file info.

**Replace `create_primary_file()` / `update_primary_file()`**: write to `asset_file`.

**Remove `list_meta()`**: `databases_metadata` is empty; return `[]`.

**Remove project link methods**: `project_database` is empty; return `[]`.

### Task 4: Break the database_id FK loop

After all read/write goes through `dataset_registry`:

- Remove `dataset_registry.database_id` column — no longer needed
- `dataset_version.database_id` now references `dataset_registry.id` directly

This is the key step that makes `databases` table truly removable.

### Task 5: Drop legacy tables

```sql
DROP TABLE databases_metadata CASCADE;
DROP TABLE databases_file CASCADE;
DROP TABLE project_database CASCADE;
DROP TABLE databases CASCADE;
```

**Files:**
- Migration: `alembic/versions/xxxx_drop_legacy_database_tables.py`
- Delete: `apps/databases/` module (models.py, crud.py, routers.py, api/, services.py)
- Delete: `apps/datasets/legacy_bridge.py`
- Update: `apps/datasets/services.py` — remove bridge imports, use `DatasetRegistry` directly

### Task 6: Update tests

- Replace `Databases.__table__` with `DatasetRegistry.__table__` in test fixtures
- Remove databases model imports from conftest.py and test files
- Verify all tests pass

### Task 7: Delete databases routers and frontend APIs

- Remove `apps/databases/routers.py` from `apps/routers.py`
- Clean up deprecated frontend API functions (already unused)
- Verify build

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| 30+ call sites break | Refactor bridge internally, keep interface stable |
| FK constraint violations | Drop child tables before parent; use CASCADE |
| Tests depend on Databases model | Update conftest.py fixtures to use DatasetRegistry |
| `database_id` FK confusion | Task 4 breaks the circular dependency explicitly |
