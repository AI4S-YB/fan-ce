from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.encoders import jsonable_encoder

from modules.common.depends import check_permission, get_active_user
from shared.database import get_db
from shared.responses import response_200

from ..schemas import (
    DatasetScanBrowseRequest,
    DatasetScanJobListRequest,
    DatasetScanRootCreateRequest,
    DatasetScanRootDeleteRequest,
    DatasetScanRootInfoRequest,
    DatasetScanRootListRequest,
    DatasetScanRootUpdateRequest,
    DatasetScanRunRequest,
    DatasetStagingDeleteRequest,
    DatasetStagingInfoRequest,
    DatasetStagingListRequest,
    DatasetStagingRegisterRequest,
)
from ..services import dataset_domain_service

dataset_staging_router = APIRouter(tags=["app:dataset:暂存区"])


@dataset_staging_router.post("/scan-root/list", dependencies=[Depends(check_permission(["app:database:info"]))], summary="扫描目录列表")
async def dataset_scan_root_list(
    request_data: DatasetScanRootListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.list_scan_roots(db=db, request_data=request_data)
    return response_200(data=jsonable_encoder(data))


@dataset_staging_router.post("/scan-root/info", dependencies=[Depends(check_permission(["app:database:info"]))], summary="扫描目录详情")
async def dataset_scan_root_info(
    request_data: DatasetScanRootInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.get_scan_root(db=db, root_id=request_data.id)
    return response_200(data=jsonable_encoder(data))


@dataset_staging_router.post("/scan-root/create", dependencies=[Depends(check_permission(["app:database:add"]))], summary="创建扫描目录")
async def dataset_scan_root_create(
    request_data: DatasetScanRootCreateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.create_scan_root(db=db, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_staging_router.post("/scan-root/update", dependencies=[Depends(check_permission(["app:database:update"]))], summary="更新扫描目录")
async def dataset_scan_root_update(
    request_data: DatasetScanRootUpdateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.update_scan_root(
        db=db,
        root_id=request_data.id,
        request_data=request_data,
        user=_user,
    )
    return response_200(data=jsonable_encoder(data))


@dataset_staging_router.post("/scan-root/delete", dependencies=[Depends(check_permission(["app:database:delete"]))], summary="删除扫描目录")
async def dataset_scan_root_delete(
    request_data: DatasetScanRootDeleteRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.delete_scan_root(db=db, root_id=request_data.id, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_staging_router.post("/scan-root/browse", dependencies=[Depends(check_permission(["app:database:info"]))], summary="浏览服务器目录供扫描目录选择")
async def dataset_scan_root_browse(
    request_data: DatasetScanBrowseRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.browse_scan_root_path(
        db=db,
        request_data=request_data,
        user=_user,
    )
    return response_200(data=jsonable_encoder(data))


@dataset_staging_router.post("/scan-job/list", dependencies=[Depends(check_permission(["app:database:info"]))], summary="扫描任务列表")
async def dataset_scan_job_list(
    request_data: DatasetScanJobListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.list_scan_jobs(db=db, request_data=request_data)
    return response_200(data=jsonable_encoder(data))


@dataset_staging_router.post("/scan/run", dependencies=[Depends(check_permission(["app:database:add"]))], summary="执行目录扫描写入暂存区")
async def dataset_scan_run(
    request_data: DatasetScanRunRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.run_scan_root(db=db, root_id=request_data.root_id, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_staging_router.post("/upload", dependencies=[Depends(check_permission(["app:database:add"]))], summary="上传文件到 dataset 暂存区")
async def dataset_staging_upload(
    file: UploadFile = File(...),
    dataset_type: str | None = Form(None),
    meta_json: str | None = Form(None),
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.upload_staging_file(
        db=db,
        upload_file=file,
        user=_user,
        dataset_type=dataset_type,
        meta_json=meta_json,
    )
    return response_200(data=jsonable_encoder(data))


@dataset_staging_router.post("/list", dependencies=[Depends(check_permission(["app:database:info"]))], summary="dataset 暂存文件列表")
async def dataset_staging_list(
    request_data: DatasetStagingListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.list_staging_files(db=db, request_data=request_data)
    return response_200(data=jsonable_encoder(data))


@dataset_staging_router.post("/info", dependencies=[Depends(check_permission(["app:database:info"]))], summary="dataset 暂存文件详情")
async def dataset_staging_info(
    request_data: DatasetStagingInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.get_staging_file(db=db, staging_id=request_data.id)
    return response_200(data=jsonable_encoder(data))


@dataset_staging_router.post("/register", dependencies=[Depends(check_permission(["app:database:add"]))], summary="从暂存文件注册 dataset")
async def dataset_staging_register(
    request_data: DatasetStagingRegisterRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.register_dataset_from_staging(
        db=db,
        staging_id=request_data.id,
        request_data=request_data,
        user=_user,
    )
    return response_200(data=jsonable_encoder(data))


@dataset_staging_router.post("/delete", dependencies=[Depends(check_permission(["app:database:delete"]))], summary="删除 dataset 暂存文件")
async def dataset_staging_delete(
    request_data: DatasetStagingDeleteRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.delete_staging_file(db=db, staging_id=request_data.id, user=_user)
    return response_200(data=jsonable_encoder(data))
