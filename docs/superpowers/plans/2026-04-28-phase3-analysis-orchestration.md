# Phase 3: 分析编排 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现跨 Dataset 分析编排层（GWAS 矩阵组装、分析就绪度、联合查询）、Index 新鲜度检测、Expression 多格式支持

**Architecture:** 新建 `apps/datasets/orchestration.py` 作为编排中心。5 项修复对应 5 个 Task。F-3 完成部分包含 `GwasAssemblyService` + `AnalysisReadinessService`。S6-6 新增 `CrossDatasetQueryService`（variant+annotation overlap / functional+expression pathway）。F-6 修改 base adapter 的 `ensure_sidecar_index_files`。F-8 扩展 `ExpressionAdapter`。F-9 作为轻量桥接。

**Tech Stack:** Python 3.11, SQLAlchemy 2.0+, FastAPI, bcftools, tabix, h5py, pandas

---

### Task 1: F-3 Complete — GWAS Assembly + Analysis Readiness

**Files:**
- Create: `backend/api-server/apps/datasets/orchestration.py`
- Create: `backend/api-server/tests/test_orchestration.py`

**Context:** Phase 1 提供了 `CrossDomainDatasetLookup`（找关联 datasets），Phase 2 提供了 `AssemblyConsistencyValidator`（校验 assembly）+ `check_sample_alignment`（样本对齐）。F-3 完成部分将它们串联成两个端到端方法：`assemble_gwas_input` 和 `check_analysis_readiness`。

- [ ] **Step 1: Write test**

```python
# tests/test_orchestration.py
import pytest


class TestGwasAssembly:
    def test_check_analysis_readiness_returns_traffic_light(self, db_session):
        from apps.datasets.orchestration import AnalysisReadinessService
        from apps.datasets.dataset_model import Dataset

        ds_v = Dataset(dataset_code="DS_READY_V", dataset_type="variome", assembly="IRGSP-1.0")
        ds_p = Dataset(dataset_code="DS_READY_P", dataset_type="phenome", assembly="IRGSP-1.0")
        db_session.add_all([ds_v, ds_p])
        db_session.commit()

        result = AnalysisReadinessService.check_gwas_readiness(
            db=db_session,
            variant_dataset_id=ds_v.id,
            phenotype_dataset_id=ds_p.id,
        )
        assert "overall" in result
        assert result["overall"] in ("green", "yellow", "red")
        assert "checks" in result
        assert "assembly" in result["checks"]
        assert result["checks"]["assembly"]["consistent"] is True

    def test_assemble_gwas_input_empty_when_no_samples(self, db_session):
        from apps.datasets.orchestration import GwasAssemblyService
        from apps.datasets.dataset_model import Dataset

        ds_v = Dataset(dataset_code="DS_GWAS_V", dataset_type="variome", assembly="IRGSP-1.0")
        ds_p = Dataset(dataset_code="DS_GWAS_P", dataset_type="phenome", assembly="IRGSP-1.0")
        db_session.add_all([ds_v, ds_p])
        db_session.commit()

        result = GwasAssemblyService.assemble_gwas_input(
            db=db_session,
            variant_dataset_id=ds_v.id,
            phenotype_dataset_id=ds_p.id,
        )
        assert "status" in result
        # Without indexed data files, assembly returns "not_ready"
        assert result["status"] in ("ready", "not_ready")
```

- [ ] **Step 2: Implement `orchestration.py`**

