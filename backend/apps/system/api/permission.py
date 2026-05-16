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
from fastapi.encoders import jsonable_encoder

from apps.common.depends import get_active_user, check_permission, get_rbd_user
from db.database import get_db
from libs.dataes import get_tree_filter
from libs.responses.response import response_200
from ..rbac.crud import permission_db, menu_permission_db
from ..rbac.schemas import PermissionCreate, PermissionUpdate
from ..schemas import PageList, DataInfo, PageFilterList

permission_router = APIRouter()


@permission_router.post("/form", summary="权限列表==sys:permission:form")
async def permission_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_rbd_user)):
    permission_obj = permission_db.get_list(db=db, page=request_data.page, size=request_data.size)
    return response_200(data=permission_obj)


@permission_router.post("/add", dependencies=[Depends(check_permission(["sys:permission:add"]))], summary="权限列表==sys:permission:add")
async def permission_list(request_data: PermissionCreate, db=Depends(get_db), _user=Depends(get_active_user)):
    request_data.create_time = int(time.time())
    request_data.is_active = 1
    permission_obj = permission_db.create_one(db=db, obj_in=request_data)
    return response_200(data=permission_obj)


@permission_router.post("/list", dependencies=[Depends(check_permission(["sys:permission:list"]))], summary="权限列表==sys:permission:list")
async def permission_list(request_data: PageFilterList, db=Depends(get_db)):
    filters = {}
    filters_exp = []
    if request_data.name:
        filters["name"] = request_data.name
    if request_data.method:
        filters["method"] = request_data.method
    if request_data.type:
        filters["type"] = request_data.type
    obj = permission_db.get_list(db=db, page=request_data.page, size=request_data.size, filters=filters)
    return response_200(data=obj)


@permission_router.post("/info", dependencies=[Depends(check_permission(["sys:permission:info"]))], summary="权限列表==sys:permission:info")
async def permission_list(request_data: DataInfo, db=Depends(get_db)):
    obj = permission_db.get(db=db, id=request_data.id)
    return response_200(data=obj)


@permission_router.post("/update", dependencies=[Depends(check_permission(["sys:permission:update"]))],
                        summary="权限列表==sys:permission:update")
async def permission_list(request_data: PermissionUpdate, db=Depends(get_db)):
    obj = permission_db.get_one(db=db, id=request_data.id)
    permission_db.update_one(db=db, db_obj=obj, obj_in=request_data)
    return response_200(data=obj)


@permission_router.post("/delete", dependencies=[Depends(check_permission(["sys:permission:delete"]))],
                        summary="权限列表==sys:permission:delete")
async def permission_list(request_data: DataInfo, db=Depends(get_db)):
    if request_data.id:
        permission_db.remove(db=db, id=request_data.id)
        permission_db.remove_batch(db=db, filters={'pid': request_data.id})
        menu_permission_db.remove_batch(db=db, filters={'permission_id': request_data.id})
    if request_data.ids:
        permission_db.remove_batch_ids(db=db, ids=request_data.ids)
        for i in request_data.ids:
            permission_db.remove_batch(db=db, filters={'pid': i})
            menu_permission_db.remove_batch(db=db, filters={'permission_id': i})
    return response_200(data={})


@permission_router.post("/tree", dependencies=[Depends(check_permission(["sys:permission:list"]))],summary="权限列表==sys:permission:list")
async def permission_list(request_data: PageFilterList, db=Depends(get_db), _user=Depends(get_rbd_user)):
    filters = {}
    if request_data.name:
        filters["name"] = request_data.name
    if request_data.method:
        filters["method"] = request_data.method
    if request_data.type:
        filters["type"] = request_data.type
    obj = permission_db.get_list(db=db, page=0, size=request_data.size, filters=filters)
    for i in obj['dataList']:
        i.meta = {"title": i.name}
    data3 = get_tree_filter(jsonable_encoder(obj['dataList']), name=request_data.name)
    return response_200(data={'dataList': data3, 'total': obj['total']})


@permission_router.post("/options/tree", summary="权限列表==sys:permission:list")
async def permission_list(request_data: PageFilterList, db=Depends(get_db)):
    filters = {}
    if request_data.name:
        filters["name"] = request_data.name
    if request_data.type:
        filters["type"] = request_data.type
    obj = permission_db.get_list(db=db, page=0, size=request_data.size, filters=filters)
    for i in obj['dataList']:
        i.meta = {"title": i.name}
    data3 = get_tree_filter(jsonable_encoder(obj['dataList']), name=request_data.name)
    return response_200(data=data3)

@permission_router.post("/controller", summary="权限列表==rbac:permission:tree")
async def permission_list(request_data: PageList, db=Depends(get_db)):
    obj = permission_db.get_list(db=db, page=0, size=request_data.size, filters={'pid': 0})
    return response_200(data=obj['dataList'])


# @permission_router.post("/map", summary="权限列表==sys:permission:tree")
# async def permission_list(request_data: PageList, db=Depends(get_db)):
#     obj = permission_db.get_list(db=db, page=0, size=request_data.size)
#     # data = get_menu_tree(jsonable_encoder(obj['dataList']))
#     data = {}
#     for i in obj['dataList']:
#         if i.controller in data:
#             data[i.controller] = [i]
#         else:
#             data[i.controller].append(i)
#     return response_200(data=data)

# @permission_router.post("/treeData", summary="权限列表==rbac:user:list")
# async def permission_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
#     permission_obj = permission_db.get_list(db=db, page=request_data.page, size=request_data.size)
#     return response_200(data=jsonable_encoder(permission_obj))
