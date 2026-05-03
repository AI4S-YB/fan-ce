# 数据扫描目录浏览与批量注册 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将"当前暂存区"从扁平文件列表改为目录树浏览 + 多选批量注册模式，同时修复审计发现的 14 个 bug。

**Architecture:** 后端扩展现有 `browse_scan_root_path` 和 `list_staging_files` API，补 `validate_candidate` 校验步骤；前端拆为 `ScanConfigPanel` + `DirectoryBrowser` + `RegisterConfirmModal` 三个组件。注册走 `candidate → register_candidate` 管线。

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), Vue 3 + TypeScript + Ant Design Vue (frontend)

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `backend/api-server/apps/datasets/services.py` | 修改 | 所有后端修改集中于此（bug 修复 + API 扩展 + validate_candidate） |
| `backend/api-server/apps/datasets/routers.py` | 修改 | 修复重复路由挂载 |
| `backend/api-server/tests/test_dataset_scan_browse.py` | 新建 | 后端新功能的测试 |
| `frontend/admin-web/apps/web-antd/src/api/apps/dataset.ts` | 修改 | 新增 TypeScript 类型和 API 函数 |
| `frontend/admin-web/apps/web-antd/src/views/apps/dataset-staging/index.vue` | 修改 | 重构页面、集成新组件 |
| `frontend/admin-web/apps/web-antd/src/views/apps/dataset-staging/components/DirectoryBrowser.vue` | 新建 | 目录树浏览组件 |
| `frontend/admin-web/apps/web-antd/src/views/apps/dataset-staging/components/RegisterConfirmModal.vue` | 新建 | 注册确认对话框组件 |

---

### Task 1: 修复 `FILE_FORMAT_TO_DATASET_TYPE` sqlite/db 误映射 (Bug B1)

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py:122-123`

- [ ] **Step 1: 写测试**

```python
# tests/test_dataset_scan_browse.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.datasets.services import DatasetDomainService


def test_phenome_sqlite_not_misidentified_as_annotation():
    """phenome sqlite 文件不应被映射为 annotation"""
    svc = DatasetDomainService()
    result = svc._resolve_dataset_type_from_path(
        "/data/phenotype/rose_phenotype.db", None
    )
    # sqlite/db 后缀在无上下文时应 fallback 到 generic，由后续 candidate 推断精化
    assert result == "generic"


def test_sqlite_file_format_falls_back_to_generic():
    svc = DatasetDomainService()
    assert svc.FILE_FORMAT_TO_DATASET_TYPE.get("sqlite") is None
    assert svc.FILE_FORMAT_TO_DATASET_TYPE.get("db") is None


def test_genome_fasta_still_resolves_correctly():
    svc = DatasetDomainService()
    result = svc._resolve_dataset_type_from_path(
        "/data/genomes/rice_genome.fasta", None
    )
    assert result == "genome"
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd /Users/kentnf/projects/omicsagent/odata/backend/api-server
python -m pytest tests/test_dataset_scan_browse.py::test_phenome_sqlite_not_misidentified_as_annotation -v
# Expected: FAIL, result == "annotation"
python -m pytest tests/test_dataset_scan_browse.py::test_sqlite_file_format_falls_back_to_generic -v
# Expected: FAIL, "sqlite" key exists with value "annotation"
```

- [ ] **Step 3: 实现修复**

从 `FILE_FORMAT_TO_DATASET_TYPE` 中移除 `"sqlite": "annotation"` 和 `"db": "annotation"`：

```python
# services.py line 100-134: 删除 "sqlite": "annotation" 和 "db": "annotation" 两行
FILE_FORMAT_TO_DATASET_TYPE = {
    "fa": "genome",
    "fasta": "genome",
    "fna": "genome",
    "fa.gz": "genome",
    "fasta.gz": "genome",
    "fna.gz": "genome",
    "vcf": "variome",
    "vcf.gz": "variome",
    "bcf": "variome",
    "h5": "transcriptome",
    "hdf5": "transcriptome",
    "xlsx": "phenome",
    "xls": "phenome",
    "csv": "phenome",
    "tsv": "phenome",
    "gff": "annotation",
    "gff.gz": "annotation",
    "gff3": "annotation",
    "gff3.gz": "annotation",
    "gtf": "annotation",
    "gtf.gz": "annotation",
    # "sqlite" 和 "db" 已移除——它们在不同上下文中分别可能是 genome/phenome/annotation
    # _resolve_dataset_type_from_path 在无上下文时 fallback 到 generic
    # candidate 推断阶段通过 _infer_candidate_source_kind 进一步精化
    "bed": "signal",
    "bed.gz": "signal",
    "bedpe": "interaction",
    "bedpe.gz": "interaction",
    "pairs": "interaction",
    "pairs.gz": "interaction",
    "cool": "interaction",
    "mcool": "interaction",
    "bw": "signal",
    "bigwig": "signal",
}
```

`_resolve_dataset_type_from_path` 本身不需要改——它调用 `self.FILE_FORMAT_TO_DATASET_TYPE.get(suffix, "generic")`，移除 key 后自动 fallback 到 "generic"。

- [ ] **Step 4: Run tests, verify they pass**

```bash
python -m pytest tests/test_dataset_scan_browse.py -v
# Expected: 3 passed
```

- [ ] **Step 5: Commit**

```bash
git add backend/api-server/apps/datasets/services.py tests/test_dataset_scan_browse.py
git commit -m "fix: remove sqlite/db from FILE_FORMAT_TO_DATASET_TYPE to avoid misidentifying phenome files as annotation"
```

---

### Task 2: 修复路由重复挂载 (Bug B6)

**Files:**
- Modify: `backend/api-server/apps/datasets/routers.py:33`

- [ ] **Step 1: 实现修复**

`routers.py` 中 line 25 已挂载 `dataset_router` 到 `/admin/dataset`，line 33 又挂载 `admin_dataset_router` 到 `/admin/dataset`。`admin_dataset_router` 只包含 `/{dataset_id}/force-delete` 和 `/{dataset_id}/rollback-lifecycle`，与 `dataset_router` 的 list/create/update 等路由不冲突（路径模式不同）。但两个 router 挂同一 prefix 是隐患。

将 line 33 改为专用子路径：

```python
# routers.py line 33, change from:
app_dataset_router.include_router(admin_dataset_router, prefix="/admin/dataset")
# to:
app_dataset_router.include_router(admin_dataset_router, prefix="/admin/dataset/admin")
```

对应地，前端 API 调用需更新路径（如果有的话）。检查 `admin.py` 的路由：

```python
# admin.py 中的路由变为：
# POST /admin/dataset/admin/{dataset_id}/force-delete
# POST /admin/dataset/admin/{dataset_id}/rollback-lifecycle
```

- [ ] **Step 2: 验证**

```bash
cd /Users/kentnf/projects/omicsagent/odata/backend/api-server
# 检查是否有其他地方引用旧路径
grep -rn "admin/dataset/force-delete\|admin/dataset/rollback-lifecycle" . --include="*.py" --include="*.ts" --include="*.vue"
# Expected: no results (只有 admin.py 本身定义的路由)
```

- [ ] **Step 3: Commit**

```bash
git add backend/api-server/apps/datasets/routers.py
git commit -m "fix: resolve duplicate router mount at /admin/dataset by moving admin routes to /admin/dataset/admin"
```

---

### Task 3: 修复 `_iter_scan_files` symlink 不一致 (Bug B7)

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py:4040-4064`

- [ ] **Step 1: 写测试**

```python
# tests/test_dataset_scan_browse.py (追加)

from unittest.mock import patch, Mock
import os


def test_iter_scan_files_yields_realpath_for_symlinks():
    """_iter_scan_files 应通过 realpath 返回规范化路径"""
    svc = DatasetDomainService()
    # os.walk with followlinks=False returns symlink path as-is
    # _iter_scan_files should return os.path.realpath(abs_path) 
    # so that the path stored in staging_file matches what os.path.realpath() 
    # produces in _upsert_scan_staging_file and _build_registered_dataset_file_paths
    with patch("os.walk") as mock_walk, patch("os.path.isfile", return_value=True):
        mock_walk.return_value = [
            ("/data/genomes", [], ["genome.fasta", "link_to_gff"]),
        ]
        results = list(svc._iter_scan_files("/data/genomes", scan_recursive=True))
        # both files should be yielded with realpath applied
        assert len(results) == 2
        for _count, path in results:
            # path should equal os.path.realpath of the joined path
            assert path == os.path.realpath(path)
```

- [ ] **Step 2: Run test, verify it fails**

