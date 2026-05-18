from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder

from modules.common.depends import check_permission, get_active_user
from shared.database import get_db
from shared.responses import response_200

from ..schemas import (
    DatasetVersionUpdateRequest,
    DatasetVersionActivateRequest,
    DatasetVersionCreateRequest,
    DatasetVersionInfoRequest,
    DatasetVersionListRequest,
    DatasetVersionPublishRecordListRequest,
    DatasetVersionQueryCapabilitiesRequest,
    DatasetVersionQueryRequest,
    DatasetVersionReleaseRequest,
    DatasetVersionWithdrawRequest,
)
from ..services import dataset_domain_service
from ..crud import dataset_version_db

dataset_version_router = APIRouter(tags=["app:dataset:版本"])
@dataset_version_router.post("/list", dependencies=[Depends(check_permission(["app:database:info"]))], summary="数据集版本列表")
async def dataset_version_list(
    request_data: DatasetVersionListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.list_dataset_versions(db=db, dataset_id=request_data.dataset_id, user=_user)
    return response_200(data=jsonable_encoder(data))
@dataset_version_router.post("/info", dependencies=[Depends(check_permission(["app:database:info"]))], summary="数据集版本详情")
async def dataset_version_info(
    request_data: DatasetVersionInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.get_dataset_version(db=db, version_id=request_data.id, user=_user)
    return response_200(data=jsonable_encoder(data))
@dataset_version_router.post("/query/capabilities", dependencies=[Depends(check_permission(["app:database:info"]))], summary="查看指定版本查询能力")
async def dataset_version_query_capabilities(
    request_data: DatasetVersionQueryCapabilitiesRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db,
        version_id=request_data.id,
        asset_code=request_data.asset_code,
        user=_user,
    )
    return response_200(data=jsonable_encoder(data))
@dataset_version_router.post("/query/execute", dependencies=[Depends(check_permission(["app:database:info"]))], summary="执行指定版本查询")
async def dataset_version_query_execute(
    request_data: DatasetVersionQueryRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.execute_dataset_version_query(
        db=db,
        version_id=request_data.id,
        operation=request_data.operation,
        asset_code=request_data.asset_code,
        params=request_data.params or {},
        user=_user,
    )
    return response_200(data=jsonable_encoder(data))
@dataset_version_router.post("/create", dependencies=[Depends(check_permission(["app:database:update"]))], summary="创建数据集草稿版本")
async def dataset_version_create(
    request_data: DatasetVersionCreateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.create_dataset_version(db=db, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))
@dataset_version_router.post("/activate", dependencies=[Depends(check_permission(["app:database:update"]))], summary="切换当前数据集版本")
async def dataset_version_activate(
    request_data: DatasetVersionActivateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.activate_dataset_version(db=db, version_id=request_data.id, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))
@dataset_version_router.post("/release", dependencies=[Depends(check_permission(["app:database:update"]))], summary="发布数据集版本")
async def dataset_version_release(
    request_data: DatasetVersionReleaseRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.release_dataset_version(db=db, version_id=request_data.id, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))
@dataset_version_router.post("/withdraw", dependencies=[Depends(check_permission(["app:database:update"]))], summary="撤回数据集版本公开")
async def dataset_version_withdraw(
    request_data: DatasetVersionWithdrawRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.withdraw_dataset_version(db=db, version_id=request_data.id, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))

@dataset_version_router.post("/publish/records", dependencies=[Depends(check_permission(["app:database:info"]))], summary="数据集版本发布记录")
async def dataset_version_publish_records(
    request_data: DatasetVersionPublishRecordListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.get_version_publish_record_list(
        db=db,
        dataset_id=request_data.dataset_id,
        version_id=request_data.version_id,
        limit=request_data.limit or 20,
        user=_user,
    )
    return response_200(data=jsonable_encoder(data))

@dataset_version_router.post("/update", dependencies=[Depends(check_permission(["app:database:update"]))], summary="更新数据集版本信息")
async def dataset_version_update(
    request_data: DatasetVersionUpdateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    version_obj = dataset_domain_service._ensure_version_write_access(db=db, version_id=request_data.id, user=_user)
    update_data = {"update_time": dataset_domain_service._now()}
    if request_data.title is not None:
        update_data["title"] = request_data.title
    if request_data.version is not None:
        update_data["version"] = request_data.version
    dataset_version_db.update_one(db=db, db_obj=version_obj, obj_in=update_data)
    return response_200(data=jsonable_encoder(update_data))

