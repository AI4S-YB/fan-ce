from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.datasets.models import DatasetRegistry as Dataset  # was dataset_model.Dataset
from modules.datasets.models import DatasetVersion
from shared.database import Base

DATASET_TEST_TABLES = [
    Dataset.__table__,
    DatasetVersion.__table__,
]


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine, tables=DATASET_TEST_TABLES)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestDatasetMasterTable:
    """F-1: Dataset master table must exist with FK from DatasetVersion."""

    def test_dataset_table_exists_and_accepts_insert(self, db_session):
        """A row can be inserted into the dataset table with required fields."""
        ds = Dataset(
            dataset_code="DS00001",
            dataset_type="genome",
            organism="Oryza sativa",
            assembly="IRGSP-1.0",
            visibility="private",
            lifecycle_state="draft",
        )
        db_session.add(ds)
        db_session.commit()

        fetched = db_session.query(Dataset).filter_by(dataset_code="DS00001").first()
        assert fetched is not None
        assert fetched.dataset_type == "genome"
        assert fetched.organism == "Oryza sativa"

    def test_dataset_code_is_unique(self, db_session):
        """dataset_code must be unique across the table."""
        ds1 = Dataset(
            dataset_code="DS_DUP",
            dataset_type="genome",
            organism="Oryza sativa",
            assembly="IRGSP-1.0",
        )
        ds2 = Dataset(
            dataset_code="DS_DUP",
            dataset_type="variome",
            organism="Oryza sativa",
            assembly="IRGSP-1.0",
        )
        db_session.add(ds1)
        db_session.commit()
        db_session.add(ds2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_dataset_version_has_dataset_id_fk(self, db_session):
        """DatasetVersion must have dataset_id FK pointing to dataset table."""
        ds = Dataset(
            dataset_code="DS_V1_TEST",
            dataset_type="genome",
            organism="Oryza sativa",
            assembly="IRGSP-1.0",
        )
        db_session.add(ds)
        db_session.commit()

        dv = DatasetVersion(
            dataset_id=ds.id,
            version="v1",
            title="Test Version",
            dataset_type="genome",
            lifecycle_state="active",
        )
        db_session.add(dv)
        db_session.commit()

        assert dv.dataset_id == ds.id

        # Verify FK constraint: referencing a non-existent dataset must fail
        dv_bad = DatasetVersion(
            dataset_id=999999,
            version="v1",
            title="Bad Version",
            dataset_type="genome",
        )
        db_session.add(dv_bad)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