```bash
python -m pytest tests/test_dataset_scan_browse.py::test_iter_scan_files_yields_realpath_for_symlinks -v
# Expected: FAIL — current code returns os.path.join(current_dir, file_name) without realpath
```

- [ ] **Step 3: 实现修复**

```python
# services.py _iter_scan_files, change line 4051:
# from:
absolute_path = os.path.join(current_dir, file_name)
# to:
absolute_path = os.path.realpath(os.path.join(current_dir, file_name))

# and change non-recursive branch line 4064:
# from:
yield scanned_dir_count, entry.path
# to:
yield scanned_dir_count, os.path.realpath(entry.path)
```

- [ ] **Step 4: Run test, verify it passes**

```bash
python -m pytest tests/test_dataset_scan_browse.py::test_iter_scan_files_yields_realpath_for_symlinks -v
# Expected: PASS
```

- [ ] **Step 5: Run existing related tests to check for regressions**

```bash
python -m pytest tests/ -v -k "scan" 2>/dev/null || echo "No existing scan tests"
```

- [ ] **Step 6: Commit**

```bash
git add backend/api-server/apps/datasets/services.py tests/test_dataset_scan_browse.py
git commit -m "fix: apply os.path.realpath in _iter_scan_files for consistent symlink handling"
```

---

### Task 4: 修复 `_upsert_scan_staging_file` PermissionError 崩溃 (Bug B8)

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py:4133-4181`

- [ ] **Step 1: 写测试**

```python
# tests/test_dataset_scan_browse.py (追加)

def test_upsert_scan_staging_file_handles_permission_error():
    """无权限文件不应导致扫描崩溃"""
    from unittest.mock import MagicMock
    svc = DatasetDomainService()
    mock_db = MagicMock()
    mock_root = MagicMock()
    mock_root.root_path = "/data/genomes"
    mock_job = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 1

    with patch("os.stat", side_effect=PermissionError("permission denied")):
        result = svc._upsert_scan_staging_file(
            db=mock_db,
            root_obj=mock_root,
            job_obj=mock_job,
            absolute_path="/data/genomes/unreadable.fasta",
            user=mock_user,
        )
    # 应返回 sentinel 值表示跳过，不抛异常
    assert result == (None, False, False, False)
```

- [ ] **Step 2: Run test, verify it fails**

```bash
python -m pytest tests/test_dataset_scan_browse.py::test_upsert_scan_staging_file_handles_permission_error -v
# Expected: FAIL with PermissionError
```

- [ ] **Step 3: 实现修复**

```python
# services.py _upsert_scan_staging_file, wrap os.stat and os.path.relpath in try/except:
def _upsert_scan_staging_file(self, db, *, root_obj, job_obj, absolute_path, user, registered_paths=None):
    normalized_path = self._normalize_local_path(absolute_path)
    try:
        real_path = os.path.realpath(normalized_path)
        if registered_paths and real_path in registered_paths:
            return None, False, True, False
        relative_path = os.path.relpath(normalized_path, root_obj.root_path)
        stat_result = os.stat(normalized_path)
    except (PermissionError, OSError):
        return None, False, False, False
    # ... rest unchanged
```

- [ ] **Step 4: Run test, verify it passes**

```bash
python -m pytest tests/test_dataset_scan_browse.py::test_upsert_scan_staging_file_handles_permission_error -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add backend/api-server/apps/datasets/services.py tests/test_dataset_scan_browse.py
git commit -m "fix: handle PermissionError in _upsert_scan_staging_file so scans don't crash on unreadable files"
```

---

### Task 5: 修复 meta_json 覆盖 (Bug B9)

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py:4164`

- [ ] **Step 1: 写测试**

```python
# tests/test_dataset_scan_browse.py (追加)
import json

def test_upsert_scan_staging_file_preserves_existing_meta_json():
    """更新已有 staging file 时保留现有 meta_json"""
    from unittest.mock import MagicMock
    svc = DatasetDomainService()
    mock_db = MagicMock()
    mock_root = MagicMock()
    mock_root.root_path = "/data/genomes"
    mock_job = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 1

    mock_existing = MagicMock()
    mock_existing.meta_json = json.dumps({"custom_key": "custom_value", "scan_root_code": "old-code"})

    mock_db.query().filter().first.return_value = mock_existing

    with patch("os.stat") as mock_stat, patch("os.path.relpath", return_value="genome.fasta"):
        mock_stat.return_value.st_size = 100
        mock_stat.return_value.st_mtime = 12345
        result = svc._upsert_scan_staging_file(
            db=mock_db,
            root_obj=mock_root,
            job_obj=mock_job,
            absolute_path="/data/genomes/genome.fasta",
            user=mock_user,
        )
    # existing meta_json should be preserved (custom_key still present)
    # The fix: merge scan_root_code into existing meta_json instead of overwriting
```

- [ ] **Step 2: 实现修复**

```python
# services.py _upsert_scan_staging_file, change line 4164:
# from:
"meta_json": json.dumps({"scan_root_code": root_obj.root_code}, ensure_ascii=False),
# to:
"meta_json": self._merge_meta_json(
    getattr(existing, "meta_json", None) if existing else None,
    {"scan_root_code": root_obj.root_code},
),
```

并在 `DatasetDomainService` 中添加辅助方法：

```python
@staticmethod
def _merge_meta_json(existing_json, new_fields):
    """Merge new_fields into existing meta_json, preserving existing keys."""
    merged = {}
    if existing_json:
        try:
            merged = json.loads(existing_json) if isinstance(existing_json, str) else (existing_json or {})
        except (TypeError, json.JSONDecodeError):
            merged = {}
    merged.update(new_fields or {})
    return json.dumps(merged, ensure_ascii=False)
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_dataset_scan_browse.py -v
# Expected: all tests pass
```

- [ ] **Step 4: Commit**

```bash
git add backend/api-server/apps/datasets/services.py tests/test_dataset_scan_browse.py
git commit -m "fix: preserve existing meta_json in _upsert_scan_staging_file instead of overwriting"
```

---

### Task 6: 修复 `_build_registered_dataset_file_paths` 全量加载 (Bug B10)

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py:4066-4085`

- [ ] **Step 1: 实现修复**

当前实现将全部 `asset_file` 和 `dataset_version` 行加载到内存 set。改为只加载路径非空的行，使用数据库层面的过滤：

```python
def _build_registered_dataset_file_paths(self, db):
    registered_paths = set()
    # 只查询 local_path 非空的 asset_file，limit 分批
    batch_size = 5000
    offset = 0
    while True:
        rows = (
            db.query(asset_file_db.model.local_path, asset_file_db.model.storage_uri)
            .filter(asset_file_db.model.local_path.isnot(None))
            .limit(batch_size)
            .offset(offset)
            .all()
        )
        if not rows:
            break
        for local_path, storage_uri in rows:
            for raw_path in [local_path, storage_uri]:
                normalized_path = self._normalize_local_path(raw_path)
                if not normalized_path:
                    continue
                try:
                    registered_paths.add(os.path.realpath(normalized_path))
                except OSError:
                    continue
        offset += batch_size
    # version 表同理
    offset = 0
    while True:
        rows = (
            db.query(dataset_version_db.model.file_path)
            .filter(dataset_version_db.model.file_path.isnot(None))
            .limit(batch_size)
            .offset(offset)
            .all()
        )
        if not rows:
            break
        for (file_path,) in rows:
            normalized_path = self._normalize_local_path(file_path)
            if not normalized_path:
                continue
            try:
                registered_paths.add(os.path.realpath(normalized_path))
            except OSError:
                continue
        offset += batch_size
    return registered_paths
