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

from modules.common.depends import get_active_user,check_permission
from shared.database import get_db
from shared.responses import response_200, response_200
from ..rbac.crud import role_db, role_menu_db
from ..rbac.schemas import RoleUpdate, RoleCreate, RoleMenuUpdate
from ..schemas import PageList, DataInfo, DataDelete
from modules.services.rbd import rbd_service
role_router = APIRouter()


@role_router.post("/list",dependencies=[Depends(check_permission(["sys:role:list"]))],  summary="角色列表")
async def role_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    filters_exp = []
    if request_data.name:
        filters_exp.append({'name':'name','exp':'like','value':request_data.name})
    obj = role_db.get_list(db=db, page=request_data.page, size=request_data.size,filters_exp=filters_exp)
    for i in obj['dataList']:
        menu_ids = [item.menu_id for item in role_menu_db.get_data(db=db, filters={'role_id': i.id})]
        i.permissions = menu_ids
    return response_200(data=obj)


@role_router.post("/options",dependencies=[Depends(check_permission(["sys:role:list"]))], summary="角色列表")
async def role_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    new_data = []
    obj = role_db.get_list(db=db, page=0, size=request_data.size)
    for i in obj['dataList']:
        new_data.append({'value': i.id, 'label': i.name})
    return response_200(data=new_data)


@role_router.post("/add",dependencies=[Depends(check_permission(["sys:role:add"]))], summary="角色添加")
async def role_add(request_data: RoleCreate, db=Depends(get_db)):
    request_data.create_time = int(time.time())
    request_data.is_active = 1
    request_data.is_delete = 0
    obj = role_db.create_one(db=db, obj_in=request_data)
    rbd_service.create_role_menus(db=db,role=obj,request_data=request_data)
    return response_200(data=jsonable_encoder(obj))


@role_router.post("/delete",dependencies=[Depends(check_permission(["sys:role:delete"]))], summary="角色删除")
async def role_delete(request_data: DataDelete, db=Depends(get_db), _user=Depends(get_active_user)):
    role_db.remove(db=db, id=request_data.id)
    rbd_service.del_role_menus(db=db,role_id=request_data.id)
    return response_200(data={})


@role_router.post("/info",dependencies=[Depends(check_permission(["sys:role:info"]))], summary="角色详情")
async def role_info(request_data: DataInfo, db=Depends(get_db), _user=Depends(get_active_user)):
    obj = role_db.get(db=db, id=request_data.id)
    menu_ids = [item.menu_id for item in role_menu_db.get_data(db=db, filters={'role_id': obj.id})]
    obj.permissions = menu_ids
    return response_200(data=obj)



@role_router.post("/update",dependencies=[Depends(check_permission(["sys:role:update"]))], summary="角色更新")
async def role_update(request_data: RoleUpdate, db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = role_db.get(db=db, id=request_data.id)
    obj = role_db.update_one(db=db, db_obj=db_obj, obj_in=request_data)
    rbd_service.update_role_menus(db=db, role=obj,request_data=request_data)
    return response_200(data=obj)


@role_router.post("/menu",dependencies=[Depends(check_permission(["sys:role:menu"]))], summary="角色授权")
async def role_update(request_data: RoleMenuUpdate, db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = role_db.get(db=db, id=request_data.role_id)
    menu_list = request_data.menu_map
    role_id = request_data.role_id
    role_data = jsonable_encoder(db_obj)
    if not menu_list is None and isinstance(menu_list, list):
        role_menu_db.remove_batch(db=db, filters={"role_id": role_id})
        role_menu_list = [{'role_id': role_id, 'menu_id': int(id)} for id in menu_list]
        role_menu_db.create_batch(db=db, add_data=role_menu_list)
    obj = role_db.update_one(db=db, db_obj=role_data, obj_in=request_data)
    return response_200(data=obj)
