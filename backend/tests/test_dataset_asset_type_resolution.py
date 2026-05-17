from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.datasets.models import AssetTypeRegistry
from shared.database import Base


DATASET_RESOLUTION_TABLES = [
    AssetTypeRegistry.__table__,
]


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=DATASET_RESOLUTION_TABLES)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    testing_session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()


class TestAssetTypeResolution:
    """F-10: Asset type resolution MUST consult AssetTypeRegistry table."""

    def test_resolve_asset_type_from_registry_when_entry_exists(self, db_session):
        """When AssetTypeRegistry has a matching active entry for the dataset type,
        the resolver must return the registry-configured asset type."""
        registry_entry = AssetTypeRegistry(
            code="custom_variant_bundle",
            base_code="variant_vcf",
            name="Custom Variant Bundle",
            allowed_dataset_types='["variome"]',
            is_active=1,
            sort_order=10,
        )
        db_session.add(registry_entry)
        db_session.commit()

        from modules.datasets.services import DatasetDomainService
        service = DatasetDomainService()
        resolved = service._resolve_default_asset_type_code(
            db=db_session,
            dataset_type="variome",
        )

        assert resolved == "custom_variant_bundle"

    def test_fallback_to_hardcoded_when_no_registry_match(self, db_session):
        """When no AssetTypeRegistry entry matches, fall back to the hardcoded map."""
        from modules.datasets.services import DatasetDomainService
        service = DatasetDomainService()
        resolved = service._resolve_default_asset_type_code(
            db=db_session,
            dataset_type="variome",
        )

        assert resolved == "variant_vcf"

    def test_registry_inactive_entry_is_skipped(self, db_session):
        """Inactive registry entries must be ignored during resolution."""
        registry_entry = AssetTypeRegistry(
            code="inactive_variant",
            base_code="variant_vcf",
            name="Inactive Variant",
            allowed_dataset_types='["variome"]',
            is_active=0,
            sort_order=10,
        )
        db_session.add(registry_entry)
        db_session.commit()

        from modules.datasets.services import DatasetDomainService
        service = DatasetDomainService()
        resolved = service._resolve_default_asset_type_code(
            db=db_session,
            dataset_type="variome",
        )

        assert resolved == "variant_vcf"