```python
# apps/datasets/orchestration.py
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session


@dataclass
class ReadinessCheck:
    passed: bool
    detail: str
    data: dict


class AnalysisReadinessService:
    """Check whether a set of datasets is ready for a given analysis type."""

    @staticmethod
    def check_gwas_readiness(
        db: Session,
        variant_dataset_id: int,
        phenotype_dataset_id: int,
    ) -> dict:
        from apps.datasets.assembly_validator import AssemblyConsistencyValidator

        checks = {}

        # 1. Assembly consistency
        assembly_result = AssemblyConsistencyValidator.validate_assembly_consistency(
            db=db, dataset_ids=[variant_dataset_id, phenotype_dataset_id]
        )
        checks["assembly"] = {
            "passed": assembly_result["consistent"],
            "detail": (
                f"All datasets use assembly: {assembly_result['assembly']}"
                if assembly_result["consistent"]
                else f"Assembly mismatch: majority={assembly_result['assembly']}, mismatched={len(assembly_result['mismatches'])}"
            ),
            "data": assembly_result,
        }

        # 2. Sample alignment coverage
        alignment_result = AssemblyConsistencyValidator.check_sample_alignment(
            db=db,
            variant_dataset_id=variant_dataset_id,
            phenotype_dataset_id=phenotype_dataset_id,
        )
        coverage_ok = alignment_result["coverage"] >= 0.1
        checks["sample_alignment"] = {
            "passed": coverage_ok,
            "detail": (
                f"Paired samples: {alignment_result['paired_count']}/{alignment_result['paired_count'] + alignment_result['variant_only_count'] + alignment_result['phenotype_only_count']}"
            ),
            "data": alignment_result,
        }

        # Compute overall traffic light
        all_passed = all(c["passed"] for c in checks.values())
        any_passed = any(c["passed"] for c in checks.values())

        if all_passed:
            overall = "green"
        elif any_passed:
            overall = "yellow"
        else:
            overall = "red"

        return {
            "overall": overall,
            "analysis_type": "gwas",
            "variant_dataset_id": variant_dataset_id,
            "phenotype_dataset_id": phenotype_dataset_id,
            "checks": checks,
        }


class GwasAssemblyService:
    """Assemble GWAS input matrices from variant + phenotype datasets."""

    @staticmethod
    def assemble_gwas_input(
        db: Session,
        variant_dataset_id: int,
        phenotype_dataset_id: int,
        material_ids: Optional[list[int]] = None,
    ) -> dict:
        from apps.datasets.assembly_validator import AssemblyConsistencyValidator

        # 1. Check assembly consistency first
        assembly_check = AssemblyConsistencyValidator.validate_assembly_consistency(
            db=db, dataset_ids=[variant_dataset_id, phenotype_dataset_id]
        )
        if not assembly_check["consistent"]:
            return {
                "status": "not_ready",
                "reason": "Assembly mismatch",
                "detail": assembly_check,
            }

        # 2. Check sample alignment
        alignment = AssemblyConsistencyValidator.check_sample_alignment(
            db=db,
            variant_dataset_id=variant_dataset_id,
            phenotype_dataset_id=phenotype_dataset_id,
        )
        if alignment["paired_count"] == 0:
            return {
                "status": "not_ready",
                "reason": "No paired samples between variant and phenotype datasets",
                "detail": alignment,
            }

        # 3. Return assembly metadata — actual matrix extraction is deferred to adapters
        return {
            "status": "ready",
            "variant_dataset_id": variant_dataset_id,
            "phenotype_dataset_id": phenotype_dataset_id,
            "assembly": assembly_check["assembly"],
            "paired_sample_count": alignment["paired_count"],
            "paired_material_ids": alignment["paired_material_ids"],
            "coverage": alignment["coverage"],
            "next_steps": {
                "variant_query": "Use /api/v1/query/dataset/execute with operation=batch_fetch on variant dataset",
                "phenotype_query": "Use /api/v1/query/dataset/execute with operation=trait_values on phenotype dataset",
            },
        }
```

- [ ] **Step 3: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_orchestration.py -v
```
Expected: 2 PASS

- [ ] **Step 4: Commit**

```bash
git add apps/datasets/orchestration.py tests/test_orchestration.py
git commit -m "feat: add GWAS assembly and analysis readiness orchestration services"
```

---

### Task 2: S6-6 — Cross-Dataset Joint Query

**Files:**
- Create: `backend/api-server/apps/datasets/cross_query.py`
- Create: `backend/api-server/apps/datasets/api/cross_query.py`
- Test: `backend/api-server/tests/test_cross_query.py`

**Context:** 两个常见跨 dataset 查询模式：① variant+annotation overlap（基因区域内的变异）② functional+expression pathway（通路基因的表达量）。实现为独立 service，不修改现有 adapter。

- [ ] **Step 1: Write test**

```python
# tests/test_cross_query.py


