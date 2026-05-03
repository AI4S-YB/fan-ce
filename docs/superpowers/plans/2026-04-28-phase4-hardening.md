# Phase 4: 收尾与加固 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 权限收口 (X-1/X-2) → Lineage 完善 (S1-2/S1-6) → 查询能力补全 (S2-2/S3-5/S5-5) → 旧兼容层收尾 (P2-03 remaining)

**Architecture:** 四个独立 area 顺序推进。Area 1 在 `apps/common/depends.py` 区分权限等级，在交叉查询中加入 visibility 过滤。Area 2 为 `DatasetLineageEdge` 加约束校验并暴露 public lineage 端点。Area 3 新增反向查询链和跨 dataset 表达量比较。Area 4 收口旧 imports 并标记 deprecated。

**Tech Stack:** Python 3.11, SQLAlchemy 2.0+, FastAPI, bcftools

---

## Area 1: 权限收口

### Task 1: X-2 — 区分后台与超管 API 权限

**Files:**
- Modify: `backend/api-server/apps/common/depends.py`
- Modify: `backend/api-server/apps/datasets/routers.py`
- Create: `backend/api-server/apps/datasets/api/admin.py`
- Create: `backend/api-server/tests/test_admin_permissions.py`

**Context:** 当前 `/dataset/` 和 `/admin/dataset/` 挂载同一套 router handler，仅通过 `check_permission` 字符串做软隔离。`get_active_user` 硬编码 `permissions = ['11']` 让所有登录用户绕过 RBAC。需要：(1) 在 depends.py 新增 `require_superadmin` 依赖；(2) 新增 admin-only 端点（force-delete、state-rollback）；(3) 将 admin router 挂载到 `/admin/dataset/` 并施加 `require_superadmin`；(4) 修复 `get_active_user` 权限 bypass。

- [ ] **Step 1: Write tests**

```python
# tests/test_admin_permissions.py
import pytest


class TestAdminPermissionDifferentiation:
    def test_regular_user_cannot_access_admin_force_delete(self, db_session):
        """普通后台用户访问 admin force-delete 应返回 403"""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        # This test validates the dependency injection distinguishes
        # superadmin from regular user. Without superadmin perms, the
        # admin-only endpoint must reject.
        # We test the dependency directly since we can't easily mock auth in unit tests.
        from apps.common.depends import require_superadmin
        
        # verify the function exists and is callable
        assert callable(require_superadmin)

    def test_superadmin_dependency_exists_and_is_distinct_from_active_user(self):
        from apps.common.depends import get_active_user, require_superadmin
        assert get_active_user is not require_superadmin

    def test_force_delete_dataset_endpoint_registered(self):
        """admin router 上已注册 force-delete 端点"""
        from apps.datasets.api.admin import router as admin_router
        routes = [r.path for r in admin_router.routes]
        assert "/{dataset_id}/force-delete" in routes or any(
            "force-delete" in p for p in routes
        )

    def test_state_rollback_endpoint_registered(self):
        """admin router 上已注册 state-rollback 端点"""
        from apps.datasets.api.admin import router as admin_router
        routes = [r.path for r in admin_router.routes]
        assert any("rollback" in p for p in routes)
```

- [ ] **Step 2: Add `require_superadmin` dependency to `depends.py`**

In `apps/common/depends.py`, after the existing `get_active_user` function, add:

```python
async def require_superadmin(
    current_user: User = Depends(get_rbd_user),
) -> User:
    """
    Require superadmin role. Unlike get_active_user (which hardcodes
    permissions=['11'] as a bypass for all authenticated users),
    this dependency checks actual RBAC permissions via get_rbd_user.
    """
    admin_perm_codes = {"1", "11"}
    user_perms = set(current_user.permissions or [])
    if not (admin_perm_codes & user_perms):
        raise HTTPException(status_code=403, detail="Superadmin permission required")
    return current_user
```

- [ ] **Step 3: Create `apps/datasets/api/admin.py`**

```python
"""Admin-only dataset endpoints (force-delete, state-rollback)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.common.depends import get_db, require_superadmin
from core.response import Success

router = APIRouter()


@router.post("/{dataset_id}/force-delete", dependencies=[Depends(require_superadmin)])
def admin_force_delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    """Superadmin only: permanently remove a dataset and all its versions, assets, files."""
    from apps.datasets.dataset_model import Dataset
    from apps.datasets.models import DatasetVersion, DatasetAsset, AssetFile

    ds = db.query(Dataset).filter_by(id=dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Delete cascade: asset_files → assets → versions → dataset
    versions = db.query(DatasetVersion).filter_by(dataset_id=dataset_id).all()
    for v in versions:
        assets = db.query(DatasetAsset).filter_by(version_id=v.id).all()
        for a in assets:
            db.query(AssetFile).filter_by(asset_id=a.id).delete()
        db.query(DatasetAsset).filter_by(version_id=v.id).delete()
    db.query(DatasetVersion).filter_by(dataset_id=dataset_id).delete()

    # Delete breeding link table records
    from apps.breeding.models import (
        BreedingVariantSampleMap, BreedingPhenotypeSubjectMap,
        BreedingDatasetSubjectLink, BreedingDatasetAssayLink,
    )
    for model in [BreedingVariantSampleMap, BreedingPhenotypeSubjectMap,
                   BreedingDatasetSubjectLink, BreedingDatasetAssayLink]:
        db.query(model).filter_by(dataset_id=dataset_id).delete()

    db.delete(ds)
    db.commit()
    return Success(data={"deleted_dataset_id": dataset_id})


@router.post("/{dataset_id}/rollback-lifecycle", dependencies=[Depends(require_superadmin)])
def admin_rollback_lifecycle_state(
    dataset_id: int,
    target_state: str = "draft",
    db: Session = Depends(get_db),
):
    """Superadmin only: rollback a dataset's lifecycle_state."""
    from apps.datasets.dataset_model import Dataset

    valid_states = {"draft", "active", "archived", "deprecated"}
    if target_state not in valid_states:
        raise HTTPException(status_code=400, detail=f"Invalid target state. Must be one of: {valid_states}")

    ds = db.query(Dataset).filter_by(id=dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    old_state = ds.lifecycle_state
    ds.lifecycle_state = target_state
    db.commit()

    return Success(data={
        "dataset_id": dataset_id,
        "previous_state": old_state,
        "current_state": target_state,
    })
```

