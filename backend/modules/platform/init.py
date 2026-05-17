import time

from sqlalchemy.exc import OperationalError

from db.database import engine

from .models import PlatformModelApiSetting, PlatformSiteDatasetLink, PlatformSiteSetting


def init_platform_tables():
    tables = [
        PlatformSiteSetting.__table__,
        PlatformSiteDatasetLink.__table__,
        PlatformModelApiSetting.__table__,
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
