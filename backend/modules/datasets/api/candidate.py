from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder

from modules.common.depends import check_permission, get_active_user
from shared.database import get_db
from shared.responses import response_200

from ..schemas import (
    DatasetRegistrationCandidateCreateRequest,
    DatasetRegistrationCandidateDeleteRequest,
    DatasetRegistrationCandidateFileListRequest,
    DatasetRegistrationCandidateFileUpdateRequest,
    DatasetRegistrationCandidateInfoRequest,
    DatasetRegistrationCandidateListRequest,
    DatasetRegistrationCandidateRegisterRequest,
    DatasetRegistrationCandidateUpdateRequest,
)
from ..services import dataset_domain_service

dataset_candidate_router = APIRouter(tags=["app:dataset:注册候选"])


@dataset_candidate_router.post("/list", dependencies=[Depends(check_permission(["app:database:info"]))], summary="注册候选列表")
async def dataset_candidate_list(
    request_data: DatasetRegistrationCandidateListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.list_registration_candidates(db=db, request_data=request_data)
    return response_200(data=jsonable_encoder(data))


@dataset_candidate_router.post("/info", dependencies=[Depends(check_permission(["app:database:info"]))], summary="注册候选详情")
async def dataset_candidate_info(
    request_data: DatasetRegistrationCandidateInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.get_registration_candidate(db=db, candidate_id=request_data.id)
    return response_200(data=jsonable_encoder(data))


@dataset_candidate_router.post("/file/list", dependencies=[Depends(check_permission(["app:database:info"]))], summary="注册候选文件列表")
async def dataset_candidate_file_list(
    request_data: DatasetRegistrationCandidateFileListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.list_registration_candidate_files(db=db, request_data=request_data)
    return response_200(data=jsonable_encoder(data))


@dataset_candidate_router.post("/file/update", dependencies=[Depends(check_permission(["app:database:update"]))], summary="更新注册候选文件映射")
async def dataset_candidate_file_update(
    request_data: DatasetRegistrationCandidateFileUpdateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.update_registration_candidate_file(
        db=db,
        candidate_file_id=request_data.id,
        request_data=request_data,
        user=_user,
    )
    return response_200(data=jsonable_encoder(data))


@dataset_candidate_router.post("/create", dependencies=[Depends(check_permission(["app:database:add"]))], summary="创建注册候选")
async def dataset_candidate_create(
    request_data: DatasetRegistrationCandidateCreateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.create_registration_candidate(db=db, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_candidate_router.post("/update", dependencies=[Depends(check_permission(["app:database:update"]))], summary="更新注册候选")
async def dataset_candidate_update(
    request_data: DatasetRegistrationCandidateUpdateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.update_registration_candidate(
        db=db,
        candidate_id=request_data.id,
        request_data=request_data,
        user=_user,
    )
    return response_200(data=jsonable_encoder(data))


@dataset_candidate_router.post("/delete", dependencies=[Depends(check_permission(["app:database:delete"]))], summary="删除注册候选")
async def dataset_candidate_delete(
    request_data: DatasetRegistrationCandidateDeleteRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.delete_registration_candidate(db=db, candidate_id=request_data.id, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_candidate_router.post("/register", dependencies=[Depends(check_permission(["app:database:add"]))], summary="将注册候选正式注册为 Dataset")
async def dataset_candidate_register(
    request_data: DatasetRegistrationCandidateRegisterRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.register_candidate(db=db, candidate_id=request_data.id, request_data=request_data, user=_user)
    return response_200(data=jsonable_encoder(data))
