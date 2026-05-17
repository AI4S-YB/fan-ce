from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.breeding.models import (
    BreedingMaterial,
    BreedingPhenotypeSubjectMap,
    BreedingProgram,
    BreedingTrial,
    BreedingPlot,
)
from modules.datasets.models import DatasetRegistry as Dataset  # was dataset_model.Dataset
from modules.datasets.models import (
    DatasetAsset,
    DatasetRegistry,
    DatasetVersion,
    PhenomeImportRun,
    PhenomeObservation,
    PhenomeSubject,
    PhenomeTrait,
)
from shared.database import Base

BRIDGE_TABLES = [
    Dataset.__table__,
    DatasetRegistry.__table__,
    DatasetVersion.__table__,
    DatasetAsset.__table__,
    BreedingProgram.__table__,
    BreedingMaterial.__table__,
    BreedingTrial.__table__,
    BreedingPlot.__table__,
    BreedingPhenotypeSubjectMap.__table__,
    PhenomeImportRun.__table__,
    PhenomeSubject.__table__,
    PhenomeTrait.__table__,
    PhenomeObservation.__table__,
]


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=BRIDGE_TABLES)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class TestPhenomeBreedingBridge:
    def test_bridge_maps_phenome_observation_to_breeding(self, db_session):
        from modules.datasets.phenome_indexing import PhenomeBreedingBridge

        program = BreedingProgram(code="P_PHBR", name="Phenome Bridge", status="active")
        db_session.add(program)
        db_session.commit()

        mat = BreedingMaterial(
            program_id=program.id,
            material_code="M_PHBR",
            material_name="Bridge Material",
            material_type="line",
        )
        db_session.add(mat)
        db_session.commit()

        ds = Dataset(
            dataset_code="DS_PHBR",
            dataset_type="phenome",
            organism="Oryza sativa",
            assembly="IRGSP-1.0",
        )
        db_session.add(ds)
        db_session.commit()

        run = PhenomeImportRun(source_file_path="/tmp/test.sqlite", status="completed")
        db_session.add(run)
        db_session.commit()

        subject = PhenomeSubject(
            import_run_id=run.id, subject_name="M_PHBR", subject_type="accession"
        )
        trait = PhenomeTrait(
            import_run_id=run.id,
            trait_code="height",
            trait_name="Plant Height",
            value_type="numeric",
        )
        db_session.add_all([subject, trait])
        db_session.commit()

        obs = PhenomeObservation(
            import_run_id=run.id,
            subject_pk=subject.id,
            trait_id=trait.id,
            trait_code="height",
            value_numeric=120.5,
        )
        db_session.add(obs)
        db_session.commit()

        result = PhenomeBreedingBridge.map_subject_to_material(
            db=db_session,
            subject_name="M_PHBR",
            dataset_id=ds.id,
            version_id=1,
            asset_id=1,
        )
        assert result["mapped"] is True
        assert result["material_id"] == mat.id

    def test_bridge_returns_unmapped_for_unknown_subject(self, db_session):
        from modules.datasets.phenome_indexing import PhenomeBreedingBridge

        result = PhenomeBreedingBridge.map_subject_to_material(
            db=db_session,
            subject_name="UNKNOWN_MATERIAL",
            dataset_id=1,
            version_id=1,
            asset_id=1,
        )
        assert result["mapped"] is False
        assert result["reason"] == "No matching material found"
