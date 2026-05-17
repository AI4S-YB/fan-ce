from fastapi import APIRouter

from .api.gene_set import gene_set_router

app_gene_router = APIRouter()
app_gene_router.include_router(gene_set_router, prefix='/gene/set')