# Phenome/Breeding Data Model Upgrade Design

> **Status:** Approved | **Date:** 2026-04-29

**Goal:** Upgrade from a flat subject×trait phenotype table to a three-tier Trial→Plot→Observation model supporting breeding trial design fields and optional germplasm linkage.

**Architecture:** New SQLite/PostgreSQL schema with three linked tables. PhenomeAdapter detects table structure at query time — old flat `phenotype` table still works, new three-table datasets get extended query operations.

**Tech Stack:** SQLite (raw data), PostgreSQL (indexed copy), Python PhenomeAdapter, Vue QueryForm frontend.

---

## 1. Data Model

### Trial（试验）

```
trial_name          TEXT    试验名称
location            TEXT    地点
year                INTEGER 年份
season              TEXT    季节/茬口
trial_type          TEXT    试验类型（品比/区域/生产/DUS）
design_type         TEXT    试验设计（随机区组/完全随机/格子方）
remark              TEXT    备注
```

### Plot（小区/试验行）

```
trial_id            INTEGER FK→Trial
germplasm_id        INTEGER FK→Germplasm（nullable，先导入后关联）
plot_code           TEXT    小区/材料编号
subject_name        TEXT    材料名称
subject_name_cn     TEXT    中文名
subject_name_en     TEXT    英文名
block               INTEGER 区组
rep                 INTEGER 重复号
row                 INTEGER 行号（可选）
col                 INTEGER 列号（可选）
treatment           TEXT    处理（可选）
```

Key design decisions:
- `germplasm_id` is nullable: users can import phenotype data first, link to germplasm later
- Plot is the pivot — one plot can have many observations (multiple traits measured on same plot)
- `subject_name` denormalized on plot for query convenience even when germplasm not linked

### Observation（观测值）

```
plot_id             FK→Plot
trait_code          TEXT    性状编码
value_numeric       REAL    数值型
value_text          TEXT    文本型
value_category      TEXT    分类型
timepoint           TEXT    时间点
obs_date            TEXT    观测日期
is_missing          INTEGER 是否缺失
```

- `value_numeric` column type corrected to REAL/Float (fixes current varchar bug causing OID 1043 error)
- One observation row per trait per plot

### Trait（性状定义，保留现有 phn_trait 表）

```
trait_code          TEXT    性状编码（唯一）
trait_name          TEXT    性状名称
trait_name_cn       TEXT    中文名
trait_name_en       TEXT    英文名
value_type          TEXT    值类型（numeric/text/category）
unit                TEXT    单位
time_axis_type      TEXT    时间轴类型
category_group      TEXT    分类组
display_order       INTEGER 排序
```

---

## 2. Storage Strategy

### SQLite（原始数据副本）
- Three tables: `trial`, `plot`, `observation`
- Created during Excel import, stored alongside source file
- Adapter queries directly when PostgreSQL index unavailable

### PostgreSQL（索引加速）
- Mirrors SQLite schema in `phn_trial`, `phn_plot`, `phn_observation` tables
- Populated by import pipeline (existing pattern in `PhenomeObservation`/`PhenomeSubject`)
- Enables SQL joins across germplasm, genotype, phenotype

---

## 3. Query Operations

Current 6 operations → upgraded to:

| Operation | Status | Description |
|-----------|--------|-------------|
| `trial_list` | New | List all trials in dataset |
| `trial_detail` | New | Trial info + plot count + trait summary |
| `trait_list` | Keep | List trait definitions |
| `trait_search` | Keep | Search traits by keyword |
| `plot_list` | Rename from `subject_list` | List plots, filter by trial_id |
| `plot_detail` | Rename from `subject_detail` | Single plot + all trait values |
| `trait_values` | Upgrade | Filter by trial_id, year, timepoint |
| `multi_trait_query` | New | Multiple traits × multiple plots → matrix |

### Example Parameters (Describe)

`describe()` extracts real IDs from actual data:

```
trial_list:      {}
trial_detail:    { trial_id: 1 }
trait_list:      { limit: 20 }
trait_search:    { keyword: <first_real_trait_name>, limit: 20 }
plot_list:       { trial_id: 1, limit: 20 }
plot_detail:     { plot_id: 1 }
trait_values:    { trait: <first_real_trait>, trial_id: 1, limit: 20 }
multi_trait_query: { trait_codes: [<first_2_traits>], plot_ids: [<first_3_plots>] }
```

---

## 4. Data Import Flow

```
Excel Upload（长表）
  ↓
1. Column Mapping
  User maps Excel columns → system fields
  Required: plot_code, trait_code, value
  Optional: trial_name, year, location, block, rep, timepoint
  ↓
2. Trial Matching
  Match on (trial_name, year, location) → existing or new Trial
  ↓
3. Germplasm Linkage（宽松）
  plot_code / subject_name → fuzzy match taxonomy germplasm_name
  Match → auto-fill germplasm_id
  No match → germplasm_id = null, record in "pending association" list
  ↓
4. Ingest
  SQLite: three-table structure saved
  PostgreSQL: indexed copy（可选，跟随现有 import pipeline）
  ↓
5. Post-Ingest
  UI shows "N plots pending germplasm association"
  User can link later without blocking query
```

---

## 5. Adapter Changes (PhenomeAdapter)

### `supports()`
No changes — gate on `asset_type == "phenotype_index"` or `file_format in ("db", "sqlite")`.

### `describe()`
- Detect table structure: `SELECT name FROM sqlite_master WHERE name IN ('trial', 'plot', 'observation')`
- If all three exist → new path, return new operation list + real examples
- If only `phenotype` exists → old path (backward compatible)

### `execute()` 
- Route to `_execute_new()` or existing `_execute_old()` based on detected schema
- New execute supports all operations in the table above

---

## 6. Migration

### Existing Data (dataset 19 / rose phenome)
- Old flat `phenotype` table remains readable via old path
- New file `rose_phenotype_v2.db` created with trial/plot/observation structure (migration script: `scripts/migrate_rose_phenome.py`)
- Register as new dataset version or update existing version's file pointer

### Fix: value_numeric Type
- PostgreSQL `phn_observation.value_numeric`: ALTER from varchar to Float
- SQLite `observation.value_numeric`: created as REAL in new schema

---

## 7. What Does NOT Change

- `GenericFileAdapter`, `SequenceAdapter`, `AnnotationAdapter`, `ExpressionAdapter`, `FunctionalAnnotationAdapter` — unaffected
- `DatasetAdapterRegistry` — no changes needed (PhenomeAdapter handles routing internally)
- Frontend `QueryForm.vue` — parameter format still JSON, examples feed via `describe()`
- Authentication, permissions, file scanning — unchanged

---

## 8. Scope Boundaries

**In scope:** Data model upgrade, PhenomeAdapter query operations, import flow design, demo data migration

**Out of scope:** Germplasm matching algorithm details, batch germplasm association UI, Excel column auto-detection, genotype-phenotype joint queries (future)
