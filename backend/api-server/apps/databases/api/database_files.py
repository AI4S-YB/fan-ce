#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project: oma
@File   : files.py
@IDE    : PyCharm
@Author: llq
@Date   : 2024/11/28 23:49
@version:  1.0
@Desc   : 
"""
import os
import time
from typing import Optional

import aiofiles
from fastapi import APIRouter, Depends, File, UploadFile, Form

from apps.common.depends import get_active_user,check_permission
from core.config import settings
from db.database import get_db
from libs.responses.response import response_2000, response_200
from utils.unitaction.filezie import convert_size
from ..crud import database_file_db
from ..schemas import PageList, FileScan, DatabaseIdRequest, FilePathsResponse
from libs.fileaction.file import file_action
from apps.services.databases import databases_service

databases_file_router = APIRouter(tags=['app:databases:数据'])


async def save_upload_file_chunks(upload_file: UploadFile, destination: str, chunk_size: int = 1024 * 1024):
    try:
        async with aiofiles.open(destination, 'wb') as out_file:
            while chunk := await upload_file.read(chunk_size):
                await out_file.write(chunk)
        return True
    except Exception as e:
        print(f"保存文件时发生错误: {str(e)}")
        return False


@databases_file_router.post("/upload",dependencies=[Depends(check_permission(["app:database:file:upload"]))], summary="数据文件上传==app:datafile:upload")
async def databases_info(file: UploadFile = File(...), uid: str = Form(...), data_type: str = Form(None),
                         chunk_size: Optional[int] = 1024 * 1024,
                         db=Depends(get_db), _user=Depends(get_active_user)):
    try:
        app_options = settings.app_options
        file_dir = app_options.get('apps.databases.fileDir')
        os.makedirs(file_dir, exist_ok=True)
        file_name = f"{uid}_{file.filename}"
        file_path = f"{file_dir}/{file_name}"
        # 分块保存文件
        save_success = await save_upload_file_chunks(
            file, file_path, chunk_size
        )
        if not save_success:
            return response_2000(data={'url': 'file/save'}, code=5000, msg="文件保存失败")
        filedata = {
            'name': file.filename,
            'uid': uid,
            'file_name': file_name,
            'size': file.size,
            'type': file.filename.split('.')[-1],
            'data_type': data_type,
            'user_id': _user.id,
            'create_time': int(time.time()),
        }
        database_file_db.create_one(db=db, obj_in=filedata)
        data = {
            "filename": file_name,
            "content_type": file.content_type,
            "url": file_path,
            "uuid": uid,
        }
        return response_2000(data=data)
    except Exception as e:
        print(e)
        return response_2000(data={'url': 'file/save'}, code=5000, msg="文件保存失败")


@databases_file_router.post("/file/list",dependencies=[Depends(check_permission(["app:database:file:list"]))],  summary="数据文件列表==app:datafile:list")
async def databases_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    filters = {}
    if request_data.database_id:
        filters['database_id'] = request_data.database_id
    databases_file_obj = database_file_db.get_list(db=db, page=request_data.page, size=request_data.size, filters=filters)
    for i in databases_file_obj['dataList']:
        result = convert_size(i.size, unit='MB')
        i.size = f"{result[0]['size']}{result[0]['unit']}"
    return response_200(data=databases_file_obj)


@databases_file_router.post("/file/scan",dependencies=[Depends(check_permission(["app:database:file:scan"]))], summary="数据文件列表==app:databasesFile:list")
async def databases_list(request_data: FileScan, db=Depends(get_db), _user=Depends(get_active_user)):
    path = request_data.path if request_data.path else settings.DATABASE_PATH
    files = file_action.get_dir_one(path)
    return response_2000(data=files)


@databases_file_router.post("/file/search",dependencies=[Depends(check_permission(["app:database:file:search"]))], summary="数据文件列表==app:databasesFile:list")
async def databases_list(request_data: FileScan, db=Depends(get_db), _user=Depends(get_active_user)):
    if _user.is_superman:
        root_path = settings.DATABASE_PATH
    else:
        root_path = databases_service.get_database_file_path(db=db, team_id=request_data.team_id)
    path = os.path.join(root_path,request_data.path) if request_data.path else root_path
    files = file_action.get_dir_one(path)
    return response_2000(data=files)

# 在文件顶部添加导入
from ..schemas import PageList, FileScan, DatabaseIdRequest, FilePathsResponse

# 更新接口
@databases_file_router.post("/database-to-paths", dependencies=[Depends(check_permission(["app:database:file:list"]))], summary="根据数据库ID获取文件路径列表")
async def get_file_paths_by_database(request_data: DatabaseIdRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    根据数据库ID（单个或多个）获取文件路径列表
    
    Args:
        request_data: 包含database_id的请求数据（支持单个int或int列表）
    
    Returns:
        包含file_paths列表的响应
    """
    database_id = request_data.database_id
    
    if not database_id:
        return response_2000(data=FilePathsResponse(file_paths=[]).dict())
    
    # 支持单个ID或ID列表
    if isinstance(database_id, int):
        database_ids = [database_id]
    elif isinstance(database_id, list):
        database_ids = database_id
    else:
        return response_2000(data=FilePathsResponse(file_paths=[]).dict())
    
    # 查询database_file表获取path列表
    file_paths = []
    for did in database_ids:
        database_files = database_file_db.get_data(db=db, filters={'database_id': did})
        for df in database_files:
            if df.path and df.path not in file_paths:
                file_paths.append(df.path)
    
    return response_2000(data=FilePathsResponse(file_paths=file_paths).dict())
