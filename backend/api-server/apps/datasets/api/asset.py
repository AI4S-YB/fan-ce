from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder

from apps.common.depends import check_permission, get_active_user
from db.database import get_db
from libs.responses.response import response_2000

from ..schemas import (
    AssetFileDeleteRequest,
    AssetFileInfoRequest,
    AssetFileListRequest,
    AssetFileRegisterRequest,
    AssetFileUpdateRequest,
    DatasetAssetCreateRequest,
    DatasetAssetDeleteRequest,
    DatasetAssetInfoRequest,
    DatasetAssetListRequest,
    DatasetAssetUpdateRequest,
)
from ..services import dataset_domain_service

dataset_asset_router = APIRouter(tags=["app:dataset:资产"])


@dataset_asset_router.post("/list", dependencies=[Depends(check_permission(["app:database:info"]))], summary="数据集版本资产列表")
async def dataset_asset_list(
    request_data: DatasetAssetListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.list_dataset_assets(db=db, version_id=request_data.version_id, user=_user)
    return response_2000(data=jsonable_encoder(data))


@dataset_asset_router.post("/info", dependencies=[Depends(check_permission(["app:database:info"]))], summary="数据集资产详情")
async def dataset_asset_info(
    request_data: DatasetAssetInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.get_dataset_asset(db=db, asset_id=request_data.id, user=_user)
    return response_2000(data=jsonable_encoder(data))


@dataset_asset_router.post("/create", dependencies=[Depends(check_permission(["app:database:update"]))], summary="创建数据集资产")
async def dataset_asset_create(
    request_data: DatasetAssetCreateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.create_dataset_asset(db=db, request_data=request_data, user=_user)
    return response_2000(data=jsonable_encoder(data))


@dataset_asset_router.post("/update", dependencies=[Depends(check_permission(["app:database:update"]))], summary="更新数据集资产")
async def dataset_asset_update(
    request_data: DatasetAssetUpdateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.update_dataset_asset(db=db, asset_id=request_data.id, request_data=request_data, user=_user)
    return response_2000(data=jsonable_encoder(data))


@dataset_asset_router.post("/delete", dependencies=[Depends(check_permission(["app:database:update"]))], summary="删除数据集资产")
async def dataset_asset_delete(
    request_data: DatasetAssetDeleteRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.delete_dataset_asset(db=db, asset_id=request_data.id, user=_user)
    return response_2000(data=jsonable_encoder(data))


@dataset_asset_router.post("/file/list", dependencies=[Depends(check_permission(["app:database:info"]))], summary="资产文件列表")
async def asset_file_list(
    request_data: AssetFileListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.list_asset_files(db=db, asset_id=request_data.asset_id, user=_user)
    return response_2000(data=jsonable_encoder(data))


@dataset_asset_router.post("/file/info", dependencies=[Depends(check_permission(["app:database:info"]))], summary="资产文件详情")
async def asset_file_info(
    request_data: AssetFileInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.get_asset_file(db=db, asset_file_id=request_data.id, user=_user)
    return response_2000(data=jsonable_encoder(data))


@dataset_asset_router.post("/file/register", dependencies=[Depends(check_permission(["app:database:update"]))], summary="登记资产文件")
async def asset_file_register(
    request_data: AssetFileRegisterRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.register_asset_file(db=db, request_data=request_data, user=_user)
    return response_2000(data=jsonable_encoder(data))


@dataset_asset_router.post("/file/update", dependencies=[Depends(check_permission(["app:database:update"]))], summary="更新资产文件")
async def asset_file_update(
    request_data: AssetFileUpdateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.update_asset_file(db=db, asset_file_id=request_data.id, request_data=request_data, user=_user)
    return response_2000(data=jsonable_encoder(data))


@dataset_asset_router.post("/file/delete", dependencies=[Depends(check_permission(["app:database:update"]))], summary="删除资产文件")
async def asset_file_delete(
    request_data: AssetFileDeleteRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.delete_asset_file(db=db, asset_file_id=request_data.id, user=_user)
    return response_2000(data=jsonable_encoder(data))
