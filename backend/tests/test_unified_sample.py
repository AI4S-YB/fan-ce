"""F-2: Unified Sample/Experiment abstraction layer tests.

Tests for the biological_sample_view and sequencing_experiment_view that
UNION ALL old SRA models (abd_sample) with new Breeding models (brd_biosample).
"""
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.breeding.models import BreedingBioSample, BreedingMaterial, BreedingPlot, BreedingProgram, BreedingTrial
from modules.sample.models import Sample
from shared.database import Base

# Tables needed for the biological_sample_view tests
BIOSAMPLE_TEST_TABLES = [
    Sample.__table__,
    BreedingProgram.__table__,
    BreedingMaterial.__table__,
    BreedingTrial.__table__,
    BreedingPlot.__table__,
    BreedingBioSample.__table__,
]

# SQLite-compatible version of the VIEW (PostgreSQL ::casts and to_timestamp removed)
BIOLOGICAL_SAMPLE_VIEW_DDL_SQLITE = """
CREATE VIEW IF NOT EXISTS biological_sample_view AS
SELECT
    id AS source_id,
    sample_code,
    sample_name,
    type AS sample_type,
    NULL AS material_id,
    CAST(project_id AS INTEGER) AS project_id,
    NULL AS program_id,
    'abd_sample' AS source_table,
    create_time AS created_at,
    update_time AS updated_at
FROM abd_sample
WHERE is_delete = 0

UNION ALL

SELECT
    id AS source_id,
    sample_code,
    NULL AS sample_name,
    sample_type,
    material_id,
    NULL AS project_id,
    NULL AS program_id,
    'brd_biosample' AS source_table,
    created_at,
    updated_at
FROM brd_biosample
WHERE status = 'active'
"""


@pytest.fixture()
def db_session():
    """Create an in-memory SQLite database with required tables and the unified VIEW."""
    engine = create_engine("sqlite:///:memory:", future=True)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine, tables=BIOSAMPLE_TEST_TABLES)

    # Create the unified VIEW in SQLite-compatible dialect
    with engine.connect() as conn:
        conn.execute(text(BIOLOGICAL_SAMPLE_VIEW_DDL_SQLITE))
        conn.commit()

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestBiologicalSampleView:
    """F-2: BiologicalSampleView unifies old abd_sample and new brd_biosample."""

    def test_view_exists_and_has_expected_columns(self, db_session):
        """The view must exist with normalized columns from both sources."""
        cols = db_session.execute(text(
            "PRAGMA table_info('biological_sample_view')"
        )).fetchall()
        col_names = [c[1] for c in cols]
        for expected in ["source_id", "sample_code", "sample_type", "source_table", "created_at"]:
            assert expected in col_names, f"Missing column: {expected}"

    def test_view_returns_new_biosample_records(self, db_session):
        """Biosample rows appear in the view with source_table = 'brd_biosample'."""
        program = BreedingProgram(code="P_VW", name="View Test", status="active")
        db_session.add(program)
        db_session.commit()

        mat = BreedingMaterial(program_id=program.id, material_code="MAT_VW",
                               material_name="View Material", material_type="inbred")
        db_session.add(mat)
        db_session.commit()

        bs = BreedingBioSample(sample_code="BS_VW001", material_id=mat.id, sample_type="leaf")
        db_session.add(bs)
        db_session.commit()

        rows = db_session.execute(text(
            "SELECT sample_code, source_table FROM biological_sample_view "
            "WHERE sample_code = 'BS_VW001'"
        )).fetchall()
        assert len(rows) == 1
        assert rows[0].source_table == "brd_biosample"

    def test_view_excludes_deleted_old_samples(self, db_session):
        """is_delete=1 (true) rows from abd_sample must not appear in the view."""
        s_active = Sample(sample_name="Active_Sample", sample_code="S_ACT", is_delete=False)
        s_deleted = Sample(sample_name="Deleted_Sample", sample_code="S_DEL", is_delete=True)
        db_session.add_all([s_active, s_deleted])
        db_session.commit()

        rows = db_session.execute(text(
            "SELECT sample_code FROM biological_sample_view "
            "WHERE sample_code IN ('S_ACT', 'S_DEL') ORDER BY sample_code"
        )).fetchall()
        codes = [r[0] for r in rows]
        assert "S_ACT" in codes
        assert "S_DEL" not in codes  # is_delete=1 rows excluded
