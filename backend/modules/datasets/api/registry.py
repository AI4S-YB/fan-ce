from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder

from modules.common.depends import get_active_user
from shared.database import get_db
from shared.responses import response_200

from ..schemas import (
    AssetFileTypeRegistryCreateRequest,
    AssetFileTypeRegistryDeleteRequest,
    AssetFileTypeRegistryInfoRequest,
    AssetFileTypeRegistryListRequest,
    AssetFileTypeRegistryOptionsRequest,
    AssetFileTypeRegistryUpdateRequest,
    AssetTypeRegistryCreateRequest,
    AssetTypeRegistryDeleteRequest,
    AssetTypeRegistryInfoRequest,
    AssetTypeRegistryListRequest,
    AssetTypeRegistryOptionsRequest,
    AssetTypeRegistryUpdateRequest,
    DatasetKindRegistryCreateRequest,
    DatasetKindRegistryDeleteRequest,
    DatasetKindRegistryInfoRequest,
    DatasetKindRegistryListRequest,
    DatasetKindRegistryOptionsRequest,
    DatasetKindRegistryUpdateRequest,
)
from ..services import dataset_domain_service

dataset_registry_admin_router = APIRouter(tags=["app:dataset:类型注册表"])


@dataset_registry_admin_router.post("/kind/options", summary="数据集类型选项")
async def dataset_kind_options(request_data: DatasetKindRegistryOptionsRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    data = dataset_domain_service.get_dataset_kind_options(db=db, request_data=request_data)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/kind/list", summary="数据集类型注册表列表")
async def dataset_kind_list(
    request_data: DatasetKindRegistryListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.list_dataset_kind_registry(db=db, request_data=request_data)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/kind/info", summary="数据集类型注册表详情")
async def dataset_kind_info(
    request_data: DatasetKindRegistryInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.get_dataset_kind_registry(db=db, registry_id=request_data.id)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/kind/create", summary="创建数据集类型注册项")
async def dataset_kind_create(
    request_data: DatasetKindRegistryCreateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.create_dataset_kind_registry(db=db, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/kind/update", summary="更新数据集类型注册项")
async def dataset_kind_update(
    request_data: DatasetKindRegistryUpdateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.update_dataset_kind_registry(db=db, registry_id=request_data.id, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/kind/delete", summary="删除数据集类型注册项")
async def dataset_kind_delete(
    request_data: DatasetKindRegistryDeleteRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.delete_dataset_kind_registry(db=db, registry_id=request_data.id, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/asset-type/options", summary="资产类型选项")
async def asset_type_options(request_data: AssetTypeRegistryOptionsRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    data = dataset_domain_service.get_asset_type_options(db=db, request_data=request_data)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/asset-type/list", summary="资产类型注册表列表")
async def asset_type_list(
    request_data: AssetTypeRegistryListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.list_asset_type_registry(db=db, request_data=request_data)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/asset-type/info", summary="资产类型注册表详情")
async def asset_type_info(
    request_data: AssetTypeRegistryInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.get_asset_type_registry(db=db, registry_id=request_data.id)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/asset-type/create", summary="创建资产类型注册项")
async def asset_type_create(
    request_data: AssetTypeRegistryCreateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.create_asset_type_registry(db=db, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/asset-type/update", summary="更新资产类型注册项")
async def asset_type_update(
    request_data: AssetTypeRegistryUpdateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.update_asset_type_registry(db=db, registry_id=request_data.id, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/asset-type/delete", summary="删除资产类型注册项")
async def asset_type_delete(
    request_data: AssetTypeRegistryDeleteRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.delete_asset_type_registry(db=db, registry_id=request_data.id, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/asset-file-type/options", summary="资产文件类型选项")
async def asset_file_type_options(request_data: AssetFileTypeRegistryOptionsRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    data = dataset_domain_service.get_asset_file_type_options(db=db, request_data=request_data)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/asset-file-type/list", summary="资产文件类型注册表列表")
async def asset_file_type_list(
    request_data: AssetFileTypeRegistryListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.list_asset_file_type_registry(db=db, request_data=request_data)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/asset-file-type/info", summary="资产文件类型注册表详情")
async def asset_file_type_info(
    request_data: AssetFileTypeRegistryInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.get_asset_file_type_registry(db=db, registry_id=request_data.id)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/asset-file-type/create", summary="创建资产文件类型注册项")
async def asset_file_type_create(
    request_data: AssetFileTypeRegistryCreateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.create_asset_file_type_registry(db=db, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/asset-file-type/update", summary="更新资产文件类型注册项")
async def asset_file_type_update(
    request_data: AssetFileTypeRegistryUpdateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.update_asset_file_type_registry(db=db, registry_id=request_data.id, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_registry_admin_router.post("/asset-file-type/delete", summary="删除资产文件类型注册项")
async def asset_file_type_delete(
    request_data: AssetFileTypeRegistryDeleteRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.delete_asset_file_type_registry(db=db, registry_id=request_data.id, user=_user)
    return response_200(data=jsonable_encoder(data))
