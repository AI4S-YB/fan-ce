import time
import os
import tempfile
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from apps.common.depends import get_active_user,check_permission
from db.database import get_db
from libs.responses.response import response_2000, response_200
from ..crud import database_meta_db, database_db
from ..models import Databases
from ..schemas import PageList, DataDelete, UpdateModel, DatabasesMetaCreate, DatabasesMetaBatchCreate

databases_meta_router = APIRouter(tags=['app:databasesMeta:数据元数据'])


@databases_meta_router.post("/field", summary="数据元数据字段")
async def databases_file(_user=Depends(get_active_user)):
    data = Databases.get_field()
    return response_2000(data=data)


@databases_meta_router.post("/list",dependencies=[Depends(check_permission(["app:database:meta:list"]))],  summary="数据元数据列表==app:database:meta::list")
async def databases_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    filters = {}
    if request_data.database_id:
        filters['database_id'] = request_data.database_id
    databases_obj = database_meta_db.get_list(db=db, page=request_data.page, size=request_data.size, filters=filters, sort='-id')
    for i in databases_obj['dataList']:
        if i.code == "genome_id":
            databases_one = database_db.get_one(db=db, id=i.value)
            i.value = databases_one.name if databases_one else i.value
    return response_200(data=databases_obj)


@databases_meta_router.post("/options",dependencies=[Depends(check_permission(["app:database:meta:list"]))],  summary="数据元数据列表==app:database:meta:options")
async def databases_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    new_data = []
    databases_obj = database_meta_db.get_list(db=db, page=0, size=request_data.size, sort='-id')
    for i in databases_obj['dataList']:
        new_data.append({'id': i.id, 'name': i.name})
    return response_2000(data=new_data)


@databases_meta_router.post("/add",dependencies=[Depends(check_permission(["app:database:meta:add"]))],  summary="数据元数据添加==app:database:meta:add")
async def databases_add(request_data: DatabasesMetaCreate, db=Depends(get_db), _user=Depends(get_active_user)):
    request_data.create_time = int(time.time())
    if database_meta_db.get_filter(db=db, filters={'code': 'genome_id','database_id': request_data.database_id}):
        return response_2000(data='', code=4012, msg='添加数据已存在')
    databases_obj = database_meta_db.create_one(db=db, obj_in=request_data)
    return response_200(data=databases_obj)


@databases_meta_router.post("/batch/add",dependencies=[Depends(check_permission(["app:database:meta:add"]))],  summary="数据元数据批量添加==app:database:meta:batch_add")
async def databases_batch_add(request_data: DatabasesMetaBatchCreate, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    批量添加数据元数据
    
    Args:
        request_data: 包含多个元数据项的批量创建请求
        db: 数据库会话
        _user: 当前用户信息
    
    Returns:
        包含处理结果统计的字典，包括成功数量、失败数量和详细的失败信息
    """
    success_count = 0
    failed_items = []
    
    for item in request_data.items:
        try:
            item.create_time = int(time.time())
            if database_meta_db.get_filter(db=db, filters={'code': 'genome_id','database_id': item.database_id}):
                failed_items.append({
                    "item": item.dict(), 
                    "error": "添加数据已存在"
                })
            else:
                database_meta_db.create_one(db=db, obj_in=item)
                success_count += 1
        except Exception as e:
            failed_items.append({
                "item": item.dict(), 
                "error": str(e)
            })
    
    result = {
        "total": len(request_data.items),
        "success_count": success_count,
        "failed_count": len(failed_items),
        "failed_items": failed_items
    }
    
    return response_200(data=result)


@databases_meta_router.post("/delete",dependencies=[Depends(check_permission(["app:database:meta:delete"]))],  summary="数据元数据删除==app:database:meta:delete")
async def databases_delete(request_data: DataDelete, db=Depends(get_db), _user=Depends(get_active_user)):
    if request_data.ids:
        for i in request_data.ids:
            database_meta_db.remove(db=db, id=int(i))
    else:
        database_meta_db.remove(db=db, id=request_data.id)
    return response_200(data={})


@databases_meta_router.post("/update",dependencies=[Depends(check_permission(["app:database:meta:update"]))],  summary="数据元数据更新==app:databases:meta:update")
async def databases_add(request_data: UpdateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    databases_obj = database_meta_db.get(db=db, id=request_data.id)
    databases_obj = database_meta_db.update_one(db=db, db_obj=databases_obj, obj_in=request_data)
    return response_200(data=databases_obj)