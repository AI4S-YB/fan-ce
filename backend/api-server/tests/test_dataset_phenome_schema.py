from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import apps.datasets.init as dataset_init_module
from apps.datasets.schemas import (
    DatasetVersionQueryCapabilitiesRequest,
    DatasetVersionQueryRequest,
)
from apps.datasets.models import (
    AssetFileTypeRegistry,
    AssetTypeRegistry,
    DatasetKindRegistry,
    PhenomeImportRun,
    PhenomeObservation,
    PhenomeSourceColumn,
    PhenomeSubject,
    PhenomeTrait,
)


PHENOME_TABLES = [
    PhenomeImportRun.__table__,
    PhenomeSubject.__table__,
    PhenomeTrait.__table__,
    PhenomeSourceColumn.__table__,
    PhenomeObservation.__table__,
]


@pytest.fixture()
def db_engine(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

    class DBManagerStub:
        def __enter__(self):
            self.db = session_factory()
            return self.db

        def __exit__(self, exc_type, exc_value, traceback):
            self.db.close()
            return False

    monkeypatch.setattr(dataset_init_module, "engine", engine)
    monkeypatch.setattr(dataset_init_module, "MyDBManager", DBManagerStub)
    dataset_init_module.init_dataset_tables()
    try:
        yield engine
    finally:
        engine.dispose()


def test_dataset_init_creates_phenome_index_tables_and_seeds_registry(db_engine):
    table_names = set(inspect(db_engine).get_table_names())
    for table in PHENOME_TABLES:
        assert table.name in table_names
    assert "asset_file_type_registry" in table_names

    dataset_init_module.seed_dataset_registry_defaults()

    session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False, expire_on_commit=False)()
    try:
        phenome_kind = session.query(DatasetKindRegistry).filter(DatasetKindRegistry.code == "phenome").first()
        phenotype_table = session.query(AssetTypeRegistry).filter(AssetTypeRegistry.code == "phenotype_table").first()
        phenotype_index = session.query(AssetTypeRegistry).filter(AssetTypeRegistry.code == "phenotype_index").first()
        genome_index = session.query(AssetFileTypeRegistry).filter(AssetFileTypeRegistry.code == "genome_sequence_index").first()

        assert phenome_kind is not None
        assert phenome_kind.base_code == "phenotype_set"
        assert phenotype_table is not None
        assert phenotype_index is not None
        assert genome_index is not None
        assert genome_index.file_role == "index"
        assert genome_index.supported_file_formats == '["fai", "gzi"]'
        assert phenotype_table.allowed_dataset_types == '["phenome"]'
        assert phenotype_index.allowed_dataset_types == '["phenome"]'
    finally:
        session.close()


def test_dataset_query_request_models_allow_frontend_context_fields():
    capability_req = DatasetVersionQueryCapabilitiesRequest(
        id=24,
        asset_code="phenotype_index",
        team_id=0,
        project_id=0,
    )
    execute_req = DatasetVersionQueryRequest(
        id=24,
        operation="dataset_summary",
        params={},
        team_id=0,
        project_id=0,
    )

    assert capability_req.id == 24
    assert capability_req.asset_code == "phenotype_index"
    assert execute_req.operation == "dataset_summary"
