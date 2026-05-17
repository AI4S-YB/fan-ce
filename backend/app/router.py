#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
# @desc : 注册路由
from fastapi import FastAPI, APIRouter

from core import settings
from apps.routers import app_routers
from basis.routers import basis_router


def register_router(app: FastAPI):
    """ 注册路由 """
    app.include_router(app_routers, prefix=settings.API_STR)
    app.include_router(basis_router, prefix=settings.API_STR)

