# Phase 1: 架构补基 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 Dataset 主表、启用 Asset Type Registry、实现 Breeding 聚合 API 和跨域数据集查询

**Architecture:** Phase 1 覆盖 4 项修复（F-1, F-3 partial, F-4, F-10），F-11（权限规则）作为配置文档落地。F-1 创建独立的 `dataset` 主表并将 `DatasetVersion` 通过 `dataset_id` FK 关联；F-3 部分在 `BreedingDomainService` 中新增 material/program → dataset 聚合查询；F-4 新增 material/trial overview 和 link-dataset 业务端点；F-10 将 `services.py` 中的硬编码映射替换为 `AssetTypeRegistry` 表查询。

**Tech Stack:** Python 3.11, SQLAlchemy 2.0+, Alembic, FastAPI, PostgreSQL, Pytest

---

### Task 1: F-10 — 替换硬编码 Asset Type 映射为 Registry 查询

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py:121-130`
- Modify: `backend/api-server/apps/datasets/services.py:1244`
- Modify: `backend/api-server/apps/datasets/services.py:1553`
- Test: `backend/api-server/tests/test_dataset_asset_type_resolution.py`

**Context:** 当前 `DatasetDomainService` 维护三个硬编码字典：`DATASET_TYPE_ALIASES` (77-85)、`FILE_FORMAT_TO_DATASET_TYPE` (86-120)、`DATASET_TYPE_TO_ASSET_TYPE` (121-130)。`AssetTypeRegistry` 表记录了 dataset_type → asset_type 的合法映射（`allowed_dataset_types` 字段），但注册新数据集时没有用上。目标是将 `_resolve_default_asset_type()` 改为查表，同时保留硬编码作为 fallback。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dataset_asset_type_resolution.py
import pytest
from apps.datasets.services import DatasetDomainService


class TestAssetTypeResolution:
    """F-10: Asset type resolution MUST consult AssetTypeRegistry table."""

    def test_resolve_asset_type_from_registry_when_entry_exists(self, db_session):
        """When AssetTypeRegistry has a matching entry for the dataset type,
        the resolver must return the registry-configured asset type, not the hardcoded default."""
        from apps.datasets.models import AssetTypeRegistry

        # Insert a registry override: "variome" datasets default to "variant_vcf" asset.
        # We register a custom asset type "custom_variant_bundle" linked to "variome".
        registry_entry = AssetTypeRegistry(
            code="custom_variant_bundle",
            base_code="variant_vcf",
            name="Custom Variant Bundle",
            allowed_dataset_types='["variome"]',
            is_active=1,
            sort_order=10,
        )
        db_session.add(registry_entry)
        db_session.commit()

        service = DatasetDomainService()
        resolved = service._resolve_default_asset_type_code(
            db=db_session,
            dataset_type="variome",
        )

        # Registry entry with highest sort_order matching "variome" wins.
        assert resolved == "custom_variant_bundle"

    def test_fallback_to_hardcoded_when_no_registry_match(self, db_session):
        """When no AssetTypeRegistry entry matches, fall back to the hardcoded map."""
        service = DatasetDomainService()
        resolved = service._resolve_default_asset_type_code(
            db=db_session,
            dataset_type="variome",
        )

        assert resolved == "variant_vcf"

    def test_registry_inactive_entry_is_skipped(self, db_session):
        """Inactive registry entries must be ignored during resolution."""
        from apps.datasets.models import AssetTypeRegistry

        registry_entry = AssetTypeRegistry(
            code="inactive_variant",
            base_code="variant_vcf",
            name="Inactive Variant",
            allowed_dataset_types='["variome"]',
            is_active=0,  # inactive
            sort_order=10,
        )
        db_session.add(registry_entry)
        db_session.commit()

        service = DatasetDomainService()
        resolved = service._resolve_default_asset_type_code(
            db=db_session,
            dataset_type="variome",
        )

        assert resolved == "variant_vcf"  # falls back to hardcoded
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dataset_asset_type_resolution.py -v`
Expected: FAIL — `_resolve_default_asset_type_code` does not exist yet

- [ ] **Step 3: Add the new method `_resolve_default_asset_type_code` to services.py**

```python
# In apps/datasets/services.py, add this method to DatasetDomainService
# Insert after line 130 (after DATASET_TYPE_TO_ASSET_TYPE dict)

def _resolve_default_asset_type_code(self, db, dataset_type):
    """Look up the default asset type for a dataset_type from AssetTypeRegistry.

    Registry entries take precedence over the hardcoded fallback map.
    Highest sort_order wins among matching entries.
    """
    canonical = self._canonical_dataset_type(dataset_type)
    rows = (
        db.query(AssetTypeRegistry)
        .filter(AssetTypeRegistry.is_active == 1)
        .order_by(AssetTypeRegistry.sort_order.desc())
        .all()
    )
    for row in rows:
        allowed = self._canonicalize_dataset_type_list(
            self._parse_json_list(row.allowed_dataset_types)
        )
        if not allowed or canonical in allowed:
            return row.code
    # Fallback to hardcoded map
    return self.DATASET_TYPE_TO_ASSET_TYPE.get(canonical, "metadata_table")
```

- [ ] **Step 4: Update call sites to use the new method**

In `services.py:1244`, replace:
```python
return self.DATASET_TYPE_TO_ASSET_TYPE.get(
    self._canonical_dataset_type(dataset_type), "metadata_table"
)
```
with:
```python
return self._resolve_default_asset_type_code(db=db, dataset_type=dataset_type)
```

In `services.py:1553`, replace:
```python
return self.FILE_FORMAT_TO_DATASET_TYPE.get(suffix, "generic")
```
with (inject the `db` parameter first — check the caller signature):
```python
# This is in _infer_dataset_type_from_file_path — add db param
return self.FILE_FORMAT_TO_DATASET_TYPE.get(suffix, "generic")
```
Note: `_infer_dataset_type_from_file_path` doesn't take `db` as parameter. For file format → dataset type inference, keep the hardcoded map for now (Phase 3 enhancement). Only change the asset type resolution path.

- [ ] **Step 5: Run tests to verify**

Run: `pytest tests/test_dataset_asset_type_resolution.py -v`
Expected: 3 PASS

Run: `pytest tests/test_dataset_adapter_resolution.py tests/test_dataset_variome_alias.py -v`
Expected: All existing tests PASS (no regression)

- [ ] **Step 6: Commit**

