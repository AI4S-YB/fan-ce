from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder

from apps.common.depends import check_permission, get_active_user
from db.database import get_db
from libs.responses.response import response_2000

from ..schemas import DatasetLineageCreateRequest, DatasetLineageDeleteRequest, DatasetLineageListRequest
from ..services import dataset_domain_service

dataset_lineage_router = APIRouter(tags=["app:dataset:血缘"])


@dataset_lineage_router.post("/list", dependencies=[Depends(check_permission(["app:database:info"]))], summary="数据集血缘列表")
async def dataset_lineage_list(
    request_data: DatasetLineageListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.list_dataset_lineage(
        db=db,
        dataset_id=request_data.dataset_id,
        version_id=request_data.version_id,
        limit=request_data.limit or 50,
        user=_user,
    )
    return response_2000(data=jsonable_encoder(data))


@dataset_lineage_router.post("/create", dependencies=[Depends(check_permission(["app:database:update"]))], summary="创建数据集血缘")
async def dataset_lineage_create(
    request_data: DatasetLineageCreateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.create_dataset_lineage(db=db, request_data=request_data, user=_user)
    return response_2000(data=jsonable_encoder(data))


@dataset_lineage_router.post("/delete", dependencies=[Depends(check_permission(["app:database:update"]))], summary="删除数据集血缘")
async def dataset_lineage_delete(
    request_data: DatasetLineageDeleteRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.delete_dataset_lineage(db=db, lineage_id=request_data.id, user=_user)
    return response_2000(data=jsonable_encoder(data))
