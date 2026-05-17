# -*- coding: utf-8 -*-
"""
@author :  llq
@file   :  routers.py
@time   :  2023/7/5  15:21
@version:  1.0
@Desc   :  None
"""
from fastapi import APIRouter
from modules.auth.login import login_router
from modules.auth.menus import menu_router

auth_routers = APIRouter()
auth_routers.include_router(login_router)
auth_routers.include_router(menu_router)
