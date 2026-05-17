import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from modules.breeding.models import BreedingTaxonomyNode
from modules.breeding.taxonomy_loader import load_taxonomy_dump
from modules.system.base.models import SystemInstallJob, SystemInstallLock
from shared.database import MyDBManager

from .setup_state import TAXONOMY_LOCK_CODE, query_taxonomy_setup_state


_BUILTIN_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
BUILTIN_TAXONOMY_DUMP = _BUILTIN_DATA_DIR / "taxonomy-plants.tar.gz"


def _now():
    return datetime.now()


def _encode_json_text(payload):
    return json.dumps(payload or {}, ensure_ascii=False)


def _decode_json_text(text_value):
    raw = (text_value or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _get_taxonomy_lock(db):
    lock_obj = db.query(SystemInstallLock).filter(
        SystemInstallLock.lock_code == TAXONOMY_LOCK_CODE
    ).first()
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


def _apply_taxonomy_lock_state(db, *, stage: str, node_count: int = 0, error_message: str | None = None):
    lock_obj = _get_taxonomy_lock(db)
    if stage == "running":
        lock_obj.is_locked = 1
        lock_obj.reason = "taxonomy 导入中"
    elif node_count > 0:
        lock_obj.is_locked = 0
        lock_obj.reason = "taxonomy 已安装"
    else:
        lock_obj.is_locked = 1
        lock_obj.reason = error_message or "taxonomy 未安装"
    lock_obj.required_action = "install_taxonomy"
    db.add(lock_obj)
    return lock_obj


def _serialize_job(job_obj):
    data = job_obj.to_dict()
    if isinstance(data.get("progress_percent"), Decimal):
        data["progress_percent"] = float(data["progress_percent"])
    for field in ("started_at", "finished_at", "created_at", "updated_at"):
        if data.get(field) is not None:
            data[field] = data[field].isoformat()
    return data


def submit_taxonomy_import_job(db, *, force_reinstall: bool = False, dump_path: str | None = None, operator_id: int | None = None):
    running_job = (
        db.query(SystemInstallJob)
        .filter(SystemInstallJob.job_type == "taxonomy_import", SystemInstallJob.status.in_(["pending", "running"]))
        .order_by(SystemInstallJob.id.desc())
        .first()
    )
    if running_job:
        raise ValueError("已有 taxonomy 导入任务正在执行")

    node_count = db.query(BreedingTaxonomyNode).count()
    if node_count > 0 and not force_reinstall:
        raise ValueError("taxonomy 已安装，如需重装请设置 force_reinstall=true")

    job_obj = SystemInstallJob(
        job_type="taxonomy_import",
        status="pending",
        stage="queued",
        progress_percent=0,
        message="taxonomy 导入任务已提交",
        result_json=_encode_json_text({"force_reinstall": bool(force_reinstall), "dump_path": dump_path}),
        created_by=operator_id,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(job_obj)
    db.commit()
    db.refresh(job_obj)
    return _serialize_job(job_obj)


def get_taxonomy_import_job(db, *, job_id: int | None = None):
    query = db.query(SystemInstallJob).filter(SystemInstallJob.job_type == "taxonomy_import")
    if job_id:
        job_obj = query.filter(SystemInstallJob.id == job_id).first()
    else:
        job_obj = query.order_by(SystemInstallJob.id.desc()).first()
    if not job_obj:
        return None
    payload = _serialize_job(job_obj)
    payload["setup_state"] = query_taxonomy_setup_state(db)
    return payload


def run_taxonomy_import_job(job_id: int):
    with MyDBManager() as db:
        job_obj = db.query(SystemInstallJob).filter(SystemInstallJob.id == job_id).first()
        if not job_obj or job_obj.job_type != "taxonomy_import":
            return

        try:
            request_payload = _decode_json_text(job_obj.result_json)
            force_reinstall = bool(request_payload.get("force_reinstall"))
            custom_dump_path = request_payload.get("dump_path")

            dump_path = custom_dump_path or str(BUILTIN_TAXONOMY_DUMP)
            if not Path(dump_path).exists():
                raise FileNotFoundError(f"taxonomy 数据文件不存在: {dump_path}")

            _apply_taxonomy_lock_state(db, stage="running")
            job_obj.status = "running"
            job_obj.stage = "importing"
            job_obj.progress_percent = 10
            job_obj.started_at = _now()
            job_obj.updated_at = _now()
            job_obj.message = f"正在导入 taxonomy 数据: {dump_path}"
            db.add(job_obj)
            db.commit()

            result = load_taxonomy_dump(
                db=db,
                dump_path=dump_path,
                source_name="ncbi_plant_taxdump",
                source_version=None,
                reset_existing=bool(force_reinstall),
            )

            _apply_taxonomy_lock_state(db, stage="success", node_count=result.get("node_count", 0))
            job_obj.status = "success"
            job_obj.stage = "completed"
            job_obj.progress_percent = 100
            job_obj.processed_count = result.get("node_count")
            job_obj.total_count = result.get("node_count")
            job_obj.message = "植物 taxonomy 导入完成"
            job_obj.error_message = None
            job_obj.result_json = _encode_json_text({**request_payload, "result": result})
            job_obj.finished_at = _now()
            job_obj.updated_at = _now()
            db.add(job_obj)
            db.commit()
        except Exception as exc:
            _apply_taxonomy_lock_state(db, stage="failed", error_message=f"taxonomy 导入失败: {exc}")
            job_obj = db.query(SystemInstallJob).filter(SystemInstallJob.id == job_id).first()
            job_obj.status = "failed"
            job_obj.stage = "failed"
            job_obj.message = "taxonomy 导入失败"
            job_obj.error_message = str(exc)
            job_obj.finished_at = _now()
            job_obj.updated_at = _now()
            db.add(job_obj)
            db.commit()
