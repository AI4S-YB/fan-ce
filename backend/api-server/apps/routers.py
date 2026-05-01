# -*- coding: utf-8 -*-
"""
@author :  llq
@file   :  routers.py
@time   :  2023/7/5  15:21
@version:  1.0
@Desc   :  None
"""
from fastapi import APIRouter

from apps.auth.routers import auth_routers
from apps.breeding.routers import app_breeding_router
from apps.databases.routers import app_databases_router
from apps.datasets.routers import app_dataset_router
from apps.sample.routers import app_sample_router
from apps.system.routers import system_routers
from apps.experiment.routers import app_experiment_router
from apps.platform.routers import app_platform_router
from apps.gene.routers import app_gene_router

app_routers = APIRouter()
app_routers.include_router(auth_routers)
app_routers.include_router(app_breeding_router)
app_routers.include_router(app_databases_router)
app_routers.include_router(app_dataset_router)
app_routers.include_router(app_sample_router)
app_routers.include_router(app_experiment_router)
app_routers.include_router(app_platform_router)
app_routers.include_router(app_gene_router)
app_routers.include_router(system_routers, prefix='/system')