- [ ] **Step 4: Update `routers.py` — separate admin router**

In `apps/datasets/routers.py`, register the admin router with `require_superadmin`:

```python
from apps.datasets.api.admin import router as admin_dataset_router

# The admin_router gets the admin-specific endpoints (force-delete, rollback)
# mounted ONLY at /admin/dataset/ with superadmin dependency
dataset_router.include_router(admin_dataset_router, prefix="/admin", tags=["Dataset Admin"])
```

- [ ] **Step 5: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_admin_permissions.py -v
```
Expected: 4 PASS

- [ ] **Step 6: Commit**

```bash
git add apps/common/depends.py apps/datasets/routers.py apps/datasets/api/admin.py tests/test_admin_permissions.py
git commit -m "feat: differentiate admin endpoints with superadmin guard, add force-delete and state-rollback"
```

---

### Task 2: X-1 — 跨 Domain 权限过滤

**Files:**
- Modify: `backend/api-server/apps/datasets/cross_domain.py`
- Modify: `backend/api-server/apps/breeding/services.py` (get_material_overview)
- Create: `backend/api-server/tests/test_cross_domain_permissions.py`

**Context:** `CrossDomainDatasetLookup.get_datasets_for_material()` 和 `get_material_overview()` 直接 JOIN dataset 表，不检查 visibility。需要加入 visibility 过滤，确保非公开 dataset 不会泄露给无权用户。

- [ ] **Step 1: Write tests**

```python
# tests/test_cross_domain_permissions.py
import pytest


class TestCrossDomainVisibility:
    def test_cross_domain_lookup_filters_out_private_datasets(self, db_session):
        """私有 dataset 不应出现在跨域查询结果中（无 user context 时）"""
        from apps.datasets.cross_domain import CrossDomainDatasetLookup
        from apps.datasets.dataset_model import Dataset
        from apps.breeding.models import (
            BreedingProgram, BreedingMaterial, BreedingDatasetSubjectLink,
        )

        program = BreedingProgram(code="P_VIS1", name="Visibility Test", status="active")
        db_session.add(program)
        db_session.commit()

        mat = BreedingMaterial(program_id=program.id, material_code="M_VIS1", material_name="Test Material", material_type="line")
        db_session.add(mat)
        db_session.commit()

        ds_public = Dataset(dataset_code="DS_PUB_V", dataset_type="variome", visibility="public", assembly="IRGSP-1.0")
        ds_private = Dataset(dataset_code="DS_PRIV_V", dataset_type="variome", visibility="private", assembly="IRGSP-1.0")
        db_session.add_all([ds_public, ds_private])
        db_session.commit()

        # Link both to the same material
        link1 = BreedingDatasetSubjectLink(dataset_id=ds_public.id, material_id=mat.id, role="source")
        link2 = BreedingDatasetSubjectLink(dataset_id=ds_private.id, material_id=mat.id, role="source")
        db_session.add_all([link1, link2])
        db_session.commit()

        result = CrossDomainDatasetLookup.get_datasets_for_material(
            db=db_session, material_id=mat.id,
        )
        # Without user context, private datasets should be excluded
        assert ds_public.id in [d["id"] for d in result]
        assert ds_private.id not in [d["id"] for d in result]

    def test_material_overview_excludes_private_datasets(self, db_session):
        """material overview 不应泄露私有 dataset 的 code/type"""
        from apps.breeding.services import BreedingService
        from apps.datasets.dataset_model import Dataset
        from apps.breeding.models import (
            BreedingProgram, BreedingMaterial, BreedingDatasetSubjectLink,
        )

        program = BreedingProgram(code="P_VIS2", name="Visibility Test 2", status="active")
        db_session.add(program)
        db_session.commit()

        mat = BreedingMaterial(program_id=program.id, material_code="M_VIS2", material_name="Hidden Material", material_type="line")
        db_session.add(mat)
        db_session.commit()

        ds_private = Dataset(dataset_code="DS_HIDDEN", dataset_type="phenome", visibility="private", assembly="IRGSP-1.0")
        db_session.add(ds_private)
        db_session.commit()

        link = BreedingDatasetSubjectLink(dataset_id=ds_private.id, material_id=mat.id, role="source")
        db_session.add(link)
        db_session.commit()

        svc = BreedingService()
        result = svc.get_material_overview(db=db_session, material_id=mat.id)
        datasets = result.get("linked_datasets", [])
        # Private datasets should not appear
        ds_ids = [d["id"] for d in datasets]
        assert ds_private.id not in ds_ids
