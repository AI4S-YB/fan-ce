import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.breeding.models import (
    BreedingMaterial,
    BreedingPhenotypeSubjectMap,
    BreedingProgram,
    BreedingVariantSampleMap,
)
from apps.databases.models import Databases, DatabasesFile, DatabasesMeta
from apps.datasets.dataset_model import Dataset
from apps.datasets.models import DatasetAsset, DatasetLineageEdge, DatasetRegistry, DatasetVersion
from db.database import Base

ASSEMBLY_VALIDATOR_TABLES = [
    Dataset.__table__,
    DatasetRegistry.__table__,
    DatasetVersion.__table__,
    DatasetAsset.__table__,
    DatasetLineageEdge.__table__,
    Databases.__table__,
    DatabasesFile.__table__,
    DatabasesMeta.__table__,
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
