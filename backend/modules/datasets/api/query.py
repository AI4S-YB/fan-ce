from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder

from modules.common.depends import check_permission, get_active_user
from shared.database import get_db
from shared.responses import response_200

from ..schemas import DatasetQueryCapabilitiesRequest, DatasetQueryRequest
from ..services import dataset_domain_service

dataset_query_router = APIRouter(tags=["query:dataset:受控查询"])


@dataset_query_router.post("/capabilities", dependencies=[Depends(check_permission(["app:database:info"]))], summary="查看受控数据集查询能力")
async def query_dataset_capabilities(
    request_data: DatasetQueryCapabilitiesRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.get_query_capabilities(db=db, dataset_id=request_data.id, user=_user)
    return response_200(data=jsonable_encoder(data))


@dataset_query_router.post("/execute", dependencies=[Depends(check_permission(["app:database:info"]))], summary="执行受控数据集查询")
async def query_dataset_execute(
    request_data: DatasetQueryRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    data = dataset_domain_service.execute_query(
        db=db,
        dataset_id=request_data.id,
        operation=request_data.operation,
        params=request_data.params or {},
        user=_user,
    )
    return response_200(data=jsonable_encoder(data))