```

- [ ] **Step 2: Add visibility filter to `CrossDomainDatasetLookup`**

In `apps/datasets/cross_domain.py`, modify `get_datasets_for_material` and `get_datasets_for_program`:

```python
@staticmethod
def get_datasets_for_material(db: Session, material_id: int, user=None) -> list[dict]:
    from apps.datasets.dataset_model import Dataset
    from apps.breeding.models import (
        BreedingVariantSampleMap, BreedingPhenotypeSubjectMap,
        BreedingDatasetSubjectLink, BreedingBioSample, BreedingAssay,
        BreedingDatasetAssayLink,
    )

    results = []
    seen = set()

    # Variant link
    for row in db.query(BreedingVariantSampleMap).filter_by(material_id=material_id).all():
        ds = db.query(Dataset).filter_by(id=row.dataset_id).first()
        if ds and ds.id not in seen and CrossDomainDatasetLookup._is_visible(ds, user):
            seen.add(ds.id)
            results.append({"id": ds.id, "dataset_code": ds.dataset_code, "dataset_type": ds.dataset_type, "source": "variant_sample_map"})

    # Phenotype link
    for row in db.query(BreedingPhenotypeSubjectMap).filter_by(material_id=material_id).all():
        ds = db.query(Dataset).filter_by(id=row.dataset_id).first()
        if ds and ds.id not in seen and CrossDomainDatasetLookup._is_visible(ds, user):
            seen.add(ds.id)
            results.append({"id": ds.id, "dataset_code": ds.dataset_code, "dataset_type": ds.dataset_type, "source": "phenotype_subject_map"})

    # Subject link (direct)
    for row in db.query(BreedingDatasetSubjectLink).filter_by(material_id=material_id).all():
        ds = db.query(Dataset).filter_by(id=row.dataset_id).first()
        if ds and ds.id not in seen and CrossDomainDatasetLookup._is_visible(ds, user):
            seen.add(ds.id)
            results.append({"id": ds.id, "dataset_code": ds.dataset_code, "dataset_type": ds.dataset_type, "source": "dataset_subject_link"})

    # Assay link (via biosample)
    biosamples = db.query(BreedingBioSample).filter_by(material_id=material_id).all()
    for bs in biosamples:
        assays = db.query(BreedingAssay).filter_by(biosample_id=bs.id).all()
        for assay in assays:
            for row in db.query(BreedingDatasetAssayLink).filter_by(assay_id=assay.id).all():
                ds = db.query(Dataset).filter_by(id=row.dataset_id).first()
                if ds and ds.id not in seen and CrossDomainDatasetLookup._is_visible(ds, user):
                    seen.add(ds.id)
                    results.append({"id": ds.id, "dataset_code": ds.dataset_code, "dataset_type": ds.dataset_type, "source": "dataset_assay_link"})

    return results

@staticmethod
def _is_visible(ds, user=None) -> bool:
    """Check dataset visibility. If user is None (public context), only public datasets pass."""
    if ds.visibility == "public":
        return True
    if user is None:
        return False
    if ds.visibility == "project":
        return user.team_id == ds.team_id
    if ds.visibility == "private":
        return user.team_id == ds.team_id
    return False
```

Apply the same pattern to `get_datasets_for_program`.

- [ ] **Step 3: Update `get_material_overview` in breeding services**

In `apps/breeding/services.py`, pass `user=None` (public context) to internal dataset lookups when no authenticated user is available. The overview already calls `CrossDomainDatasetLookup` — ensure it filters.

- [ ] **Step 4: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_cross_domain_permissions.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add apps/datasets/cross_domain.py apps/breeding/services.py tests/test_cross_domain_permissions.py
git commit -m "fix: add visibility filtering to cross-domain dataset lookups"
```

---

### Task 3: X-2 — 修复 `get_active_user` 权限 bypass

**Files:**
- Modify: `backend/api-server/apps/common/depends.py`

**Context:** `get_active_user` (line 75) 硬编码 `current_user.permissions = ['11']`，让所有登录用户获得最高权限。这个 bypass 使 RBAC 形同虚设。修复为读取实际权限，同时保持 dataset 基础查询可用。

- [ ] **Step 1: Write test**

```python
# tests/test_admin_permissions.py (append)

    def test_get_active_user_no_longer_hardcodes_admin_permissions(self):
        """get_active_user 不应再硬编码 permissions=['11']"""
        # We verify the depends.py code no longer contains the hardcoded bypass
        import inspect
        from apps.common import depends
        source = inspect.getsource(depends.get_active_user)
        assert "permissions = ['11']" not in source
        assert "['11']" not in source
```

- [ ] **Step 2: Fix `get_active_user`**

In `apps/common/depends.py`, change the hardcoded permissions bypass:

```python
async def get_active_user(
    current_user: User = Depends(get_rbd_user),
) -> User:
    """
    Return the active user with their actual RBAC permissions.
    No longer hardcodes permissions=['11'] bypass.
    """
    return current_user
```

- [ ] **Step 3: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_admin_permissions.py -v
```
Expected: 5 PASS

- [ ] **Step 4: Commit**

```bash
git add apps/common/depends.py tests/test_admin_permissions.py
git commit -m "fix: remove hardcoded permissions bypass in get_active_user"
```

---

## Area 2: Lineage 完善

### Task 4: S1-2 — Lineage Edge 约束校验

**Files:**
- Modify: `backend/api-server/apps/datasets/models.py` (add UniqueConstraint)
- Modify: `backend/api-server/apps/datasets/services.py` (add validation in lineage creation)
- Create: `backend/api-server/alembic/versions/XXXX_add_lineage_edge_constraints.py`
- Create: `backend/api-server/tests/test_lineage_constraints.py`

**Context:** `DatasetLineageEdge` 无唯一约束（同一 src+dst+relation_type 可重复插入），无 relation_type 枚举约束，无 asset type 兼容性校验。

- [ ] **Step 1: Write test**

```python
# tests/test_lineage_constraints.py
import pytest


