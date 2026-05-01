from fastapi import APIRouter

from .api.asset import dataset_asset_router
from .api.candidate import dataset_candidate_router
from .api.dataset import dataset_router
from .api.ingest import dataset_ingest_router
from .api.lineage import dataset_lineage_router
from .api.public import public_dataset_router
from .api.admin import router as admin_dataset_router
from .api.query import dataset_query_router
from .api.registry import dataset_registry_admin_router
from .api.staging import dataset_staging_router
from .api.version import dataset_version_router

app_dataset_router = APIRouter()
app_dataset_router.include_router(dataset_router, prefix="/dataset")
app_dataset_router.include_router(dataset_asset_router, prefix="/dataset/asset")
app_dataset_router.include_router(dataset_candidate_router, prefix="/dataset/candidate")
app_dataset_router.include_router(dataset_ingest_router, prefix="/dataset/ingest")
app_dataset_router.include_router(dataset_lineage_router, prefix="/dataset/lineage")
app_dataset_router.include_router(dataset_registry_admin_router, prefix="/dataset/registry")
app_dataset_router.include_router(dataset_staging_router, prefix="/dataset/staging")
app_dataset_router.include_router(dataset_version_router, prefix="/dataset/version")
app_dataset_router.include_router(dataset_query_router, prefix="/query/dataset")
app_dataset_router.include_router(dataset_router, prefix="/admin/dataset")
app_dataset_router.include_router(dataset_asset_router, prefix="/admin/dataset/asset")
app_dataset_router.include_router(dataset_candidate_router, prefix="/admin/dataset/candidate")
app_dataset_router.include_router(dataset_ingest_router, prefix="/admin/dataset/ingest")
app_dataset_router.include_router(dataset_lineage_router, prefix="/admin/dataset/lineage")
app_dataset_router.include_router(dataset_registry_admin_router, prefix="/admin/dataset/registry")
app_dataset_router.include_router(dataset_staging_router, prefix="/admin/dataset/staging")
app_dataset_router.include_router(dataset_version_router, prefix="/admin/dataset/version")
app_dataset_router.include_router(admin_dataset_router, prefix="/admin/dataset/admin")
app_dataset_router.include_router(public_dataset_router, prefix="/public/dataset")