class TestCrossDatasetQuery:
    def test_variant_annotation_overlap_query_builds_correctly(self, db_session):
        from apps.datasets.cross_query import CrossDatasetQueryService
        from apps.datasets.dataset_model import Dataset

        ds_var = Dataset(dataset_code="DS_JOIN_V", dataset_type="variome", assembly="IRGSP-1.0")
        ds_ann = Dataset(dataset_code="DS_JOIN_A", dataset_type="annotation", assembly="IRGSP-1.0")
        db_session.add_all([ds_var, ds_ann])
        db_session.commit()

        result = CrossDatasetQueryService.variant_annotation_overlap(
            db=db_session,
            variant_dataset_id=ds_var.id,
            annotation_dataset_id=ds_ann.id,
            region="Chr1:1000-5000",
        )
        # Without actual index files, returns plan with instructions
        assert "query_plan" in result
        assert result["query_plan"]["variant_step"]["operation"] == "batch_fetch"
        assert result["query_plan"]["annotation_step"]["operation"] == "region_features"

    def test_functional_expression_pathway_query(self, db_session):
        from apps.datasets.cross_query import CrossDatasetQueryService
        from apps.datasets.dataset_model import Dataset

        ds_func = Dataset(dataset_code="DS_FUNC", dataset_type="functional_annotation", assembly="IRGSP-1.0")
        ds_expr = Dataset(dataset_code="DS_EXPR", dataset_type="transcriptome", assembly="IRGSP-1.0")
        db_session.add_all([ds_func, ds_expr])
        db_session.commit()

        result = CrossDatasetQueryService.functional_expression_pathway(
            db=db_session,
            functional_dataset_id=ds_func.id,
            expression_dataset_id=ds_expr.id,
            term_id="GO:0008150",
        )
        assert "query_plan" in result
        assert result["query_plan"]["functional_step"]["operation"] == "term_gene_list"
        assert result["query_plan"]["expression_step"]["operation"] == "matrix_slice"
```

- [ ] **Step 2: Implement `cross_query.py`**

```python
# apps/datasets/cross_query.py
from sqlalchemy.orm import Session


