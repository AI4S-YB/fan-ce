"""Analysis API endpoints."""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.common.depends import get_active_user

from db.database import get_db
from libs.responses.response import response_2000
from apps.analysis.models import BrdAnalysisJob
from apps.analysis.worker import get_tools, register_tool, _get_tool


class SubmitJobRequest(BaseModel):
    tool_id: str
    input_bindings: dict
    param_overrides: dict = {}


class FileSearchRequest(BaseModel):
    asset_types: list = []
    file_formats: list = []
    file_roles: list = []

analysis_router = APIRouter(tags=["app:analysis:分析任务"])


class JobResponse(BaseModel):
    id: int
    tool_id: str
    status: str
    input_bindings: dict
    param_overrides: dict
    output_files: list | None = None
    command_log: str | None = None
    exit_code: int | None = None
    error_message: str | None = None
    created_at: int | None = None
    started_at: int | None = None
    finished_at: int | None = None


@analysis_router.get("/tools", summary="列出可用的分析工具")
def list_tools():
    tools = get_tools()
    return response_2000(data=[
        {
            "tool_id": t.tool_id, "display_name": t.display_name,
            "description": t.description, "category": t.category,
            "version": t.tool_version,
            "input_schema": t.get_input_schema(),
            "parameter_schema": t.get_parameter_schema(),
            "output_schema": t.get_output_schema(),
            "timeout_seconds": t.timeout_seconds,
        }
        for t in tools
    ])


@analysis_router.post("/jobs", summary="提交分析任务")
def submit_job(req: SubmitJobRequest, db: Session = Depends(get_db), user_id: int = None):
    tool = _get_tool(req.tool_id)
    if not tool:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {req.tool_id}")

    # Validate input bindings exist
    from apps.datasets.models import AssetFile
    for param_name, asset_file_id in req.input_bindings.items():
        af = db.query(AssetFile).filter_by(id=asset_file_id).first()
        if not af:
            raise HTTPException(status_code=400, detail=f"AssetFile id={asset_file_id} not found")

    job = BrdAnalysisJob(
        tool_id=req.tool_id,
        status="pending",
        input_bindings=json.dumps(req.input_bindings),
        param_overrides=json.dumps(req.param_overrides),
        created_by=user_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return response_2000(data={"id": job.id, "status": job.status})


@analysis_router.get("/jobs/{job_id}", summary="查询任务状态")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(BrdAnalysisJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return response_2000(data={
        "id": job.id, "tool_id": job.tool_id, "status": job.status,
        "input_bindings": json.loads(job.input_bindings) if isinstance(job.input_bindings, str) else job.input_bindings,
        "param_overrides": json.loads(job.param_overrides) if isinstance(job.param_overrides, str) else job.param_overrides,
        "output_files": json.loads(job.output_files) if job.output_files else None,
        "command_log": job.command_log,
        "exit_code": job.exit_code,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    })


@analysis_router.get("/jobs", summary="列出用户的任务")
def list_jobs(page: int = 1, size: int = 20, db: Session = Depends(get_db)):
    total = db.query(BrdAnalysisJob).count()
    jobs = db.query(BrdAnalysisJob).order_by(BrdAnalysisJob.id.desc()) \
        .offset((page - 1) * size).limit(size).all()
    return response_2000(data={
        "items": [
            {
                "id": j.id, "tool_id": j.tool_id, "status": j.status,
                "created_at": j.created_at, "finished_at": j.finished_at,
            }
            for j in jobs
        ],
        "total": total, "page": page, "size": size,
    })


@analysis_router.post("/jobs/{job_id}/cancel", summary="取消任务")
def cancel_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(BrdAnalysisJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in ("pending", "running"):
        job.status = "cancelled"
        db.commit()
    return response_2000(data={"id": job.id, "status": job.status})


@analysis_router.post("/files/search", summary="搜索可用于分析的 asset_files")
def search_files(req: FileSearchRequest, db: Session = Depends(get_db)):
    from apps.datasets.models import AssetFile, DatasetAsset, DatasetRegistry
    query = db.query(AssetFile, DatasetAsset.asset_type, DatasetRegistry.dataset_code, DatasetRegistry.title)\
        .join(DatasetAsset, AssetFile.dataset_asset_id == DatasetAsset.id)\
        .join(DatasetRegistry, DatasetAsset.database_id == DatasetRegistry.database_id)
    if req.asset_types:
        query = query.filter(DatasetAsset.asset_type.in_(req.asset_types))
    if req.file_formats:
        query = query.filter(AssetFile.file_format.in_(req.file_formats))
    if req.file_roles:
        query = query.filter(AssetFile.file_role.in_(req.file_roles))
    rows = query.all()
    items = [{"id": af.id, "file_name": af.file_name, "file_format": af.file_format,
              "file_role": af.file_role, "file_size": af.file_size,
              "asset_type": at, "dataset_code": dc, "dataset_title": dt,
              "label": f"{dt or dc} / {af.file_name}"}
             for af, at, dc, dt in rows]
    return response_2000(data={"items": items, "total": len(items)})


# ── Admin endpoints ──

@analysis_router.get("/admin/tools", summary="管理端：列出分析工具（含状态）")
def admin_list_tools(_user=Depends(get_active_user)):
    tools = get_tools()
    return response_2000(data=[
        {
            "tool_id": t.tool_id, "display_name": t.display_name,
            "description": t.description, "category": t.category,
            "version": t.tool_version, "timeout_seconds": t.timeout_seconds,
            "input_schema": t.get_input_schema(),
            "parameter_schema": t.get_parameter_schema(),
            "output_schema": t.get_output_schema(),
            "dependencies": t.dependencies,
            "plugin_class": f"{t.__class__.__module__}:{t.__class__.__qualname__}",
        }
        for t in tools
    ])


@analysis_router.get("/admin/tools/{tool_id}", summary="管理端：查看工具详情")
def admin_get_tool(tool_id: str, _user=Depends(get_active_user)):
    from apps.analysis.worker import _get_tool
    t = _get_tool(tool_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tool not found")
    return response_2000(data={
        "tool_id": t.tool_id, "display_name": t.display_name,
        "description": t.description, "category": t.category,
        "version": t.tool_version, "timeout_seconds": t.timeout_seconds,
        "input_schema": t.get_input_schema(),
        "parameter_schema": t.get_parameter_schema(),
        "output_schema": t.get_output_schema(),
        "dependencies": t.dependencies,
        "plugin_class": f"{t.__class__.__module__}:{t.__class__.__qualname__}",
    })


@analysis_router.get("/jobs/{job_id}/output/{file_name}", summary="下载输出文件")
def download_output(job_id: int, file_name: str, db: Session = Depends(get_db)):
    import os
    from fastapi.responses import FileResponse
    job = db.query(BrdAnalysisJob).filter_by(id=job_id).first()
    if not job or not job.output_files:
        raise HTTPException(status_code=404, detail="File not found")
    outputs = json.loads(job.output_files) if isinstance(job.output_files, str) else job.output_files
    for f in outputs:
        if f.get("name") == file_name:
            path = f.get("path", "")
            if os.path.exists(path):
                return FileResponse(path, filename=os.path.basename(path))
    raise HTTPException(status_code=404, detail="File not found")
