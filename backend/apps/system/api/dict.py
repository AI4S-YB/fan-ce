# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/10/8 17:48
@Function: 
@version :  1.0
@Desc    :  None
"""
import time

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder

from apps.common.depends import get_active_user
from db.database import get_db
from libs.responses.response import response_2000, response_200
from ..base.crud import system_dict_db, system_dict_field_db
from ..base.models import SystemDictField
from ..base.schemas import PageList, DataInfo, DataDelete, SystemDictCreate, SystemDictUpdate, SystemDictFieldCreate, SystemDictFieldUpdate, \
    DictOptions

dict_router = APIRouter()


@dict_router.post("/field", summary="字典字段")
async def user_list():
    data = SystemDictField.get_field()
    return response_2000(data=data)


@dict_router.post("/map", summary="字典列表==sys:dict:list")
async def dict_list(request_data: DictOptions, db=Depends(get_db), _user=Depends(get_active_user)):
    data = []
    filters = {}
    if request_data.key:
        filters["key"] = request_data.key
    dict_type_list = [i.id for i in system_dict_db.get_list(db=db, page=0, filters=filters)['dataList']]
    filters_exp = [{'name': 'type_id', 'exp': 'contain', 'value': dict_type_list}]
    filed_obj = system_dict_field_db.get_list(db=db, page=0, filters_exp=filters_exp)
    for i in filed_obj['dataList']:
        dict_type = system_dict_db.get_one(db=db, id=i.type_id)
        if dict_type:
            data.append({'label': i.label, 'value': i.value, 'dictType': dict_type.key, 'color': i.color,'key': i.id})
    return response_2000(data=data)


@dict_router.post("/options", summary="字典列表==sys:dict:list")
async def dict_list(request_data: DictOptions, db=Depends(get_db)):
    dict_type = system_dict_db.get_filter(db=db, filters={'key': request_data.type})
    if dict_type:
        obj = system_dict_field_db.get_list(db=db, page=0, filters={'type_id': dict_type.id})
        return response_2000(data=jsonable_encoder(obj['dataList']))
    else:
        return response_2000(data=[])


@dict_router.post("/list", summary="字典列表==sys:dict:list")
async def dict_list(request_data: PageList, db=Depends(get_db)):
    print(jsonable_encoder(request_data))
    obj = system_dict_db.get_list(db=db, page=request_data.page, size=request_data.size)
    return response_2000(data=jsonable_encoder(obj))


@dict_router.post("/add", summary="字典详情==sys:dict:add")
async def dict_add(request_data: SystemDictCreate, db=Depends(get_db)):
    obj1 = system_dict_db.get_filter(db=db, filters={'key': request_data.key})
    if obj1:
        return response_2000(data={}, code=4009, msg=f"{request_data.key}已存在")
    request_data.create_time = int(time.time())
    request_data.status = "1"
    obj = system_dict_db.create_one(db=db, obj_in=request_data)
    return response_2000(data=jsonable_encoder(obj))


@dict_router.post("/info", summary="字典详情==sys:dict:info")
async def dict_info(request_data: DataInfo, db=Depends(get_db)):
    obj = system_dict_db.get(db=db, id=request_data.id)
    return response_2000(data=jsonable_encoder(obj))


@dict_router.post("/update", summary="字典更新==sys:dict:update")
async def dict_update(request_data: SystemDictUpdate, db=Depends(get_db)):
    if system_dict_db.get_data(db=db, filters={'key': request_data.key}):
        return response_2000(data={}, code=4009, msg=f"{request_data.key}已存在")
    obj = system_dict_db.get(db=db, id=request_data.id)
    system_dict_db.update_one(db=db, obj_in=request_data, db_obj=obj)
    return response_2000(data='')


@dict_router.post("/delete", summary="字典删除==sys:dict:delete")
async def dict_delete(request_data: DataDelete, db=Depends(get_db)):
    if request_data.id:
        system_dict_db.remove(db=db, id=request_data.id)
    if request_data.ids:
        system_dict_db.remove(db=db, ids=request_data.ids)
    return response_200(data={})


@dict_router.post("/field/list", summary="字典字段列表==sys:dict:list")
async def dict_list(request_data: PageList, db=Depends(get_db)):
    filters = {'type_id': request_data.type_id}
    dict_obj = system_dict_db.get_one(db=db, id=request_data.type_id)
    obj = system_dict_field_db.get_list(db=db, page=request_data.page, size=request_data.size, filters=filters)
    for i in obj['dataList']:
        i.type_name = ''
        i.type_key = ''
        if dict_obj:
            i.type_name = dict_obj.name
            i.type_key = dict_obj.key
    return response_2000(data=jsonable_encoder(obj))


@dict_router.post("/field/add", summary="字典字段详情==sys:dict:add")
async def dict_add(request_data: SystemDictFieldCreate, db=Depends(get_db)):
    obj1 = system_dict_field_db.get_filter(db=db, filters={'value': request_data.value, 'type_id': request_data.type_id})
    if obj1:
        return response_2000(data={}, code=4009, msg=f"{request_data.value}已存在")
    request_data.create_time = int(time.time())
    request_data.status = "1"
    obj = system_dict_field_db.create_one(db=db, obj_in=request_data)
    return response_2000(data=jsonable_encoder(obj))


@dict_router.post("/field/info", summary="字典字段详情==sys:dict:info")
async def dict_info(request_data: DataInfo, db=Depends(get_db)):
    obj = system_dict_field_db.get(db=db, id=request_data.id)
    return response_2000(data=jsonable_encoder(obj))


@dict_router.post("/field/update", summary="字典字段更新==sys:dict:update")
async def dict_update(request_data: SystemDictFieldUpdate, db=Depends(get_db)):
    obj = system_dict_field_db.get(db=db, id=request_data.id)
    if request_data.value != obj.value:
        if system_dict_field_db.get_filter(db=db, filters={'value': request_data.value, 'type_id': request_data.type_id}):
            return response_2000(data={}, code=4009, msg=f"{request_data.value}已存在")
    system_dict_field_db.update_one(db=db, obj_in=request_data, db_obj=obj)
    return response_2000(data='')


@dict_router.post("/field/delete", summary="字典字段删除==sys:dictField:delete")
async def dict_field_delete(request_data: DataDelete, db=Depends(get_db)):
    system_dict_field_db.remove(db=db, id=request_data.id)
    return response_200(data={})
