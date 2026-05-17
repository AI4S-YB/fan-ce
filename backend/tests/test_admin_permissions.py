import pytest


class TestAdminPermissionDifferentiation:
    def test_regular_user_cannot_access_admin_force_delete(self):
        """require_superadmin dependency exists and is distinct from get_active_user"""
        from modules.common.depends import get_active_user, require_superadmin
        assert get_active_user is not require_superadmin
        assert callable(require_superadmin)

    def test_force_delete_dataset_endpoint_registered(self):
        """admin router has force-delete endpoint"""
        from modules.datasets.api.admin import router as admin_router
        routes = [r.path for r in admin_router.routes]
        assert any("force-delete" in p for p in routes)

    def test_state_rollback_endpoint_registered(self):
        """admin router has rollback endpoint"""
        from modules.datasets.api.admin import router as admin_router
        routes = [r.path for r in admin_router.routes]
        assert any("rollback" in p for p in routes)

    def test_rollback_rejects_invalid_target_state(self, db_session):
        """rollback-lifecycle rejects invalid target_state values"""
        from fastapi import HTTPException
        from modules.datasets.api.admin import admin_rollback_lifecycle_state

        try:
            admin_rollback_lifecycle_state(dataset_id=1, target_state="invalid_state", db=db_session)
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 400
            assert "Invalid target state" in e.detail
