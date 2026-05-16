import os
from apps.breeding.init import init_breeding_tables
from apps.datasets.init import init_dataset_tables, seed_dataset_registry_defaults
from apps.platform.init import init_platform_tables
from apps.system.init import init_system_tables
from db.bootstrap import init_dev_seed_data
from db.init import init_db
from db.database import MyDBManager
from core.config import settings

app_options = settings.app_options
from utils.fileaction import file_update


def register_init(app):
    # Ensure PostgreSQL extensions exist before creating tables
    from db.database import engine
    if engine.dialect.name == "postgresql":
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    init_dataset_tables()
    init_breeding_tables()
    init_platform_tables()
    init_system_tables()
    seed_dataset_registry_defaults()

    # Ensure analysis tables exist (worker requires brd_analysis_job)
    try:
        from apps.analysis.models import BrdAnalysisJob
        BrdAnalysisJob.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        pass

    # Start analysis worker (registers tools + launches worker threads)
    try:
        from apps.analysis.routers import on_startup
        on_startup()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Analysis startup failed: {e}")

    if app_options.get('app.db_init'):
        init_db()
    if app_options.get('app.seed_data'):
        with MyDBManager() as db:
            init_dev_seed_data(db)
    if app_options.get('app.alembic'):
        from db.database import database_url
        file_update(file=os.path.join(settings.BASE_PATH, 'alembic.ini'), filed='alembic.sqlalchemy.url', value=database_url)
