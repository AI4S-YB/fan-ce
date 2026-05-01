# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/9/23 10:20
@Function:
@version :  1.0
@Desc    :  None
"""

from fastapi import APIRouter, Depends

from apps.common.depends import get_active_user,check_permission
from apps.databases.crud import database_db
from apps.databases.services import database_format
from db.database import get_db
from libs.responses.response import response_2000
from ..schemas import DatabaseFormatModel
from libs.tools import run_in_background

action_router = APIRouter(tags=['databases:action:数据'], prefix='/action')


@action_router.post("/extract", summary="数据提取==app:databases:list")
async def databases_list(request_data: DatabaseFormatModel, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_2000(data={})


@action_router.post("/format",dependencies=[Depends(check_permission(["app:database:format"]))], summary="数据格式化==app:databases:format")
async def databases_list(request_data: DatabaseFormatModel, db=Depends(get_db), _user=Depends(get_active_user)):
    # genome
    database_obj = database_db.get(db=db, id=request_data.id)
    #
    database_db.update_one(db=db, db_obj=database_obj, obj_in={'status': 6})
    run_in_background(database_format, args=(db, database_obj))

    return response_2000(data={})
