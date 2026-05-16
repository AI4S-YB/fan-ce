from fastapi import APIRouter

from .api.experiment import experiment_router
from .api.experiment_meta import experiment_meta_router

app_experiment_router = APIRouter()
app_experiment_router.include_router(experiment_router, prefix='/experiment')
app_experiment_router.include_router(experiment_meta_router, prefix='/experiment/meta')