```bash
git add backend/api-server/apps/datasets/services.py \
        backend/api-server/tests/test_dataset_asset_type_resolution.py
git commit -m "$(cat <<'EOF'
fix: resolve default asset type from AssetTypeRegistry instead of hardcoded map

Registry entries match by allowed_dataset_types; highest sort_order wins.
Inactive entries are skipped. Falls back to DATASET_TYPE_TO_ASSET_TYPE
dict when no registry entry matches.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: F-1 — Dataset 主表模型与迁移

**Files:**
- Create: `backend/api-server/apps/datasets/dataset_model.py`
- Modify: `backend/api-server/apps/datasets/models.py:237-258`
- Create: `backend/api-server/alembic/versions/xxxx_add_dataset_master_table.py`
- Modify: `backend/api-server/apps/datasets/services.py` (multiple sites)
- Test: `backend/api-server/tests/test_dataset_master_table.py`

**Context:** `DatasetRegistry` 同时承担"数据集主记录"和"旧兼容桥"两个职责。`DatasetVersion` 通过 `database_id` 回指 Registry，没有直接引用。目标是在不破坏现有功能的前提下建立独立的 `dataset` 表，让 `DatasetVersion.dataset_id` FK 指向它。先创建表 + 回填数据，后续 Phase 再移除 `database_id`。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dataset_master_table.py
import pytest
from apps.datasets.dataset_model import Dataset
from apps.datasets.models import DatasetVersion


class TestDatasetMasterTable:
    """F-1: Dataset master table must exist with FK from DatasetVersion."""

    def test_dataset_table_exists_and_accepts_insert(self, db_session):
        """A row can be inserted into the dataset table with required fields."""
        ds = Dataset(
            dataset_code="DS00001",
            dataset_type="genome",
            organism="Oryza sativa",
            assembly="IRGSP-1.0",
            visibility="private",
            lifecycle_state="draft",
        )
        db_session.add(ds)
        db_session.commit()

        fetched = db_session.query(Dataset).filter_by(dataset_code="DS00001").first()
        assert fetched is not None
        assert fetched.dataset_type == "genome"
        assert fetched.organism == "Oryza sativa"

    def test_dataset_code_is_unique(self, db_session):
        """dataset_code must be unique across the table."""
        ds1 = Dataset(
            dataset_code="DS_DUP",
            dataset_type="genome",
            organism="Oryza sativa",
            assembly="IRGSP-1.0",
        )
        ds2 = Dataset(
            dataset_code="DS_DUP",
            dataset_type="variome",
            organism="Oryza sativa",
            assembly="IRGSP-1.0",
        )
        db_session.add(ds1)
        db_session.commit()
        db_session.add(ds2)

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_dataset_version_has_dataset_id_fk(self, db_session):
        """DatasetVersion must have dataset_id FK pointing to dataset table."""
        ds = Dataset(
            dataset_code="DS_V1_TEST",
            dataset_type="genome",
            organism="Oryza sativa",
            assembly="IRGSP-1.0",
        )
        db_session.add(ds)
        db_session.commit()

        dv = DatasetVersion(
            dataset_id=ds.id,
            version="v1",
            title="Test Version",
            dataset_type="genome",
            lifecycle_state="active",
        )
        db_session.add(dv)
        db_session.commit()

        assert dv.dataset_id == ds.id

        # Verify the FK constraint: referencing a non-existent dataset must fail
        dv_bad = DatasetVersion(
            dataset_id=999999,
            version="v1",
            title="Bad Version",
            dataset_type="genome",
        )
        db_session.add(dv_bad)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dataset_master_table.py -v`
Expected: ImportError — `dataset_model` module does not exist yet

- [ ] **Step 3: Create the Dataset model**

```python
# apps/datasets/dataset_model.py
from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, String, Text, func

from db.database import Base


class Dataset(Base):
    __tablename__ = "dataset"

    id = Column(Integer, primary_key=True, index=True)
    dataset_code = Column(String(128), unique=True, index=True, nullable=False, comment="稳定数据集编码")
    dataset_type = Column(String(128), index=True, comment="数据集类型")
    organism = Column(String(128), index=True, comment="物种")
    assembly = Column(String(128), comment="组装版本")
    visibility = Column(String(32), nullable=False, default="private", comment="可见性")
    lifecycle_state = Column(String(64), nullable=False, default="draft", comment="生命周期状态")
    team_id = Column(Integer, index=True, comment="团队 ID")
    project_id = Column(Integer, index=True, comment="项目 ID")
    meta_json = Column(Text, comment="扩展元数据")
    create_time = Column(DateTime, server_default=func.now(), comment="创建时间")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
```

- [ ] **Step 4: Add `dataset_id` to DatasetVersion model**

```python
# In apps/datasets/models.py, add to DatasetVersion class after line 257:
# Replace the class definition with one that includes dataset_id

# --- Find the class DatasetVersion(Base): block at line 237 ---
# Add after `update_time = Column(Integer, comment="更新时间")` at line 257:

    dataset_id = Column(
        Integer,
        ForeignKey("dataset.id", ondelete="RESTRICT"),
        index=True,
        comment="dataset 主表 ID",
    )

# Also add the import at the top of models.py (line 1):
# Change: from sqlalchemy import BigInteger, Column, ...
# To include ForeignKey:
from sqlalchemy import BigInteger, Column, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
```

- [ ] **Step 5: Generate Alembic migration**

Run:
```bash
cd backend/api-server
alembic revision --autogenerate -m "add_dataset_master_table"
```

Review the generated migration in `alembic/versions/`. It should create:
1. `dataset` table with columns as defined
2. `ALTER TABLE dataset_version ADD COLUMN dataset_id INTEGER`
3. `CREATE INDEX ix_dataset_version_dataset_id ON dataset_version(dataset_id)`
4. `ALTER TABLE dataset_version ADD CONSTRAINT fk_dataset_version_dataset_id FOREIGN KEY (dataset_id) REFERENCES dataset(id) ON DELETE RESTRICT`

Then apply:
```bash
alembic upgrade head
```

Expected: Migration applies without error.

- [ ] **Step 6: Run tests again**

Run: `pytest tests/test_dataset_master_table.py -v`
Expected: 3 PASS

Run full dataset test suite:
```bash
pytest tests/test_dataset_*.py -v
```
Expected: No regressions (all previously passing tests still pass).

- [ ] **Step 7: Commit**

