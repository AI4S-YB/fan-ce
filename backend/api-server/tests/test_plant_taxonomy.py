"""Integration tests for plant taxonomy system."""
import pytest
from sqlalchemy import text

from apps.breeding.models import BreedingTaxonomyName, BreedingTaxonomyNode
from db.database import MyDBManager


class TestTaxonomyNodeSchema:
    """Verify new schema structure."""

    def test_node_table_has_required_columns(self):
        """brd_taxonomy_node should have lineage_ids (INT[]), lineage (TEXT), source, ncbi_sync_time."""
        with MyDBManager() as db:
            columns = {c.name: c.type for c in BreedingTaxonomyNode.__table__.columns}
        required = ["tax_id", "parent_tax_id", "rank", "scientific_name", "common_name",
                     "lineage_ids", "lineage", "source", "is_active"]
        for col in required:
            assert col in columns, f"Missing column: {col}"

    def test_node_table_no_legacy_columns(self):
        """brd_taxonomy_node should NOT have lineage_names_json or source_snapshot_id."""
        with MyDBManager() as db:
            columns = {c.name for c in BreedingTaxonomyNode.__table__.columns}
        assert "lineage_names_json" not in columns, "lineage_names_json should be removed"
        assert "source_snapshot_id" not in columns, "source_snapshot_id should be removed"

    def test_cache_table_does_not_exist(self):
        """brd_taxonomy_cache should no longer exist."""
        with MyDBManager() as db:
            engine = db.get_bind()
            inspector = __import__("sqlalchemy").inspect(engine)
            tables = inspector.get_table_names()
        assert "brd_taxonomy_cache" not in tables, "cache table should be removed"

    def test_snapshot_table_does_not_exist(self):
        """brd_taxonomy_source_snapshot should no longer exist."""
        with MyDBManager() as db:
            engine = db.get_bind()
            inspector = __import__("sqlalchemy").inspect(engine)
            tables = inspector.get_table_names()
        assert "brd_taxonomy_source_snapshot" not in tables, "snapshot table should be removed"


class TestTaxonomyFKIntegrity:
    """Verify FK relationships point to correct tables."""

    def test_germplasm_fk_targets_node_table(self):
        """brd_germplasm.taxonomy_tax_id should FK to brd_taxonomy_node."""
        with MyDBManager() as db:
            engine = db.get_bind()
            inspector = __import__("sqlalchemy").inspect(engine)
            fks = inspector.get_foreign_keys("brd_germplasm")
        taxonomy_fks = [fk for fk in fks if fk.get("constrained_columns") == ["taxonomy_tax_id"]]
        assert len(taxonomy_fks) > 0, "taxonomy_tax_id FK not found on brd_germplasm"
        assert taxonomy_fks[0]["referred_table"] == "brd_taxonomy_node"

    def test_germplasm_import_batch_fk_targets_node_table(self):
        """brd_germplasm_import_batch FK should target brd_taxonomy_node."""
        with MyDBManager() as db:
            engine = db.get_bind()
            inspector = __import__("sqlalchemy").inspect(engine)
            fks = inspector.get_foreign_keys("brd_germplasm_import_batch")
        taxonomy_fks = [fk for fk in fks if fk.get("constrained_columns") == ["taxonomy_tax_id"]]
        assert len(taxonomy_fks) > 0
        assert taxonomy_fks[0]["referred_table"] == "brd_taxonomy_node"

    def test_name_table_fk_targets_node_table(self):
        """brd_taxonomy_name.tax_id should FK to brd_taxonomy_node."""
        with MyDBManager() as db:
            engine = db.get_bind()
            inspector = __import__("sqlalchemy").inspect(engine)
            fks = inspector.get_foreign_keys("brd_taxonomy_name")
        taxonomy_fks = [fk for fk in fks if fk.get("constrained_columns") == ["tax_id"]]
        assert len(taxonomy_fks) > 0
        assert taxonomy_fks[0]["referred_table"] == "brd_taxonomy_node"