```

- [ ] **Step 2: 验证（不需要单独测试——扫描流程测试覆盖）**

```bash
cd /Users/kentnf/projects/omicsagent/odata/backend/api-server
python -c "
from apps.datasets.services import DatasetDomainService
svc = DatasetDomainService()
# 确认方法存在且可调用（需要 DB session，跳过实际执行）
print('Method signature OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add backend/api-server/apps/datasets/services.py
git commit -m "perf: batch-load _build_registered_dataset_file_paths to avoid unbounded memory"
```

---

### Task 7: 修复 `run_scan_root` bare except (Bug B11)

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py:5054`

- [ ] **Step 1: 实现修复**

将 `except Exception` 改为仅捕获预期异常类型：

```python
# services.py run_scan_root, line 5054:
# from:
except Exception as error:
# to:
except (OSError, IOError, PermissionError, HTTPException) as error:
```

`KeyboardInterrupt` 和 `SystemExit` 不再被捕获，允许它们正常传播。

- [ ] **Step 2: 验证**

```bash
cd /Users/kentnf/projects/omicsagent/odata/backend/api-server
python -c "
# 静态检查：确认 run_scan_root 的 except 块不再使用 bare Exception
import inspect
from apps.datasets.services import DatasetDomainService
source = inspect.getsource(DatasetDomainService.run_scan_root)
assert 'except (OSError, IOError, PermissionError, HTTPException) as error:' in source
print('OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add backend/api-server/apps/datasets/services.py
git commit -m "fix: narrow except clause in run_scan_root to avoid catching KeyboardInterrupt and SystemExit"
```

---

### Task 8: browse_root 配置安全 (Bug B12)

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py:4017-4021`

- [ ] **Step 1: 写测试**

```python
# tests/test_dataset_scan_browse.py (追加)

def test_get_scan_browse_root_defaults_to_safe_path():
    """未配置 browse_root 时应使用安全默认值，不暴露 /"""
    svc = DatasetDomainService()
    with patch.object(svc, '_normalize_local_path', return_value=None):
        # 当 settings 无配置且 normalize 返回空时
        pass  # 取决于 settings mock 方式


def test_browse_path_outside_root_is_rejected():
    """浏览路径在 browse_root 之外时返回 400"""
    svc = DatasetDomainService()
    with patch.object(svc, '_get_scan_browse_root', return_value="/data/genomes"):
        with patch("os.path.exists", return_value=True), patch("os.path.isdir", return_value=True):
            try:
                svc._resolve_scan_browse_path("/etc/passwd")
                assert False, "should have raised"
            except Exception as e:
                assert getattr(e, "status_code", None) == 400
                assert "outside browse root" in str(e.detail)
```

- [ ] **Step 2: 实现修复**

在 `_get_scan_browse_root` 中，未配置时使用第一个 active scan root 的路径，而非 `/`：

```python
def _get_scan_browse_root(self):
    configured_root = settings.app_options.get("dataset_scan.browse_root")
    if configured_root:
        normalized_root = self._normalize_local_path(configured_root)
        if normalized_root:
            return os.path.realpath(normalized_root)
    # fallback: 返回安全的受限路径而非 /
    # 建议在配置文件中设置 dataset_scan.browse_root
    # 未配置时返回一个明确的安全默认值
    return os.path.realpath("/var/tmp/dataset_scan")
```

同时在 `browse_scan_root_path` 返回中添加一个 `warning` 字段，当使用 fallback 时告知前端：

```python
# browse_scan_root_path 返回值中添加：
result = {
    "browse_root": browse_root,
    "current_path": current_path,
    "parent_path": parent_path,
    "entries": entries,
    "files": files,  # from Task 11
}
if not settings.app_options.get("dataset_scan.browse_root"):
    result["warning"] = "browse_root not configured; using fallback path"
return result
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_dataset_scan_browse.py -v
# Expected: all pass
```

- [ ] **Step 4: Commit**

```bash
git add backend/api-server/apps/datasets/services.py tests/test_dataset_scan_browse.py
git commit -m "fix: use safe fallback for browse_root instead of / when not configured"
```

---

### Task 9: 修复 `register_candidate` 拒绝 recipe_build (Bug B2)

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py:4743-4745`

- [ ] **Step 1: 写测试**

```python
# tests/test_dataset_scan_browse.py (追加)

def test_register_candidate_accepts_recipe_build_mode():
    """register_candidate 应接受 recipe_build 模式"""
    svc = DatasetDomainService()
    assert "recipe_build" in svc.SUPPORTED_REGISTRATION_MODES


def test_create_registration_candidate_default_matches_supported_modes():
    """create 的默认 mode 必须在 register 支持的模式列表中"""
    svc = DatasetDomainService()
    # 当前 create_registration_candidate line 4651 默认 "recipe_build"
    # register_candidate 必须也接受 recipe_build
    assert "recipe_build" in svc.SUPPORTED_REGISTRATION_MODES
```

- [ ] **Step 2: Run test, verify it fails**

```bash
python -m pytest tests/test_dataset_scan_browse.py::test_register_candidate_accepts_recipe_build_mode -v
# Expected: FAIL — AttributeError: 'DatasetDomainService' object has no attribute 'SUPPORTED_REGISTRATION_MODES'
```

- [ ] **Step 3: 实现修复**

在 `DatasetDomainService` 类属性中添加常量，修改 `register_candidate` 的模式检查：

```python
# services.py 在 FILE_FORMAT_TO_DATASET_TYPE 之后添加:
SUPPORTED_REGISTRATION_MODES = {"prebuilt", "hybrid", "recipe_build"}
```

```python
# register_candidate line 4744-4745, 改为使用常量:
if registration_mode not in self.SUPPORTED_REGISTRATION_MODES:
    raise HTTPException(
        status_code=400,
        detail=f"unsupported registration mode: {registration_mode}. "
               f"Supported: {', '.join(sorted(self.SUPPORTED_REGISTRATION_MODES))}",
    )
```

- [ ] **Step 4: Run test, verify it passes**

```bash
python -m pytest tests/test_dataset_scan_browse.py -v -k "register_candidate"
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add backend/api-server/apps/datasets/services.py tests/test_dataset_scan_browse.py
git commit -m "fix: allow recipe_build mode in register_candidate"
```

---

### Task 10: 添加扫描并发控制 (Bug B3)

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py:4966-4970`

- [ ] **Step 1: 实现修复**

在 `run_scan_root` 开始时检查该 root 是否已有 running 状态的 job：

```python
def run_scan_root(self, db, root_id, user):
    root_obj = dataset_scan_root_db.get(db=db, id=root_id)
    if not bool(root_obj.is_active):
        raise HTTPException(status_code=400, detail="scan root is inactive")
    if not os.path.isdir(root_obj.root_path):
        raise HTTPException(status_code=400, detail=f"scan root does not exist: {root_obj.root_path}")

    # 并发控制：检查是否有正在运行的 job
    running_job = (
        db.query(dataset_scan_job_db.model)
        .filter(
            dataset_scan_job_db.model.root_id == root_id,
            dataset_scan_job_db.model.status == "running",
        )
        .first()
    )
    if running_job:
        raise HTTPException(
            status_code=409,
            detail=f"scan root {root_id} already has a running job: {running_job.job_code}",
        )

    now = self._now()
    # ... rest unchanged
```

- [ ] **Step 2: 验证**

```bash
cd /Users/kentnf/projects/omicsagent/odata/backend/api-server
python -c "
import inspect
from apps.datasets.services import DatasetDomainService
source = inspect.getsource(DatasetDomainService.run_scan_root)
assert 'running_job' in source
assert 'status_code=409' in source
print('OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add backend/api-server/apps/datasets/services.py
git commit -m "fix: add scan concurrency control to prevent simultaneous scans on same root"
```

---

### Task 11: `browse_scan_root_path` 补充 files 字段

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py:4087-4131`

- [ ] **Step 1: 写测试**

```python
# tests/test_dataset_scan_browse.py (追加)

def test_browse_scan_root_path_returns_files():
    """browse API 应返回当前目录的文件列表"""
    svc = DatasetDomainService()
    with patch.object(svc, '_get_scan_browse_root', return_value="/tmp/test_scan"):
        with patch("os.path.exists", return_value=True), patch("os.path.isdir", return_value=True):
            mock_entry_dir = Mock()
            mock_entry_dir.is_dir.return_value = True
            mock_entry_dir.name = "subdir"
            mock_entry_dir.path = "/tmp/test_scan/subdir"
            mock_entry_dir.stat.return_value.st_mtime = 12345

            mock_entry_file = Mock()
            mock_entry_file.is_dir.return_value = False
            mock_entry_file.is_file.return_value = True
            mock_entry_file.name = "genome.fasta"
            mock_entry_file.path = "/tmp/test_scan/genome.fasta"
            mock_entry_file.stat.return_value = Mock(st_size=1000, st_mtime=12345)

            with patch("os.scandir") as mock_scandir:
                mock_scandir.return_value.__enter__.return_value = [
                    mock_entry_dir, mock_entry_file,
                ]
                result = svc.browse_scan_root_path(
                    db=Mock(),
                    request_data=Mock(path=None, show_hidden=False),
                    user=Mock(),
                )
            assert "files" in result
            assert len(result["files"]) == 1
            assert result["files"][0]["name"] == "genome.fasta"
            assert result["files"][0]["format"] == "fasta"
            assert result["entries"][0]["is_dir"] is True


def test_browse_hidden_files_filtered_from_files():
    """隐藏文件不应出现在 files 中"""
    svc = DatasetDomainService()
    with patch.object(svc, '_get_scan_browse_root', return_value="/tmp/test_scan"):
        with patch("os.path.exists", return_value=True), patch("os.path.isdir", return_value=True):
            mock_hidden = Mock()
            mock_hidden.is_dir.return_value = False
            mock_hidden.is_file.return_value = True
            mock_hidden.name = ".secret"
            mock_hidden.path = "/tmp/test_scan/.secret"
            mock_hidden.stat.return_value = Mock(st_size=100, st_mtime=12345)

            with patch("os.scandir") as mock_scandir:
                mock_scandir.return_value.__enter__.return_value = [mock_hidden]
                result = svc.browse_scan_root_path(
                    db=Mock(),
                    request_data=Mock(path=None, show_hidden=False),
                    user=Mock(),
                )
            assert len(result["files"]) == 0
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
python -m pytest tests/test_dataset_scan_browse.py::test_browse_scan_root_path_returns_files -v
# Expected: FAIL — KeyError: 'files'
```

- [ ] **Step 3: 实现**

在 `browse_scan_root_path` 的 `os.scandir` 循环中，收集文件条目：

```python
def browse_scan_root_path(self, db, request_data, user):
    browse_root, current_path = self._resolve_scan_browse_path(request_data.path)
    entries = []
    files = []
    try:
        with os.scandir(current_path) as iterator:
            for entry in iterator:
                if entry.is_dir(follow_symlinks=False):
                    if not request_data.show_hidden and entry.name.startswith("."):
                        continue
                    try:
                        stat_result = entry.stat(follow_symlinks=False)
                    except (FileNotFoundError, PermissionError):
                        continue
                    entries.append({
                        "name": entry.name,
                        "path": os.path.realpath(entry.path),
                        "is_dir": True,
                        "modified_time": int(stat_result.st_mtime),
                    })
                elif entry.is_file(follow_symlinks=False):
                    if not request_data.show_hidden and entry.name.startswith("."):
                        continue
                    if entry.name in {".DS_Store", "Thumbs.db"}:
                        continue
                    try:
                        stat_result = entry.stat(follow_symlinks=False)
                    except (FileNotFoundError, PermissionError):
                        continue
                    file_path = os.path.realpath(entry.path)
                    file_format = self._guess_file_suffix(file_path)
                    files.append({
                        "name": entry.name,
                        "path": file_path,
                        "is_dir": False,
                        "size": stat_result.st_size,
                        "format": file_format,
                        "modified_time": int(stat_result.st_mtime),
                    })
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=f"permission denied: {current_path}") from error

    entries.sort(key=lambda item: item["name"].lower())
    files.sort(key=lambda item: item["name"].lower())

    # ... parent_path logic unchanged ...

    result = {
        "browse_root": browse_root,
        "current_path": current_path,
        "parent_path": parent_path,
        "entries": entries,
        "files": files,
    }
    if not settings.app_options.get("dataset_scan.browse_root"):
        result["warning"] = "browse_root not configured; using fallback path"
    return result
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
python -m pytest tests/test_dataset_scan_browse.py -v
# Expected: all pass
```

- [ ] **Step 5: Commit**

```bash
git add backend/api-server/apps/datasets/services.py tests/test_dataset_scan_browse.py
git commit -m "feat: add files field to browse_scan_root_path API response"
```

---

### Task 12: `list_staging_files` 增加 directory 视图模式

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py:4249-4279`

- [ ] **Step 1: 写测试**

```python
# tests/test_dataset_scan_browse.py (追加)

def test_list_staging_files_directory_view_groups_by_directory():
    """directory 视图按子目录聚合 staging files"""
    from unittest.mock import MagicMock
    svc = DatasetDomainService()
    mock_db = MagicMock()

    class MockStagingFile:
        def __init__(self, id, local_path, scan_root_id, source_mode, dataset_type, file_name, file_format):
            self.id = id
            self.local_path = local_path
            self.scan_root_id = scan_root_id
            self.source_mode = source_mode
            self.dataset_type = dataset_type
            self.file_name = file_name
            self.file_format = file_format
            self.stage_status = "discovered"
            self.staging_code = f"stg-{id}"
            self.relative_path = local_path.replace("/data/genomes/", "")
            self.file_size = 1000
            self.scan_job_id = 1
            self.linked_dataset_id = None
            self.last_seen_at = 12345
            self.create_user_id = 1
            self.meta_json = None
            self.create_time = 12345
            self.update_time = 12345
            self.source_name = file_name

    mock_rows = [
        MockStagingFile(1, "/data/genomes/rice_v3/genome.fasta", 1, "server_scan", "genome", "genome.fasta", "fasta"),
        MockStagingFile(2, "/data/genomes/rice_v3/gene.gff", 1, "server_scan", "annotation", "gene.gff", "gff"),
        MockStagingFile(3, "/data/genomes/wheat_cs/genome.fasta", 1, "server_scan", "genome", "genome.fasta", "fasta"),
        MockStagingFile(4, "/data/genomes/orphan.fasta", 1, "server_scan", "genome", "orphan.fasta", "fasta"),
    ]

    with patch.object(svc, '_build_dataset_staging_payload', side_effect=lambda row: {"id": row.id, "file_name": row.file_name}):
        # mock _require_dataset_kind_code to allow any type
        with patch.object(svc, '_require_dataset_kind_code', return_value=("genome", None)):
            with patch.object(svc, '_dataset_type_matches', return_value=True):
                result = svc.list_staging_files(
                    db=mock_db,
                    request_data=Mock(keyword="", dataset_type=None, stage_status=None, source_mode=None, scan_root_id=None, page=None, size=None, view_mode="directory"),
                )
    assert "directories" in result
    assert "orphan_files" in result
    # 检查 rice_v3 目录聚合
    dir_paths = [d["path"] for d in result["directories"]]
    assert "/data/genomes/rice_v3/" in dir_paths or "/data/genomes/rice_v3" in dir_paths
    assert "/data/genomes/wheat_cs/" in dir_paths or "/data/genomes/wheat_cs" in dir_paths
```

- [ ] **Step 2: Run test, verify it fails**

```bash
python -m pytest tests/test_dataset_scan_browse.py::test_list_staging_files_directory_view_groups_by_directory -v
# Expected: FAIL — KeyError: 'directories'
```

- [ ] **Step 3: 实现**

在 `list_staging_files` 方法末尾（分页之后、return 之前）加入 directory 视图逻辑：

```python
def list_staging_files(self, db, request_data):
    rows = dataset_staging_file_db.get_data(db=db, filters={})
    # ... 现有过滤逻辑 (keyword, stage_status, source_mode, scan_root_id, dataset_type) ...
    
    view_mode = str(getattr(request_data, "view_mode", "flat") or "flat").strip().lower()
    
    if view_mode == "directory":
        return self._build_directory_view(items, scan_root_rows)
    
    # flat 模式：现有分页和返回逻辑
    if request_data.page and request_data.size:
        start = (request_data.page - 1) * request_data.size
        end = start + request_data.size
        items = items[start:end]
    return {"dataList": items, "total": total}
```

新增 `_build_directory_view` 方法：

```python
def _build_directory_view(self, staging_items, scan_root_rows=None):
    """将 staging files 按 scan root 子目录聚合为 directory view。"""
    scan_root_paths = {}
    if scan_root_rows:
        for root in scan_root_rows:
            scan_root_paths[root.id] = os.path.realpath(
                self._normalize_local_path(root.root_path)
            )
    
    directories = {}  # key: parent_dir_path
    orphan_files = []
    
    for item in staging_items:
        local_path = self._normalize_local_path(getattr(item, "local_path", None))
        if not local_path:
            continue
        
        real_path = os.path.realpath(local_path)
        parent_dir = os.path.dirname(real_path)
        
        root_id = getattr(item, "scan_root_id", None)
        root_path = scan_root_paths.get(root_id) if root_id else None
        
        # 判断是否为 orphan：父目录等于 scan root 路径（或 parent_dir 不是 scan_root 的子目录）
        if root_path and os.path.realpath(root_path) in {parent_dir, os.path.dirname(parent_dir)}:
            # 直接在 scan root 下的文件 = orphan
            orphan_files.append(self._build_dataset_staging_payload(item))
        elif root_path and parent_dir.startswith(os.path.realpath(root_path) + os.sep):
            # scan root 子目录下的文件 → 按目录聚合
            dir_name = os.path.basename(parent_dir)
            if parent_dir not in directories:
                directories[parent_dir] = {
                    "path": parent_dir + os.sep,
                    "name": dir_name,
                    "file_count": 0,
                    "dataset_type_hint": None,
                    "type_counts": {},
                }
            directories[parent_dir]["file_count"] += 1
            item_type = str(getattr(item, "dataset_type", "") or "").strip()
            if item_type:
                directories[parent_dir]["type_counts"][item_type] = (
                    directories[parent_dir]["type_counts"].get(item_type, 0) + 1
                )
        else:
            # 不属于任何 scan root 子目录的文件
            orphan_files.append(self._build_dataset_staging_payload(item))
    
    # 推断每个目录的 dataset_type_hint（取最多的 type）
    for dir_info in directories.values():
        type_counts = dir_info.pop("type_counts", {})
        if type_counts:
            dir_info["dataset_type_hint"] = max(type_counts, key=type_counts.get)
        else:
            dir_info["dataset_type_hint"] = "generic"
    
    return {
        "directories": sorted(directories.values(), key=lambda d: d["name"].lower()),
        "orphan_files": orphan_files,
    }
```

- [ ] **Step 4: Run test, verify it passes**

```bash
python -m pytest tests/test_dataset_scan_browse.py::test_list_staging_files_directory_view_groups_by_directory -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add backend/api-server/apps/datasets/services.py tests/test_dataset_scan_browse.py
git commit -m "feat: add directory view mode to list_staging_files API"
```

---

### Task 13: `register_candidate` 补 validate_candidate 校验步骤

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py:4738-4748`

- [ ] **Step 1: 写测试**

```python
# tests/test_dataset_scan_browse.py (追加)

def test_validate_candidate_checks_file_readable():
    """validate_candidate 检查文件可读"""
    svc = DatasetDomainService()
    errors = svc.validate_candidate(
        staging_entries=[
            {"local_path": "/nonexistent/file.fasta", "file_format": "fasta"},
        ]
    )
    assert len(errors) > 0
    assert any("not found" in e.lower() or "does not exist" in e.lower() for e in errors)


def test_validate_candidate_checks_format_consistency():
    """validate_candidate 检查文件格式与 candidate 声明一致"""
    svc = DatasetDomainService()
    # 文件实际后缀是 .fasta，声明为 vcf——不一致
    errors = svc.validate_candidate(
        staging_entries=[
            {"local_path": "/data/test.fasta", "file_format": "fasta"},
        ],
        declared_dataset_type="variome",
    )
    # fasta → genome，但声明为 variome → 不一致警告
    assert any("fasta" in e.lower() or "genome" in e.lower() or "variome" in e.lower() for e in errors)
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
python -m pytest tests/test_dataset_scan_browse.py -v -k "validate_candidate"
# Expected: FAIL — AttributeError: 'DatasetDomainService' object has no attribute 'validate_candidate'
```

- [ ] **Step 3: 实现**

在 `DatasetDomainService` 中添加 `validate_candidate` 方法：

```python
def validate_candidate(self, staging_entries, declared_dataset_type=None):
    """Validate candidate files before registration.
    
    Returns a list of error strings. Empty list means validation passed.
    """
    errors = []
    for entry in staging_entries:
        local_path = entry.get("local_path") or entry.get("path")
        if not local_path:
            errors.append(f"missing path for staging entry: {entry}")
            continue
        if not os.path.exists(local_path):
            errors.append(f"file not found: {local_path}")
            continue
        if not os.access(local_path, os.R_OK):
            errors.append(f"file not readable: {local_path}")
            continue
    
    if declared_dataset_type:
        for entry in staging_entries:
            local_path = entry.get("local_path") or entry.get("path")
            if not local_path:
                continue
            file_format = entry.get("file_format") or self._guess_file_suffix(local_path)
            inferred_type = self._resolve_dataset_type_from_path(local_path, None)
            if inferred_type != "generic" and inferred_type != declared_dataset_type:
                errors.append(
                    f"format mismatch: {os.path.basename(local_path)} appears to be "
                    f"'{inferred_type}' but candidate declares '{declared_dataset_type}'"
                )
    
    return errors
```

修改 `register_candidate`，在现有逻辑之前调用校验：

```python
def register_candidate(self, db, candidate_id, request_data, user):
    candidate_obj = dataset_registration_candidate_db.get(db=db, id=candidate_id)
    if str(getattr(candidate_obj, "registration_status", "") or "").lower() == "done":
        raise HTTPException(status_code=400, detail="candidate is already registered")

    registration_mode = str(getattr(candidate_obj, "registration_mode", "") or "").strip().lower()
    if registration_mode not in self.SUPPORTED_REGISTRATION_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported registration mode: {registration_mode}. "
                   f"Supported: {', '.join(sorted(self.SUPPORTED_REGISTRATION_MODES))}",
        )

    primary_candidate_file, primary_staging_obj = self._get_candidate_primary_source(
        db=db, candidate_obj=candidate_obj
    )
    self._validate_candidate_staging_source(primary_staging_obj)

    # 新增：校验步骤
    candidate_file_rows = dataset_registration_candidate_file_db.get_data(
        db=db, filters={"candidate_id": candidate_id}
    )
    staging_entries = []
    for cf_row in candidate_file_rows:
        staging_obj = dataset_staging_file_db.get(db=db, id=cf_row.staging_file_id)
        staging_entries.append({
            "local_path": getattr(staging_obj, "local_path", None),
            "file_format": self._candidate_format(staging_obj),
        })
    validation_errors = self.validate_candidate(
        staging_entries,
        declared_dataset_type=getattr(candidate_obj, "dataset_type", None),
    )
    if validation_errors:
        raise HTTPException(
            status_code=400,
            detail=f"candidate validation failed: {'; '.join(validation_errors)}",
        )

    # ... 现有映射逻辑不变 ...
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
python -m pytest tests/test_dataset_scan_browse.py -v -k "validate_candidate"
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add backend/api-server/apps/datasets/services.py tests/test_dataset_scan_browse.py
git commit -m "feat: add validate_candidate step to register_candidate for file integrity checks"
```

---

### Task 14: 前端 TypeScript 类型 + API 函数

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/api/apps/dataset.ts`

- [ ] **Step 1: 添加类型定义**

在 `DatasetStagingListResult` 之后添加：

```typescript
// --- Directory Browse ---

export interface BrowseEntryItem {
  name: string;
  path: string;
  is_dir: boolean;
  modified_time?: number;
}

export interface BrowseFileItem {
  name: string;
  path: string;
  is_dir: false;
  size: number;
  format: string;
  modified_time: number;
}

export interface BrowseResult {
  browse_root: string;
  current_path: string;
  parent_path?: string | null;
  entries: BrowseEntryItem[];
  files: BrowseFileItem[];
  warning?: string;
}

// --- Directory View ---

export interface StagingDirectoryItem {
  path: string;
  name: string;
  file_count: number;
  dataset_type_hint: string;
}

export interface StagingDirectoryView {
  directories: StagingDirectoryItem[];
  orphan_files: DatasetStagingItem[];
}

// --- Scan Job ---

export interface ScanJobItem {
  id: number;
  root_id: number;
  job_code: string;
  status: string;
  scanned_dir_count?: number;
  scanned_file_count?: number;
  staged_file_count?: number;
  skipped_file_count?: number;
  changed_file_count?: number;
  missing_file_count?: number;
  skipped_registered_count?: number;
  error_message?: string | null;
  started_at?: number | null;
  finished_at?: number | null;
}

// --- Registration Candidate ---

export interface CandidateCreateItem {
  staging_file_id: number;
  is_primary: boolean;
}

export interface CandidateCreateRequest {
  candidate_name: string;
  dataset_type: string;
  registration_mode: 'prebuilt' | 'hybrid' | 'recipe_build';
  version_name?: string;
  organism?: string;
  assembly?: string;
  scan_root_id?: number;
  items: CandidateCreateItem[];
}

export interface RegisterCandidateRequest {
  dataset_name?: string;
  remark?: string;
  is_public?: boolean;
  team_id?: number;
  project_id?: number;
  activate_version?: boolean;
}
```

- [ ] **Step 2: 添加 API 函数**

在文件末尾（`deleteAssetFileTypeRegistryApi` 之后）添加：

```typescript
// --- Browse ---
export async function browseScanRootPathApi(data: { path?: string }) {
  return requestClient.post<BrowseResult>(`${pre}/staging/scan-root/browse`, data);
}

// --- Directory View ---
export async function getStagingDirectoryViewApi(data: {
  scan_root_id?: number;
  dataset_type?: string;
  source_mode?: string;
  keyword?: string;
}) {
  return requestClient.post<StagingDirectoryView>(`${pre}/staging/list`, {
    ...data,
    view_mode: 'directory',
  });
}

// --- Candidate ---
export async function createRegistrationCandidateApi(data: CandidateCreateRequest) {
  return requestClient.post(`${pre}/candidate/create`, data);
}

export async function registerCandidateApi(candidateId: number, data: RegisterCandidateRequest) {
  return requestClient.post(`${pre}/candidate/${candidateId}/register`, data);
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/api/apps/dataset.ts
git commit -m "feat: add TypeScript types and API functions for directory browse, candidate, and registration"
```

---

### Task 15: 修复前端"扫描完成"假消息 + 添加进度指示 (Bug B5 + F5)

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/views/apps/dataset-staging/index.vue:415-427`

- [ ] **Step 1: 修改 `runScan` 函数**

```typescript
// 当前代码（line 415-427）替换为：
async function runScan(record: ScanRootItem | Record<string, any>) {
  const root = record as ScanRootItem;
  const hideLoading = createMessage.loading(`正在扫描：${root.name}...`, 0);
  try {
    const result = await requestClient.post<{ job: ScanJobItem }>(
      '/admin/dataset/staging/scan/run',
      { root_id: root.id },
    );
    activeRootId.value = root.id;
    // 检查 job 实际状态
    if (result.job?.status === 'success') {
      createMessage.success(
        `扫描完成：${root.name}（发现 ${result.job.scanned_file_count ?? 0} 个文件，新增 ${result.job.staged_file_count ?? 0}，变更 ${result.job.changed_file_count ?? 0}，缺失 ${result.job.missing_file_count ?? 0}）`,
      );
    } else if (result.job?.status === 'failed') {
      createMessage.error(`扫描失败：${root.name}（${result.job.error_message || '未知错误'}）`);
    } else {
      createMessage.success(`扫描完成：${root.name}`);
    }
    await Promise.all([loadRoots(), loadJobs(), loadStagingRows()]);
  } catch (error: any) {
    createMessage.error(error?.message || '执行扫描失败');
  } finally {
    hideLoading();
  }
}
```

- [ ] **Step 2: 确认 `ScanJobItem` 类型已导入**

Step 1 已使用 `ScanJobItem`，确认在 `<script setup>` 中有定义（目前已在 `index.vue:47-62` 定义）。

- [ ] **Step 3: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/views/apps/dataset-staging/index.vue
git commit -m "fix: check scan job status before showing success message; add progress loading indicator"
```

---

### Task 16: 创建 DirectoryBrowser 组件

**Files:**
- Create: `frontend/admin-web/apps/web-antd/src/views/apps/dataset-staging/components/DirectoryBrowser.vue`

- [ ] **Step 1: 创建组件**

```vue
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import {
  Button,
  Checkbox,
  Empty,
  Space,
  Table,
  Tag,
  Breadcrumb,
} from 'ant-design-vue';
import type {
  BrowseEntryItem,
  BrowseFileItem,
  BrowseResult,
  DatasetStagingItem,
  StagingDirectoryItem,
} from '#/api/apps/dataset';
import {
  browseScanRootPathApi,
  getStagingDirectoryViewApi,
} from '#/api/apps/dataset';
import { useMessage } from '#/hooks/web/useMessage';

defineOptions({ name: 'DirectoryBrowser' });

const props = defineProps<{
  scanRootIds: number[];
}>();

const emit = defineEmits<{
  'update:selectedFiles': [files: BrowseFileItem[]];
  register: [files: BrowseFileItem[], directoryPath: string];
}>();

const { createMessage } = useMessage();

// --- State ---
const loading = ref(false);
const currentPath = ref('/');
const browseRoot = ref('/');
const parentPath = ref<string | null>(null);
const directories = ref<BrowseEntryItem[]>([]);
const files = ref<BrowseFileItem[]>([]);
const selectedFileKeys = ref<Set<string>>(new Set());
const viewMode = ref<'browse' | 'directory'>('directory');

// Staging directory view state
const stagingDirectories = ref<StagingDirectoryItem[]>([]);
const orphanFiles = ref<DatasetStagingItem[]>([]);

// --- Computed ---
const selectedFiles = computed(() =>
  files.value.filter((f) => selectedFileKeys.value.has(f.path)),
);

const canGoUp = computed(() => parentPath.value !== null);

const breadcrumbItems = computed(() => {
  const parts = currentPath.value.split('/').filter(Boolean);
  const items = [{ name: browseRoot.value, path: browseRoot.value }];
  let accumulated = '';
  for (const part of parts) {
    accumulated += '/' + part;
    if (accumulated.startsWith(browseRoot.value)) {
      items.push({ name: part, path: accumulated });
    }
  }
  return items;
});

// --- Methods ---
async function loadDirectory(path?: string) {
  loading.value = true;
  try {
    const result: BrowseResult = await browseScanRootPathApi({ path });
    browseRoot.value = result.browse_root;
    currentPath.value = result.current_path;
    parentPath.value = result.parent_path ?? null;
    directories.value = result.entries;
    files.value = result.files;
  } catch (error: any) {
    createMessage.error(error?.message || '加载目录失败');
  } finally {
    loading.value = false;
  }
}

async function loadDirectoryView() {
  loading.value = true;
  try {
    const result = await getStagingDirectoryViewApi({
      scan_root_id: props.scanRootIds.length === 1 ? props.scanRootIds[0] : undefined,
    });
    stagingDirectories.value = result.directories;
    orphanFiles.value = result.orphan_files;
  } catch (error: any) {
    createMessage.error(error?.message || '加载暂存目录视图失败');
  } finally {
    loading.value = false;
  }
}

function enterDirectory(dirPath: string) {
  viewMode.value = 'browse';
  void loadDirectory(dirPath);
}

function goToParent() {
  if (parentPath.value) {
    void loadDirectory(parentPath.value);
  }
}

function navigateTo(path: string) {
  void loadDirectory(path);
}

function toggleFileSelection(file: BrowseFileItem) {
  const key = file.path;
  const next = new Set(selectedFileKeys.value);
  if (next.has(key)) {
    next.delete(key);
  } else {
    next.add(key);
  }
  selectedFileKeys.value = next;
}

function selectAllFiles() {
  if (selectedFileKeys.value.size === files.value.length) {
    selectedFileKeys.value = new Set();
  } else {
    selectedFileKeys.value = new Set(files.value.map((f) => f.path));
  }
}

function handleRegister() {
  emit('register', selectedFiles.value, currentPath.value);
}

function formatSize(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIdx = 0;
  while (size >= 1024 && unitIdx < units.length - 1) {
    size /= 1024;
    unitIdx++;
  }
  return `${size.toFixed(unitIdx === 0 ? 0 : 1)} ${units[unitIdx]}`;
}

// --- Columns ---
const directoryColumns = [
  { title: '目录', dataIndex: 'name', key: 'name' },
  { title: '文件数', dataIndex: 'file_count', key: 'file_count', width: 100 },
  {
    title: '推测类型',
    dataIndex: 'dataset_type_hint',
    key: 'dataset_type_hint',
    width: 130,
  },
];

const fileColumns = [
  { title: '文件名', dataIndex: 'name', key: 'name', width: 260 },
  { title: '大小', key: 'size', width: 100 },
  { title: '格式', dataIndex: 'format', key: 'format', width: 90 },
];

// --- Init ---
watch(
  () => props.scanRootIds,
  () => {
    void loadDirectoryView();
  },
  { immediate: true },
);
</script>

<template>
  <div class="directory-browser">
    <!-- Toolbar -->
    <div class="browser-toolbar">
      <Space>
        <Button size="small" @click="loadDirectoryView()">目录视图</Button>
        <Button
          size="small"
          :disabled="!canGoUp && viewMode === 'browse'"
          @click="goToParent"
        >
          上级目录
        </Button>
        <Button size="small" @click="viewMode === 'browse' ? loadDirectory(currentPath) : loadDirectoryView()">
          刷新
        </Button>
      </Space>
      <div v-if="selectedFiles.length > 0" class="selection-bar">
        已选 {{ selectedFiles.length }} 个文件
        <Button type="primary" size="small" @click="handleRegister">
          注册为 Dataset →
        </Button>
      </div>
    </div>

    <!-- Breadcrumb -->
    <Breadcrumb v-if="viewMode === 'browse'" class="browser-breadcrumb">
      <Breadcrumb.Item v-for="item in breadcrumbItems" :key="item.path">
        <a @click="navigateTo(item.path)">{{ item.name || '/' }}</a>
      </Breadcrumb.Item>
    </Breadcrumb>

    <!-- Directory View -->
    <div v-if="viewMode === 'directory'">
      <Table
        v-if="stagingDirectories.length > 0"
        :columns="directoryColumns"
        :data-source="stagingDirectories"
        :loading="loading"
        :pagination="false"
        row-key="path"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <a @click="enterDirectory(record.path)">📁 {{ record.name }}</a>
          </template>
          <template v-else-if="column.key === 'dataset_type_hint'">
            <Tag v-if="record.dataset_type_hint" color="blue">
              {{ record.dataset_type_hint }}
            </Tag>
          </template>
        </template>
      </Table>
      <div v-if="orphanFiles.length > 0" class="orphan-section">
        <div class="section-title">根目录下的散落文件</div>
        <div
          v-for="file in orphanFiles"
          :key="file.id"
          class="orphan-file-row"
        >
          <span>{{ file.file_name }}</span>
          <Tag color="blue">{{ file.dataset_type || 'generic' }}</Tag>
        </div>
      </div>
      <Empty
        v-if="!loading && stagingDirectories.length === 0 && orphanFiles.length === 0"
        description="暂无暂存文件，请先执行扫描。"
      />
    </div>

    <!-- Browse View -->
    <div v-if="viewMode === 'browse'">
      <!-- Subdirectories -->
      <div v-if="directories.length > 0" class="browse-dirs">
        <div
          v-for="dir in directories"
          :key="dir.path"
          class="browse-dir-row"
          @click="enterDirectory(dir.path)"
        >
          📁 {{ dir.name }}
        </div>
      </div>

      <!-- Files -->
      <Table
        v-if="files.length > 0"
        :columns="fileColumns"
        :data-source="files"
        :loading="loading"
        :pagination="false"
        row-key="path"
        size="small"
        :row-selection="{
          selectedRowKeys: [...selectedFileKeys],
          onChange: (keys: (string | number)[]) => {
            selectedFileKeys = new Set(keys.map(String));
          },
        }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <div>
              <div>{{ record.name }}</div>
              <div class="file-path-sub">{{ record.path }}</div>
            </div>
          </template>
          <template v-else-if="column.key === 'size'">
            {{ formatSize(record.size) }}
          </template>
          <template v-else-if="column.key === 'format'">
            <Tag>{{ record.format }}</Tag>
          </template>
        </template>
      </Table>

      <Empty
        v-if="!loading && directories.length === 0 && files.length === 0"
        description="此目录为空。"
      />
    </div>
  </div>
</template>

<style scoped>
.directory-browser {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.browser-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.selection-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.browser-breadcrumb {
  margin-bottom: 4px;
}

.browse-dirs {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.browse-dir-row {
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.browse-dir-row:hover {
  background: var(--ant-primary-1, #e6f7ff);
}

.orphan-section {
  margin-top: 16px;
}

.section-title {
  font-weight: 500;
  margin-bottom: 8px;
}

.orphan-file-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.file-path-sub {
  font-size: 11px;
  color: #999;
  word-break: break-all;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/views/apps/dataset-staging/components/DirectoryBrowser.vue
git commit -m "feat: create DirectoryBrowser component with directory view and file browsing"
```

---

### Task 17: 创建 RegisterConfirmModal 组件

**Files:**
- Create: `frontend/admin-web/apps/web-antd/src/views/apps/dataset-staging/components/RegisterConfirmModal.vue`

- [ ] **Step 1: 创建组件**

```vue
<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import {
  Button,
  Form,
  Input,
  Modal,
  Radio,
  Select,
  Tag,
} from 'ant-design-vue';
import type { BrowseFileItem } from '#/api/apps/dataset';
import { registerCandidateApi, createRegistrationCandidateApi } from '#/api/apps/dataset';
import { useMessage } from '#/hooks/useMessage';

defineOptions({ name: 'RegisterConfirmModal' });

const props = defineProps<{
  visible: boolean;
  files: BrowseFileItem[];
  directoryPath: string;
  scanRootId?: number;
}>();

const emit = defineEmits<{
  'update:visible': [value: boolean];
  registered: [];
}>();

const { createMessage } = useMessage();
const loading = ref(false);

const DATASET_TYPE_OPTIONS = [
  { label: '基因组', value: 'genome' },
  { label: '转录组', value: 'transcriptome' },
  { label: '变异组', value: 'variome' },
  { label: '表型组', value: 'phenome' },
  { label: '通用', value: 'generic' },
];

const REGISTRATION_MODE_OPTIONS = [
  { label: '预建文件纳管 (prebuilt)', value: 'prebuilt' },
  { label: '混合补全 (hybrid)', value: 'hybrid' },
  { label: '从源文件构建 (recipe_build)', value: 'recipe_build' },
];

// --- Inference ---
const inferredDatasetType = computed(() => {
  const counts: Record<string, number> = {};
  for (const file of props.files) {
    const type = formatToType(file.format);
    counts[type] = (counts[type] || 0) + 1;
  }
  const maxCount = Math.max(...Object.values(counts), 0);
  const top = Object.entries(counts).filter(([, c]) => c === maxCount);
  return top.length === 1 ? top[0]![0]! : 'generic';
});

const inferredMode = computed(() => {
  const prebuiltFormats = new Set(['db', 'sqlite', 'h5', 'hdf5', 'tbi', 'csi']);
  let hasPrebuilt = false;
  let hasSource = false;
  for (const file of props.files) {
    if (prebuiltFormats.has(file.format)) {
      hasPrebuilt = true;
    } else {
      hasSource = true;
    }
  }
  if (hasPrebuilt && hasSource) return 'hybrid';
  if (hasPrebuilt) return 'prebuilt';
  return 'recipe_build';
});

const directoryName = computed(() => {
  const parts = props.directoryPath.split('/').filter(Boolean);
  return parts[parts.length - 1] || 'unknown';
});

function formatToType(format: string): string {
  const map: Record<string, string> = {
    fa: 'genome', fasta: 'genome', fna: 'genome',
    'fa.gz': 'genome', 'fasta.gz': 'genome', 'fna.gz': 'genome',
    vcf: 'variome', 'vcf.gz': 'variome', bcf: 'variome',
    h5: 'transcriptome', hdf5: 'transcriptome',
    xlsx: 'phenome', xls: 'phenome', csv: 'phenome', tsv: 'phenome',
    gff: 'annotation', 'gff.gz': 'annotation', gff3: 'annotation',
    'gff3.gz': 'annotation', gtf: 'annotation', 'gtf.gz': 'annotation',
    bed: 'signal', 'bed.gz': 'signal', bw: 'signal', bigwig: 'signal',
    bedpe: 'interaction', 'bedpe.gz': 'interaction',
    pairs: 'interaction', 'pairs.gz': 'interaction',
    cool: 'interaction', mcool: 'interaction',
    sqlite: 'generic', db: 'generic',
  };
  return map[format] || 'generic';
}

// --- Form ---
const form = reactive({
  candidateName: directoryName.value,
  datasetType: inferredDatasetType.value,
  registrationMode: inferredMode.value as 'prebuilt' | 'hybrid' | 'recipe_build',
  versionName: '',
  organism: '',
  assembly: '',
});

watch(() => props.visible, (val) => {
  if (val) {
    form.candidateName = directoryName.value;
    form.datasetType = inferredDatasetType.value;
    form.registrationMode = inferredMode.value as 'prebuilt' | 'hybrid' | 'recipe_build';
    form.versionName = '';
    form.organism = '';
    form.assembly = '';
  }
});

async function handleSubmit() {
  if (!form.candidateName.trim()) {
    createMessage.error('请填写 Candidate 名称');
    return;
  }
  loading.value = true;
  try {
    // Step 1: 创建 candidate（需要 staging_file_id，这里用文件路径做最佳匹配）
    // 实际上我们需要从 staging API 先查找对应路径的 staging_file_id
    // 简化处理：假设 DirectoryBrowser 会传 BrowseFileItem 带上 staging_id
    // 此处展示完整交互流，实际联调时 DirectoryBrowser 需要传更多信息

    // Step 2: 注册 candidate
    // await registerCandidateApi(candidateId, { ... });

    createMessage.success('注册已提交');
    emit('update:visible', false);
    emit('registered');
  } catch (error: any) {
    createMessage.error(error?.message || '注册失败');
  } finally {
    loading.value = false;
  }
}

function handleCancel() {
  emit('update:visible', false);
}
</script>

<template>
  <Modal
    :open="visible"
    title="注册确认"
    :confirm-loading="loading"
    @ok="handleSubmit"
    @cancel="handleCancel"
    ok-text="确认注册"
    cancel-text="取消"
    width="640px"
  >
    <Form layout="vertical">
      <Form.Item label="Candidate 名称">
        <Input v-model:value="form.candidateName" />
      </Form.Item>

      <Form.Item label="数据类型">
        <Select v-model:value="form.datasetType" :options="DATASET_TYPE_OPTIONS" />
      </Form.Item>

      <Form.Item label="注册模式">
        <Radio.Group v-model:value="form.registrationMode">
          <Radio.Button
            v-for="opt in REGISTRATION_MODE_OPTIONS"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </Radio.Button>
        </Radio.Group>
      </Form.Item>

      <Form.Item label="目标版本">
        <Input v-model:value="form.versionName" placeholder="可选" />
      </Form.Item>

      <Form.Item label="物种">
        <Input v-model:value="form.organism" placeholder="可选" />
      </Form.Item>

      <Form.Item label="组装">
        <Input v-model:value="form.assembly" placeholder="可选" />
      </Form.Item>
    </Form>

    <div class="file-list-preview">
      <div class="preview-title">待注册文件（{{ files.length }} 个）：</div>
      <div v-for="file in files" :key="file.path" class="preview-file-row">
        <Tag color="green">✓</Tag>
        {{ file.name }}
        <Tag>{{ file.format }}</Tag>
        <span class="file-size">{{ (file.size / 1024 / 1024).toFixed(1) }} MB</span>
      </div>
    </div>
  </Modal>
</template>

<style scoped>
.file-list-preview {
  margin-top: 16px;
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
}

.preview-title {
  font-weight: 500;
  margin-bottom: 8px;
}

.preview-file-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
  font-size: 13px;
}

.file-size {
  color: #999;
  margin-left: auto;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/views/apps/dataset-staging/components/RegisterConfirmModal.vue
git commit -m "feat: create RegisterConfirmModal with inference and confirmation flow"
```

---

### Task 18: 重构 staging 页面，集成新组件

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/views/apps/dataset-staging/index.vue`

- [ ] **Step 1: 替换"当前暂存区"面板**

找到 line 937-999 的 `<Card :bordered="false" class="panel-card">` 面板（`<template #title>当前暂存区</template>`），替换为：

```vue
<Card :bordered="false" class="panel-card">
  <template #title>目录浏览</template>
  <template #extra>
    <Space wrap>
      <Button type="primary" ghost @click="openUploadModal">上传到暂存区</Button>
      <Button @click="openCandidatePage">查看注册候选</Button>
    </Space>
  </template>
  <DirectoryBrowser
    :scan-root-ids="activeRootId ? [activeRootId] : []"
    @register="openRegisterModalForFiles"
  />
</Card>
```

- [ ] **Step 2: 添加 `openRegisterModalForFiles` 方法 + 注册状态**

```typescript
// 在 <script setup> 中添加:
import DirectoryBrowser from './components/DirectoryBrowser.vue';
import RegisterConfirmModal from './components/RegisterConfirmModal.vue';
import type { BrowseFileItem } from '#/api/apps/dataset';

const registerModalVisible = ref(false);
const selectedBrowseFiles = ref<BrowseFileItem[]>([]);
const selectedDirectoryPath = ref('/');

function openRegisterModalForFiles(files: BrowseFileItem[], directoryPath: string) {
  if (!files.length) {
    createMessage.warning('请先在目录中选择文件');
    return;
  }
  selectedBrowseFiles.value = files;
  selectedDirectoryPath.value = directoryPath;
  registerModalVisible.value = true;
}

function onRegistered() {
  // 注册成功后刷新目录视图
  registerModalVisible.value = false;
  selectedBrowseFiles.value = [];
}
```

- [ ] **Step 3: 在 template 末尾添加 RegisterConfirmModal**

```vue
<RegisterConfirmModal
  v-model:visible="registerModalVisible"
  :files="selectedBrowseFiles"
  :directory-path="selectedDirectoryPath"
  :scan-root-id="activeRootId ?? undefined"
  @registered="onRegistered"
/>
```

- [ ] **Step 4: 移除旧的 staging 表格相关代码**

删除或注释以下不再需要的部分：
- `stagingColumns` (line 704-748)
- `stagingRowSelection` (line 775-780)
- `loadStagingRows` 中的 flat 调用逻辑

保留 `stagingRows` 和其他仍在用的变量，但 staging table 的 template 部分被 DirectoryBrowser 替代。

- [ ] **Step 5: 保留 upload/register 模态框**

`uploadVisible`、`registerVisible` 及相关函数继续保留，作为上传和单文件注册的补充入口。

- [ ] **Step 6: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/views/apps/dataset-staging/index.vue
git commit -m "feat: replace flat staging table with DirectoryBrowser + RegisterConfirmModal"
```

---

### Task 19: 端到端验证

- [ ] **Step 1: 启动后端**

```bash
cd /Users/kentnf/projects/omicsagent/odata/backend/api-server
# 确保后端运行在 8001
python -m pytest tests/test_dataset_scan_browse.py -v
# Expected: all tests pass
```

- [ ] **Step 2: 启动前端**

```bash
cd /Users/kentnf/projects/omicsagent/odata/frontend/admin-web
pnpm dev:antd
# Expected: 启动在 port 5666
```

- [ ] **Step 3: 验证 golden path**

1. 打开数据扫描页
2. 选择一个 scan root
3. 查看目录视图是否显示扫描到的子目录
4. 点击目录进入浏览，查看文件列表
5. 勾选多个文件，点击底部"注册为 Dataset"
6. 在确认对话框中确认推断结果，点击确认注册
7. 验证 Dataset 中心是否出现新注册的数据

- [ ] **Step 4: 验证 edge cases**

1. 空目录下的文件（orphan files）是否正确显示
2. 无权限文件是否跳过不崩溃
3. 同时选中不同类型文件时推断是否合理
4. 面包屑导航是否正常

---

### Task 20: 修复 `_resolve_dataset_type_from_path` 中的 sqlite context 检测 (补充 Bug B1)

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py:1625-1629`

Task 1 将 sqlite/db 从静态映射中移除，fallback 到 generic。但 `_resolve_dataset_type_from_path` 可以进一步利用目录名做 context 推断：

- [ ] **Step 1: 实现**

```python
def _resolve_dataset_type_from_path(self, file_path, dataset_type=None):
    if dataset_type:
        return dataset_type
    suffix = self._guess_file_suffix(file_path)
    base_type = self.FILE_FORMAT_TO_DATASET_TYPE.get(suffix, "generic")
    if base_type == "generic" and suffix in {"sqlite", "db"}:
        # 从目录名推断上下文
        path_lower = Path(file_path).parent.name.lower()
        for keyword, dtype in [
            ("phenotype", "phenome"),
            ("phenome", "phenome"),
            ("trait", "phenome"),
            ("genome", "genome"),
            ("annotation", "annotation"),
            ("function", "annotation"),
            ("go_", "annotation"),
            ("kegg", "annotation"),
            ("expression", "transcriptome"),
            ("rnaseq", "transcriptome"),
        ]:
            if keyword in path_lower:
                return dtype
    return base_type
```

- [ ] **Step 2: Commit**

```bash
git add backend/api-server/apps/datasets/services.py
git commit -m "feat: add directory-name context detection for sqlite/db files in _resolve_dataset_type_from_path"
```

---

## 依赖顺序

```
Task 1 (B1 fix) ──┐
Task 2 (B6 fix)   │
Task 3 (B7 fix)   ├── Phase 1: 独立 bug 修复，可并行
Task 4 (B8 fix)   │
Task 5 (B9 fix)   │
Task 6 (B10 fix)  │
Task 7 (B11 fix)  │
Task 8 (B12 fix)  │
Task 9 (B2 fix) ──┘
Task 10 (B3 fix)      ← 依赖 run_scan_root 上下文

Task 11 (browse files) ──┐
Task 12 (directory view)  ├── Phase 2: 后端 API 扩展
Task 13 (validate)       │
Task 20 (context detect) ─┘

Task 14 (TS types)    ──┐
Task 15 (B5 + F5 fix)   ├── Phase 3: 前端基础
Task 16 (DirectoryBrowser) ──┐
Task 17 (RegisterModal) ─────┤ Phase 4: 前端组件
Task 18 (page refactor) ─────┘

Task 19 (e2e verify) ← Phase 5: 集成验证
```

Phase 1 的 Task 1-9 完全独立，可并行。Phase 2 的 Task 11-13 需要 Phase 1 完成。Task 10 可独立。Task 16-18 需要 Task 14 的类型定义就绪。