```bash
git add backend/api-server/apps/datasets/dataset_model.py \
        backend/api-server/apps/datasets/models.py \
        backend/api-server/alembic/versions/*add_dataset_master_table*.py \
        backend/api-server/tests/test_dataset_master_table.py
git commit -m "$(cat <<'EOF'
feat: add dataset master table with dataset_id FK on DatasetVersion

Create independent `dataset` table holding dataset-level fields
(code, type, organism, assembly, visibility, lifecycle_state, team_id,
project_id). Add dataset_id column to DatasetVersion with FK constraint.
Legacy database_id remains in place for backward compatibility.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: F-4a — Material Overview 聚合端点

**Files:**
- Modify: `backend/api-server/apps/breeding/services.py` (add method)
- Modify: `backend/api-server/apps/breeding/api/core.py` (add endpoint)
- Modify: `backend/api-server/apps/breeding/schemas.py` (add response schema)
- Test: `backend/api-server/tests/test_breeding_aggregates.py`

**Context:** 当前 `list_programs()` 有 `_collect_program_counts` 和 `_collect_program_previews` 做聚合，但 `get_material()` 仅返回单条记录的序列化结果。用户查看某个 material 详情时，看不到它关联了哪些 dataset、参与了哪些 trial、有多少 observation。Material overview 要返回这些聚合信息。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_breeding_aggregates.py
import pytest
from apps.breeding.services import BreedingDomainService


class TestMaterialOverview:
    """F-4a: Material overview aggregates linked datasets, trials, observations."""

    def test_material_overview_includes_linked_dataset_count(self, db_session):
        """Material overview must include counts of linked datasets by type."""
        from apps.breeding.models import (
            BreedingMaterial,
            BreedingProgram,
            BreedingDatasetSubjectLink,
            BreedingVariantSampleMap,
            BreedingPhenotypeSubjectMap,
        )
        from apps.datasets.dataset_model import Dataset

        # Setup: create program, material, dataset, and link records
        program = BreedingProgram(code="P_OVERVIEW", name="Overview Test", status="active")
        db_session.add(program)
        db_session.commit()

        material = BreedingMaterial(
            program_id=program.id,
            material_code="MAT_OV_001",
            material_name="Test Material",
        )
        db_session.add(material)
        db_session.commit()

        ds_variant = Dataset(
            dataset_code="DS_VAR_OV", dataset_type="variome",
            organism="Oryza sativa", assembly="IRGSP-1.0",
        )
        ds_pheno = Dataset(
            dataset_code="DS_PHENO_OV", dataset_type="phenome",
            organism="Oryza sativa", assembly="IRGSP-1.0",
        )
        db_session.add_all([ds_variant, ds_pheno])
        db_session.commit()

        # Create link records
        variant_map = BreedingVariantSampleMap(
            dataset_id=ds_variant.id, version_id=1, asset_id=1,
            vcf_sample_name="SAMPLE_1", material_id=material.id,
            mapping_status="matched",
        )
        pheno_map = BreedingPhenotypeSubjectMap(
            dataset_id=ds_pheno.id, version_id=1, asset_id=1,
            row_key="SUBJ_1", material_id=material.id,
            trait_code="height", value_numeric=120.5,
            mapping_status="matched",
        )
        db_session.add_all([variant_map, pheno_map])
        db_session.commit()

        service = BreedingDomainService()
        overview = service.get_material_overview(db=db_session, material_id=material.id)

        assert overview is not None
        assert overview["material_code"] == "MAT_OV_001"
        assert overview["linked_dataset_count"] >= 2
        dataset_ids = {d["dataset_id"] for d in overview["linked_datasets"]}
        assert ds_variant.id in dataset_ids
        assert ds_pheno.id in dataset_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_breeding_aggregates.py::TestMaterialOverview::test_material_overview_includes_linked_dataset_count -v`
Expected: AttributeError — `get_material_overview` does not exist

- [ ] **Step 3: Add the response schema**

```python
# In apps/breeding/schemas.py, add:

class MaterialOverviewDataset(BaseModel):
    dataset_id: int
    dataset_code: Optional[str] = None
    dataset_type: Optional[str] = None
    role: Optional[str] = None
    link_type: str  # "variant_sample_map" | "phenotype_subject_map" | "dataset_subject_link" | "dataset_assay_link"


class MaterialOverviewResponse(BaseModel):
    id: int
    material_code: str
    material_name: Optional[str] = None
    program_id: Optional[int] = None
    germplasm_accession: Optional[str] = None
    linked_dataset_count: int = 0
    linked_datasets: List[MaterialOverviewDataset] = []
    trial_count: int = 0
    trials: List[dict] = []
    observation_count: int = 0
    biosample_count: int = 0
    assay_count: int = 0
```

- [ ] **Step 4: Implement `get_material_overview` in BreedingDomainService**