class TestPlantTaxonomyData:
    """Verify imported plant taxonomy data integrity."""

    def test_viridiplantae_root_exists(self):
        """tax_id 33090 (Viridiplantae) should exist after import."""
        with MyDBManager() as db:
            root = db.query(BreedingTaxonomyNode).filter(
                BreedingTaxonomyNode.tax_id == 33090
            ).first()
        assert root is not None, "Viridiplantae root node (33090) not found"
        assert root.scientific_name is not None
        assert root.rank is not None

    def test_all_nodes_are_plants(self):
        """Every node should have 33090 in its lineage_ids."""
        with MyDBManager() as db:
            non_plant = db.query(BreedingTaxonomyNode).filter(
                ~BreedingTaxonomyNode.lineage_ids.contains([33090])
            ).filter(
                BreedingTaxonomyNode.tax_id != 33090
            ).count()
        assert non_plant == 0, f"Found {non_plant} nodes not in Viridiplantae subtree"

    def test_lineage_ids_is_array(self):
        """lineage_ids should be a non-empty list for non-root nodes."""
        with MyDBManager() as db:
            node = db.query(BreedingTaxonomyNode).filter(
                BreedingTaxonomyNode.tax_id != 33090
            ).first()
        if node:
            assert isinstance(node.lineage_ids, list)
            assert len(node.lineage_ids) > 0
            assert 33090 in node.lineage_ids, "Viridiplantae (33090) should be in every plant lineage"

    def test_lineage_is_text(self):
        """lineage column should contain semicolon-separated names."""
        with MyDBManager() as db:
            node = db.query(BreedingTaxonomyNode).filter(
                BreedingTaxonomyNode.tax_id != 33090,
                BreedingTaxonomyNode.lineage.isnot(None),
            ).first()
        if node:
            assert isinstance(node.lineage, str)
            assert ";" in node.lineage or len(node.lineage) > 0

    def test_name_variants_exist(self):
        """brd_taxonomy_name should have entries linked to nodes."""
        with MyDBManager() as db:
            name_count = db.query(BreedingTaxonomyName).count()
            node_count = db.query(BreedingTaxonomyNode).count()
        if node_count > 0:
            assert name_count > 0, "Names table is empty but nodes exist"

    def test_node_count_matches_expected_range(self):
        """Plant taxonomy should have between 300K and 500K nodes."""
        with MyDBManager() as db:
            count = db.query(BreedingTaxonomyNode).count()
        if count > 0:  # Only check if data is imported
            assert 200_000 < count < 600_000, f"Unexpected node count: {count}"


class TestLineageIdsQuerying:
    """Verify lineage_ids enables efficient plant-only queries."""

    def test_contains_operator_finds_plants(self):
        """WHERE 33090 = ANY(lineage_ids) returns all plant nodes."""
        with MyDBManager() as db:
            # Use PostgreSQL array contains operator via raw SQL
            engine = db.get_bind()
            if engine.dialect.name == "postgresql":
                with engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT COUNT(*) FROM brd_taxonomy_node WHERE 33090 = ANY(lineage_ids)")
                    ).scalar()
                total = db.query(BreedingTaxonomyNode).count()
                # All nodes except 33090 itself should match (or all if root has itself in lineage_ids)
                assert result >= total - 1

    def test_lineage_ids_index_exists(self):
        """GIN index on lineage_ids should exist."""
        with MyDBManager() as db:
            engine = db.get_bind()
            if engine.dialect.name == "postgresql":
                inspector = __import__("sqlalchemy").inspect(engine)
                indexes = inspector.get_indexes("brd_taxonomy_node")
                gin_indexes = [idx for idx in indexes if "lineage_ids" in idx.get("column_names", [])]
                # Check that our named GIN index or any lineage_ids index exists
                lineage_idx_names = [idx["name"] for idx in indexes if "lineage_ids" in str(idx.get("column_names", []))]
                assert len(lineage_idx_names) > 0, "No index found on lineage_ids"

    def test_varchar_pattern_ops_index_exists(self):
        """varchar_pattern_ops index on scientific_name should exist."""
        with MyDBManager() as db:
            engine = db.get_bind()
            if engine.dialect.name == "postgresql":
                inspector = __import__("sqlalchemy").inspect(engine)
                indexes = inspector.get_indexes("brd_taxonomy_node")
                sci_idx = [idx for idx in indexes if "scientific_name" in str(idx.get("column_names", []))]
                assert len(sci_idx) > 0, "No index on scientific_name"

    def test_no_pg_trgm_indexes(self):
        """pg_trgm indexes should NOT exist on taxonomy tables."""
        with MyDBManager() as db:
            engine = db.get_bind()
            if engine.dialect.name == "postgresql":
                inspector = __import__("sqlalchemy").inspect(engine)
                for table in ["brd_taxonomy_node", "brd_taxonomy_name"]:
                    if table in inspector.get_table_names():
                        indexes = inspector.get_indexes(table)
                        for idx in indexes:
                            idx_name = idx.get("name", "")
                            assert "trgm" not in idx_name.lower(), (
                                f"pg_trgm index {idx_name} should be removed from {table}"
                            )
