import pytest


class TestDatabaseDeprecation:
    """The apps.databases module has been removed; these tests are deprecated."""

    def test_old_database_module_no_longer_exists(self):
        """Verify the deprecated databases module is truly gone."""
        with pytest.raises(ModuleNotFoundError):
            import apps.databases.models  # noqa: F401

    def test_old_database_routers_are_removed(self):
        """The deprecated databases routers module is gone."""
        with pytest.raises(ModuleNotFoundError):
            import apps.databases.routers  # noqa: F401
