import json
from datetime import datetime

from apps.breeding.models import BreedingTaxonomySourceSnapshot
from apps.breeding.taxonomy_loader import load_taxonomy_dump
from apps.system.base.models import SystemInstallJob, SystemInstallLock, SystemInstallPackage
from db.database import MyDBManager

from .setup_state import (
    TAXONOMY_JOB_TYPE,
    TAXONOMY_LOCK_CODE,
    TAXONOMY_PACKAGE_TYPES,
    query_taxonomy_setup_state,
    serialize_install_job,
)


def _now():
    return datetime.now()


def _decode_json_text(text_value):
    raw = (text_value or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _encode_json_text(payload):
    return json.dumps(payload or {}, ensure_ascii=False)


def _get_taxonomy_package(db, package_id):
    package_obj = db.query(SystemInstallPackage).filter(SystemInstallPackage.id == package_id).first()
    if not package_obj:
        raise ValueError("安装包不存在")
    if package_obj.package_type not in TAXONOMY_PACKAGE_TYPES:
        raise ValueError("安装包类型不支持 taxonomy 导入")
    return package_obj


def _get_latest_taxonomy_snapshot(db):
    return db.query(BreedingTaxonomySourceSnapshot).order_by(BreedingTaxonomySourceSnapshot.id.desc()).first()


def _get_taxonomy_lock(db):
    lock_obj = db.query(SystemInstallLock).filter(SystemInstallLock.lock_code == TAXONOMY_LOCK_CODE).first()
    if lock_obj is None:
        lock_obj = SystemInstallLock(
            lock_code=TAXONOMY_LOCK_CODE,
            is_locked=1,
            reason="taxonomy 未安装",
            required_action="install_taxonomy",
        )
        db.add(lock_obj)
        db.flush()
    return lock_obj


def _apply_taxonomy_lock_state(db, *, stage: str, latest_snapshot=None, error_message: str | None = None):
    lock_obj = _get_taxonomy_lock(db)
    if stage == "running" and latest_snapshot is None:
        lock_obj.is_locked = 1
        lock_obj.reason = "taxonomy 导入中"
    elif latest_snapshot is not None:
        lock_obj.is_locked = 0
        lock_obj.reason = "taxonomy 已安装"
    else:
        lock_obj.is_locked = 1
        lock_obj.reason = error_message or "taxonomy 未安装"
    lock_obj.required_action = "install_taxonomy"
    db.add(lock_obj)
    return lock_obj


def submit_taxonomy_import_job(db, *, package_id: int, force_reinstall: bool = False, operator_id: int | None = None):
    running_job = (
        db.query(SystemInstallJob)
        .filter(SystemInstallJob.job_type == TAXONOMY_JOB_TYPE, SystemInstallJob.status.in_(["pending", "running"]))
        .order_by(SystemInstallJob.id.desc())
        .first()
    )
    if running_job:
        raise ValueError("已有 taxonomy 导入任务正在执行")

    package_obj = _get_taxonomy_package(db, package_id)
    latest_snapshot = _get_latest_taxonomy_snapshot(db)
    if latest_snapshot and not force_reinstall:
        raise ValueError("taxonomy 已安装，如需重装请设置 force_reinstall=true")

    request_payload = {
        "package_id": package_obj.id,
        "force_reinstall": bool(force_reinstall),
        "package_code": package_obj.package_code,
        "source_version": package_obj.source_version,
    }
    job_obj = SystemInstallJob(
        job_type=TAXONOMY_JOB_TYPE,
        package_id=package_obj.id,
        status="pending",
        stage="queued",
        progress_percent=0,
        message="taxonomy 导入任务已提交",
        result_json=_encode_json_text(request_payload),
        created_by=operator_id,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(job_obj)
    db.commit()
    db.refresh(job_obj)
    return serialize_install_job(job_obj)


def get_taxonomy_import_job(db, *, job_id: int | None = None):
    query = db.query(SystemInstallJob).filter(SystemInstallJob.job_type == TAXONOMY_JOB_TYPE)
    if job_id:
        job_obj = query.filter(SystemInstallJob.id == job_id).first()
    else:
        job_obj = query.order_by(SystemInstallJob.id.desc()).first()
    if not job_obj:
        return None
    payload = serialize_install_job(job_obj)
    payload["setup_state"] = query_taxonomy_setup_state(db)
    return payload


def run_taxonomy_import_job(job_id: int):
    with MyDBManager() as db:
        job_obj = db.query(SystemInstallJob).filter(SystemInstallJob.id == job_id).first()
        if not job_obj or job_obj.job_type != TAXONOMY_JOB_TYPE:
            return

        try:
            package_obj = _get_taxonomy_package(db, job_obj.package_id)
            request_payload = _decode_json_text(job_obj.result_json)
            force_reinstall = bool(request_payload.get("force_reinstall"))

            latest_snapshot = _get_latest_taxonomy_snapshot(db)
            _apply_taxonomy_lock_state(db, stage="running", latest_snapshot=latest_snapshot)
            job_obj.status = "running"
            job_obj.stage = "package_check"
            job_obj.progress_percent = 5
            job_obj.started_at = _now()
            job_obj.updated_at = _now()
            job_obj.message = "正在检查 taxonomy 安装包"
            db.add(job_obj)
            db.commit()

            source_version = package_obj.source_version or request_payload.get("source_version")
            source_name = "ncbi_new_taxdump"
            job_obj.stage = "importing"
            job_obj.progress_percent = 20
            job_obj.updated_at = _now()
            job_obj.message = "正在导入 taxonomy 数据"
            db.add(job_obj)
            db.commit()

            result = load_taxonomy_dump(
                db=db,
                dump_path=package_obj.storage_path,
                source_name=source_name,
                source_version=source_version,
                reset_existing=bool(force_reinstall),
            )

            latest_snapshot = _get_latest_taxonomy_snapshot(db)
            _apply_taxonomy_lock_state(db, stage="success", latest_snapshot=latest_snapshot)
            job_payload = {
                **request_payload,
                "result": result,
            }
            job_obj.status = "success"
            job_obj.stage = "completed"
            job_obj.progress_percent = 100
            job_obj.processed_count = result.get("node_count")
            job_obj.total_count = result.get("node_count")
            job_obj.message = "taxonomy 导入完成"
            job_obj.error_message = None
            job_obj.result_json = _encode_json_text(job_payload)
            job_obj.finished_at = _now()
            job_obj.updated_at = _now()
            db.add(job_obj)
            db.commit()
        except Exception as exc:
            latest_snapshot = _get_latest_taxonomy_snapshot(db)
            _apply_taxonomy_lock_state(
                db,
                stage="failed",
                latest_snapshot=latest_snapshot,
                error_message=f"taxonomy 导入失败: {exc}",
            )
            job_obj = db.query(SystemInstallJob).filter(SystemInstallJob.id == job_id).first()
            job_obj.status = "failed"
            job_obj.stage = "failed"
            job_obj.message = "taxonomy 导入失败"
            job_obj.error_message = str(exc)
            job_obj.finished_at = _now()
            job_obj.updated_at = _now()
            db.add(job_obj)
            db.commit()
