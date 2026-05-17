import inspect
import pytest


class TestLegacyIsolation:
    def test_services_py_no_longer_imports_legacy_models_directly(self):
        """services.py must not directly import old apps.databases models"""
        from modules.datasets import services
        source = inspect.getsource(services)
        for forbidden in [
            "from modules.databases",
            "import Databases",
            "import DatabasesFile",
            "import DatabasesMeta",
            "import ProjectDatabasesLink",
        ]:
            assert forbidden not in source, (
                f"services.py still directly imports: {forbidden}"
            )

    def test_legacy_bridge_exposes_delete_cascade(self):
        """legacy_bridge exposes delete_legacy_cascade needed by services.py"""
        from modules.datasets.legacy_bridge import dataset_legacy_bridge
        assert hasattr(dataset_legacy_bridge, "delete_legacy_cascade")
        assert callable(dataset_legacy_bridge.delete_legacy_cascade)

    def test_legacy_bridge_exposes_required_wrappers(self):
        """legacy_bridge exposes all CRUD methods needed by services.py"""
        from modules.datasets.legacy_bridge import dataset_legacy_bridge
        for name in [
            "get_database",
            "list_databases",
            "create_database",
            "update_database",
            "get_primary_file",
            "create_primary_file",
            "update_primary_file",
            "list_meta",
            "list_project_links_by_dataset",
            "list_project_links_by_project",
            "create_project_link",
            "delete_legacy_cascade",
        ]:
            assert hasattr(dataset_legacy_bridge, name), (
                f"legacy_bridge missing: {name}"
            )
            assert callable(getattr(dataset_legacy_bridge, name)), (
                f"legacy_bridge.{name} is not callable"
            )
