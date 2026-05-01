"""
@File    :   user.routers.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""
from fastapi import APIRouter
from .api import user_router

user_routers = APIRouter()
user_routers.include_router(user_router)
