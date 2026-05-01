import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
ADMIN_SRC_ROOT = REPO_ROOT / "frontend/admin-web/apps/web-antd/src"


def _parse_module(relative_path: str):
    return ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))


def test_dataset_service_uses_legacy_databases_only_via_bridge():
    tree = _parse_module("apps/datasets/services.py")

    direct_legacy_crud_imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "apps.databases.crud"
    ]
    bridge_imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "legacy_bridge" and node.level == 1
    ]

    assert not direct_legacy_crud_imports
    assert bridge_imports


def test_dataset_crud_module_no_longer_exports_legacy_database_crud():
    tree = _parse_module("apps/datasets/crud.py")
    assigned_names = {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }

    assert "legacy_database_db" not in assigned_names


def test_migrated_admin_pages_no_longer_import_legacy_database_options_api():
    migrated_pages = [
        "frontend/admin-web/apps/web-antd/src/views/apps/variant/data.ts",
        "frontend/admin-web/apps/web-antd/src/views/apps/rnaseq/data.ts",
        "frontend/admin-web/apps/web-antd/src/views/apps/genome/data.ts",
        "frontend/admin-web/apps/web-antd/src/views/apps/datashow/sequence/data.ts",
        "frontend/admin-web/apps/web-antd/src/views/system/project/data.ts",
    ]

    for relative_path in migrated_pages:
        content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert "getDatabaseOptionsApi" not in content, relative_path


def test_legacy_database_options_api_is_limited_to_known_compat_pages():
    allowed_pages = {
        "views/apps/grn/data.ts",
        "views/apps/germplasm/data.ts",
        "views/apps/phenotype/data.ts",
        "views/apps/database/meta/data.ts",
        "views/apps/database/dataInfo/genome/data.ts",
        "views/apps/database/dataInfo/variant/data.ts",
        "views/apps/database/dataInfo/rnaseq/data.ts",
    }

    views_root = ADMIN_SRC_ROOT / "views"
    actual_pages = {
        path.relative_to(ADMIN_SRC_ROOT).as_posix()
        for path in views_root.rglob("*.ts")
        if "getDatabaseOptionsApi" in path.read_text(encoding="utf-8")
    }

    assert actual_pages == allowed_pages


def test_dashboard_workspace_uses_dataset_center_entry_instead_of_legacy_database_list():
    content = (
        REPO_ROOT / "frontend/admin-web/apps/web-antd/src/views/dashboard/workspace/index.vue"
    ).read_text(encoding="utf-8")

    assert "/apps/dataset" in content
    assert "/database/list" not in content


def test_legacy_database_pages_show_dataset_center_compat_notice():
    compat_pages = [
        "frontend/admin-web/apps/web-antd/src/views/apps/database/index.vue",
        "frontend/admin-web/apps/web-antd/src/views/apps/database-files/index.vue",
        "frontend/admin-web/apps/web-antd/src/views/apps/database/info.vue",
    ]

    for relative_path in compat_pages:
        content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert "LegacyCompatNotice" in content, relative_path
        assert "/apps/dataset" in content or "LegacyCompatNotice" in content, relative_path
