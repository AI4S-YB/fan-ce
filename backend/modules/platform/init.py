import time

from sqlalchemy.exc import OperationalError

from shared.database import engine

from .models import PlatformModelApiSetting, PlatformSiteDatasetLink, PlatformSiteSetting


def init_platform_tables():
    """Tables are now created by alembic migration (consolidate_init_tables)."""
    pass