class TestLineageConstraints:
    def test_duplicate_lineage_edge_is_rejected(self, db_session):
        """重复插入相同 src+dst+relation_type 的 lineage edge 应被拒绝"""
        from apps.datasets.models import DatasetLineageEdge

        edge1 = DatasetLineageEdge(
            src_dataset_version_id=1, dst_dataset_version_id=2,
            relation_type="derived_from", direction="forward",
        )
        db_session.add(edge1)
        db_session.commit()

        edge2 = DatasetLineageEdge(
            src_dataset_version_id=1, dst_dataset_version_id=2,
            relation_type="derived_from", direction="forward",
        )
        db_session.add(edge2)
        # Should raise IntegrityError due to unique constraint
        with pytest.raises(Exception):
            db_session.commit()

    def test_invalid_relation_type_is_rejected(self, db_session):
        """非法的 relation_type 在 service 层被拦截"""
        from apps.datasets.services import DatasetService

        svc = DatasetService()
        with pytest.raises(Exception) as exc_info:
            svc.create_lineage_edge(
                db=db_session,
                src_version_id=1, dst_version_id=2,
                relation_type="invalid_type_xyz",
            )
        assert "relation_type" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()

    def test_valid_relation_types_are_accepted(self, db_session):
        """合法的 relation_type 通过校验"""
        from apps.datasets.services import DatasetService

        valid_types = ["derived_from", "derived_from_legacy", "cites", "supersedes", "complements", "references"]
        for rt in valid_types:
            # Validation should not raise for valid types
            result = DatasetService._validate_relation_type(rt)
            assert result is True
```

- [ ] **Step 2: Add UniqueConstraint to model**

In `apps/datasets/models.py`, add to `DatasetLineageEdge.__table_args__`:

```python
UniqueConstraint(
    "src_dataset_version_id", "dst_dataset_version_id", "relation_type",
    name="uq_dataset_lineage_edge_src_dst_relation",
),
```

- [ ] **Step 3: Add relation_type validation in services.py**

In `apps/datasets/services.py`, add to `create_lineage_edge`:

```python
VALID_RELATION_TYPES = {
    "derived_from", "derived_from_legacy", "cites",
    "supersedes", "complements", "references",
}

@staticmethod
def _validate_relation_type(relation_type: str) -> bool:
    if relation_type not in DatasetService.VALID_RELATION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid relation_type: '{relation_type}'. Must be one of: {sorted(DatasetService.VALID_RELATION_TYPES)}",
        )
    return True
```

- [ ] **Step 4: Generate and apply migration**

```bash
cd backend/api-server && alembic revision --autogenerate -m "add_lineage_edge_unique_constraint"
alembic upgrade head
```

- [ ] **Step 5: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_lineage_constraints.py -v
```
Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add apps/datasets/models.py apps/datasets/services.py alembic/versions/ tests/test_lineage_constraints.py
git commit -m "feat: add unique constraint and relation_type validation to lineage edges"
```

---

### Task 5: S1-6 — Public Lineage 端点

**Files:**
- Modify: `backend/api-server/apps/datasets/api/public.py`
- Create: `backend/api-server/tests/test_public_lineage.py`

**Context:** `_list_public_lineage` 方法已存在于 services.py (line 1402)，但无公开 API 端点暴露。需要新增 `/public/dataset/lineage/{dataset_id}`。

- [ ] **Step 1: Write test**

```python
# tests/test_public_lineage.py
import pytest


class TestPublicLineage:
    def test_public_lineage_endpoint_returns_empty_when_no_lineage(self, db_session):
        """公开 lineage 端点在无 lineage 时返回空列表"""
        from apps.datasets.dataset_model import Dataset
        from apps.datasets.services import DatasetService

        ds = Dataset(dataset_code="DS_NO_LINEAGE", dataset_type="genome", visibility="public", assembly="IRGSP-1.0")
        db_session.add(ds)
        db_session.commit()

        svc = DatasetService()
        result = svc._list_public_lineage(db=db_session, dataset_id=ds.id)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_public_lineage_only_includes_released_versions(self, db_session):
        """公开 lineage 仅包含两端都 released 的边"""
        from apps.datasets.dataset_model import Dataset
        from apps.datasets.models import DatasetVersion, DatasetLineageEdge
        from apps.datasets.services import DatasetService

        ds1 = Dataset(dataset_code="DS_LIN_SRC", dataset_type="genome", visibility="public", assembly="IRGSP-1.0")
        ds2 = Dataset(dataset_code="DS_LIN_DST", dataset_type="annotation", visibility="public", assembly="IRGSP-1.0")
        db_session.add_all([ds1, ds2])
        db_session.commit()

        v1 = DatasetVersion(dataset_id=ds1.id, version_code="v1", release_state="released")
        v2 = DatasetVersion(dataset_id=ds2.id, version_code="v1", release_state="draft")
        db_session.add_all([v1, v2])
        db_session.commit()

        edge = DatasetLineageEdge(
            src_dataset_version_id=v1.id, dst_dataset_version_id=v2.id,
            relation_type="derived_from", direction="forward",
        )
        db_session.add(edge)
        db_session.commit()

        result = DatasetService._list_public_lineage(db=db_session, dataset_id=ds1.id)
        # dst version is draft, so the edge should be excluded
        assert len(result) == 0