```python
# In apps/breeding/services.py, add to BreedingDomainService:

def get_material_overview(self, db, material_id):
    from apps.datasets.dataset_model import Dataset

    material = breeding_material_db.get(db=db, id=material_id)
    if not material:
        return None

    base = jsonable_encoder(material)

    # Collect linked datasets from 4 link tables
    linked_datasets: list[dict] = []

    # variant_sample_map
    variant_rows = (
        db.query(BreedingVariantSampleMap, Dataset)
        .join(Dataset, Dataset.id == BreedingVariantSampleMap.dataset_id)
        .filter(BreedingVariantSampleMap.material_id == material_id)
        .all()
    )
    for vmap, ds in variant_rows:
        linked_datasets.append({
            "dataset_id": ds.id,
            "dataset_code": ds.dataset_code,
            "dataset_type": ds.dataset_type,
            "role": "variant",
            "link_type": "variant_sample_map",
        })

    # phenotype_subject_map
    pheno_rows = (
        db.query(BreedingPhenotypeSubjectMap, Dataset)
        .join(Dataset, Dataset.id == BreedingPhenotypeSubjectMap.dataset_id)
        .filter(BreedingPhenotypeSubjectMap.material_id == material_id)
        .all()
    )
    for pmap, ds in pheno_rows:
        linked_datasets.append({
            "dataset_id": ds.id,
            "dataset_code": ds.dataset_code,
            "dataset_type": ds.dataset_type,
            "role": "phenotype",
            "link_type": "phenotype_subject_map",
        })

    # dataset_subject_link (may link via material_id)
    subject_rows = (
        db.query(BreedingDatasetSubjectLink, Dataset)
        .join(Dataset, Dataset.id == BreedingDatasetSubjectLink.dataset_id)
        .filter(BreedingDatasetSubjectLink.material_id == material_id)
        .all()
    )
    for slink, ds in subject_rows:
        linked_datasets.append({
            "dataset_id": ds.id,
            "dataset_code": ds.dataset_code,
            "dataset_type": ds.dataset_type,
            "role": slink.role or "subject",
            "link_type": "dataset_subject_link",
        })

    # dataset_assay_link (via biosample → material)
    biosample_ids_subq = (
        db.query(BreedingBioSample.id)
        .filter(BreedingBioSample.material_id == material_id)
        .subquery()
    )
    assay_rows = (
        db.query(BreedingDatasetAssayLink, Dataset)
        .join(Dataset, Dataset.id == BreedingDatasetAssayLink.dataset_id)
        .filter(BreedingDatasetAssayLink.assay_id.in_(
            db.query(BreedingAssay.id).filter(
                BreedingAssay.biosample_id.in_(biosample_ids_subq)
            ).subquery()
        ))
        .all()
    )
    for alink, ds in assay_rows:
        linked_datasets.append({
            "dataset_id": ds.id,
            "dataset_code": ds.dataset_code,
            "dataset_type": ds.dataset_type,
            "role": alink.role or "expression",
            "link_type": "dataset_assay_link",
        })

    # Deduplicate by dataset_id
    seen = set()
    unique_datasets = []
    for d in linked_datasets:
        if d["dataset_id"] not in seen:
            seen.add(d["dataset_id"])
            unique_datasets.append(d)

    # Counts
    trial_count = (
        db.query(func.count(BreedingTrial.id))
        .join(BreedingPlot, BreedingPlot.trial_id == BreedingTrial.id)
        .join(BreedingBioSample, BreedingBioSample.plot_id == BreedingPlot.id)
        .filter(BreedingBioSample.material_id == material_id)
        .scalar()
    ) or 0

    observation_count = (
        db.query(func.count(BreedingObservation.id))
        .filter(BreedingObservation.material_id == material_id)
        .scalar()
    ) or 0

    biosample_count = (
        db.query(func.count(BreedingBioSample.id))
        .filter(BreedingBioSample.material_id == material_id)
        .scalar()
    ) or 0

    assay_count = (
        db.query(func.count(BreedingAssay.id))
        .join(BreedingBioSample, BreedingBioSample.id == BreedingAssay.biosample_id)
        .filter(BreedingBioSample.material_id == material_id)
        .scalar()
    ) or 0

    # Trials list
    trials = (
        db.query(BreedingTrial)
        .join(BreedingPlot, BreedingPlot.trial_id == BreedingTrial.id)
        .join(BreedingBioSample, BreedingBioSample.plot_id == BreedingPlot.id)
        .filter(BreedingBioSample.material_id == material_id)
        .distinct()
        .all()
    )
    trial_list = [
        {"id": t.id, "trial_name": t.trial_name, "trial_type": t.trial_type}
        for t in trials
    ]

    return {
        **base,
        "linked_dataset_count": len(unique_datasets),
        "linked_datasets": unique_datasets,
        "trial_count": trial_count,
        "trials": trial_list,
        "observation_count": observation_count,
        "biosample_count": biosample_count,
        "assay_count": assay_count,
    }
```

- [ ] **Step 5: Add API endpoint**

```python
# In apps/breeding/api/core.py, add:

@breeding_router.post("/material/overview")
async def breeding_material_overview(
    request_data: BreedingInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    overview = breeding_domain_service.get_material_overview(
        db=db, material_id=request_data.id
    )
    if overview is None:
        return response_4004(message="Material not found")
    return response_2000(data=overview)
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_breeding_aggregates.py::TestMaterialOverview::test_material_overview_includes_linked_dataset_count -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/api-server/apps/breeding/services.py \
        backend/api-server/apps/breeding/api/core.py \
        backend/api-server/apps/breeding/schemas.py \
        backend/api-server/tests/test_breeding_aggregates.py
git commit -m "$(cat <<'EOF'
feat: add material overview endpoint with linked dataset aggregation

Aggregates linked datasets from all 4 link tables (variant_sample_map,
phenotype_subject_map, dataset_subject_link, dataset_assay_link),
trial count, observation count, biosample count, and assay count.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: F-4b — Trial Overview 聚合端点

**Files:**
- Modify: `backend/api-server/apps/breeding/services.py`
- Modify: `backend/api-server/apps/breeding/api/core.py`
- Modify: `backend/api-server/apps/breeding/schemas.py`
- Test: `backend/api-server/tests/test_breeding_aggregates.py` (append)

**Context:** 类似 Material Overview，Trial 也需要聚合视图：该 trial 下有多少 plot、observation、material，关联了哪些 dataset。

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_breeding_aggregates.py

class TestTrialOverview:
    """F-4b: Trial overview aggregates plots, materials, observations, datasets."""

    def test_trial_overview_includes_counts(self, db_session):
        from apps.breeding.models import (
            BreedingMaterial,
            BreedingProgram,
            BreedingTrial,
            BreedingPlot,
            BreedingObservation,
        )

        program = BreedingProgram(code="P_TRIAL_OV", name="Trial Overview Test", status="active")
        db_session.add(program)
        db_session.commit()

        trial = BreedingTrial(
            program_id=program.id, trial_name="T_OV_001", trial_type="field",
        )
        db_session.add(trial)
        db_session.commit()

        material = BreedingMaterial(
            program_id=program.id, material_code="MAT_TRIAL", material_name="Mat for Trial",
        )
        db_session.add(material)
        db_session.commit()

        plot = BreedingPlot(
            trial_id=trial.id, plot_code="PLOT_001", material_id=material.id,
        )
        db_session.add(plot)
        db_session.commit()

        obs = BreedingObservation(
            trial_id=trial.id, plot_id=plot.id, material_id=material.id,
            trait_code="height", value_numeric=110.3,
        )
        db_session.add(obs)
        db_session.commit()

        service = BreedingDomainService()
        overview = service.get_trial_overview(db=db_session, trial_id=trial.id)

        assert overview is not None
        assert overview["trial_name"] == "T_OV_001"
        assert overview["plot_count"] == 1
        assert overview["observation_count"] == 1
        assert overview["material_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_breeding_aggregates.py::TestTrialOverview::test_trial_overview_includes_counts -v`
Expected: AttributeError — `get_trial_overview` does not exist

- [ ] **Step 3: Add response schema**