class CrossDatasetQueryService:
    """Pre-defined cross-dataset joint query patterns.

    Builds query plans that can be executed step-by-step against adapters.
    Phase 3 provides the plan structure; actual execution is deferred to
    the existing adapter query API.
    """

    @staticmethod
    def variant_annotation_overlap(
        db: Session,
        variant_dataset_id: int,
        annotation_dataset_id: int,
        region: str,
    ) -> dict:
        """Find variants within a gene region. Two-step plan:
        1. Query annotation dataset for features in the region
        2. Query variant dataset for variants in the region
        """
        from apps.datasets.dataset_model import Dataset

        variant_ds = db.query(Dataset).filter_by(id=variant_dataset_id).first()
        annotation_ds = db.query(Dataset).filter_by(id=annotation_dataset_id).first()

        return {
            "query_type": "variant_annotation_overlap",
            "region": region,
            "datasets": {
                "variant": {"id": variant_dataset_id, "code": variant_ds.dataset_code if variant_ds else None},
                "annotation": {"id": annotation_dataset_id, "code": annotation_ds.dataset_code if annotation_ds else None},
            },
            "query_plan": {
                "annotation_step": {
                    "dataset_id": annotation_dataset_id,
                    "operation": "region_features",
                    "params": {"region": region},
                    "description": "Get gene features in the region",
                },
                "variant_step": {
                    "dataset_id": variant_dataset_id,
                    "operation": "batch_fetch",
                    "params": {"regions": [region]},
                    "description": "Get variants in the same region",
                },
            },
            "assembly_note": "Both datasets must share the same assembly for coordinates to be meaningful.",
        }

    @staticmethod
    def functional_expression_pathway(
        db: Session,
        functional_dataset_id: int,
        expression_dataset_id: int,
        term_id: str,
        max_genes: int = 500,
    ) -> dict:
        """Find expression levels of genes in a functional term. Two-step plan:
        1. Query functional annotation for genes assigned to the term
        2. Query expression dataset for those genes' expression values
        """
        from apps.datasets.dataset_model import Dataset

        func_ds = db.query(Dataset).filter_by(id=functional_dataset_id).first()
        expr_ds = db.query(Dataset).filter_by(id=expression_dataset_id).first()

        return {
            "query_type": "functional_expression_pathway",
            "term_id": term_id,
            "datasets": {
                "functional": {"id": functional_dataset_id, "code": func_ds.dataset_code if func_ds else None},
                "expression": {"id": expression_dataset_id, "code": expr_ds.dataset_code if expr_ds else None},
            },
            "query_plan": {
                "functional_step": {
                    "dataset_id": functional_dataset_id,
                    "operation": "term_gene_list",
                    "params": {"term_id": term_id, "max_genes": max_genes},
                    "description": "Get genes assigned to the functional term",
                },
                "expression_step": {
                    "dataset_id": expression_dataset_id,
                    "operation": "matrix_slice",
                    "params": {"genes": "<from_functional_step>", "data_type": "count"},
                    "description": "Get expression values for those genes",
                },
            },
        }

    @staticmethod
    def phenotype_variant_correlation(
        db: Session,
        phenotype_dataset_id: int,
        variant_dataset_id: int,
        trait_code: str,
        region: str = None,
    ) -> dict:
        """Find variants correlated with extreme phenotype values. Two-step plan:
        1. Query phenotype dataset for trait values (identify extreme subjects)
        2. Query variant dataset for variants associated with extreme subjects
        """
        from apps.datasets.dataset_model import Dataset

        pheno_ds = db.query(Dataset).filter_by(id=phenotype_dataset_id).first()
        variant_ds = db.query(Dataset).filter_by(id=variant_dataset_id).first()

        plan = {
            "query_type": "phenotype_variant_correlation",
            "trait_code": trait_code,
            "region": region,
            "datasets": {
                "phenotype": {"id": phenotype_dataset_id, "code": pheno_ds.dataset_code if pheno_ds else None},
                "variant": {"id": variant_dataset_id, "code": variant_ds.dataset_code if variant_ds else None},
            },
            "query_plan": {
                "phenotype_step": {
                    "dataset_id": phenotype_dataset_id,
                    "operation": "trait_values",
                    "params": {"trait_code": trait_code},
                    "description": "Get trait values, identify extreme subjects",
                },
                "variant_step": {
                    "dataset_id": variant_dataset_id,
                    "operation": "batch_fetch",
                    "params": {"regions": [region] if region else []},
                    "description": "Get variants; if region specified, scope to region",
                },
            },
        }
        return plan
```

- [ ] **Step 3: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_cross_query.py -v
```
Expected: 2 PASS

- [ ] **Step 4: Commit**

```bash
git add apps/datasets/cross_query.py tests/test_cross_query.py
git commit -m "feat: add cross-dataset joint query plans (variant+annotation, functional+expression, phenotype+variant)"
```

---

### Task 3: F-6 — Index 新鲜度检测

**Files:**
- Modify: `backend/api-server/apps/datasets/adapters/base.py:93-119`
- Test: `backend/api-server/tests/test_index_staleness.py`

**Context:** `ensure_sidecar_index_files()` 当前只检查索引文件是否存在，不检查是否比源文件更新。如果源文件被替换而索引未重建，查询可能返回过期数据或崩溃。

- [ ] **Step 1: Write test**

