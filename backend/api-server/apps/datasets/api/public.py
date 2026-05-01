from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder

from db.database import get_db
from libs.responses.response import response_2000

from ..dataset_model import Dataset
from ..schemas import (
    PublicDatasetInfoRequest,
    PublicDatasetListRequest,
    PublicDatasetQueryCapabilitiesRequest,
    PublicDatasetQueryRequest,
    PublicDatasetVersionInfoRequest,
    PublicDatasetVersionListRequest,
    PublicDatasetVersionQueryCapabilitiesRequest,
    PublicDatasetVersionQueryRequest,
)
from ..services import dataset_domain_service

public_dataset_router = APIRouter(tags=["public:dataset:公开数据集"])


@public_dataset_router.post("/list", summary="公开数据集列表")
async def public_dataset_list(request_data: PublicDatasetListRequest):
    data = dataset_domain_service.list_public_datasets(request_data=request_data)
    return response_2000(data=jsonable_encoder(data))


@public_dataset_router.post("/info", summary="公开数据集详情")
async def public_dataset_info(request_data: PublicDatasetInfoRequest):
    data = dataset_domain_service.get_public_dataset(dataset_id=request_data.id)
    return response_2000(data=jsonable_encoder(data))


@public_dataset_router.post("/version/list", summary="公开数据集版本列表")
async def public_dataset_version_list(request_data: PublicDatasetVersionListRequest):
    data = dataset_domain_service.list_public_dataset_versions(
        dataset_id=request_data.id,
        keyword=request_data.keyword,
        is_default_public=request_data.is_default_public,
        is_current=request_data.is_current,
        release_state=request_data.release_state,
    )
    return response_2000(data=jsonable_encoder(data))


@public_dataset_router.post("/version/info", summary="公开数据集指定版本详情")
async def public_dataset_version_info(request_data: PublicDatasetVersionInfoRequest):
    data = dataset_domain_service.get_public_dataset_version(dataset_id=request_data.id, version_id=request_data.version_id)
    return response_2000(data=jsonable_encoder(data))


@public_dataset_router.post("/query/capabilities", summary="查看公开数据集查询能力")
async def public_dataset_query_capabilities(request_data: PublicDatasetQueryCapabilitiesRequest):
    data = dataset_domain_service.get_public_query_capabilities(
        dataset_id=request_data.id,
        asset_code=request_data.asset_code,
    )
    return response_2000(data=jsonable_encoder(data))


@public_dataset_router.post("/query/execute", summary="执行公开数据集查询")
async def public_dataset_query_execute(request_data: PublicDatasetQueryRequest):
    data = dataset_domain_service.execute_public_query(
        dataset_id=request_data.id,
        operation=request_data.operation,
        asset_code=request_data.asset_code,
        params=request_data.params or {},
    )
    return response_2000(data=jsonable_encoder(data))


@public_dataset_router.post("/version/query/capabilities", summary="查看公开数据集指定版本查询能力")
async def public_dataset_version_query_capabilities(request_data: PublicDatasetVersionQueryCapabilitiesRequest):
    data = dataset_domain_service.get_public_dataset_version_query_capabilities(
        dataset_id=request_data.id,
        version_id=request_data.version_id,
        asset_code=request_data.asset_code,
    )
    return response_2000(data=jsonable_encoder(data))


@public_dataset_router.post("/version/query/execute", summary="执行公开数据集指定版本查询")
async def public_dataset_version_query_execute(request_data: PublicDatasetVersionQueryRequest):
    data = dataset_domain_service.execute_public_dataset_version_query(
        dataset_id=request_data.id,
        version_id=request_data.version_id,
        operation=request_data.operation,
        asset_code=request_data.asset_code,
        params=request_data.params or {},
    )
    return response_2000(data=jsonable_encoder(data))


@public_dataset_router.get("/{dataset_code}/lineage", summary="公开数据集血缘")
def public_dataset_lineage(
    dataset_code: str,
    db=Depends(get_db),
):
    """Public lineage: list lineage edges where both src and dst versions are released."""
    ds = db.query(Dataset).filter_by(dataset_code=dataset_code).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if ds.visibility != "public":
        raise HTTPException(status_code=404, detail="Dataset not found")

    svc = dataset_domain_service
    edges = svc._list_public_lineage(db=db, dataset_id=ds.id)
    return response_2000(data=jsonable_encoder(
        {"dataset_id": ds.id, "dataset_code": ds.dataset_code, "lineage_edges": edges}
    ))
