from fastapi import APIRouter

from .api.core import breeding_router

app_breeding_router = APIRouter()
app_breeding_router.include_router(breeding_router, prefix="/breeding")