```python
# In apps/breeding/schemas.py, add:

class TrialOverviewResponse(BaseModel):
    id: int
    trial_name: str
    trial_type: Optional[str] = None
    program_id: Optional[int] = None
    plot_count: int = 0
    observation_count: int = 0
    material_count: int = 0
    trait_codes: List[str] = []
    linked_dataset_count: int = 0
    linked_datasets: List[MaterialOverviewDataset] = []
```

- [ ] **Step 4: Implement `get_trial_overview` in BreedingDomainService**

```python
# In apps/breeding/services.py, add to BreedingDomainService:

def get_trial_overview(self, db, trial_id):
    trial = breeding_trial_db.get(db=db, id=trial_id)
    if not trial:
        return None

    base = jsonable_encoder(trial)

    plot_count = (
        db.query(func.count(BreedingPlot.id))
        .filter(BreedingPlot.trial_id == trial_id)
        .scalar()
    ) or 0

    observation_count = (
        db.query(func.count(BreedingObservation.id))
        .filter(BreedingObservation.trial_id == trial_id)
        .scalar()
    ) or 0

    material_count = (
        db.query(func.count(func.distinct(BreedingPlot.material_id)))
        .filter(BreedingPlot.trial_id == trial_id)
        .filter(BreedingPlot.material_id.isnot(None))
        .scalar()
    ) or 0

    trait_rows = (
        db.query(func.distinct(BreedingObservation.trait_code))
        .filter(BreedingObservation.trial_id == trial_id)
        .filter(BreedingObservation.trait_code.isnot(None))
        .all()
    )
    trait_codes = [r[0] for r in trait_rows if r[0]]

    # Linked datasets — trace through material in plots
    material_ids = (
        db.query(BreedingPlot.material_id)
        .filter(BreedingPlot.trial_id == trial_id)
        .filter(BreedingPlot.material_id.isnot(None))
        .distinct()
        .all()
    )
    material_id_list = [r[0] for r in material_ids if r[0]]

    linked_datasets: list[dict] = []
    seen = set()

    if material_id_list:
        from apps.datasets.dataset_model import Dataset

        # variant_sample_map
        for vmap, ds in (
            db.query(BreedingVariantSampleMap, Dataset)
            .join(Dataset, Dataset.id == BreedingVariantSampleMap.dataset_id)
            .filter(BreedingVariantSampleMap.material_id.in_(material_id_list))
            .all()
        ):
            if ds.id not in seen:
                seen.add(ds.id)
                linked_datasets.append({
                    "dataset_id": ds.id, "dataset_code": ds.dataset_code,
                    "dataset_type": ds.dataset_type, "role": "variant",
                    "link_type": "variant_sample_map",
                })

        # phenotype_subject_map
        for pmap, ds in (
            db.query(BreedingPhenotypeSubjectMap, Dataset)
            .join(Dataset, Dataset.id == BreedingPhenotypeSubjectMap.dataset_id)
            .filter(BreedingPhenotypeSubjectMap.material_id.in_(material_id_list))
            .all()
        ):
            if ds.id not in seen:
                seen.add(ds.id)
                linked_datasets.append({
                    "dataset_id": ds.id, "dataset_code": ds.dataset_code,
                    "dataset_type": ds.dataset_type, "role": "phenotype",
                    "link_type": "phenotype_subject_map",
                })

    return {
        **base,
        "plot_count": plot_count,
        "observation_count": observation_count,
        "material_count": material_count,
        "trait_codes": trait_codes,
        "linked_dataset_count": len(linked_datasets),
        "linked_datasets": linked_datasets,
    }
```

- [ ] **Step 5: Add API endpoint**

```python
# In apps/breeding/api/core.py, add:

@breeding_router.post("/trial/overview")
async def breeding_trial_overview(
    request_data: BreedingInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    overview = breeding_domain_service.get_trial_overview(
        db=db, trial_id=request_data.id
    )
    if overview is None:
        return response_4004(message="Trial not found")
    return response_2000(data=overview)
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_breeding_aggregates.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/api-server/apps/breeding/services.py \
        backend/api-server/apps/breeding/api/core.py \
        backend/api-server/apps/breeding/schemas.py \
        backend/api-server/tests/test_breeding_aggregates.py
git commit -m "$(cat <<'EOF'
feat: add trial overview endpoint with plot/material/observation aggregation

Aggregates plot count, observation count, material count, unique trait
codes, and linked datasets traced through material references.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: F-4c — Link Dataset 业务端点

**Files:**
- Modify: `backend/api-server/apps/breeding/services.py`
- Modify: `backend/api-server/apps/breeding/api/core.py`
- Modify: `backend/api-server/apps/breeding/schemas.py`
- Test: `backend/api-server/tests/test_breeding_aggregates.py` (append)

**Context:** 当前创建 link table 记录只能通过通用 CRUD（如 `breeding_dataset_subject_link_create` 手动填 `dataset_id`/`version_id`/`material_id`）。用户需要业务面端点 `POST /breeding/program/{id}/link-dataset`，传入 dataset_id 和 link_type，系统自动查找或创建对应的 link 记录。

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_breeding_aggregates.py

class TestLinkDatasetEndpoint:
    """F-4c: Business-facing link-dataset API."""

    def test_link_dataset_to_program_creates_subject_link(self, db_session):
        from apps.breeding.models import BreedingProgram
        from apps.datasets.dataset_model import Dataset

        program = BreedingProgram(code="P_LINK", name="Link Test", status="active")
        db_session.add(program)
        db_session.commit()

        ds = Dataset(
            dataset_code="DS_LINK", dataset_type="phenome",
            organism="Oryza sativa", assembly="IRGSP-1.0",
        )
        db_session.add(ds)
        db_session.commit()

        service = BreedingDomainService()
        result = service.link_dataset_to_program(
            db=db_session,
            program_id=program.id,
            dataset_id=ds.id,
            version_id=None,  # auto-resolve latest
            link_type="dataset_subject_link",
            role="phenotype",
        )

        assert result["linked"] is True
        assert result["dataset_id"] == ds.id
        assert result["link_type"] == "dataset_subject_link"

        # Verify the link record was created
        from apps.breeding.models import BreedingDatasetSubjectLink
        link = (
            db_session.query(BreedingDatasetSubjectLink)
            .filter_by(dataset_id=ds.id, program_id=program.id)
            .first()
        )
        assert link is not None
        assert link.role == "phenotype"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_breeding_aggregates.py::TestLinkDatasetEndpoint -v`
Expected: AttributeError — `link_dataset_to_program` does not exist

- [ ] **Step 3: Add request/response schemas**

