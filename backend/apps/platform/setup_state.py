from apps.breeding.models import BreedingTaxonomyNode
from apps.system.base.models import SystemInstallJob, SystemInstallLock

TAXONOMY_LOCK_CODE = "taxonomy_required"


def _serialize_job(job_obj):
    from decimal import Decimal

    data = job_obj.to_dict()
    if isinstance(data.get("progress_percent"), Decimal):
        data["progress_percent"] = float(data["progress_percent"])
    for field in ("started_at", "finished_at", "created_at", "updated_at"):
        if data.get(field) is not None:
            data[field] = data[field].isoformat()
    return data


def serialize_lock(lock_obj: SystemInstallLock | None):
    if not lock_obj:
        return {
            "lock_code": TAXONOMY_LOCK_CODE,
            "is_locked": 1,
            "reason": "taxonomy 未安装",
            "required_action": "install_taxonomy",
            "payload_json": None,
            "updated_at": None,
        }
    data = lock_obj.to_dict()
    if data.get("updated_at") is not None:
        data["updated_at"] = data["updated_at"].isoformat()
    return data


def query_taxonomy_setup_state(db):
    lock_obj = db.query(SystemInstallLock).filter(
        SystemInstallLock.lock_code == TAXONOMY_LOCK_CODE
    ).first()
    node_count = db.query(BreedingTaxonomyNode).count()
    has_taxonomy = node_count > 0

    lock_data = serialize_lock(lock_obj)
    ready = has_taxonomy and (
        lock_obj is not None and int(getattr(lock_obj, "is_locked", 1) or 0) == 0
    )
    status = "ready" if ready else ("not_installed" if not has_taxonomy else "importing")

    latest_job = (
        db.query(SystemInstallJob)
        .filter(SystemInstallJob.job_type == "taxonomy_import")
        .order_by(SystemInstallJob.id.desc())
        .first()
    )

    return {
        "lock": lock_data,
        "status": status,
        "ready": ready,
        "node_count": node_count,
        "latest_job": _serialize_job(latest_job) if latest_job else None,
    }


def is_taxonomy_ready(db):
    return bool(query_taxonomy_setup_state(db).get("ready"))
