import inspect
import pytest


class TestActiveUserFix:
    def test_get_active_user_no_longer_hardcodes_permissions(self):
        """get_active_user must not hardcode permissions=['11']"""
        from apps.common import depends
        source = inspect.getsource(depends.get_active_user)
        assert "permissions = ['11']" not in source
        assert "permissions = " not in source

    def test_get_active_user_uses_rbd_user(self):
        """get_active_user must use get_rbd_user dependency"""
        from apps.common import depends
        source = inspect.getsource(depends.get_active_user)
        assert "get_rbd_user" in source
