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

from modules.common.depends import get_active_user,check_permission
from shared.database import get_db
from shared.responses import response_200
from ..crud import experiment_meta_db
from ..schemas import PageList, DataInfo, DataDelete,UpdateModel,CreateModel

experiment_meta_router = APIRouter(tags=['app:experimentMeta:实验'])


@experiment_meta_router.post("/list",dependencies=[Depends(check_permission(["app:experiment:meta:list"]))], summary="实验列表==app:experiment:meta:list")
async def experiment_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    filters = {}
    if request_data.experiment_id:
        filters['experiment_id'] = request_data.experiment_id
    db_obj = experiment_meta_db.get_list(db=db, page=request_data.page, size=request_data.size,filters=filters,sort='-id')
    return response_200(data=db_obj)



@experiment_meta_router.post("/info",dependencies=[Depends(check_permission(["app:experiment:meta:info"]))], summary="实验列表==app:experimentMeta:list")
async def experiment_list(request_data: DataInfo, db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = experiment_meta_db.get_one(db=db, id=request_data.id)
    return response_200(data=db_obj)


@experiment_meta_router.post("/options",dependencies=[Depends(check_permission(["app:experiment:meta:list"]))], summary="实验下拉列表==app:experimentMeta:options")
async def experiment_list(db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = experiment_meta_db.get_list(db=db, page=0)
    return response_200(data=db_obj)


@experiment_meta_router.post("/add",dependencies=[Depends(check_permission(["app:experiment:meta:add"]))], summary="实验添加==app:experimentMeta:add")
async def experiment_list(request_data: CreateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    request_data.type = '1'
    request_data.create_time = int(time.time())
    request_data.is_deleted = False
    request_data.status = 1
    db_obj = experiment_meta_db.create_one(db=db, obj_in=request_data)
    return response_200(data=db_obj)


@experiment_meta_router.post("/update",dependencies=[Depends(check_permission(["app:experiment:meta:update"]))], summary="实验修改==app:experimentMeta:update")
async def experiment_list(request_data: UpdateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    one_obj = experiment_meta_db.get(db=db, id=request_data.id)
    db_obj = experiment_meta_db.update_one(db=db, db_obj=one_obj, obj_in=request_data)
    return response_200(data=db_obj)


@experiment_meta_router.post("/delete",dependencies=[Depends(check_permission(["app:experiment:meta:delete"]))], summary="实验删除==app:experimentMeta:delete")
async def experiment_list(request_data: DataDelete, db=Depends(get_db), _user=Depends(get_active_user)):
    if request_data.ids:
        for i in request_data.ids:
            experiment_meta_db.remove(db=db, id=int(i))
    else:
        experiment_meta_db.remove(db=db, id=request_data.id)
    return response_200(data={})