```python
# In apps/breeding/schemas.py:

class LinkDatasetRequest(BaseModel):
    program_id: int
    dataset_id: int
    version_id: Optional[int] = None
    link_type: str  # "dataset_subject_link" | "dataset_assay_link" | "variant_sample_map" | "phenotype_subject_map"
    role: Optional[str] = None
    material_id: Optional[int] = None
    note: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class LinkDatasetResponse(BaseModel):
    linked: bool
    dataset_id: int
    link_type: str
    link_id: Optional[int] = None
    message: Optional[str] = None
```

- [ ] **Step 4: Implement `link_dataset_to_program` in BreedingDomainService**

```python
# In apps/breeding/services.py, add to BreedingDomainService:

def link_dataset_to_program(self, db, program_id, dataset_id, version_id=None, link_type="dataset_subject_link", role=None, material_id=None, note=None):
    from apps.datasets.dataset_model import Dataset
    from apps.datasets.models import DatasetVersion

    # Validate dataset exists
    dataset = db.query(Dataset).filter_by(id=dataset_id).first()
    if not dataset:
        return {"linked": False, "dataset_id": dataset_id, "link_type": link_type, "message": "Dataset not found"}

    # Auto-resolve version
    if version_id is None:
        latest_version = (
            db.query(DatasetVersion)
            .filter(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.id.desc())
            .first()
        )
        if latest_version:
            version_id = latest_version.id
        else:
            return {"linked": False, "dataset_id": dataset_id, "link_type": link_type, "message": "No version found for dataset"}

    link_id = None
    if link_type == "dataset_subject_link":
        link = BreedingDatasetSubjectLink(
            dataset_id=dataset_id,
            version_id=version_id,
            program_id=program_id,
            material_id=material_id,
            role=role or "subject",
            mapping_status="draft",
            mapping_method="manual",
        )
        db.add(link)
        db.commit()
        link_id = link.id
    elif link_type == "dataset_assay_link":
        link = BreedingDatasetAssayLink(
            dataset_id=dataset_id,
            version_id=version_id,
            assay_id=material_id,  # caller passes assay_id as material_id
            role=role or "assay",
            mapping_status="draft",
            mapping_method="manual",
        )
        db.add(link)
        db.commit()
        link_id = link.id
    else:
        return {"linked": False, "dataset_id": dataset_id, "link_type": link_type, "message": f"Unsupported link_type: {link_type}"}

    return {"linked": True, "dataset_id": dataset_id, "link_type": link_type, "link_id": link_id}
```

- [ ] **Step 5: Add API endpoint**

```python
# In apps/breeding/api/core.py, add:

@breeding_router.post("/program/link-dataset")
async def breeding_program_link_dataset(
    request_data: LinkDatasetRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    result = breeding_domain_service.link_dataset_to_program(
        db=db,
        program_id=request_data.program_id,
        dataset_id=request_data.dataset_id,
        version_id=request_data.version_id,
        link_type=request_data.link_type,
        role=request_data.role,
        material_id=request_data.material_id,
        note=request_data.note,
    )
    return response_2000(data=result)
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_breeding_aggregates.py::TestLinkDatasetEndpoint -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/api-server/apps/breeding/services.py \
        backend/api-server/apps/breeding/api/core.py \
        backend/api-server/apps/breeding/schemas.py \
        backend/api-server/tests/test_breeding_aggregates.py
git commit -m "$(cat <<'EOF'
feat: add link-dataset business endpoint for breeding program

POST /breeding/program/link-dataset accepts (program_id, dataset_id,
link_type, role). Auto-resolves latest version when version_id is None.
Supports dataset_subject_link and dataset_assay_link.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: F-3 Partial — get_datasets_for_material 和 get_datasets_for_program

**Files:**
- Create: `backend/api-server/apps/datasets/cross_domain.py`
- Modify: `backend/api-server/apps/breeding/api/core.py` (add two endpoints)
- Modify: `backend/api-server/apps/breeding/schemas.py` (add request schema)
- Test: `backend/api-server/tests/test_cross_domain_dataset_lookup.py`

**Context:** 从 material/program 反查关联的 dataset 是 GWAS 工作流和第 S6-1 缺口的核心需求。当前没有聚合方法。实现为 `CrossDomainDatasetLookup`，放在 dataset app 下（因为返回的是 dataset 信息），查询 breeding 侧的 link table。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cross_domain_dataset_lookup.py
import pytest
from apps.datasets.cross_domain import CrossDomainDatasetLookup


class TestGetDatasetsForMaterial:
    """F-3 partial: Material → Dataset reverse lookup."""

    def test_get_datasets_for_material_returns_all_link_types(self, db_session):
        from apps.breeding.models import (
            BreedingMaterial,
            BreedingProgram,
            BreedingVariantSampleMap,
            BreedingPhenotypeSubjectMap,
        )
        from apps.datasets.dataset_model import Dataset

        program = BreedingProgram(code="P_XD", name="Cross Domain", status="active")
        db_session.add(program)
        db_session.commit()

        material = BreedingMaterial(
            program_id=program.id, material_code="MAT_XD_001", material_name="XD Material",
        )
        db_session.add(material)
        db_session.commit()

        ds_v = Dataset(dataset_code="DS_XD_V", dataset_type="variome", organism="Oryza sativa", assembly="IRGSP-1.0")
        ds_p = Dataset(dataset_code="DS_XD_P", dataset_type="phenome", organism="Oryza sativa", assembly="IRGSP-1.0")
        db_session.add_all([ds_v, ds_p])
        db_session.commit()

        db_session.add(BreedingVariantSampleMap(
            dataset_id=ds_v.id, version_id=1, asset_id=1,
            vcf_sample_name="S1", material_id=material.id, mapping_status="matched",
        ))
        db_session.add(BreedingPhenotypeSubjectMap(
            dataset_id=ds_p.id, version_id=1, asset_id=1,
            row_key="S1", material_id=material.id,
            trait_code="height", value_numeric=100.0, mapping_status="matched",
        ))
        db_session.commit()

        lookup = CrossDomainDatasetLookup()
        result = lookup.get_datasets_for_material(db=db_session, material_id=material.id)

        assert len(result) == 2
        assert {r["dataset_code"] for r in result} == {"DS_XD_V", "DS_XD_P"}
        assert all("dataset_type" in r for r in result)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cross_domain_dataset_lookup.py -v`
Expected: ImportError — module or class does not exist

- [ ] **Step 3: Implement CrossDomainDatasetLookup**

