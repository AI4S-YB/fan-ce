import time

from sqlalchemy.exc import OperationalError

from apps.breeding.models import BreedingTaxonomyNode
from db.database import MyDBManager, engine

from .base.models import SysLog, SystemDictData, SystemDictField, SystemInstallJob, SystemInstallLock, SystemInstallPackage


def init_system_tables():
    tables = [
        SystemDictData.__table__,
        SystemDictField.__table__,
        SysLog.__table__,
        SystemInstallPackage.__table__,
        SystemInstallJob.__table__,
        SystemInstallLock.__table__,
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
    _ensure_install_defaults()


def _ensure_install_defaults():
    with MyDBManager() as db:
        taxonomy_node_count = db.query(BreedingTaxonomyNode).count()
        has_taxonomy = taxonomy_node_count > 0

        lock_obj = db.query(SystemInstallLock).filter(
            SystemInstallLock.lock_code == "taxonomy_required"
        ).first()
        if not lock_obj:
            lock_obj = SystemInstallLock(
                lock_code="taxonomy_required",
                required_action="install_taxonomy",
            )
            db.add(lock_obj)

        if has_taxonomy:
            lock_obj.is_locked = 0
            lock_obj.reason = "taxonomy 已安装"
        else:
            lock_obj.is_locked = 1
            lock_obj.reason = "taxonomy 未安装"
        lock_obj.required_action = "install_taxonomy"
        db.add(lock_obj)
        db.commit()
