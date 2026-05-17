import time

from sqlalchemy.exc import OperationalError

from modules.breeding.models import BreedingTaxonomyNode
from shared.database import MyDBManager, engine

from .base.models import SysLog, SystemDictData, SystemDictField, SystemInstallJob, SystemInstallLock, SystemInstallPackage


def init_system_tables():
    """Tables are now created by alembic migration (consolidate_init_tables).
    This function keeps only the install defaults check."""
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
