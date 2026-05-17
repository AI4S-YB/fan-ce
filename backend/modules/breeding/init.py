import time

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError

from shared.database import engine

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
    BreedingTaxonomyName,
    BreedingTaxonomyNode,
    BreedingTrial,
    BreedingVariantSampleMap,
)


def init_breeding_tables():
    """Tables are now created by alembic migration (consolidate_init_tables).
    This function keeps only the runtime schema/index helpers."""
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

    _ensure_breeding_foreign_keys()


def _ensure_breeding_foreign_keys():
    """Recreate FK constraints that may have been dropped by CASCADE."""
    if engine.dialect.name != "postgresql":
        return

    fk_checks = [
        (
            "brd_germplasm",
            "brd_taxonomy_node",
            "brd_germplasm_taxonomy_tax_id_fkey",
            "FOREIGN KEY (taxonomy_tax_id) REFERENCES brd_taxonomy_node(tax_id) ON DELETE RESTRICT",
        ),
        (
            "brd_germplasm_import_batch",
            "brd_taxonomy_node",
            "brd_germplasm_import_batch_taxonomy_tax_id_fkey",
            "FOREIGN KEY (taxonomy_tax_id) REFERENCES brd_taxonomy_node(tax_id) ON DELETE RESTRICT",
        ),
        (
            "brd_germplasm_lineage",
            "brd_taxonomy_node",
            "brd_germplasm_lineage_taxonomy_tax_id_fkey",
            "FOREIGN KEY (taxonomy_tax_id) REFERENCES brd_taxonomy_node(tax_id) ON DELETE RESTRICT",
        ),
    ]

    with engine.begin() as conn:
        for table_name, ref_table, fk_name, fk_def in fk_checks:
            result = conn.execute(
                text(
                    "SELECT 1 FROM pg_catalog.pg_constraint co "
                    "JOIN pg_catalog.pg_class tbl ON co.conrelid = tbl.oid "
                    "JOIN pg_catalog.pg_class ref ON co.confrelid = ref.oid "
                    "WHERE tbl.relname = :tbl AND ref.relname = :ref AND co.contype = 'f'"
                ),
                {"tbl": table_name, "ref": ref_table},
            ).fetchone()
            if result is None:
                conn.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        f"ADD CONSTRAINT {fk_name} {fk_def}"
                    )
                )


def _ensure_breeding_search_indexes():
    if engine.dialect.name != "postgresql":
        return

    statements = [
        # Drop legacy pg_trgm indexes (no longer used, save 5-9 GB)
        "DROP INDEX IF EXISTS ix_brd_taxonomy_node_scientific_name_trgm",
        "DROP INDEX IF EXISTS ix_brd_taxonomy_node_common_name_trgm",
        "DROP INDEX IF EXISTS ix_brd_taxonomy_name_name_txt_trgm",
        (
            "CREATE INDEX IF NOT EXISTS ix_brd_taxonomy_node_scientific_name_vpo "
            "ON brd_taxonomy_node (scientific_name varchar_pattern_ops)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_brd_taxonomy_node_lineage_ids_gin "
            "ON brd_taxonomy_node USING gin (lineage_ids)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_brd_taxonomy_name_name_txt_vpo "
            "ON brd_taxonomy_name (name_txt varchar_pattern_ops)"
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


from modules.breeding.tools import register_breeding_tools

register_breeding_tools()
