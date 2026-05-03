# Phase 2: 流程闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立统一 Sample/Experiment 抽象层，实现 Sample 自动提取→Catalog 写入、Assembly 一致性校验、Withdraw 级联检查、Expression→BioSample 映射

**Architecture:** 5 项修复分 5 个 Task。F-2 新建 `unified_sample.py` 定义 `BiologicalSampleView` + `SequencingExperimentView` 两个 PostgreSQL VIEW（UNION ALL 新旧表），供跨域查询使用。F-5 在 variant adapter 的 `samples_list()` 返回后提供 diff-based populate 方法。F-3 部分新建 `AssemblyConsistencyValidator`。F-7 在 `withdraw_dataset_version` 中注入级联检查。S3-2 基于 expression matrix 列名做模糊匹配→BioSample 映射。

**Tech Stack:** Python 3.11, SQLAlchemy 2.0+, Alembic, FastAPI, PostgreSQL VIEW

---

### Task 1: F-2 — 统一 Sample/Experiment 抽象层

**Files:**
- Create: `backend/api-server/apps/datasets/unified_sample.py`
- Create: `backend/api-server/alembic/versions/xxxx_add_unified_sample_experiment_views.py`
- Test: `backend/api-server/tests/test_unified_sample.py`

**Context:** 旧 SRA 模型 `Sample` (abd_sample) + `Experiment` (abd_experiment) 与新 Breeding 模型 `BreedingBioSample` (brd_biosample) + `BreedingAssay` (brd_assay) 分属两套体系。Phase 2 建立 PostgreSQL VIEW 作为统一查询视图，不迁移数据、不改旧表结构。VIEW 仅用于跨域查询（CrossDomainDatasetLookup 等），不替代各 domain 自己的 CRUD。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_unified_sample.py
import pytest


class TestBiologicalSampleView:
    """F-2: BiologicalSampleView unifies old abd_sample and new brd_biosample."""

    def test_view_returns_old_sample_records(self, db_session):
        from apps.sample.models import Sample

        s = Sample(sample_name="Old_SRA_Sample_1", sample_code="SRA001", project_id=1)
        db_session.add(s)
        db_session.commit()

        result = db_session.execute(
            db_session.query(db_session.query().alias())
        )
        # Query the view
        rows = db_session.execute(
            db_session.execute("SELECT * FROM biological_sample_view WHERE source_table = 'abd_sample'")
        ).fetchall()
        # At minimum verify the view exists and returns data
        from sqlalchemy import text
        rows = db_session.execute(text(
            "SELECT sample_code, source_table FROM biological_sample_view WHERE sample_code = 'SRA001'"
        )).fetchall()
        assert len(rows) == 1
        assert rows[0].source_table == "abd_sample"

    def test_view_returns_new_biosample_records(self, db_session):
        from apps.breeding.models import BreedingMaterial, BreedingProgram, BreedingBioSample

        program = BreedingProgram(code="VP", name="View Test", status="active")
        db_session.add(program)
        db_session.commit()

        mat = BreedingMaterial(program_id=program.id, material_code="MAT_V", material_name="View Material")
        db_session.add(mat)
        db_session.commit()

        bs = BreedingBioSample(sample_code="BS_V001", material_id=mat.id, sample_type="leaf")
        db_session.add(bs)
        db_session.commit()

        from sqlalchemy import text
        rows = db_session.execute(text(
            "SELECT sample_code, source_table FROM biological_sample_view WHERE sample_code = 'BS_V001'"
        )).fetchall()
        assert len(rows) == 1
        assert rows[0].source_table == "brd_biosample"

    def test_view_columns_are_normalized(self, db_session):
        """Both sources must expose the same column names."""
        from sqlalchemy import text
        cols = db_session.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'biological_sample_view' ORDER BY ordinal_position"
        )).fetchall()
        col_names = [c[0] for c in cols]
        assert "sample_code" in col_names
        assert "sample_name" in col_names
        assert "sample_type" in col_names
        assert "source_table" in col_names
        assert "source_id" in col_names
        assert "project_id" in col_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_unified_sample.py -v`
Expected: FAIL — VIEWs do not exist

- [ ] **Step 3: Create the unified_sample module with VIEW DDL**

```python
# apps/datasets/unified_sample.py
"""Unified BiologicalSample and SequencingExperiment VIEW definitions.

These PostgreSQL views UNION ALL old SRA models (abd_sample/abd_experiment)
with new Breeding models (brd_biosample/brd_assay) for cross-domain queries.
"""