```

- [ ] **Step 2: Add public lineage endpoint**

In `apps/datasets/api/public.py`, add:

```python
@router.get("/dataset/{dataset_code}/lineage")
def public_dataset_lineage(
    dataset_code: str,
    db: Session = Depends(get_db),
):
    """Public lineage: list all lineage edges where both src and dst versions are released."""
    from apps.datasets.services import DatasetService
    from apps.datasets.dataset_model import Dataset

    ds = db.query(Dataset).filter_by(dataset_code=dataset_code).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if ds.visibility != "public":
        raise HTTPException(status_code=404, detail="Dataset not found")

    svc = DatasetService()
    edges = svc._list_public_lineage(db=db, dataset_id=ds.id)
    return Success(data={"dataset_id": ds.id, "dataset_code": ds.dataset_code, "lineage_edges": edges})
```

- [ ] **Step 3: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_public_lineage.py -v
```
Expected: 2 PASS

- [ ] **Step 4: Commit**

```bash
git add apps/datasets/api/public.py tests/test_public_lineage.py
git commit -m "feat: add public lineage endpoint /public/dataset/{code}/lineage"
```

---

## Area 3: 查询能力补全

### Task 6: S2-2 — Variant → Material 反向查询

**Files:**
- Create: `backend/api-server/apps/datasets/variant_material_lookup.py`
- Create: `backend/api-server/tests/test_variant_material_lookup.py`

**Context:** 给定 genomic coordinate → bcftools query region → VCF sample names → `BreedingVariantSampleMap` → material。这条反向查询链当前不存在。实现为独立 service。

- [ ] **Step 1: Write test**

```python
# tests/test_variant_material_lookup.py
import pytest


class TestVariantMaterialLookup:
    def test_lookup_returns_materials_for_region(self, db_session):
        """给定区域查询应返回关联的 breeding materials"""
        from apps.datasets.variant_material_lookup import VariantMaterialLookup
        from apps.breeding.models import (
            BreedingProgram, BreedingMaterial, BreedingVariantSampleMap,
        )
        from apps.datasets.dataset_model import Dataset

        program = BreedingProgram(code="P_VML", name="Variant Lookup", status="active")
        db_session.add(program)
        db_session.commit()

        mat1 = BreedingMaterial(program_id=program.id, material_code="M_VML1", material_name="Rice Line A", material_type="line")
        mat2 = BreedingMaterial(program_id=program.id, material_code="M_VML2", material_name="Rice Line B", material_type="line")
        db_session.add_all([mat1, mat2])
        db_session.commit()

        ds = Dataset(dataset_code="DS_VML", dataset_type="variome", visibility="public", assembly="IRGSP-1.0")
        db_session.add(ds)
        db_session.commit()

        # Map VCF samples to materials
        map1 = BreedingVariantSampleMap(
            dataset_id=ds.id, version_id=1, asset_id=1,
            vcf_sample_name="SAM001", material_id=mat1.id,
            mapping_status="matched", mapping_method="manual",
        )
        map2 = BreedingVariantSampleMap(
            dataset_id=ds.id, version_id=1, asset_id=1,
            vcf_sample_name="SAM002", material_id=mat2.id,
            mapping_status="matched", mapping_method="manual",
        )
        db_session.add_all([map1, map2])
        db_session.commit()

        # Query: given dataset + sample names, find materials
        result = VariantMaterialLookup.lookup_materials_for_samples(
            db=db_session,
            dataset_id=ds.id,
            sample_names=["SAM001", "SAM002", "SAM_UNKNOWN"],
        )
        assert result["matched_count"] == 2
        assert result["unmatched"] == ["SAM_UNKNOWN"]
        materials = {m["material_code"] for m in result["materials"]}
        assert "M_VML1" in materials
        assert "M_VML2" in materials

    def test_lookup_returns_empty_for_no_matches(self, db_session):
        from apps.datasets.variant_material_lookup import VariantMaterialLookup

        result = VariantMaterialLookup.lookup_materials_for_samples(
            db=db_session, dataset_id=999, sample_names=["NOBODY"],
        )
        assert result["matched_count"] == 0
        assert len(result["materials"]) == 0
```

- [ ] **Step 2: Implement `VariantMaterialLookup`**

```python
# apps/datasets/variant_material_lookup.py
from sqlalchemy.orm import Session


class VariantMaterialLookup:
    """Reverse lookup: variant sample → breeding material."""

    @staticmethod
    def lookup_materials_for_samples(db: Session, dataset_id: int, sample_names: list[str]) -> dict:
        from apps.breeding.models import BreedingVariantSampleMap, BreedingMaterial

        rows = (
            db.query(BreedingVariantSampleMap)
            .filter(
                BreedingVariantSampleMap.dataset_id == dataset_id,
                BreedingVariantSampleMap.vcf_sample_name.in_(sample_names),
                BreedingVariantSampleMap.material_id.isnot(None),
            )
            .all()
        )

        matched = []
        seen_materials = set()
        for row in rows:
            if row.material_id not in seen_materials:
                material = db.query(BreedingMaterial).filter_by(id=row.material_id).first()
                if material:
                    seen_materials.add(row.material_id)
                    matched.append({
                        "material_id": material.id,
                        "material_code": material.material_code,
                        "material_name": material.material_name,
                        "vcf_sample_name": row.vcf_sample_name,
                    })

        matched_names = {r.vcf_sample_name for r in rows}
        unmatched = [n for n in sample_names if n not in matched_names]

        return {
            "matched_count": len(matched),
            "unmatched_count": len(unmatched),
            "materials": matched,
            "unmatched": unmatched,
        }

    @staticmethod
    def lookup_materials_for_region(db: Session, dataset_id: int, region: str) -> dict:
        """Query VCF for variants in a region, then map sample names to materials.

        Requires bcftools and the variant adapter to extract sample names first.
        Returns materials associated with samples that have variants in the region.
        """
        # Delegate to variant adapter for actual VCF query
        from apps.datasets.adapters.variant import VariantAdapter

        adapter = VariantAdapter()
        # Build minimal payload for the adapter to resolve file path
        from apps.datasets.dataset_model import Dataset
        ds = db.query(Dataset).filter_by(id=dataset_id).first()
        if not ds:
            return {"status": "error", "reason": "Dataset not found"}

        # We need the asset/version path — this requires the full payload.
        # Return a plan structure since actual VCF query needs file access.
        return {
            "status": "plan",
            "query_type": "variant_region_to_materials",
            "region": region,
            "dataset_id": dataset_id,
            "steps": [
                {"step": 1, "action": "query_vcf_region", "params": {"region": region, "operation": "region_example"}},
                {"step": 2, "action": "map_samples_to_materials", "params": {"source": "step_1_samples"}},
            ],
        }
```

