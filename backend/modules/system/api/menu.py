# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/9/23 10:20
@Function: 
@version :  1.0
@Desc    :  None
"""
import json
import os
import time

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder

from apps.common.depends import get_active_user,check_permission
from apps.services.rbd import menu_service
from db.database import get_db
from libs.dataes import get_menu_tree
from libs.exceptions.exception import exceptions
from libs.responses.response import response_200, response_200
from ..rbac.crud import menu_db, menu_permission_db, permission_db
from ..rbac.models import Menu
from ..rbac.schemas import PageList, MenuCreate, MenuUpdate, MenuDelete, MenuInfo

menu_router = APIRouter()


@menu_router.post("/field", summary="菜单字段")
async def user_list():
    data = Menu.get_field()
    return response_200(data=data)


@menu_router.post("/list",dependencies=[Depends(check_permission(["sys:menu:list"]))], summary="菜单列表==sys:menu:list")
async def menu_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    menu_obj = menu_db.get_list(db=db, page=request_data.page, size=request_data.size)
    return response_200(data=jsonable_encoder(menu_obj))


@menu_router.post("/option",dependencies=[Depends(check_permission(["sys:menu:list"]))],  summary="菜单列表==sys:menu:list")
async def menu_list(db=Depends(get_db), _user=Depends(get_active_user)):
    menu_obj = menu_db.get_list(db=db, page=0)
    return response_200(data=jsonable_encoder(menu_obj['dataList']))


@menu_router.post("/info",dependencies=[Depends(check_permission(["sys:menu:info"]))],  summary="菜单列表==sys:menu:info")
async def menu_info(request_data: MenuInfo, db=Depends(get_db), _user=Depends(get_active_user)):
    menu_obj = menu_db.get(db=db, id=request_data.id)
    permission_list = []
    permission_link = menu_permission_db.get_data(db=db, filters={'menu_id': menu_obj.id})
    for permission in permission_link:
        p_obj = permission_db.get_one(db=db, id=permission.permission_id)
        if p_obj:
            permission_list.append(p_obj)
    menu_obj.permission_list = permission_list
    return response_200(data=menu_obj)


@menu_router.post("/tree",dependencies=[Depends(check_permission(["sys:menu:list"]))],  summary="菜单树结构==sys:menu:tree")
async def menu_tree(db=Depends(get_db), _user=Depends(get_active_user)):
    menu_obj = menu_db.get_list(db=db, page=0, size=0)
    for i in menu_obj['dataList']:
        permission_list = []
        permission_link = menu_permission_db.get_data(db=db, filters={'menu_id': i.id})
        for permission in permission_link:
            p_obj = permission_db.get_one(db=db, id=permission.permission_id)
            if p_obj:
                permission_list.append(p_obj)
        i.permission_list = permission_list
    data = get_menu_tree(jsonable_encoder(menu_obj['dataList']))
    return response_200(data=data)


@menu_router.post("/permission", summary="授权选择==sys:menu:tree")
async def menu_tree(db=Depends(get_db), _user=Depends(get_active_user)):
    menu_obj = menu_db.get_list(db=db, page=0, size=0)
    for i in menu_obj['dataList']:
        is_hide = False if i.is_visible else True
        if i.meta:
            i.meta = json.loads(i.meta)
            i.meta = {'title': i.title, 'icon': i.icon, 'hideInMenu': is_hide, **i.meta}
        else:
            i.meta = {'title': i.title, 'icon': i.icon, 'hideInMenu': is_hide}
    data = get_menu_tree(jsonable_encoder(menu_obj['dataList']))
    return response_200(data=data)


@menu_router.post("/add",dependencies=[Depends(check_permission(["sys:menu:add"]))],  summary="菜单添加==sys:menu:add")
async def menu_add(request_data: MenuCreate, db=Depends(get_db), _user=Depends(get_active_user)):
    if menu_db.get_filter(db=db, filters={'name': request_data.name}):
        return response_200(msg=f"菜单名称{exceptions.CODE_4025['msg']}", code=exceptions.CODE_4025['code'])
    if request_data.pid == 0:
        request_data.path = os.path.join('/', request_data.path)
    request_data.create_time = int(time.time())
    request_data.status = 1
    menu_obj = menu_db.create_one(db=db, obj_in=request_data)
    menu_service.create_menu_permissions(db=db, menu_obj=menu_obj, request_data=request_data)
    return response_200(data=menu_obj)


@menu_router.post("/delete",dependencies=[Depends(check_permission(["sys:menu:delete"]))],  summary="菜单删除==sys:menu:delete")
async def menu_delete(request_data: MenuDelete, db=Depends(get_db)):
    if request_data.id:
        menu_db.remove(db=db, id=request_data.id)
    if request_data.ids:
        menu_db.remove_batch_ids(db=db, ids=request_data.ids)
    return response_200(data={})


@menu_router.post("/update",dependencies=[Depends(check_permission(["sys:menu:update"]))],  summary="菜单更新==sys:menu:update")
async def menu_add(request_data: MenuUpdate, db=Depends(get_db)):
    menu_obj = menu_db.get(db=db, id=request_data.id)
    if menu_obj.type != 1:
        request_data.redirect = None
    menu_data = jsonable_encoder(menu_obj)
    menu_service.update_menu_permissions(db=db, menu_id=menu_obj.id, request_data=request_data)
    menu_db.update_one(db=db, db_obj=menu_data, obj_in=request_data)
    return response_200(data=jsonable_encoder(menu_obj))


@menu_router.post("/treeData",dependencies=[Depends(check_permission(["sys:menu:treeData"]))],  include_in_schema=False, summary="菜单树结构==sys:menu:tree")
async def tree_list(db=Depends(get_db), _user=Depends(get_active_user)):
    menu_obj = menu_db.get_list(db=db, page=0, size=0)
    data = get_menu_tree(jsonable_encoder(menu_obj['dataList']))
    return response_200(data=data)