```python
# apps/datasets/cross_domain.py
from sqlalchemy.orm import Session


class CrossDomainDatasetLookup:
    """Cross-domain dataset lookup: given a breeding entity, find linked datasets.

    Consumes breeding link tables from apps.breeding.models.
    Returns dataset summaries from apps.datasets.dataset_model.Dataset.
    Placed in datasets app to avoid circular imports.
    """

    def get_datasets_for_material(self, db: Session, material_id: int) -> list[dict]:
        from apps.breeding.models import (
            BreedingVariantSampleMap,
            BreedingPhenotypeSubjectMap,
            BreedingDatasetSubjectLink,
            BreedingDatasetAssayLink,
            BreedingBioSample,
            BreedingAssay,
        )
        from apps.datasets.dataset_model import Dataset

        results: dict[int, dict] = {}

        def add(ds, role, link_type):
            if ds.id not in results:
                results[ds.id] = {
                    "dataset_id": ds.id,
                    "dataset_code": ds.dataset_code,
                    "dataset_type": ds.dataset_type,
                    "organism": ds.organism,
                    "assembly": ds.assembly,
                    "links": [],
                }
            results[ds.id]["links"].append({"role": role, "link_type": link_type})

        # variant_sample_map
        for vmap, ds in (
            db.query(BreedingVariantSampleMap, Dataset)
            .join(Dataset, Dataset.id == BreedingVariantSampleMap.dataset_id)
            .filter(BreedingVariantSampleMap.material_id == material_id)
            .all()
        ):
            add(ds, "variant", "variant_sample_map")

        # phenotype_subject_map
        for pmap, ds in (
            db.query(BreedingPhenotypeSubjectMap, Dataset)
            .join(Dataset, Dataset.id == BreedingPhenotypeSubjectMap.dataset_id)
            .filter(BreedingPhenotypeSubjectMap.material_id == material_id)
            .all()
        ):
            add(ds, "phenotype", "phenotype_subject_map")

        # dataset_subject_link
        for slink, ds in (
            db.query(BreedingDatasetSubjectLink, Dataset)
            .join(Dataset, Dataset.id == BreedingDatasetSubjectLink.dataset_id)
            .filter(BreedingDatasetSubjectLink.material_id == material_id)
            .all()
        ):
            add(ds, slink.role or "subject", "dataset_subject_link")

        # dataset_assay_link (via biosample → assay)
        biosample_subq = (
            db.query(BreedingBioSample.id)
            .filter(BreedingBioSample.material_id == material_id)
            .subquery()
        )
        assay_subq = (
            db.query(BreedingAssay.id)
            .filter(BreedingAssay.biosample_id.in_(biosample_subq))
            .subquery()
        )
        for alink, ds in (
            db.query(BreedingDatasetAssayLink, Dataset)
            .join(Dataset, Dataset.id == BreedingDatasetAssayLink.dataset_id)
            .filter(BreedingDatasetAssayLink.assay_id.in_(assay_subq))
            .all()
        ):
            add(ds, alink.role or "expression", "dataset_assay_link")

        return list(results.values())

    def get_datasets_for_program(self, db: Session, program_id: int, dataset_type: str = None) -> list[dict]:
        from apps.breeding.models import (
            BreedingVariantSampleMap,
            BreedingPhenotypeSubjectMap,
            BreedingDatasetSubjectLink,
            BreedingDatasetAssayLink,
            BreedingBioSample,
            BreedingAssay,
            BreedingMaterial,
        )
        from apps.datasets.dataset_model import Dataset

        results: dict[int, dict] = {}
        material_ids_subq = (
            db.query(BreedingMaterial.id)
            .filter(BreedingMaterial.program_id == program_id)
            .subquery()
        )

        def add(ds, role, link_type):
            if ds.id not in results:
                results[ds.id] = {
                    "dataset_id": ds.id,
                    "dataset_code": ds.dataset_code,
                    "dataset_type": ds.dataset_type,
                    "organism": ds.organism,
                    "assembly": ds.assembly,
                    "links": [],
                }
            results[ds.id]["links"].append({"role": role, "link_type": link_type})

        # variant_sample_map
        for vmap, ds in (
            db.query(BreedingVariantSampleMap, Dataset)
            .join(Dataset, Dataset.id == BreedingVariantSampleMap.dataset_id)
            .filter(BreedingVariantSampleMap.material_id.in_(material_ids_subq))
            .all()
        ):
            add(ds, "variant", "variant_sample_map")

        # phenotype_subject_map
        for pmap, ds in (
            db.query(BreedingPhenotypeSubjectMap, Dataset)
            .join(Dataset, Dataset.id == BreedingPhenotypeSubjectMap.dataset_id)
            .filter(BreedingPhenotypeSubjectMap.material_id.in_(material_ids_subq))
            .all()
        ):
            add(ds, "phenotype", "phenotype_subject_map")

        # dataset_subject_link via program_id
        for slink, ds in (
            db.query(BreedingDatasetSubjectLink, Dataset)
            .join(Dataset, Dataset.id == BreedingDatasetSubjectLink.dataset_id)
            .filter(BreedingDatasetSubjectLink.program_id == program_id)
            .all()
        ):
            add(ds, slink.role or "subject", "dataset_subject_link")

        # dataset_assay_link via biosample → material
        biosample_subq = (
            db.query(BreedingBioSample.id)
            .filter(BreedingBioSample.material_id.in_(material_ids_subq))
            .subquery()
        )
        assay_subq = (
            db.query(BreedingAssay.id)
            .filter(BreedingAssay.biosample_id.in_(biosample_subq))
            .subquery()
        )
        for alink, ds in (
            db.query(BreedingDatasetAssayLink, Dataset)
            .join(Dataset, Dataset.id == BreedingDatasetAssayLink.dataset_id)
            .filter(BreedingDatasetAssayLink.assay_id.in_(assay_subq))
            .all()
        ):
            add(ds, alink.role or "expression", "dataset_assay_link")

        # Filter by dataset_type if requested
        result_list = list(results.values())
        if dataset_type:
            result_list = [r for r in result_list if r["dataset_type"] == dataset_type]

        return result_list
```

- [ ] **Step 4: Add API endpoints**

