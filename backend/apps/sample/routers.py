from fastapi import APIRouter

from .api.sample import sample_router
from .api.sample_meta import sample_meta_router

app_sample_router = APIRouter()
app_sample_router.include_router(sample_router, prefix='/sample')
app_sample_router.include_router(sample_meta_router, prefix='/sample/meta')