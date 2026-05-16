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
    """Legacy variant/rnaseq/genome/datashow/project pages have been removed.
    The getDatabaseOptionsApi is no longer used anywhere in the frontend."""
    views_root = ADMIN_SRC_ROOT / "views"
    remaining_uses = {
        path.relative_to(ADMIN_SRC_ROOT).as_posix()
        for path in views_root.rglob("*.ts")
        if path.exists() and "getDatabaseOptionsApi" in path.read_text(encoding="utf-8")
    }
    assert remaining_uses == set(), f"Unexpected legacy getDatabaseOptionsApi usage: {remaining_uses}"


def test_legacy_database_options_api_is_limited_to_known_compat_pages():
    """No pages should still use the legacy getDatabaseOptionsApi."""
    views_root = ADMIN_SRC_ROOT / "views"
    actual_pages = {
        path.relative_to(ADMIN_SRC_ROOT).as_posix()
        for path in views_root.rglob("*.ts")
        if path.exists() and "getDatabaseOptionsApi" in path.read_text(encoding="utf-8")
    }

    assert actual_pages == set()


def test_dashboard_workspace_uses_dataset_center_entry_instead_of_legacy_database_list():
    workspace_path = (
        REPO_ROOT / "frontend/admin-web/apps/web-antd/src/views/dashboard/workspace/index.vue"
    )
    if workspace_path.exists():
        content = workspace_path.read_text(encoding="utf-8")
        assert "/apps/dataset" in content or "apps/dataset" in content
        assert "/database/list" not in content
    else:
        # Workspace file removed - no legacy reference possible
        pass


def test_legacy_database_pages_show_dataset_center_compat_notice():
    """Legacy database pages have been removed. Verify they no longer exist."""
    compat_pages = [
        "frontend/admin-web/apps/web-antd/src/views/apps/database/index.vue",
        "frontend/admin-web/apps/web-antd/src/views/apps/database-files/index.vue",
        "frontend/admin-web/apps/web-antd/src/views/apps/database/info.vue",
    ]

    for relative_path in compat_pages:
        path = REPO_ROOT / relative_path
        assert not path.exists(), f"Legacy page should be removed: {relative_path}"
