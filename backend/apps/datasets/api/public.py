from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
import os

from db.database import get_db
from libs.responses.response import response_2000

from ..dataset_model import Dataset
from ..models import AssetFile, DatasetAsset, DatasetRegistry, DatasetVersion
from ..schemas import (
    BatchSequenceRequest,
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


@public_dataset_router.post("/sequence/batch", summary="批量提取序列")
def public_sequence_batch(request_data: BatchSequenceRequest):
    """Batch sequence retrieval supporting coordinate (genome) and gene-ID modes."""
    data = dataset_domain_service.batch_sequence_retrieval(request_data=request_data)
    return response_2000(data=jsonable_encoder(data))


@public_dataset_router.get("/sequence/download", summary="下载批量提取的序列")
def public_sequence_download(file: str = None):
    """Download batch sequence results as FASTA."""
    if not file:
        raise HTTPException(status_code=400, detail="file parameter is required")
    basename = os.path.basename(file)
    if not basename.startswith("fance-seq-"):
        raise HTTPException(status_code=400, detail="Invalid file reference")
    tmp_path = f"/tmp/{basename}"
    if not os.path.exists(tmp_path):
        raise HTTPException(status_code=404, detail="File not found or expired")
    return FileResponse(tmp_path, filename="sequences.fasta", media_type="text/plain")


@public_dataset_router.get("/{dataset_code}/lineage", summary="公开数据集血缘")
def public_dataset_lineage(
    dataset_code: str,
    db=Depends(get_db),
):
    """Public lineage: list lineage edges where both src and dst versions are released."""
    ds = db.query(DatasetRegistry).filter_by(dataset_code=dataset_code).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if ds.visibility != "public":
        raise HTTPException(status_code=404, detail="Dataset not found")

    svc = dataset_domain_service
    edges = svc._list_public_lineage(db=db, dataset_id=ds.database_id)
    return response_2000(data=jsonable_encoder(
        {"dataset_id": ds.database_id, "dataset_code": ds.dataset_code, "lineage_edges": edges}
    ))


@public_dataset_router.get("/{dataset_code}/downloads", summary="公开数据集可下载文件列表")
def public_dataset_downloads(
    dataset_code: str,
    db=Depends(get_db),
):
    """List downloadable files for a public dataset."""
    ds = db.query(DatasetRegistry).filter_by(dataset_code=dataset_code).first()
    if not ds or ds.visibility != "public":
        raise HTTPException(status_code=404, detail="Dataset not found or not public")

    version = db.query(DatasetVersion).filter_by(
        database_id=ds.database_id, is_current=1,
    ).first()
    if not version:
        return response_2000(data=jsonable_encoder({"dataset_code": dataset_code, "files": []}))

    # Get assets for this version
    assets = db.query(DatasetAsset).filter_by(
        dataset_version_id=version.id,
    ).all()
    asset_ids = [a.id for a in assets]

    files = db.query(AssetFile).filter(
        AssetFile.dataset_asset_id.in_(asset_ids),
        AssetFile.is_downloadable == True,
    ).all()

    return response_2000(data=jsonable_encoder({
        "dataset_code": dataset_code,
        "files": [
            {
                "id": f.id,
                "file_name": f.file_name,
                "file_format": f.file_format,
                "file_size": f.file_size,
                "file_role": f.file_role,
            }
            for f in files
        ],
    }))


@public_dataset_router.get("/{dataset_code}/download/{file_id}", summary="下载公开数据集文件")
def public_dataset_download(
    dataset_code: str,
    file_id: int,
    db=Depends(get_db),
):
    """Download a file from a public dataset."""
    ds = db.query(DatasetRegistry).filter_by(dataset_code=dataset_code).first()
    if not ds or ds.visibility != "public":
        raise HTTPException(status_code=404, detail="Dataset not found or not public")

    file_obj = db.query(AssetFile).filter_by(id=file_id, is_downloadable=True).first()
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found or not downloadable")

    file_path = file_obj.local_path or file_obj.storage_uri
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_path,
        filename=file_obj.file_name or os.path.basename(file_path),
        media_type=file_obj.mime_type or "application/octet-stream",
    )