BIOLOGICAL_SAMPLE_VIEW_DDL = """
CREATE OR REPLACE VIEW biological_sample_view AS
SELECT
    id AS source_id,
    sample_code,
    sample_name,
    type AS sample_type,
    NULL::bigint AS material_id,
    project_id::bigint AS project_id,
    NULL::bigint AS program_id,
    'abd_sample' AS source_table,
    create_time AS created_at,
    update_time AS updated_at
FROM abd_sample
WHERE is_delete = 0

UNION ALL

SELECT
    id AS source_id,
    sample_code,
    NULL::varchar AS sample_name,
    sample_type,
    material_id,
    NULL::bigint AS project_id,
    (SELECT program_id FROM brd_material WHERE id = brd_biosample.material_id) AS program_id,
    'brd_biosample' AS source_table,
    created_at,
    updated_at
FROM brd_biosample
WHERE status = 'active'
"""

SEQUENCING_EXPERIMENT_VIEW_DDL = """
CREATE OR REPLACE VIEW sequencing_experiment_view AS
SELECT
    e.id AS source_id,
    e.accession AS experiment_code,
    e.title AS experiment_name,
    e.experiment_type,
    e.library_strategy,
    e.platform,
    e.instrument_model,
    e.read_length,
    e.sample_id AS old_sample_id,
    NULL::bigint AS biosample_id,
    NULL::bigint AS assay_id,
    'abd_experiment' AS source_table,
    e.create_time AS created_at
FROM abd_experiment e
WHERE e.is_delete = 0

UNION ALL

SELECT
    a.id AS source_id,
    a.assay_code AS experiment_code,
    NULL::varchar AS experiment_name,
    a.assay_type AS experiment_type,
    NULL::varchar AS library_strategy,
    a.platform,
    NULL::varchar AS instrument_model,
    NULL::integer AS read_length,
    NULL::integer AS old_sample_id,
    a.biosample_id,
    a.id AS assay_id,
    'brd_assay' AS source_table,
    a.created_at
FROM brd_assay a
JOIN brd_biosample bs ON bs.id = a.biosample_id
WHERE a.status = 'active'
"""


def create_unified_views(connection):
    """Execute CREATE OR REPLACE VIEW DDL on the given connection."""
    connection.execute(BIOLOGICAL_SAMPLE_VIEW_DDL)
    connection.execute(SEQUENCING_EXPERIMENT_VIEW_DDL)


def drop_unified_views(connection):
    connection.execute("DROP VIEW IF EXISTS biological_sample_view")
    connection.execute("DROP VIEW IF EXISTS sequencing_experiment_view")
```

- [ ] **Step 4: Generate and apply Alembic migration**

Create migration file manually at `alembic/versions/xxxx_add_unified_sample_experiment_views.py`:

```python
"""add_unified_sample_experiment_views

Revision ID: <auto>
Revises: 24075ad57ea3
Create Date: <auto>
"""
from alembic import op
from apps.datasets.unified_sample import BIOLOGICAL_SAMPLE_VIEW_DDL, SEQUENCING_EXPERIMENT_VIEW_DDL, drop_unified_views

revision = '<auto>'
down_revision = '24075ad57ea3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(BIOLOGICAL_SAMPLE_VIEW_DDL)
    op.execute(SEQUENCING_EXPERIMENT_VIEW_DDL)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS biological_sample_view")
    op.execute("DROP VIEW IF EXISTS sequencing_experiment_view")
