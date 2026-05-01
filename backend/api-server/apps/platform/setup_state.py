import json
import os
from decimal import Decimal
from datetime import datetime

from apps.breeding.models import BreedingTaxonomySourceSnapshot
from apps.system.base.models import SystemInstallJob, SystemInstallLock, SystemInstallPackage

TAXONOMY_PACKAGE_TYPES = ("taxonomy_bundle", "taxonomy_raw_dump")
TAXONOMY_JOB_TYPE = "taxonomy_import"
TAXONOMY_LOCK_CODE = "taxonomy_required"


def normalize_decimal(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def serialize_install_package(package_obj: SystemInstallPackage | None):
    if not package_obj:
        return None
    data = package_obj.to_dict()
    if data.get("created_at") is not None:
        data["created_at"] = data["created_at"].isoformat()
    if data.get("updated_at") is not None:
        data["updated_at"] = data["updated_at"].isoformat()
    return data


def serialize_install_job(job_obj: SystemInstallJob | None):
    if not job_obj:
        return None
    data = job_obj.to_dict()
    data["progress_percent"] = normalize_decimal(data.get("progress_percent"))
    for field in ("started_at", "finished_at", "created_at", "updated_at"):
        if data.get(field) is not None:
            data[field] = data[field].isoformat()
    return data


def serialize_snapshot(snapshot_obj: BreedingTaxonomySourceSnapshot | None):
    if not snapshot_obj:
        return None
    return {
        "id": snapshot_obj.id,
        "source_name": snapshot_obj.source_name,
        "source_version": snapshot_obj.source_version,
        "archive_path": snapshot_obj.archive_path,
        "extracted_path": snapshot_obj.extracted_path,
        "node_count": snapshot_obj.node_count,
        "name_count": snapshot_obj.name_count,
        "notes": snapshot_obj.notes,
        "loaded_at": snapshot_obj.loaded_at.isoformat() if snapshot_obj.loaded_at else None,
    }


def normalize_json_text(text_value: str | None):
    raw = (text_value or "").strip()
    if not raw:
        return "{}"
    try:
        return json.dumps(json.loads(raw), ensure_ascii=False)
    except Exception:
        return raw


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


def infer_taxonomy_status(lock_obj, snapshot_obj, package_obj, latest_job):
    if snapshot_obj and (lock_obj is None or not int(getattr(lock_obj, "is_locked", 1) or 0)):
        return "ready"
    job_status = (getattr(latest_job, "status", "") or "").lower()
    if job_status in {"pending", "running"}:
        return "importing"
    if job_status in {"failed", "error", "cancelled"}:
        return "failed"
    if package_obj:
        return "package_ready"
    return "not_installed"


def query_taxonomy_setup_state(db):
    lock_obj = db.query(SystemInstallLock).filter(SystemInstallLock.lock_code == TAXONOMY_LOCK_CODE).first()
    package_obj = (
        db.query(SystemInstallPackage)
        .filter(SystemInstallPackage.package_type.in_(TAXONOMY_PACKAGE_TYPES))
        .order_by(SystemInstallPackage.id.desc())
        .first()
    )
    latest_job = (
        db.query(SystemInstallJob)
        .filter(SystemInstallJob.job_type == TAXONOMY_JOB_TYPE)
        .order_by(SystemInstallJob.id.desc())
        .first()
    )
    snapshot_obj = (
        db.query(BreedingTaxonomySourceSnapshot)
        .order_by(BreedingTaxonomySourceSnapshot.id.desc())
        .first()
    )
    if lock_obj is None and snapshot_obj is not None:
        lock_data = {
            "lock_code": TAXONOMY_LOCK_CODE,
            "is_locked": 0,
            "reason": "taxonomy 已安装",
            "required_action": "install_taxonomy",
            "payload_json": None,
            "updated_at": None,
        }
    else:
        lock_data = serialize_lock(lock_obj)
    status = infer_taxonomy_status(lock_obj, snapshot_obj, package_obj, latest_job)
    ready = status == "ready"
    return {
        "lock": lock_data,
        "status": status,
        "ready": ready,
        "package": serialize_install_package(package_obj),
        "job": serialize_install_job(latest_job),
        "snapshot": serialize_snapshot(snapshot_obj),
    }


def is_taxonomy_ready(db):
    return bool(query_taxonomy_setup_state(db).get("ready"))


def list_taxonomy_packages(db):
    rows = (
        db.query(SystemInstallPackage)
        .filter(SystemInstallPackage.package_type.in_(TAXONOMY_PACKAGE_TYPES))
        .order_by(SystemInstallPackage.created_at.desc(), SystemInstallPackage.id.desc())
        .all()
    )
    items = [serialize_install_package(row) for row in rows]
    recommended_package = next((item for item in items if item.get("status") == "ready"), None)
    if recommended_package is None and items:
        recommended_package = items[0]
    return {
        "items": items,
        "recommended_package": recommended_package,
    }


def register_taxonomy_package(db, *, payload: dict, created_by: int | None = None):
    package_code = (payload.get("package_code") or "").strip()
    package_name = (payload.get("package_name") or "").strip()
    package_type = (payload.get("package_type") or "").strip()
    storage_path = (payload.get("storage_path") or "").strip()
    source = (payload.get("source") or "builtin").strip()
    source_version = (payload.get("source_version") or "").strip() or None
    sha256 = (payload.get("sha256") or "").strip() or None
    status = (payload.get("status") or "ready").strip() or "ready"
    if not package_code:
        raise ValueError("package_code 不能为空")
    if not package_name:
        raise ValueError("package_name 不能为空")
    if package_type not in TAXONOMY_PACKAGE_TYPES:
        raise ValueError("package_type 不合法")
    if not storage_path:
        raise ValueError("storage_path 不能为空")
    if not os.path.exists(storage_path):
        raise ValueError("安装包路径不存在")

    file_size = payload.get("file_size")
    if not file_size:
        file_size = os.path.getsize(storage_path)

    now = datetime.now()
    package_obj = db.query(SystemInstallPackage).filter(SystemInstallPackage.package_code == package_code).first()
    if not package_obj:
        package_obj = SystemInstallPackage(package_code=package_code, created_by=created_by)
        db.add(package_obj)
    package_obj.package_name = package_name
    package_obj.package_type = package_type
    package_obj.storage_path = storage_path
    package_obj.source = source
    package_obj.source_version = source_version
    package_obj.sha256 = sha256
    package_obj.file_size = int(file_size or 0)
    package_obj.manifest_json = normalize_json_text(payload.get("manifest_json"))
    package_obj.status = status
    package_obj.created_by = created_by
    package_obj.updated_at = now
    db.add(package_obj)
    db.commit()
    db.refresh(package_obj)
    return serialize_install_package(package_obj)
