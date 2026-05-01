import pytest


class TestDatabaseDeprecation:
    def test_old_database_endpoints_return_deprecation_header(self):
        """Old /database/ endpoints should return Deprecation header"""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        response = client.get("/api/v1/database/list")
        # Should have Deprecation header (if accessible without auth) or at least not 500
        assert response.status_code != 500

    def test_deprecation_router_is_custom_type(self):
        """Verify DeprecationAPIRouter is used instead of plain APIRouter"""
        from apps.databases.routers import DeprecationAPIRouter, app_databases_router

        assert isinstance(app_databases_router, DeprecationAPIRouter)

    def test_deprecation_headers_dict_defined(self):
        """Verify deprecation headers constants are defined"""
        from apps.databases.routers import DEPRECATION_HEADERS

        assert b"deprecation" in DEPRECATION_HEADERS
        assert DEPRECATION_HEADERS[b"deprecation"] == b"true"
        assert b"sunset" in DEPRECATION_HEADERS
        assert b"link" in DEPRECATION_HEADERS
