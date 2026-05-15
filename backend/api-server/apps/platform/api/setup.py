from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from apps.common.depends import get_active_user
from db.database import get_db
from libs.responses.response import response_200
from ..schemas import PlatformSetupTaxonomyImportStartRequest
from ..setup_jobs import get_taxonomy_import_job, run_taxonomy_import_job, submit_taxonomy_import_job
from ..setup_state import query_taxonomy_setup_state

setup_router = APIRouter(tags=["app:platform:平台初始化"])


def _require_platform_admin(user):
    if getattr(user, "is_superman", False) or int(getattr(user, "user_type", 0) or 0) == 1:
        return
    raise HTTPException(status_code=4030, detail="没有权限")


@setup_router.get("/setup/status", summary="平台初始化状态")
async def get_setup_status(
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    _require_platform_admin(_user)
    state = query_taxonomy_setup_state(db)
    return response_200(
        data={
            "taxonomy_ready": state["ready"],
            "taxonomy_status": state["status"],
            "locks": [state["lock"]],
        }
    )


@setup_router.get("/setup/taxonomy/current", summary="当前 taxonomy 初始化状态")
async def get_taxonomy_current(
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    _require_platform_admin(_user)
    state = query_taxonomy_setup_state(db)
    return response_200(
        data={
            "ready": state["ready"],
            "status": state["status"],
            "node_count": state["node_count"],
            "latest_job": state["latest_job"],
            "lock": state["lock"],
        }
    )


@setup_router.post("/setup/taxonomy/import/start", summary="启动 taxonomy 导入任务")
async def start_taxonomy_import(
    request_data: PlatformSetupTaxonomyImportStartRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    _require_platform_admin(_user)
    try:
        job_data = submit_taxonomy_import_job(
            db,
            force_reinstall=bool(request_data.force_reinstall),
            operator_id=getattr(_user, "id", None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=4000, detail=str(exc)) from exc
    background_tasks.add_task(run_taxonomy_import_job, job_data["id"])
    return response_200(data=job_data)


@setup_router.get("/setup/taxonomy/import/status", summary="查询 taxonomy 导入任务状态")
async def get_taxonomy_import_status(
    job_id: int | None = None,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    _require_platform_admin(_user)
    data = get_taxonomy_import_job(db, job_id=job_id)
    if data is None:
        return response_200(data={})
    return response_200(data=data)
