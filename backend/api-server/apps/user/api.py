"""
@File    :   routes.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""
from typing import Any
from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from db.database import get_db
from libs.responses.response import response_2000
from .crud import users_db
from .schemas import UserList, UserCreate
from apps.common.depends import get_active_user, check_permission

user_router = APIRouter(tags=['users'])


@user_router.post("/list", summary="用户列表==rbac:user:list")
async def user_list(request_data: UserList, db=Depends(get_db), _user=Depends(get_active_user)):
    user_data = users_db.get_list(db=db, page=request_data.page, size=request_data.size)
    return response_2000(data=jsonable_encoder(user_data))


@user_router.post("/info", summary="用户列表==rbac:user:info")
async def user_info(request_data: UserList, db=Depends(get_db), _user=Depends(get_active_user)):
    user_data = users_db.get_list(db=db, page=request_data.page, size=request_data.size)
    return response_2000(data=jsonable_encoder(user_data))


@user_router.get("/auth/info", summary="用户认证信息")
async def login_get_user(db: Session = Depends(get_db), user=Depends(get_active_user)) -> Any:
    data = {
        "user": {'user_name': user.user_name, 'nickName': 'nickName'},
        "permissions": ['all:all:all'],
        "roles": [],
        "menus": []
    }
    return response_2000(data=data, code=0)