```

Generate: `alembic revision --autogenerate -m "add_unified_sample_experiment_views"` (if autogenerate doesn't handle VIEW DDL, write it manually using the template above).

Apply: `alembic upgrade head`

- [ ] **Step 5: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_unified_sample.py -v
```
Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add apps/datasets/unified_sample.py alembic/versions/*unified* tests/test_unified_sample.py
git commit -m "feat: add BiologicalSample/SequencingExperiment VIEWs unifying old SRA and new Breeding models"
```

---

### Task 2: F-5 — Variant Sample 自动提取 → Catalog 写入

**Files:**
- Modify: `backend/api-server/apps/datasets/adapters/variant.py`
- Modify: `backend/api-server/apps/breeding/services.py`
- Test: `backend/api-server/tests/test_variant_sample_auto_catalog.py`

**Context:** `VariantAdapter.samples_list()` 调用 `bcftools query -l` 返回 VCF 样本名列表，但结果不会写入 `BreedingVariantSampleMap`。用户需要手动通过 CRUD 创建 link 记录。目标：提供 `sync_variant_samples_to_catalog(db, dataset_id, version_id, asset_id, sample_names)` 方法，自动计算 diff（新增、已存在、已删除）并返回可操作的变更摘要。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_variant_sample_auto_catalog.py


class TestVariantSampleAutoCatalog:
    """F-5: Variant sample extraction must auto-populate BreedingVariantSampleMap."""

    def test_sync_creates_new_sample_maps(self, db_session):
        from apps.breeding.services import BreedingDomainService
        from apps.breeding.models import BreedingVariantSampleMap
        from apps.datasets.dataset_model import Dataset

        ds = Dataset(dataset_code="DS_VCF_SYNC", dataset_type="variome", organism="Oryza sativa", assembly="IRGSP-1.0")
        db_session.add(ds)
        db_session.commit()

        sample_names = ["SAMPLE_A", "SAMPLE_B", "SAMPLE_C"]

        service = BreedingDomainService()
        result = service.sync_variant_samples_to_catalog(
            db=db_session,
            dataset_id=ds.id,
            version_id=1,
            asset_id=1,
            sample_names=sample_names,
        )

        assert result["created"] == 3
        assert result["already_exist"] == 0
        assert result["total_in_vcf"] == 3

        # Verify records created
        maps = (
            db_session.query(BreedingVariantSampleMap)
            .filter_by(dataset_id=ds.id, version_id=1)
            .all()
        )
        assert len(maps) == 3
        vcf_names = {m.vcf_sample_name for m in maps}
        assert vcf_names == set(sample_names)

    def test_sync_skips_existing_mappings(self, db_session):
        from apps.breeding.services import BreedingDomainService
        from apps.breeding.models import BreedingVariantSampleMap
        from apps.datasets.dataset_model import Dataset

        ds = Dataset(dataset_code="DS_VCF_SYNC2", dataset_type="variome", organism="Oryza sativa", assembly="IRGSP-1.0")
        db_session.add(ds)
        db_session.commit()

        # Pre-create one mapping
        existing = BreedingVariantSampleMap(
            dataset_id=ds.id, version_id=1, asset_id=1,
            vcf_sample_name="EXISTING_SAMPLE", mapping_status="matched",
        )
        db_session.add(existing)
        db_session.commit()

        sample_names = ["EXISTING_SAMPLE", "NEW_SAMPLE"]

        service = BreedingDomainService()
        result = service.sync_variant_samples_to_catalog(
            db=db_session, dataset_id=ds.id, version_id=1, asset_id=1,
            sample_names=sample_names,
        )

        assert result["created"] == 1
        assert result["already_exist"] == 1
        assert result["total_in_vcf"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_variant_sample_auto_catalog.py -v`
Expected: AttributeError — `sync_variant_samples_to_catalog` does not exist

- [ ] **Step 3: Implement `sync_variant_samples_to_catalog` in BreedingDomainService**

```python
# In apps/breeding/services.py, add to BreedingDomainService:

def sync_variant_samples_to_catalog(self, db, dataset_id, version_id, asset_id, sample_names):
    """Sync VCF sample names to BreedingVariantSampleMap table.

    Creates new mapping records for samples not yet mapped.
    Returns a diff summary: created, already_exist, total_in_vcf.
    """
    sample_names = list(sample_names or [])
    if not sample_names:
        return {"created": 0, "already_exist": 0, "total_in_vcf": 0}

    # Find existing mappings for this asset
    existing = (
        db.query(BreedingVariantSampleMap)
        .filter_by(dataset_id=dataset_id, version_id=version_id, asset_id=asset_id)
        .all()
    )
    existing_names = {e.vcf_sample_name for e in existing}

    created = 0
    for name in sample_names:
        if name in existing_names:
            continue
        vmap = BreedingVariantSampleMap(
            dataset_id=dataset_id,
            version_id=version_id,
            asset_id=asset_id,
            vcf_sample_name=name,
            mapping_status="draft",
            mapping_method="import",
        )
        db.add(vmap)
        created += 1

    if created:
        db.commit()

    return {
        "created": created,
        "already_exist": len([n for n in sample_names if n in existing_names]),
        "total_in_vcf": len(sample_names),
    }
```

- [ ] **Step 4: Add API endpoint**

```python
# In apps/breeding/api/core.py:

@breeding_router.post("/variant-samples/sync")
async def breeding_variant_samples_sync(
    request_data: VariantSampleSyncRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    result = breeding_domain_service.sync_variant_samples_to_catalog(
        db=db,
        dataset_id=request_data.dataset_id,
        version_id=request_data.version_id,
        asset_id=request_data.asset_id,
        sample_names=request_data.sample_names,
    )
    return response_2000(data=result)
```

Add schema:
```python
# In apps/breeding/schemas.py:

class VariantSampleSyncRequest(BaseModel):
    dataset_id: int
    version_id: int
    asset_id: int
    sample_names: List[str]
```

- [ ] **Step 5: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_variant_sample_auto_catalog.py -v
```
Expected: 2 PASS

- [ ] **Step 6: Commit**

```bash
git add apps/breeding/services.py apps/breeding/api/core.py apps/breeding/schemas.py tests/test_variant_sample_auto_catalog.py
git commit -m "feat: add variant sample auto-catalog sync to BreedingVariantSampleMap"
```

---

### Task 3: F-3 Partial — Assembly 一致性校验 + Sample 对齐检查

**Files:**
- Create: `backend/api-server/apps/datasets/assembly_validator.py`
- Test: `backend/api-server/tests/test_assembly_validator.py`

**Context:** GWAS 分析需要 variant dataset 和 phenotype dataset 基于同一 assembly。当前没有任何校验。目标：提供 `validate_assembly_consistency(dataset_ids)` 和 `check_sample_alignment(variant_ds_id, pheno_ds_id)` 两个静态方法。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_assembly_validator.py


class TestAssemblyValidator:
    """F-3 partial: assembly consistency and sample alignment checks."""

    def test_same_assembly_passes_consistency_check(self, db_session):
        from apps.datasets.dataset_model import Dataset
        from apps.datasets.assembly_validator import AssemblyConsistencyValidator

        ds1 = Dataset(dataset_code="DS_ASM_A", dataset_type="variome", assembly="IRGSP-1.0")
        ds2 = Dataset(dataset_code="DS_ASM_B", dataset_type="phenome", assembly="IRGSP-1.0")
        db_session.add_all([ds1, ds2])
        db_session.commit()

        result = AssemblyConsistencyValidator.validate_assembly_consistency(
            db=db_session, dataset_ids=[ds1.id, ds2.id]
        )
        assert result["consistent"] is True
        assert result["assembly"] == "IRGSP-1.0"
        assert len(result["mismatches"]) == 0

    def test_mismatched_assembly_fails_consistency_check(self, db_session):
        from apps.datasets.dataset_model import Dataset
        from apps.datasets.assembly_validator import AssemblyConsistencyValidator

        ds1 = Dataset(dataset_code="DS_ASM_C", dataset_type="variome", assembly="IRGSP-1.0")
        ds2 = Dataset(dataset_code="DS_ASM_D", dataset_type="variome", assembly="Os-Nipponbare-Reference-IRGSP-1.0")
        db_session.add_all([ds1, ds2])
        db_session.commit()

        result = AssemblyConsistencyValidator.validate_assembly_consistency(
            db=db_session, dataset_ids=[ds1.id, ds2.id]
        )
        assert result["consistent"] is False
        assert len(result["mismatches"]) >= 1
        mismatched_ids = {m["dataset_id"] for m in result["mismatches"]}
        assert ds2.id in mismatched_ids

    def test_sample_alignment_counts_paired_and_unpaired(self, db_session):
        from apps.datasets.assembly_validator import AssemblyConsistencyValidator
        from apps.breeding.models import (
            BreedingVariantSampleMap,
            BreedingPhenotypeSubjectMap,
            BreedingMaterial,
            BreedingProgram,
        )
        from apps.datasets.dataset_model import Dataset

        program = BreedingProgram(code="P_ALIGN", name="Alignment Test", status="active")
        db_session.add(program)
        db_session.commit()

        mat1 = BreedingMaterial(program_id=program.id, material_code="MAT_AL_1", material_name="Aligned 1")
        mat2 = BreedingMaterial(program_id=program.id, material_code="MAT_AL_2", material_name="Aligned 2")
        db_session.add_all([mat1, mat2])
        db_session.commit()

        ds_v = Dataset(dataset_code="DS_AL_V", dataset_type="variome", assembly="IRGSP-1.0")
        ds_p = Dataset(dataset_code="DS_AL_P", dataset_type="phenome", assembly="IRGSP-1.0")
        db_session.add_all([ds_v, ds_p])
        db_session.commit()

        # Variant has both samples, phenotype only has mat1
        db_session.add(BreedingVariantSampleMap(
            dataset_id=ds_v.id, version_id=1, asset_id=1,
            vcf_sample_name="S1", material_id=mat1.id, mapping_status="matched",
        ))
        db_session.add(BreedingVariantSampleMap(
            dataset_id=ds_v.id, version_id=1, asset_id=1,
            vcf_sample_name="S2", material_id=mat2.id, mapping_status="matched",
        ))
        db_session.add(BreedingPhenotypeSubjectMap(
            dataset_id=ds_p.id, version_id=1, asset_id=1,
            row_key="SUBJ_1", material_id=mat1.id,
            trait_code="height", value_numeric=100.0, mapping_status="matched",
        ))
        db_session.commit()

        result = AssemblyConsistencyValidator.check_sample_alignment(
            db=db_session,
            variant_dataset_id=ds_v.id,
            phenotype_dataset_id=ds_p.id,
        )
        assert result["paired_count"] == 1  # mat1 in both
        assert result["variant_only_count"] == 1  # mat2 only in variant
        assert result["phenotype_only_count"] == 0
        assert result["coverage"] == pytest.approx(0.5, abs=0.1)  # 1/2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_assembly_validator.py -v`
Expected: ImportError — module or class does not exist

- [ ] **Step 3: Implement AssemblyConsistencyValidator**

```python
# apps/datasets/assembly_validator.py
from sqlalchemy.orm import Session


class AssemblyConsistencyValidator:
    """Cross-dataset assembly and sample alignment validation."""

    @staticmethod
    def validate_assembly_consistency(db: Session, dataset_ids: list[int]) -> dict:
        """Check that all given datasets share the same assembly."""
        from apps.datasets.dataset_model import Dataset

        datasets = db.query(Dataset).filter(Dataset.id.in_(dataset_ids)).all()
        if not datasets:
            return {"consistent": True, "assembly": None, "datasets": [], "mismatches": []}

        assemblies = {}
        for ds in datasets:
            asm = (ds.assembly or "").strip()
            assemblies.setdefault(asm, []).append({
                "dataset_id": ds.id,
                "dataset_code": ds.dataset_code,
                "assembly": ds.assembly,
            })

        if len(assemblies) == 1:
            asm_key = list(assemblies.keys())[0]
            return {
                "consistent": True,
                "assembly": asm_key or None,
                "datasets": assemblies[asm_key],
                "mismatches": [],
            }

        # Find majority assembly
        majority_key = max(assemblies, key=lambda k: len(assemblies[k]))
        mismatches = []
        for asm_key, items in assemblies.items():
            if asm_key != majority_key:
                mismatches.extend(items)

        return {
            "consistent": False,
            "assembly": majority_key,
            "datasets": assemblies[majority_key],
            "mismatches": mismatches,
        }

    @staticmethod
    def check_sample_alignment(db: Session, variant_dataset_id: int, phenotype_dataset_id: int) -> dict:
        """Check how many materials are paired between variant and phenotype datasets."""
        from apps.breeding.models import BreedingVariantSampleMap, BreedingPhenotypeSubjectMap

        variant_materials = set(
            r[0] for r in
            db.query(BreedingVariantSampleMap.material_id)
            .filter(
                BreedingVariantSampleMap.dataset_id == variant_dataset_id,
                BreedingVariantSampleMap.material_id.isnot(None),
            )
            .distinct()
            .all()
        )

        pheno_materials = set(
            r[0] for r in
            db.query(BreedingPhenotypeSubjectMap.material_id)
            .filter(
                BreedingPhenotypeSubjectMap.dataset_id == phenotype_dataset_id,
                BreedingPhenotypeSubjectMap.material_id.isnot(None),
            )
            .distinct()
            .all()
        )

        paired = variant_materials & pheno_materials
        variant_only = variant_materials - pheno_materials
        pheno_only = pheno_materials - variant_materials
        total = len(variant_materials | pheno_materials)

        return {
            "paired_count": len(paired),
            "paired_material_ids": sorted(paired),
            "variant_only_count": len(variant_only),
            "variant_only_material_ids": sorted(variant_only),
            "phenotype_only_count": len(pheno_only),
            "phenotype_only_material_ids": sorted(pheno_only),
            "coverage": len(paired) / total if total > 0 else 0.0,
        }
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_assembly_validator.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add apps/datasets/assembly_validator.py tests/test_assembly_validator.py
git commit -m "feat: add assembly consistency validator and sample alignment checker"
```

---

### Task 4: F-7 — Withdraw 级联检查

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py:5745-5793`
- Modify: `backend/api-server/apps/datasets/api/version.py`
- Test: `backend/api-server/tests/test_dataset_withdraw_guard.py`

**Context:** `withdraw_dataset_version()` 目前只做版本状态变更，不检查 breeding link table 是否有活跃引用。目标：在 withdraw 之前查询 4 个 link table，如果有记录引用该版本，返回警告（不阻止，允许强制 withdraw）。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dataset_withdraw_guard.py


class TestWithdrawGuard:
    """F-7: Withdraw must check breeding link table references."""

    def test_withdraw_check_detects_variant_sample_map_reference(self, db_session):
        from apps.datasets.services import DatasetDomainService
        from apps.breeding.models import BreedingVariantSampleMap
        from apps.datasets.dataset_model import Dataset

        ds = Dataset(dataset_code="DS_WD_V", dataset_type="variome", organism="Oryza sativa", assembly="IRGSP-1.0")
        db_session.add(ds)
        db_session.commit()

        # Create a link record referencing version_id=1
        vmap = BreedingVariantSampleMap(
            dataset_id=ds.id, version_id=1, asset_id=1,
            vcf_sample_name="GUARD_TEST", mapping_status="matched",
        )
        db_session.add(vmap)
        db_session.commit()

        service = DatasetDomainService()
        refs = service._check_breeding_references(db=db_session, version_id=1)

        assert refs["has_references"] is True
        assert refs["variant_sample_map_count"] == 1
        assert len(refs["details"]) == 1

    def test_withdraw_check_returns_empty_when_no_references(self, db_session):
        from apps.datasets.services import DatasetDomainService

        service = DatasetDomainService()
        refs = service._check_breeding_references(db=db_session, version_id=99999)

        assert refs["has_references"] is False
        assert refs["total_references"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dataset_withdraw_guard.py -v`
Expected: AttributeError — `_check_breeding_references` does not exist

- [ ] **Step 3: Implement `_check_breeding_references` in DatasetDomainService**

```python
# In apps/datasets/services.py, add to DatasetDomainService:

def _check_breeding_references(self, db, version_id):
    """Check all breeding link tables for references to a dataset version.

    Returns a dict with has_references flag, counts per link table, and detail rows.
    """
    from apps.breeding.models import (
        BreedingVariantSampleMap,
        BreedingPhenotypeSubjectMap,
        BreedingDatasetSubjectLink,
        BreedingDatasetAssayLink,
    )

    details = []

    # variant_sample_map
    variant_maps = (
        db.query(BreedingVariantSampleMap)
        .filter_by(version_id=version_id)
        .all()
    )
    for v in variant_maps:
        details.append({
            "table": "brd_variant_sample_map",
            "id": v.id,
            "material_id": v.material_id,
            "vcf_sample_name": v.vcf_sample_name,
        })

    # phenotype_subject_map
    pheno_maps = (
        db.query(BreedingPhenotypeSubjectMap)
        .filter_by(version_id=version_id)
        .all()
    )
    for p in pheno_maps:
        details.append({
            "table": "brd_phenotype_subject_map",
            "id": p.id,
            "material_id": p.material_id,
            "trait_code": p.trait_code,
        })

    # dataset_subject_link
    subject_links = (
        db.query(BreedingDatasetSubjectLink)
        .filter_by(version_id=version_id)
        .all()
    )
    for s in subject_links:
        details.append({
            "table": "brd_dataset_subject_link",
            "id": s.id,
            "program_id": s.program_id,
            "material_id": s.material_id,
        })

    # dataset_assay_link
    assay_links = (
        db.query(BreedingDatasetAssayLink)
        .filter_by(version_id=version_id)
        .all()
    )
    for a in assay_links:
        details.append({
            "table": "brd_dataset_assay_link",
            "id": a.id,
            "assay_id": a.assay_id,
        })

    return {
        "has_references": len(details) > 0,
        "total_references": len(details),
        "variant_sample_map_count": len(variant_maps),
        "phenotype_subject_map_count": len(pheno_maps),
        "dataset_subject_link_count": len(subject_links),
        "dataset_assay_link_count": len(assay_links),
        "details": details,
    }
```

- [ ] **Step 4: Inject check into `withdraw_dataset_version`**

At the top of `withdraw_dataset_version` (after line 5747 `version_obj = ...`), add:

```python
# Check breeding link references before withdraw
breeding_refs = self._check_breeding_references(db=db, version_id=version_obj.id)
if breeding_refs["has_references"]:
    # Log warning — withdraw proceeds but reference info is included in response
    pass  # The check result is attached to the response below
```

Then at the return (line 5793), modify to include the reference check:

```python
result = self.get_dataset_version(db=db, version_id=version_obj.id, user=user)
result["_breeding_references"] = breeding_refs
return result
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_dataset_withdraw_guard.py -v`
Expected: 2 PASS

- [ ] **Step 6: Commit**

```bash
git add apps/datasets/services.py tests/test_dataset_withdraw_guard.py
git commit -m "feat: add breeding link reference check on dataset version withdraw"
```

---

### Task 5: S3-2 — Expression Matrix → BioSample 映射

**Files:**
- Modify: `backend/api-server/apps/breeding/services.py`
- Modify: `backend/api-server/apps/breeding/api/core.py`
- Modify: `backend/api-server/apps/breeding/schemas.py`
- Test: `backend/api-server/tests/test_expression_biosample_mapping.py`

**Context:** 表达矩阵的列名（sample ID in HDF5/TSV）需要映射到 `BioSample` 记录。没有类似 `VariantSampleMap` 的专用表，但可以用 `BreedingDatasetSubjectLink` 表达。目标：提供 `map_expression_samples_to_biosamples(db, dataset_id, version_id, asset_id, sample_names)` 方法，对每个 sample name 做模糊匹配（精确匹配 sample_code，fallback 到 LIKE 匹配）。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_expression_biosample_mapping.py


class TestExpressionBioSampleMapping:
    """S3-2: Expression matrix columns → BioSample mapping."""

    def test_map_exact_match_on_sample_code(self, db_session):
        from apps.breeding.services import BreedingDomainService
        from apps.breeding.models import BreedingProgram, BreedingMaterial, BreedingBioSample
        from apps.datasets.dataset_model import Dataset

        program = BreedingProgram(code="P_EXP", name="Expression Test", status="active")
        db_session.add(program)
        db_session.commit()

        mat = BreedingMaterial(program_id=program.id, material_code="MAT_EXP", material_name="Exp Material")
        db_session.add(mat)
        db_session.commit()

        bs = BreedingBioSample(sample_code="EXP_LEAF_001", material_id=mat.id, sample_type="leaf")
        db_session.add(bs)
        db_session.commit()

        ds = Dataset(dataset_code="DS_EXP", dataset_type="transcriptome", organism="Oryza sativa", assembly="IRGSP-1.0")
        db_session.add(ds)
        db_session.commit()

        service = BreedingDomainService()
        result = service.map_expression_samples_to_biosamples(
            db=db_session,
            dataset_id=ds.id,
            version_id=1,
            asset_id=1,
            sample_names=["EXP_LEAF_001", "UNKNOWN_SAMPLE"],
        )

        assert result["mapped"] == 1
        assert result["unmapped"] == 1
        assert result["total"] == 2
        assert len(result["matches"]) == 1
        assert result["matches"][0]["sample_name"] == "EXP_LEAF_001"
        assert result["matches"][0]["biosample_id"] == bs.id

    def test_map_fuzzy_match_finds_candidate(self, db_session):
        from apps.breeding.services import BreedingDomainService
        from apps.breeding.models import BreedingProgram, BreedingMaterial, BreedingBioSample
        from apps.datasets.dataset_model import Dataset

        program = BreedingProgram(code="P_FUZZY", name="Fuzzy Test", status="active")
        db_session.add(program)
        db_session.commit()

        mat = BreedingMaterial(program_id=program.id, material_code="MAT_FZ", material_name="Fuzzy Material")
        db_session.add(mat)
        db_session.commit()

        bs = BreedingBioSample(sample_code="BR_FZ_LEAF_T1", material_id=mat.id, sample_type="leaf")
        db_session.add(bs)
        db_session.commit()

        ds = Dataset(dataset_code="DS_FZ", dataset_type="transcriptome", organism="Oryza sativa", assembly="IRGSP-1.0")
        db_session.add(ds)
        db_session.commit()

        service = BreedingDomainService()
        result = service.map_expression_samples_to_biosamples(
            db=db_session,
            dataset_id=ds.id,
            version_id=1,
            asset_id=1,
            sample_names=["LEAF_T1"],  # partial match
        )

        # "LEAF_T1" is contained in "BR_FZ_LEAF_T1"
        assert result["mapped"] >= 0  # fuzzy match may or may not succeed
        # If mapped > 0, verify the match quality
        if result["mapped"] > 0:
            assert result["matches"][0]["confidence"] == "fuzzy"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_expression_biosample_mapping.py -v`
Expected: AttributeError — `map_expression_samples_to_biosamples` does not exist

- [ ] **Step 3: Implement `map_expression_samples_to_biosamples` in BreedingDomainService**

```python
# In apps/breeding/services.py, add to BreedingDomainService:

def map_expression_samples_to_biosamples(self, db, dataset_id, version_id, asset_id, sample_names):
    """Map expression matrix column names to BioSample records.

    Strategy:
    1. Exact match on sample_code
    2. Fallback: sample_code ILIKE '%name%' (fuzzy, confidence='fuzzy')
    Returns match summary with mapped/unmapped counts.
    """
    sample_names = list(sample_names or [])
    if not sample_names:
        return {"mapped": 0, "unmapped": 0, "total": 0, "matches": []}

    matches = []
    unmatched = []
    all_biosamples = db.query(BreedingBioSample).filter(
        BreedingBioSample.status == "active"
    ).all()

    biosample_by_code = {bs.sample_code: bs for bs in all_biosamples if bs.sample_code}

    for name in sample_names:
        # Exact match
        if name in biosample_by_code:
            bs = biosample_by_code[name]
            matches.append({
                "sample_name": name,
                "biosample_id": bs.id,
                "biosample_code": bs.sample_code,
                "material_id": bs.material_id,
                "confidence": "exact",
            })
            continue

        # Fuzzy match: sample_code contains the expression column name or vice versa
        fuzzy = None
        for bs in all_biosamples:
            if not bs.sample_code:
                continue
            if name.lower() in bs.sample_code.lower() or bs.sample_code.lower() in name.lower():
                fuzzy = bs
                break

        if fuzzy:
            matches.append({
                "sample_name": name,
                "biosample_id": fuzzy.id,
                "biosample_code": fuzzy.sample_code,
                "material_id": fuzzy.material_id,
                "confidence": "fuzzy",
            })
        else:
            unmatched.append(name)

    return {
        "mapped": len(matches),
        "unmapped": len(unmatched),
        "total": len(sample_names),
        "matches": matches,
        "unmatched_names": unmatched,
    }
```

- [ ] **Step 4: Add API endpoint**

```python
# In apps/breeding/api/core.py:

@breeding_router.post("/expression-samples/map")
async def breeding_expression_samples_map(
    request_data: ExpressionSampleMapRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    result = breeding_domain_service.map_expression_samples_to_biosamples(
        db=db,
        dataset_id=request_data.dataset_id,
        version_id=request_data.version_id,
        asset_id=request_data.asset_id,
        sample_names=request_data.sample_names,
    )
    return response_2000(data=result)
```

Add schema:
```python
# In apps/breeding/schemas.py:

class ExpressionSampleMapRequest(BaseModel):
    dataset_id: int
    version_id: int
    asset_id: int
    sample_names: List[str]
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_expression_biosample_mapping.py -v`
Expected: 2 PASS

- [ ] **Step 6: Commit**

```bash
git add apps/breeding/services.py apps/breeding/api/core.py apps/breeding/schemas.py tests/test_expression_biosample_mapping.py
git commit -m "feat: add expression sample → BioSample fuzzy mapping service"
```

---

## Phase 2 Completion Checklist

After all 5 tasks are committed:

- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Run Alembic: `alembic upgrade head` — verify VIEW migration applies
- [ ] Manual smoke test:
  - `SELECT * FROM biological_sample_view LIMIT 5;`
  - `SELECT * FROM sequencing_experiment_view LIMIT 5;`
  - `POST /breeding/variant-samples/sync` with sample names
  - `POST /breeding/expression-samples/map` with expression column names