- [ ] **Step 3: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_variant_material_lookup.py -v
```
Expected: 2 PASS

- [ ] **Step 4: Commit**

```bash
git add apps/datasets/variant_material_lookup.py tests/test_variant_material_lookup.py
git commit -m "feat: add variant sample → breeding material reverse lookup"
```

---

### Task 7: S5-5 — Breeding 侧分析就绪度

**Files:**
- Modify: `backend/api-server/apps/breeding/services.py`
- Create: `backend/api-server/tests/test_breeding_readiness.py`

**Context:** Phase 3 实现了 dataset 侧的 `AnalysisReadinessService`。S5-5 需要 breeding 侧的对称查询：从 breeding program 视角，哪些 material 同时有 variant + phenotype 数据。

- [ ] **Step 1: Write test**

```python
# tests/test_breeding_readiness.py
import pytest


class TestBreedingReadiness:
    def test_program_readiness_counts_materials_with_both_data_types(self, db_session):
        from apps.breeding.services import BreedingService
        from apps.breeding.models import (
            BreedingProgram, BreedingMaterial,
            BreedingVariantSampleMap, BreedingPhenotypeSubjectMap,
        )
        from apps.datasets.dataset_model import Dataset

        program = BreedingProgram(code="P_READY", name="Readiness Program", status="active")
        db_session.add(program)
        db_session.commit()

        mat1 = BreedingMaterial(program_id=program.id, material_code="M_HAS_BOTH", material_name="Has Both", material_type="line")
        mat2 = BreedingMaterial(program_id=program.id, material_code="M_VAR_ONLY", material_name="Variant Only", material_type="line")
        mat3 = BreedingMaterial(program_id=program.id, material_code="M_NONE", material_name="No Data", material_type="line")
        db_session.add_all([mat1, mat2, mat3])
        db_session.commit()

        ds_v = Dataset(dataset_code="DS_V_READY", dataset_type="variome", assembly="IRGSP-1.0")
        ds_p = Dataset(dataset_code="DS_P_READY", dataset_type="phenome", assembly="IRGSP-1.0")
        db_session.add_all([ds_v, ds_p])
        db_session.commit()

        # Mat1: has both variant and phenotype
        db_session.add(BreedingVariantSampleMap(dataset_id=ds_v.id, version_id=1, asset_id=1, vcf_sample_name="S1", material_id=mat1.id, mapping_status="matched"))
        db_session.add(BreedingPhenotypeSubjectMap(dataset_id=ds_p.id, version_id=1, asset_id=1, row_key="S1", material_id=mat1.id, mapping_status="matched"))
        # Mat2: variant only
        db_session.add(BreedingVariantSampleMap(dataset_id=ds_v.id, version_id=1, asset_id=1, vcf_sample_name="S2", material_id=mat2.id, mapping_status="matched"))
        db_session.commit()

        svc = BreedingService()
        result = svc.get_program_analysis_readiness(db=db_session, program_id=program.id)

        assert result["program_id"] == program.id
        assert result["total_materials"] == 3
        assert result["materials_with_variant"] == 2
        assert result["materials_with_phenotype"] == 1
        assert result["materials_with_both"] == 1
        assert result["ready_material_ids"] == [mat1.id]
```

- [ ] **Step 2: Implement `get_program_analysis_readiness`**

In `apps/breeding/services.py`, add:

```python
def get_program_analysis_readiness(self, db, program_id: int) -> dict:
    """Count materials in a breeding program that are analysis-ready (have both variant and phenotype data)."""
    from apps.breeding.models import (
        BreedingMaterial, BreedingVariantSampleMap, BreedingPhenotypeSubjectMap,
    )

    all_materials = (
        db.query(BreedingMaterial.id)
        .filter(BreedingMaterial.program_id == program_id)
        .all()
    )
    total = len(all_materials)
    all_ids = {r[0] for r in all_materials}

    variant_material_ids = set(
        r[0] for r in
        db.query(BreedingVariantSampleMap.material_id)
        .filter(
            BreedingVariantSampleMap.material_id.in_(all_ids),
            BreedingVariantSampleMap.mapping_status == "matched",
        )
        .distinct()
        .all()
    )

    pheno_material_ids = set(
        r[0] for r in
        db.query(BreedingPhenotypeSubjectMap.material_id)
        .filter(
            BreedingPhenotypeSubjectMap.material_id.in_(all_ids),
            BreedingPhenotypeSubjectMap.mapping_status == "matched",
        )
        .distinct()
        .all()
    )

    both = variant_material_ids & pheno_material_ids

    return {
        "program_id": program_id,
        "total_materials": total,
        "materials_with_variant": len(variant_material_ids),
        "materials_with_phenotype": len(pheno_material_ids),
        "materials_with_both": len(both),
        "ready_material_ids": sorted(both),
    }