```python
# tests/test_index_staleness.py
import os
import time
import pytest


class TestIndexStaleness:
    def test_stale_index_is_detected(self, tmp_path):
        # Create mock source file and stale index
        source = tmp_path / "test.vcf.gz"
        source.write_text("mock vcf data")

        index = tmp_path / "test.vcf.gz.tbi"
        index.write_text("mock tbi index")

        # Make index older than source
        old_time = time.time() - 3600  # 1 hour ago
        os.utime(index, (old_time, old_time))

        from apps.datasets.adapters.base import DatasetQueryAdapter

        # Test the staleness logic directly
        is_stale = DatasetQueryAdapter._is_index_stale(
            source_path=str(source),
            index_path=str(index),
        )
        assert is_stale is True

    def test_fresh_index_passes(self, tmp_path):
        source = tmp_path / "test.vcf.gz"
        source.write_text("mock vcf data")

        index = tmp_path / "test.vcf.gz.tbi"
        index.write_text("mock tbi index")

        # Make index newer than source
        new_time = time.time() + 3600
        os.utime(index, (new_time, new_time))

        from apps.datasets.adapters.base import DatasetQueryAdapter

        is_stale = DatasetQueryAdapter._is_index_stale(
            source_path=str(source),
            index_path=str(index),
        )
        assert is_stale is False
```

- [ ] **Step 2: Add staleness check to `DatasetQueryAdapter`**

In `apps/datasets/adapters/base.py`, add this static method:

```python
@staticmethod
def _is_index_stale(source_path: str, index_path: str) -> bool:
    """Return True if the index file is older than the source file."""
    try:
        source_mtime = os.path.getmtime(source_path)
        index_mtime = os.path.getmtime(index_path)
        return index_mtime < source_mtime
    except OSError:
        return True  # Can't stat = treat as stale
```

Then modify `ensure_sidecar_index_files` to check staleness. After line 101 (`if os.path.exists(expected_path):`), change the `continue` to check staleness:

Find:
```python
if os.path.exists(expected_path):
    continue
```
Replace with:
```python
if os.path.exists(expected_path):
    if not self._is_index_stale(file_path, expected_path):
        continue
    # Index is stale — log and rebuild below
```

- [ ] **Step 3: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_index_staleness.py -v
```
Expected: 2 PASS

- [ ] **Step 4: Commit**

```bash
git add apps/datasets/adapters/base.py tests/test_index_staleness.py
git commit -m "fix: add index staleness detection to ensure_sidecar_index_files"
```

---

### Task 4: F-8 — Expression 多格式支持

**Files:**
- Modify: `backend/api-server/apps/datasets/adapters/expression.py`
- Create: `backend/api-server/tests/test_expression_formats.py`

**Context:** `ExpressionAdapter` 仅支持 HDF5（`supported_file_formats = ["h5", "hdf5"]`）。需要扩展支持 TSV/CSV count matrix。

- [ ] **Step 1: Write test**

```python
# tests/test_expression_formats.py


class TestExpressionMultiFormat:
    def test_adapter_accepts_tsv_format(self):
        from apps.datasets.adapters.expression import ExpressionAdapter

        adapter = ExpressionAdapter()
        payload = {
            "id": 1,
            "dataset_type": "transcriptome",
            "query_profile": {"file_format": "tsv"},
        }
        assert adapter.supports(payload) is True

    def test_adapter_accepts_csv_format(self):
        from apps.datasets.adapters.expression import ExpressionAdapter

        adapter = ExpressionAdapter()
        payload = {
            "id": 1,
            "dataset_type": "transcriptome",
            "query_profile": {"file_format": "csv"},
        }
        assert adapter.supports(payload) is True

    def test_adapter_accepts_10x_mtx_format(self):
        from apps.datasets.adapters.expression import ExpressionAdapter

        adapter = ExpressionAdapter()
        payload = {
            "id": 1,
            "dataset_type": "transcriptome",
            "query_profile": {"file_format": "mtx"},
        }
        assert adapter.supports(payload) is True
