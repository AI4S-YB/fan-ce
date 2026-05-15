#!/usr/bin/env python3
"""Initialize database tables and import plant taxonomy data.

Called by install.sh during fresh installation.
Safe to run multiple times (checks if taxonomy already installed).
"""
import sys
from pathlib import Path

# Ensure backend is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "api-server"))

from sqlalchemy import text
from db.database import engine, MyDBManager
from apps.datasets.init import init_dataset_tables
from apps.breeding.init import init_breeding_tables
from apps.platform.init import init_platform_tables
from apps.system.init import init_system_tables
from apps.breeding.models import BreedingTaxonomyNode
from apps.breeding.taxonomy_loader import load_taxonomy_dump
from apps.system.base.models import SystemInstallLock


def ensure_extensions():
    """Ensure required PostgreSQL extensions exist."""
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))


def create_tables():
    """Create all application tables (idempotent)."""
    init_dataset_tables()
    init_breeding_tables()
    init_platform_tables()
    init_system_tables()

    # Also ensure analysis table exists (worker needs it on first startup)
    try:
        from apps.analysis.models import BrdAnalysisJob
        BrdAnalysisJob.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        pass


def import_taxonomy(dump_path: str):
    """Import plant taxonomy data if not already installed."""
    with MyDBManager() as db:
        existing = db.query(BreedingTaxonomyNode).count()
        if existing > 0:
            print(f"Taxonomy already installed ({existing:,} nodes). Skipping import.")
            return

        print("Importing plant taxonomy data...")
        result = load_taxonomy_dump(
            db=db,
            dump_path=dump_path,
            source_name="ncbi_plant_taxdump",
            reset_existing=False,
        )
        print(f"Imported {result['node_count']:,} nodes, {result['name_count']:,} names")

        # Mark taxonomy as ready
        lock = db.query(SystemInstallLock).filter(
            SystemInstallLock.lock_code == "taxonomy_required"
        ).first()
        if lock:
            lock.is_locked = 0
            lock.reason = "taxonomy 已安装"
            db.add(lock)
            db.commit()


def main():
    dump_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not dump_path or not Path(dump_path).exists():
        print(f"Usage: python {__file__} <path_to_taxonomy-plants.tar.gz>")
        print(f"Error: taxonomy data file not found: {dump_path}")
        sys.exit(1)

    print("=== Database Initialization ===")
    ensure_extensions()
    create_tables()
    print("Tables created.")
    import_taxonomy(dump_path)
    print("Done.")


if __name__ == "__main__":
    main()