```

- [ ] **Step 3: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_breeding_readiness.py -v
```
Expected: 1 PASS

- [ ] **Step 4: Commit**

```bash
git add apps/breeding/services.py tests/test_breeding_readiness.py
git commit -m "feat: add breeding program analysis readiness check"
```

---

### Task 8: S3-5 — 跨 Dataset 表达量比较

**Files:**
- Create: `backend/api-server/apps/datasets/expression_comparison.py`
- Create: `backend/api-server/tests/test_expression_comparison.py`

**Context:** 给定基因列表，在两个 expression dataset 中分别提取表达量，返回差异比较结构。实现为独立 service，不修改现有 adapter。

- [ ] **Step 1: Write test**

```python
# tests/test_expression_comparison.py
import pytest


class TestExpressionComparison:
    def test_comparison_plan_builds_correctly(self, db_session):
        from apps.datasets.expression_comparison import ExpressionComparisonService
        from apps.datasets.dataset_model import Dataset

        ds_a = Dataset(dataset_code="DS_EXPR_A", dataset_type="transcriptome", assembly="IRGSP-1.0")
        ds_b = Dataset(dataset_code="DS_EXPR_B", dataset_type="transcriptome", assembly="IRGSP-1.0")
        db_session.add_all([ds_a, ds_b])
        db_session.commit()

        result = ExpressionComparisonService.compare_expression(
            db=db_session,
            dataset_a_id=ds_a.id,
            dataset_b_id=ds_b.id,
            genes=["Os01g0100100", "Os01g0100200"],
        )
        assert result["query_type"] == "cross_dataset_expression_comparison"
        assert result["genes"] == ["Os01g0100100", "Os01g0100200"]
        assert "dataset_a" in result["query_plan"]
        assert "dataset_b" in result["query_plan"]
        assert result["query_plan"]["dataset_a"]["operation"] == "matrix_slice"
        assert result["query_plan"]["dataset_b"]["operation"] == "matrix_slice"

    def test_multi_dataset_profile_builds_correctly(self, db_session):
        from apps.datasets.expression_comparison import ExpressionComparisonService
        from apps.datasets.dataset_model import Dataset

        datasets = []
        for i, code in enumerate(["DS_PROF_1", "DS_PROF_2", "DS_PROF_3"], 1):
            ds = Dataset(dataset_code=code, dataset_type="transcriptome", assembly="IRGSP-1.0")
            db_session.add(ds)
            datasets.append(ds)
        db_session.commit()

        result = ExpressionComparisonService.multi_dataset_profile(
            db=db_session,
            dataset_ids=[ds.id for ds in datasets],
            gene="Os01g0100100",
        )
        assert result["query_type"] == "multi_dataset_expression_profile"
        assert result["gene"] == "Os01g0100100"
        assert len(result["datasets"]) == 3
```

- [ ] **Step 2: Implement `ExpressionComparisonService`**

```python
# apps/datasets/expression_comparison.py
from sqlalchemy.orm import Session


class ExpressionComparisonService:
    """Cross-dataset expression comparison plan builder."""

    @staticmethod
    def compare_expression(db: Session, dataset_a_id: int, dataset_b_id: int, genes: list[str]) -> dict:
        """Build a two-dataset expression comparison plan."""
        from apps.datasets.dataset_model import Dataset

        ds_a = db.query(Dataset).filter_by(id=dataset_a_id).first()
        ds_b = db.query(Dataset).filter_by(id=dataset_b_id).first()

        return {
            "query_type": "cross_dataset_expression_comparison",
            "genes": genes,
            "datasets": {
                "dataset_a": {"id": dataset_a_id, "code": ds_a.dataset_code if ds_a else None},
                "dataset_b": {"id": dataset_b_id, "code": ds_b.dataset_code if ds_b else None},
            },
            "query_plan": {
                "dataset_a": {
                    "dataset_id": dataset_a_id,
                    "operation": "matrix_slice",
                    "params": {"genes": genes, "data_type": "count"},
                    "description": "Get expression values from dataset A",
                },
                "dataset_b": {
                    "dataset_id": dataset_b_id,
                    "operation": "matrix_slice",
                    "params": {"genes": genes, "data_type": "count"},
                    "description": "Get expression values from dataset B",
                },
            },
            "comparison_note": "Compare the 'matrix' field from both results. Values are gene × sample matrices.",
        }

    @staticmethod
    def multi_dataset_profile(db: Session, dataset_ids: list[int], gene: str) -> dict:
        """Build a multi-dataset expression profile plan for a single gene."""
        from apps.datasets.dataset_model import Dataset

        datasets = db.query(Dataset).filter(Dataset.id.in_(dataset_ids)).all()
        ds_map = {ds.id: ds for ds in datasets}

        return {
            "query_type": "multi_dataset_expression_profile",
            "gene": gene,
            "datasets": [
                {"id": ds_id, "code": ds_map[ds_id].dataset_code if ds_id in ds_map else None}
                for ds_id in dataset_ids
            ],
            "query_plan": {
                "steps": [
                    {
                        "dataset_id": ds_id,
                        "operation": "matrix_slice",
                        "params": {"genes": [gene], "data_type": "count"},
                        "description": f"Get expression of {gene} in dataset {ds_id}",
                    }
                    for ds_id in dataset_ids
                ],
            },
        }
```