```python
# In apps/breeding/api/core.py, add:

@breeding_router.post("/material/datasets")
async def breeding_material_datasets(
    request_data: BreedingInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    from apps.datasets.cross_domain import CrossDomainDatasetLookup

    lookup = CrossDomainDatasetLookup()
    datasets = lookup.get_datasets_for_material(db=db, material_id=request_data.id)
    return response_2000(data={"material_id": request_data.id, "datasets": datasets, "total": len(datasets)})


@breeding_router.post("/program/datasets")
async def breeding_program_datasets(
    request_data: ProgramDatasetsRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    from apps.datasets.cross_domain import CrossDomainDatasetLookup

    lookup = CrossDomainDatasetLookup()
    datasets = lookup.get_datasets_for_program(
        db=db, program_id=request_data.program_id,
        dataset_type=request_data.dataset_type,
    )
    return response_2000(data={"program_id": request_data.program_id, "datasets": datasets, "total": len(datasets)})
```

Add the request schema:
```python
# In apps/breeding/schemas.py:

class ProgramDatasetsRequest(BaseModel):
    program_id: int
    dataset_type: Optional[str] = None
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_cross_domain_dataset_lookup.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/api-server/apps/datasets/cross_domain.py \
        backend/api-server/apps/breeding/api/core.py \
        backend/api-server/apps/breeding/schemas.py \
        backend/api-server/tests/test_cross_domain_dataset_lookup.py
git commit -m "$(cat <<'EOF'
feat: add cross-domain material/program → dataset reverse lookup

CrossDomainDatasetLookup queries all 4 breeding link tables to find
datasets associated with a material or program. Returns dataset summary
with link provenance. Endpoints: POST /breeding/material/datasets and
POST /breeding/program/datasets.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: F-11 — 跨 Domain 权限规则

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py` (add permission check helper)
- Modify: `backend/api-server/apps/breeding/api/core.py` (add guard on dataset-linking endpoints)
- Test: `backend/api-server/tests/test_dataset_permissions.py` (append)

**Context:** 当 breeding program 成员通过 link table 访问 dataset 时，需要遵循最小权限原则：默认使用 dataset 自身的 visibility 设置，link table 不传递权限。本任务添加一个可调用的权限检查函数供 breeding endpoint 使用。

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_dataset_permissions.py

class TestCrossDomainPermission:
    """F-11: Cross-domain permission checks respect dataset visibility."""

    def test_public_dataset_accessible_to_any_program_member(self, db_session):
        from apps.datasets.cross_domain import CrossDomainDatasetLookup

        # A public dataset linked to a program should appear in lookup results
        # regardless of team/project membership.
        lookup = CrossDomainDatasetLookup()

        # This is tested implicitly: get_datasets_for_material does NOT filter
        # by visibility. The visibility check is done by the caller endpoint.
        # Here we verify the permission check helper works correctly.
        from apps.datasets.services import DatasetDomainService

        service = DatasetDomainService()

        # Private dataset: user must be in the same team.
        assert service.can_access_dataset(
            db=db_session,
            dataset_visibility="private",
            dataset_team_id=1,
            user_team_ids=[1],
        ) is True

        assert service.can_access_dataset(
            db=db_session,
            dataset_visibility="private",
            dataset_team_id=1,
            user_team_ids=[2, 3],
        ) is False

        # Project dataset: user must be in the same project.
        assert service.can_access_dataset(
            db=db_session,
            dataset_visibility="project",
            dataset_team_id=1,
            dataset_project_id=10,
            user_team_ids=[1],
            user_project_ids=[10],
        ) is True

        # Public dataset: anyone can access.
        assert service.can_access_dataset(
            db=db_session,
            dataset_visibility="public",
            dataset_team_id=99,
            user_team_ids=[1],
        ) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dataset_permissions.py::TestCrossDomainPermission -v`
Expected: AttributeError — `can_access_dataset` does not exist

- [ ] **Step 3: Add `can_access_dataset` helper**

```python
# In apps/datasets/services.py, add static method to DatasetDomainService:

@staticmethod
def can_access_dataset(*, db, dataset_visibility, dataset_team_id, dataset_project_id=None, user_team_ids=None, user_project_ids=None):
    """Check if a user can access a dataset based on its visibility.

    Visibility semantics:
    - public: anyone
    - project: members of the same team AND project
    - private: members of the same team only

    For cross-domain (breeding) access, this check is applied IN ADDITION to
    the breeding program membership check. The dataset visibility is NOT relaxed
    just because a link table record exists.
    """
    if dataset_visibility == "public":
        return True
    if dataset_visibility == "private":
        return dataset_team_id in (user_team_ids or [])
    if dataset_visibility == "project":
        in_team = dataset_team_id in (user_team_ids or [])
        in_project = dataset_project_id in (user_project_ids or [])
        return in_team and in_project
    return False
```

- [ ] **Step 4: Integrate permission check into link-dataset endpoint**

```python
# In apps/breeding/api/core.py, modify breeding_program_link_dataset:

# Add before creating link:
from apps.datasets.services import DatasetDomainService
from apps.datasets.dataset_model import Dataset

dataset = db.query(Dataset).filter_by(id=request_data.dataset_id).first()
if not dataset:
    return response_4004(message="Dataset not found")

# Check cross-domain permission
user_team_ids = getattr(_user, "team_ids", [])
user_project_ids = getattr(_user, "project_ids", [])
can_access = DatasetDomainService.can_access_dataset(
    db=db,
    dataset_visibility=dataset.visibility,
    dataset_team_id=dataset.team_id or 0,
    dataset_project_id=dataset.project_id,
    user_team_ids=user_team_ids,
    user_project_ids=user_project_ids,
)
if not can_access:
    return response_4003(message="Access denied: dataset is not accessible to your team/project scope")
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_dataset_permissions.py::TestCrossDomainPermission -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/api-server/apps/datasets/services.py \
        backend/api-server/apps/breeding/api/core.py \
        backend/api-server/tests/test_dataset_permissions.py
git commit -m "$(cat <<'EOF'
feat: add cross-domain dataset permission check with visibility guard

can_access_dataset() enforces visibility-based access (public/project/
private). Applied at link-dataset endpoint to prevent linking datasets
outside the user's team/project scope.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Phase 1 Completion Checklist

After all 7 tasks are committed:

- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Run Alembic check: `alembic check` (verify no drift between models and migrations)
- [ ] Manual smoke test: Start server, POST to `/api/v1/breeding/material/overview`, `/api/v1/breeding/trial/overview`, `/api/v1/breeding/program/link-dataset`, `/api/v1/breeding/material/datasets`
- [ ] Verify `AssetTypeRegistry` lookup: Create a dataset with non-standard asset type mapping, verify it uses registry entry
- [ ] Verify `dataset` table: `SELECT count(*) FROM dataset;` returns > 0 after migration
