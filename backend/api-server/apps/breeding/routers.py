from fastapi import APIRouter

from .api.core import breeding_router
from .api.public import public_germplasm_router

app_breeding_router = APIRouter()
app_breeding_router.include_router(breeding_router, prefix="/breeding")
app_breeding_router.include_router(public_germplasm_router, prefix="/public/germplasm")
