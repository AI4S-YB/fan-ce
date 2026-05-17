import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.breeding.models import (
    BreedingDatasetAssayLink,
    BreedingDatasetSubjectLink,
    BreedingPhenotypeSubjectMap,
    BreedingVariantSampleMap,
)
from modules.datasets.models import DatasetRegistry
from shared.database import Base

BREEDING_CORE_TABLES = [
    BreedingVariantSampleMap.__table__,
    BreedingPhenotypeSubjectMap.__table__,
    BreedingDatasetSubjectLink.__table__,
    BreedingDatasetAssayLink.__table__,
    DatasetRegistry.__table__,
]


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=BREEDING_CORE_TABLES)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class TestWithdrawGuard:
    def test_check_breeding_references_detects_variant_map(self, db_session):
        from modules.datasets.services import DatasetDomainService

        ds = DatasetRegistry(
            dataset_code="DS_WD_V2", dataset_type="variome",
            organism="Oryza sativa",
        )
        db_session.add(ds)
        db_session.commit()

        vmap = BreedingVariantSampleMap(
            dataset_id=ds.id, version_id=99, asset_id=1,
            vcf_sample_name="GUARD_TEST", mapping_status="matched",
        )
        db_session.add(vmap)
        db_session.commit()

        service = DatasetDomainService()
        refs = service._check_breeding_references(db=db_session, version_id=99)

        assert refs["has_references"] is True
        assert refs["variant_sample_map_count"] == 1
        assert len(refs["details"]) == 1
        assert refs["details"][0]["vcf_sample_name"] == "GUARD_TEST"

    def test_check_breeding_references_empty_when_none(self, db_session):
        from modules.datasets.services import DatasetDomainService

        service = DatasetDomainService()
        refs = service._check_breeding_references(db=db_session, version_id=99999)

        assert refs["has_references"] is False
        assert refs["total_references"] == 0
