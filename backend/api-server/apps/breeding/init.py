import time

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError

from db.database import engine

from .models import (
    BreedingAssay,
    BreedingBioSample,
    BreedingDataFile,
    BreedingDatasetAssayLink,
    BreedingDatasetSubjectLink,
    BreedingGermplasm,
    BreedingGermplasmImportBatch,
    BreedingGermplasmLineage,
    BreedingMaterial,
    BreedingObservation,
    BreedingPhenotypeSubjectMap,
    BreedingPlot,
    BreedingProgram,
    BreedingTaxonomyCache,
    BreedingTaxonomyName,
    BreedingTaxonomyNode,
    BreedingTaxonomySourceSnapshot,
    BreedingTrial,
    BreedingVariantSampleMap,
)


def init_breeding_tables():
    tables = [
        BreedingProgram.__table__,
        BreedingMaterial.__table__,
        BreedingTaxonomySourceSnapshot.__table__,
        BreedingTaxonomyNode.__table__,
        BreedingTaxonomyName.__table__,
        BreedingTaxonomyCache.__table__,
        BreedingGermplasmImportBatch.__table__,
        BreedingGermplasm.__table__,
        BreedingGermplasmLineage.__table__,
        BreedingTrial.__table__,
        BreedingPlot.__table__,
        BreedingObservation.__table__,
        BreedingBioSample.__table__,
        BreedingAssay.__table__,
        BreedingDataFile.__table__,
        BreedingDatasetSubjectLink.__table__,
        BreedingDatasetAssayLink.__table__,
        BreedingVariantSampleMap.__table__,
        BreedingPhenotypeSubjectMap.__table__,
    ]
    for table in tables:
        for attempt in range(3):
            try:
                table.create(bind=engine, checkfirst=True)
                break
            except OperationalError:
                if attempt == 2:
                    raise
                time.sleep(1)
    _ensure_breeding_schema_columns()
    _ensure_breeding_search_indexes()


def _ensure_breeding_schema_columns():
    inspector = inspect(engine)
    table_columns = {
        "brd_material": {column["name"] for column in inspector.get_columns("brd_material")},
        "brd_germplasm_import_batch": {column["name"] for column in inspector.get_columns("brd_germplasm_import_batch")},
    }
    ddl_statements = []
    if "germplasm_accession" not in table_columns["brd_material"]:
        ddl_statements.append("ALTER TABLE brd_material ADD COLUMN germplasm_accession VARCHAR(128)")
    if "germplasm_name" not in table_columns["brd_material"]:
        ddl_statements.append("ALTER TABLE brd_material ADD COLUMN germplasm_name VARCHAR(256)")
    if "germplasm_source_file" not in table_columns["brd_material"]:
        ddl_statements.append("ALTER TABLE brd_material ADD COLUMN germplasm_source_file TEXT")
    if "field_schema_json" not in table_columns["brd_germplasm_import_batch"]:
        ddl_statements.append("ALTER TABLE brd_germplasm_import_batch ADD COLUMN field_schema_json TEXT")

    if ddl_statements:
        with engine.begin() as conn:
            for statement in ddl_statements:
                conn.execute(text(statement))


def _ensure_breeding_search_indexes():
    if engine.dialect.name != "postgresql":
        return

    statements = [
        "CREATE EXTENSION IF NOT EXISTS pg_trgm",
        (
            "CREATE INDEX IF NOT EXISTS ix_brd_taxonomy_node_scientific_name_trgm "
            "ON brd_taxonomy_node USING gin (scientific_name gin_trgm_ops)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_brd_taxonomy_node_common_name_trgm "
            "ON brd_taxonomy_node USING gin (common_name gin_trgm_ops)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_brd_taxonomy_name_name_txt_trgm "
            "ON brd_taxonomy_name USING gin (name_txt gin_trgm_ops)"
        ),
    ]
    with engine.begin() as conn:
        for statement in statements:
            try:
                conn.execute(text(statement))
            except (IntegrityError, ProgrammingError) as exc:
                detail = str(exc).lower()
                if "already exists" in detail or "pg_class_relname_nsp_index" in detail:
                    continue
                raise