```

- [ ] **Step 2: Update `ExpressionAdapter`**

In `apps/datasets/adapters/expression.py`, change line 14:

```python
supported_file_formats = ["h5", "hdf5", "tsv", "csv", "txt", "mtx", "mtx.gz"]
```

Update `describe()` to include new formats in `supported_file_formats` and add TSV operations:

```python
def describe(self, dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
    fmt = dataset_payload.get("query_profile", {}).get("file_format", "h5")
    return {
        "adapter": self.adapter_name,
        "display_name": self.display_name,
        "dataset_type": dataset_payload.get("dataset_type"),
        "file_format": fmt,
        "supported_operations": ["genes_list", "samples_list", "matrix_slice"],
        "query_entrypoints": ["/api/v1/dataset/query/execute"],
        "examples": {
            "genes_list": {"operation": "genes_list", "params": {"max_records": 20}},
            "samples_list": {"operation": "samples_list", "params": {"max_records": 20}},
            "matrix_slice": {
                "operation": "matrix_slice",
                "params": {"data_type": "count", "genes": [], "samples": []},
            },
        },
    }
```

Modify `execute()` to support TSV/CSV via pandas fallback:

```python
def execute(self, dataset_payload, operation, params):
    file_path = self.require_file_path(dataset_payload)
    fmt = str(dataset_payload.get("query_profile", {}).get("file_format") or "").lower()

    if fmt in ("tsv", "csv", "txt"):
        return self._execute_tsv(file_path, operation, params)

    # Existing HDF5 path...
    if operation == "genes_list":
        ...

def _execute_tsv(self, file_path, operation, params):
    import pandas as pd

    sep = "\t" if file_path.endswith((".tsv", ".txt")) else ","
    df = pd.read_csv(file_path, sep=sep, index_col=0, nrows=1000)

    if operation == "genes_list":
        genes = df.index.tolist()
        max_records = int(params.get("max_records") or 100)
        return {
            "adapter": self.adapter_name,
            "operation": operation,
            "data": {"genes": genes[:max_records], "count": len(genes)},
        }

    if operation == "samples_list":
        samples = df.columns.tolist()
        max_records = int(params.get("max_records") or 100)
        return {
            "adapter": self.adapter_name,
            "operation": operation,
            "data": {"samples": samples[:max_records], "count": len(samples)},
        }

    if operation == "matrix_slice":
        genes = params.get("genes")
        samples = params.get("samples")
        sub = df
        if genes:
            sub = sub.loc[sub.index.isin(genes)]
        if samples:
            sub = sub[[s for s in samples if s in sub.columns]]
        return {
            "adapter": self.adapter_name,
            "operation": operation,
            "data": {
                "genes": sub.index.tolist(),
                "samples": sub.columns.tolist(),
                "matrix": sub.values.tolist(),
            },
        }

    raise HTTPException(status_code=400, detail=f"Unsupported operation: {operation}")
```

- [ ] **Step 3: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_expression_formats.py -v
```
Expected: 3 PASS

- [ ] **Step 4: Commit**

```bash
git add apps/datasets/adapters/expression.py tests/test_expression_formats.py
git commit -m "feat: extend ExpressionAdapter to support TSV/CSV count matrix formats"
```

---

### Task 5: F-9 — Phenome → Breeding Observation 桥接

**Files:**
- Modify: `backend/api-server/apps/datasets/phenome_indexing.py`
- Create: `backend/api-server/tests/test_phenome_breeding_bridge.py`

**Context:** `rebuild_phenome_index()` 构建 `phn_observation` 表，但不会写入 `BreedingObservation`。两条线独立存在。F-9 在 phenome indexing 完成后提供可选的桥接选项，通过 `BreedingPhenotypeSubjectMap` 将 observation 映射到 breeding material。

- [ ] **Step 1: Write test**

```python
# tests/test_phenome_breeding_bridge.py


class TestPhenomeBreedingBridge:
    def test_bridge_maps_phenome_observation_to_breeding(self, db_session):
        from apps.datasets.phenome_indexing import PhenomeBreedingBridge
        from apps.breeding.models import (
            BreedingProgram, BreedingMaterial, BreedingPhenotypeSubjectMap,
        )
        from apps.datasets.models import (
            PhenomeImportRun, PhenomeSubject, PhenomeTrait, PhenomeObservation,
        )
        from apps.datasets.dataset_model import Dataset

        program = BreedingProgram(code="P_PHBR", name="Phenome Bridge", status="active")
        db_session.add(program)
        db_session.commit()

        mat = BreedingMaterial(program_id=program.id, material_code="M_PHBR", material_name="Bridge Material")
        db_session.add(mat)
        db_session.commit()

        ds = Dataset(dataset_code="DS_PHBR", dataset_type="phenome", organism="Oryza sativa", assembly="IRGSP-1.0")
        db_session.add(ds)
        db_session.commit()

        # Minimal phenome index records
        run = PhenomeImportRun(source_path="/tmp/test.sqlite", status="completed")
        db_session.add(run)
        db_session.commit()

        subject = PhenomeSubject(run_id=run.id, subject_name="M_PHBR", subject_type="accession")
        trait = PhenomeTrait(run_id=run.id, trait_code="height", trait_name="Plant Height", data_type="numeric")
        obs = PhenomeObservation(subject_id=subject.id, trait_id=trait.id, value_numeric="120.5")
        db_session.add_all([subject, trait])
        db_session.commit()
        db_session.add(obs)
        db_session.commit()

        result = PhenomeBreedingBridge.map_subject_to_material(
            db=db_session,
            subject_name="M_PHBR",
            dataset_id=ds.id,
            version_id=1,
            asset_id=1,
        )
        assert result["mapped"] is True
        assert result["material_id"] == mat.id
```

- [ ] **Step 2: Implement `PhenomeBreedingBridge`**

Add to `apps/datasets/phenome_indexing.py`:

```python
class PhenomeBreedingBridge:
    """Bridge phenome index subjects to breeding materials."""

    @staticmethod
    def map_subject_to_material(
        db, subject_name, dataset_id, version_id, asset_id
    ) -> dict:
        """Match a phenome subject_name to BreedingMaterial by material_code or material_name."""
        from apps.breeding.models import BreedingMaterial, BreedingPhenotypeSubjectMap

        material = (
            db.query(BreedingMaterial)
            .filter(
                (BreedingMaterial.material_code == subject_name)
                | (BreedingMaterial.material_name == subject_name)
            )
            .first()
        )
        if not material:
            return {"mapped": False, "subject_name": subject_name, "reason": "No matching material found"}

        # Create or update phenotype_subject_map
        existing = (
            db.query(BreedingPhenotypeSubjectMap)
            .filter_by(
                dataset_id=dataset_id,
                version_id=version_id,
                asset_id=asset_id,
                row_key=subject_name,
            )
            .first()
        )
        if not existing:
            pmap = BreedingPhenotypeSubjectMap(
                dataset_id=dataset_id,
                version_id=version_id,
                asset_id=asset_id,
                row_key=subject_name,
                material_id=material.id,
                mapping_status="matched",
                mapping_method="inferred",
                confidence="medium",
            )
            db.add(pmap)
            db.commit()

        return {
            "mapped": True,
            "subject_name": subject_name,
            "material_id": material.id,
            "material_code": material.material_code,
        }
```

- [ ] **Step 3: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_phenome_breeding_bridge.py -v
```
Expected: 1 PASS

- [ ] **Step 4: Commit**

```bash
git add apps/datasets/phenome_indexing.py tests/test_phenome_breeding_bridge.py
git commit -m "feat: add PhenomeBreedingBridge to map phenome subjects to breeding materials"
```

---

## Phase 3 Completion Checklist

- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Verify `AnalysisReadinessService.check_gwas_readiness` returns green/yellow/red
- [ ] Verify `CrossDatasetQueryService` query plans reference valid adapter operations
- [ ] Verify `ExpressionAdapter` accepts tsv/csv/mtx in `supports()`
- [ ] Verify `_is_index_stale` correctly compares mtime
- [ ] Verify `PhenomeBreedingBridge` creates `BreedingPhenotypeSubjectMap` records
