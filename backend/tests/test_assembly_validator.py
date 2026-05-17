import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.breeding.models import (
    BreedingMaterial,
    BreedingPhenotypeSubjectMap,
    BreedingProgram,
    BreedingVariantSampleMap,
)
from modules.datasets.models import DatasetAsset, DatasetRegistry, DatasetVersion
from modules.datasets.assembly_validator import AssemblyConsistencyValidator
from shared.database import Base

ASSEMBLY_VALIDATOR_TABLES = [
    DatasetRegistry.__table__,
    DatasetVersion.__table__,
    DatasetAsset.__table__,
    BreedingProgram.__table__,
    BreedingMaterial.__table__,
    BreedingVariantSampleMap.__table__,
    BreedingPhenotypeSubjectMap.__table__,
]


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=ASSEMBLY_VALIDATOR_TABLES)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class TestAssemblyValidator:
    def test_sample_alignment_counts_paired_and_unpaired(self, db_session):
        program = BreedingProgram(code="P_AL2", name="Align Test", status="active")
        db_session.add(program)
        db_session.commit()

        mat1 = BreedingMaterial(program_id=program.id, material_code="M_A1", material_name="A1",
                                material_type="line", status="active")
        mat2 = BreedingMaterial(program_id=program.id, material_code="M_A2", material_name="A2",
                                material_type="line", status="active")
        db_session.add_all([mat1, mat2])
        db_session.commit()

        ds_v = DatasetRegistry(dataset_code="DS_ALV2", dataset_type="variome")
        ds_p = DatasetRegistry(dataset_code="DS_ALP2", dataset_type="phenome")
        db_session.add_all([ds_v, ds_p])
        db_session.commit()

        # Create corresponding DatasetRegistry / DatasetVersion / DatasetAsset
        # records so FK constraints on the breeding map tables are satisfied.
        reg_v = DatasetRegistry(database_id=0, dataset_code="DS_ALV2", dataset_type="variome",
                                version="v1", title="DS_ALV2", create_time=1, update_time=1)
        reg_p = DatasetRegistry(database_id=0, dataset_code="DS_ALP2", dataset_type="phenome",
                                version="v1", title="DS_ALP2", create_time=1, update_time=1)
        db_session.add_all([reg_v, reg_p])
        db_session.commit()

        ver_v = DatasetVersion(database_id=0, dataset_id=ds_v.id, version="v1", title="v1",
                               dataset_type="variome", create_time=1, update_time=1)
        ver_p = DatasetVersion(database_id=0, dataset_id=ds_p.id, version="v1", title="v1",
                               dataset_type="phenome", create_time=1, update_time=1)
        db_session.add_all([ver_v, ver_p])
        db_session.commit()

        ast_v = DatasetAsset(database_id=0, dataset_version_id=ver_v.id, asset_code="vc",
                             asset_name="variant_calls", asset_type="variant_calls",
                             create_time=1, update_time=1)
        ast_p = DatasetAsset(database_id=0, dataset_version_id=ver_p.id, asset_code="ps",
                             asset_name="phenotype_subjects", asset_type="phenotype_table",
                             create_time=1, update_time=1)
        db_session.add_all([ast_v, ast_p])
        db_session.commit()

        db_session.add(BreedingVariantSampleMap(
            dataset_id=reg_v.id, version_id=ver_v.id, asset_id=ast_v.id,
            vcf_sample_name="S1", material_id=mat1.id, mapping_status="matched",
        ))
        db_session.add(BreedingVariantSampleMap(
            dataset_id=reg_v.id, version_id=ver_v.id, asset_id=ast_v.id,
            vcf_sample_name="S2", material_id=mat2.id, mapping_status="matched",
        ))
        db_session.add(BreedingPhenotypeSubjectMap(
            dataset_id=reg_p.id, version_id=ver_p.id, asset_id=ast_p.id,
            row_key="SUBJ_1", material_id=mat1.id,
            trait_code="height", mapping_status="matched",
        ))
        db_session.commit()

        result = AssemblyConsistencyValidator.check_sample_alignment(
            db=db_session,
            variant_dataset_id=reg_v.id,
            phenotype_dataset_id=reg_p.id,
        )
        assert result["paired_count"] == 1
        assert result["variant_only_count"] == 1
        assert result["phenotype_only_count"] == 0
