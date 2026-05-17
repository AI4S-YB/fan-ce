import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.breeding.models import (
    BreedingMaterial,
    BreedingPhenotypeSubjectMap,
    BreedingProgram,
    BreedingVariantSampleMap,
)
from modules.datasets.models import DatasetRegistry as Dataset  # was dataset_model.Dataset
from modules.datasets.models import DatasetAsset, DatasetLineageEdge, DatasetRegistry, DatasetVersion
from shared.database import Base

ASSEMBLY_VALIDATOR_TABLES = [
    Dataset.__table__,
    DatasetRegistry.__table__,
    DatasetVersion.__table__,
    DatasetAsset.__table__,
    DatasetLineageEdge.__table__,
    BreedingProgram.__table__,
    BreedingMaterial.__table__,
    BreedingVariantSampleMap.__table__,
    BreedingPhenotypeSubjectMap.__table__,
]

# ── PostgreSQL test database ──
# Uses the same config as the app (config.dev.yaml).
# PostgreSQL must be running at the configured host:port.
from urllib.parse import quote_plus

from config.settings import settings

_pg = settings.app_options.get("pgsql_options") or {}
TEST_DB_URL = (
    f"postgresql+psycopg://{_pg.get('user', 'postgres')}:"
    f"{quote_plus(str(_pg.get('password', '')))}"
    f"@{_pg.get('host', '127.0.0.1')}:{_pg.get('port', 5433)}"
    f"/{_pg.get('database', 'fan_ce_dev')}"
)


@pytest.fixture()
def db_session():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(bind=engine, tables=ASSEMBLY_VALIDATOR_TABLES, checkfirst=True)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = testing_session()
    try:
        yield session
        session.rollback()
    finally:
        session.close()
        engine.dispose()