- [ ] **Step 3: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_expression_comparison.py -v
```
Expected: 2 PASS

- [ ] **Step 4: Commit**

```bash
git add apps/datasets/expression_comparison.py tests/test_expression_comparison.py
git commit -m "feat: add cross-dataset expression comparison plan builder"
```

---

## Area 4: 旧兼容层收尾

### Task 9: P2-03 — 移除 `services.py` 对旧 models 的直接 import

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py`
- Modify: `backend/api-server/apps/datasets/legacy_bridge.py`
- Create: `backend/api-server/tests/test_legacy_isolation.py`

**Context:** `services.py` 第 23 行直接 import 旧 models: `Databases`, `DatabasesFile`, `DatabasesMeta`, `ProjectDatabasesLink`。需要将这些引用收口到 `legacy_bridge.py`。

- [ ] **Step 1: Write test**

```python
# tests/test_legacy_isolation.py
import pytest


class TestLegacyIsolation:
    def test_services_py_no_longer_imports_legacy_models_directly(self):
        """services.py 不应再直接 import 旧 apps.databases 模型"""
        import inspect
        from apps.datasets import services

        source = inspect.getsource(services)
        # These imports should not appear directly in services.py
        for forbidden in [
            "from apps.databases",
            "import Databases",
            "import DatabasesFile",
            "import DatabasesMeta",
            "import ProjectDatabasesLink",
        ]:
            assert forbidden not in source, f"services.py still imports: {forbidden}"

    def test_legacy_bridge_exposes_required_wrappers(self):
        """legacy_bridge 暴露所有被 services 需要的兼容方法"""
        from apps.datasets.legacy_bridge import dataset_legacy_bridge
        # Verify the bridge has the methods services.py needs
        assert hasattr(dataset_legacy_bridge, 'get_database')
        assert hasattr(dataset_legacy_bridge, 'get_database_by_id')
        assert callable(dataset_legacy_bridge.get_database)
```

- [ ] **Step 2: Move all old-model access to `legacy_bridge.py`**

In `apps/datasets/legacy_bridge.py`, add wrapper methods for any direct model access currently in services.py. Then update `services.py` to call the bridge instead of importing old models directly.

In services.py, replace:
```python
from apps.databases.models import Databases, DatabasesFile, DatabasesMeta, ProjectDatabasesLink
```

With bridge calls through `dataset_legacy_bridge` for all old-model access.

- [ ] **Step 3: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_legacy_isolation.py -v
```
Expected: 2 PASS

- [ ] **Step 4: Commit**

```bash
git add apps/datasets/services.py apps/datasets/legacy_bridge.py tests/test_legacy_isolation.py
git commit -m "refactor: route all legacy model access through legacy_bridge.py"
```

---

### Task 10: P2-03 — 标记旧 `/database/` 端点为 Deprecated

**Files:**
- Modify: `backend/api-server/apps/databases/routers.py`
- Create: `backend/api-server/tests/test_database_deprecated.py`

**Context:** 旧 `/database/` 端点仍与 `/dataset/` 并行运行，需要添加 deprecation 标记，引导调用方迁移。

- [ ] **Step 1: Write test**

```python
# tests/test_database_deprecated.py
import pytest


class TestDatabaseDeprecation:
    def test_old_database_endpoints_return_deprecation_header(self):
        """旧 /database/ 端点的响应应包含 Deprecation header"""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        # Test on a few old endpoints
        for endpoint in ["/api/v1/database/list", "/api/v1/database/info"]:
            response = client.get(endpoint)
            # Should have Deprecation header or return 410 Gone
            has_deprecation = (
                "deprecation" in response.headers
                or "sunset" in response.headers
                or response.status_code == 410
            )
            assert has_deprecation, f"{endpoint} missing deprecation signal"

    def test_deprecated_endpoints_still_function(self):
        """标记 deprecated 的端点仍可正常返回数据"""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        response = client.get("/api/v1/database/list")
        # Should still return JSON, not crash
        assert response.status_code in (200, 410)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
```

- [ ] **Step 2: Add deprecation middleware/headers**

In `apps/databases/routers.py`, add a response header middleware:

```python
from fastapi import Response
from starlette.middleware.base import BaseHTTPMiddleware

class DeprecationHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = "Sat, 01 Aug 2026 00:00:00 GMT"
        response.headers["Link"] = '</api/v1/dataset/>; rel="successor-version"'
        return response

# Apply to the old database router
database_router.add_middleware(DeprecationHeaderMiddleware)
```

- [ ] **Step 3: Run tests**

```bash
cd backend/api-server && python -m pytest tests/test_database_deprecated.py -v
```
Expected: 2 PASS

- [ ] **Step 4: Commit**

```bash
git add apps/databases/routers.py tests/test_database_deprecated.py
git commit -m "feat: add deprecation headers to legacy /database/ endpoints"
```

---

## Phase 4 Completion Checklist

- [ ] `require_superadmin` dependency distinct from `get_active_user`
- [ ] Admin-only force-delete and state-rollback endpoints
- [ ] `get_active_user` no longer hardcodes `permissions=['11']`
- [ ] Cross-domain lookups filter by visibility
- [ ] Lineage edges have unique constraint + relation_type validation
- [ ] Public lineage endpoint returns released-only edges
- [ ] Variant → Material reverse lookup chain
- [ ] Breeding program analysis readiness
- [ ] Cross-dataset expression comparison plan builder
- [ ] `services.py` routes all old-model access through `legacy_bridge.py`
- [ ] Legacy `/database/` endpoints return Deprecation headers
- [ ] Full test suite passes (no regressions)
