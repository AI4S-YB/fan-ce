# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/9/23 10:20
@Function:
@version :  1.0
@Desc    :  None
"""
import time
from fastapi import APIRouter, Depends

from apps.common.depends import get_active_user
from db.database import get_db
from libs.responses.response import response_200
from ..crud import sample_meta_db
from ..schemas import PageList, CreateModel, UpdateModel, DataInfo, DataDelete

sample_meta_router = APIRouter(tags=['app:sample_meta:样本'])


@sample_meta_router.post("/list", summary="样本列表==app:sample_meta:list")
async def sample_meta_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    filters = {}
    if request_data.sample_id:
        filters['sample_id'] = request_data.sample_id
    db_obj = sample_meta_db.get_list(db=db, page=request_data.page, size=request_data.size,filters=filters,sort='-id')
    return response_200(data=db_obj)


@sample_meta_router.post("/info", summary="样本列表==app:sample_meta:list")
async def sample_meta_list(request_data: DataInfo, db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = sample_meta_db.get_one(db=db, id=request_data.id)
    return response_200(data=db_obj)


@sample_meta_router.post("/options", summary="样本下拉列表==app:sample_meta:options")
async def sample_meta_list(db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = sample_meta_db.get_list(db=db, page=0)
    return response_200(data=db_obj)


@sample_meta_router.post("/add", summary="样本添加==app:sample_meta:add")
async def sample_meta_list(request_data: CreateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    request_data.type = '1'
    request_data.create_time = int(time.time())
    request_data.is_deleted = False
    request_data.status = 1
    db_obj = sample_meta_db.create_one(db=db, obj_in=request_data)
    return response_200(data=db_obj)


@sample_meta_router.post("/update", summary="样本修改==app:sample_meta:update")
async def sample_meta_list(request_data: UpdateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    one_obj = sample_meta_db.get(db=db, id=request_data.id)
    db_obj = sample_meta_db.update_one(db=db, db_obj=one_obj, obj_in=request_data)
    return response_200(data=db_obj)


@sample_meta_router.post("/delete", summary="样本删除==app:sample_meta:delete")
async def sample_meta_list(request_data: DataDelete, db=Depends(get_db), _user=Depends(get_active_user)):
    if request_data.ids:
        for i in request_data.ids:
            sample_meta_db.remove(db=db, id=int(i))
    else:
        sample_meta_db.remove(db=db, id=request_data.id)
    return response_200(data={})
