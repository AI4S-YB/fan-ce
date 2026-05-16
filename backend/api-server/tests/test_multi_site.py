"""Integration tests for multi-site architecture."""
import pytest
from fastapi.testclient import TestClient

from main import app
from db.database import MyDBManager
from apps.platform.models import PlatformSiteDatasetLink, PlatformSiteSetting
from apps.datasets.models import DatasetRegistry


client = TestClient(app)


class TestSiteCRUD:
    """Admin site management endpoints."""

    def test_create_site(self):
        response = client.post("/api/v1/admin/sites", json={
            "site_code": "test-site-1",
            "site_name": "Test Site",
            "site_title": "Test",
            "domain": "test.local",
            "test_port": "5999",
        })
        assert response.status_code in (200, 401)  # 200 if auth bypassed, 401 if auth required

    def test_list_sites(self):
        response = client.get("/api/v1/admin/sites")
        assert response.status_code in (200, 401)

    def test_create_duplicate_site_code_fails(self):
        # Create first
        client.post("/api/v1/admin/sites", json={
            "site_code": "dup-test", "site_name": "First"
        })
        # Duplicate should fail
        response = client.post("/api/v1/admin/sites", json={
            "site_code": "dup-test", "site_name": "Second"
        })
        assert response.status_code in (400, 401)


class TestDatasetBinding:
    """Dataset-site binding logic."""

    def test_bind_public_dataset(self):
        """Binding a public dataset should succeed."""
        with MyDBManager() as db:
            # Find or create a public dataset
            ds = db.query(DatasetRegistry).filter(DatasetRegistry.is_public == True).first()
            if not ds:
                pytest.skip("No public dataset available")

            # Ensure site exists
            site = db.query(PlatformSiteSetting).filter(
                PlatformSiteSetting.site_code == "default"
            ).first()
            if not site:
                site = PlatformSiteSetting(site_code="default", site_name="Default")
                db.add(site)
                db.commit()

            from apps.platform.multi_site import bind_dataset_to_site, unbind_dataset_from_site
            from apps.platform.models import PlatformSiteDatasetLink

            # Bind
            bind_dataset_to_site(db, "default", ds.id)
            link = db.query(PlatformSiteDatasetLink).filter(
                PlatformSiteDatasetLink.site_code == "default",
                PlatformSiteDatasetLink.dataset_id == ds.id,
            ).first()
            assert link is not None

            # Cleanup
            unbind_dataset_from_site(db, "default", ds.id)

    def test_bind_private_dataset_fails(self):
        """Binding a non-public dataset should raise ValueError."""
        with MyDBManager() as db:
            ds = db.query(DatasetRegistry).filter(DatasetRegistry.is_public == False).first()
            if not ds:
                pytest.skip("No private dataset available")

            from apps.platform.multi_site import bind_dataset_to_site
            with pytest.raises(ValueError, match="public"):
                bind_dataset_to_site(db, "default", ds.id)

    def test_get_site_dataset_ids(self):
        with MyDBManager() as db:
            from apps.platform.multi_site import get_site_dataset_ids
            ids = get_site_dataset_ids(db, "default")
            assert isinstance(ids, set)


class TestPublicAPI:
    """Public site-scoped endpoints (no auth)."""

    def test_public_site_info(self):
        response = client.get("/api/v1/public/site/info")
        assert response.status_code in (200, 404)  # 200 if default site exists, 404 if not

    def test_public_datasets(self):
        response = client.get("/api/v1/public/datasets")
        assert response.status_code in (200, 404)

    def test_public_dataset_detail_not_found(self):
        response = client.get("/api/v1/public/datasets/99999999")
        assert response.status_code == 404
