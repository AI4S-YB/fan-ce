from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.encoders import jsonable_encoder

from apps.common.depends import check_permission, get_active_user
from db.database import get_db
from libs.responses.response import response_2000

from ..schemas import (
    DatasetIngestActionRequest,
    DatasetIngestPipelineRequest,
    DatasetIngestTaskSubmitRequest,
    DatasetRegisterRequest,
    DatasetWorkflowTaskInfoRequest,
    DatasetWorkflowTaskRetryRequest,
)
from ..services import dataset_domain_service

dataset_ingest_router = APIRouter(tags=["app:dataset:导入"])


@dataset_ingest_router.post("/register", dependencies=[Depends(check_permission(["app:database:add"]))], summary="注册服务器已有文件为 dataset")
async def dataset_register(
    request_data: DatasetRegisterRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.register_dataset_source(db=db, request_data=request_data, user=_user)
    return response_2000(data=jsonable_encoder(data))


@dataset_ingest_router.post("/validate", dependencies=[Depends(check_permission(["app:database:update"]))], summary="统一校验 dataset 或文件")
async def dataset_validate(
    request_data: DatasetIngestActionRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.validate_ingest_target(db=db, request_data=request_data, user=_user)
    return response_2000(data=jsonable_encoder(data))


@dataset_ingest_router.post("/index", dependencies=[Depends(check_permission(["app:database:update"]))], summary="统一建索引或转换 dataset")
async def dataset_index(
    request_data: DatasetIngestActionRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.index_ingest_target(db=db, request_data=request_data, user=_user)
    return response_2000(data=jsonable_encoder(data))


@dataset_ingest_router.post("/pipeline", dependencies=[Depends(check_permission(["app:database:update"]))], summary="执行 validate + index 标准流程")
async def dataset_pipeline(
    request_data: DatasetIngestPipelineRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.run_ingest_pipeline(db=db, request_data=request_data, user=_user)
    return response_2000(data=jsonable_encoder(data))


@dataset_ingest_router.post("/task/submit", dependencies=[Depends(check_permission(["app:database:update"]))], summary="提交异步 ingest 任务")
async def dataset_ingest_task_submit(
    request_data: DatasetIngestTaskSubmitRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.submit_ingest_task(db=db, request_data=request_data, user=_user)
    background_tasks.add_task(dataset_domain_service.run_ingest_task, data["id"])
    return response_2000(data=jsonable_encoder(data))


@dataset_ingest_router.post("/task/info", dependencies=[Depends(check_permission(["app:database:info"]))], summary="查看 ingest 任务详情")
async def dataset_ingest_task_info(
    request_data: DatasetWorkflowTaskInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.get_task_info(db=db, task_id=request_data.id, user=_user)
    return response_2000(data=jsonable_encoder(data))


@dataset_ingest_router.post("/task/retry", dependencies=[Depends(check_permission(["app:database:update"]))], summary="重试 ingest 任务")
async def dataset_ingest_task_retry(
    request_data: DatasetWorkflowTaskRetryRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.retry_ingest_task(db=db, task_id=request_data.id, user=_user)
    background_tasks.add_task(dataset_domain_service.run_ingest_task, data["id"])
    return response_2000(data=jsonable_encoder(data))
