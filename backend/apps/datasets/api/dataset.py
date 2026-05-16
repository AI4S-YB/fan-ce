# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder

from apps.common.depends import check_permission, get_active_user
from db.database import get_db
from libs.responses.response import response_200

from ..schemas import (
    DatasetDeleteRequest,
    DatasetInfoRequest,
    DatasetListRequest,
    DatasetOptionsRequest,
    DatasetQueryCapabilitiesRequest,
    DatasetQueryRequest,
    DatasetPublishRecordListRequest,
    DatasetPublishRequest,
    DatasetStateTransitionRequest,
    DatasetTaskListRequest,
    DatasetUpdateRequest,
)
from ..services import dataset_domain_service

dataset_router = APIRouter(tags=["app:dataset:数据集"])


@dataset_router.post("/list", dependencies=[Depends(check_permission(["app:database:list"]))], summary="数据集列表")
async def dataset_list(request_data: DatasetListRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    data = dataset_domain_service.list_datasets(db=db, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_router.post("/options", dependencies=[Depends(check_permission(["app:database:list"]))], summary="数据集选项")
async def dataset_options(request_data: DatasetOptionsRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    data = dataset_domain_service.get_options(db=db, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_router.post("/info", dependencies=[Depends(check_permission(["app:database:info"]))], summary="数据集详情")
async def dataset_info(request_data: DatasetInfoRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    data = dataset_domain_service.get_dataset(db=db, dataset_id=request_data.id, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_router.post("/update", dependencies=[Depends(check_permission(["app:database:update"]))], summary="更新数据集控制面信息")
async def dataset_update(request_data: DatasetUpdateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    data = dataset_domain_service.update_dataset(db=db, dataset_id=request_data.id, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_router.post("/delete", dependencies=[Depends(check_permission(["app:database:delete"]))], summary="删除数据集记录")
async def dataset_delete(request_data: DatasetDeleteRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    data = dataset_domain_service.delete_dataset(db=db, dataset_id=request_data.id, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_router.post("/workflow/transition", dependencies=[Depends(check_permission(["app:database:update"]))], summary="推进数据集工作流状态")
async def dataset_transition(
    request_data: DatasetStateTransitionRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.transition_state(
        db=db,
        dataset_id=request_data.id,
        request_data=request_data,
        user=_user,
    )
    return response_200(data=jsonable_encoder(data))


@dataset_router.post("/publish", dependencies=[Depends(check_permission(["app:database:update"]))], summary="发布数据集")
async def dataset_publish(request_data: DatasetPublishRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    data = dataset_domain_service.publish_dataset(db=db, dataset_id=request_data.id, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_router.post("/unpublish", dependencies=[Depends(check_permission(["app:database:update"]))], summary="撤回公开数据集")
async def dataset_unpublish(request_data: DatasetPublishRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    data = dataset_domain_service.unpublish_dataset(db=db, dataset_id=request_data.id, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_router.post("/workflow/tasks", dependencies=[Depends(check_permission(["app:database:info"]))], summary="数据集工作流任务列表")
async def dataset_tasks(request_data: DatasetTaskListRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    data = dataset_domain_service.get_task_list(db=db, dataset_id=request_data.id, limit=request_data.limit or 20, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_router.post("/publish/records", dependencies=[Depends(check_permission(["app:database:info"]))], summary="数据集发布记录")
async def dataset_publish_records(
    request_data: DatasetPublishRecordListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.get_publish_record_list(db=db, dataset_id=request_data.id, limit=request_data.limit or 20, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_router.post("/query/capabilities", dependencies=[Depends(check_permission(["app:database:info"]))], summary="查看数据集查询能力")
async def dataset_query_capabilities(
    request_data: DatasetQueryCapabilitiesRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.get_query_capabilities(
        db=db,
        dataset_id=request_data.id,
        asset_code=request_data.asset_code,
        user=_user,
    )
    return response_200(data=jsonable_encoder(data))


@dataset_router.post("/query/execute", dependencies=[Depends(check_permission(["app:database:info"]))], summary="通过适配器执行数据集查询")
async def dataset_query_execute(
    request_data: DatasetQueryRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.execute_query(
        db=db,
        dataset_id=request_data.id,
        operation=request_data.operation,
        asset_code=request_data.asset_code,
        params=request_data.params or {},
        user=_user,
    )
    return response_200(data=jsonable_encoder(data))
