# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/12/20 10:20
@Function: DatabasesFile API - 专门处理 databases_file 表的API接口
@version :  1.0
@Desc    :  仿照 database.py 创建的 databases_file 表专用API
"""
import os
import time
from typing import List
import uuid

from fastapi import APIRouter, Depends, Header, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
import mimetypes
from urllib.parse import quote
from sqlalchemy import null
from db.database import get_db
from libs.httpclient.request import data_format
from libs.responses.response import response_2000, response_200
from apps.common.depends import get_active_user, check_permission, users_db
from ..schemas import (
    DatabasesFilePageList, DatabasesFileCreate, DatabasesFileUpdate, 
    DatabasesFileResponse, DatabasesFileDelete, DatabasesFileBatchCreate,
    DatabasesFileInfo, DatabasesFileOptions, DatabasesFileOptionsResponse
)
from libs.tools import run_in_background
from ..crud import database_file_db, database_db
from ..models import DatabasesFile

databases_file_router = APIRouter(tags=['app:database_file:增强元数据'])


@databases_file_router.post("/field", summary="增强元数据文件字段")
async def databases_file_field(_user=Depends(get_active_user)):
    """获取增强元数据文件表的字段信息"""
    data = DatabasesFile.get_field()
    return response_2000(data=data)


@databases_file_router.post("/list", dependencies=[Depends(check_permission(["app:database-file:list"]))], 
                           summary="增强元数据文件列表==app:database-file:list")
async def databases_file_list(request_data: DatabasesFilePageList, db=Depends(get_db), _user=Depends(get_active_user)):
    """获取增强元数据文件列表，支持分页和过滤"""
    filters = {}
    filters_exp = []
    
    # 处理 team_id 和 project_id 过滤逻辑（与原始 databases_list 方法完全一致）
    
    # 1. team_id 过滤在社区版已移除
    team_database_ids = None
    
    # 2. 总是处理 project_id（与原始方法一致，不管 project_id 是否为 None）
    from apps.services.databases import databases_service
    project_database_ids = databases_service.get_databases_by_project(db=db, project_id=request_data.project_id)
    
    # 3. 确定最终的 database_ids
    if team_database_ids is not None:
        # 如果指定了 team_id，需要取交集
        if project_database_ids:
            database_ids = list(set(team_database_ids) & set(project_database_ids))
        else:
            database_ids = team_database_ids
    else:
        # 如果没有指定 team_id，直接使用 project_id 的结果
        database_ids = project_database_ids
    
    # 4. 如果没有找到任何数据库，使用假 ID -1（与原始方法一致）
    if database_ids:
        filters_exp.append({'name': 'database_id', 'exp': 'contain', 'value': database_ids})
    else:
        filters_exp.append({'name': 'database_id', 'exp': 'contain', 'value': [-1]})
    
    # 根据类型过滤
    if request_data.type:
        filters['type'] = request_data.type
        
    # 根据数据类型过滤
    if request_data.data_type:
        filters['data_type'] = request_data.data_type
        
    # 根据状态过滤
    if request_data.status is not None:
        filters['status'] = request_data.status
        
    # 根据名称模糊搜索
    if request_data.name:
        filters_exp.append({'name': 'name', 'exp': 'like', 'value': f'%{request_data.name}%'})

    # 获取分页数据
    data = database_file_db.get_list(
        db=db, 
        page=request_data.page, 
        size=request_data.size, 
        filters=filters,
        filters_exp=filters_exp,
        sort='-create_time'
    )
    
    # 转换为字典并格式化文件大小
    formatted_data = []
    for item in data['dataList']:
        item_dict = item.to_dict() if hasattr(item, 'to_dict') else jsonable_encoder(item)
        if item_dict.get('size'):
            item_dict['size_formatted'] = f"{item_dict['size'] / (1024*1024):.2f} MB"
        formatted_data.append(item_dict)
    
    data['dataList'] = formatted_data
    return response_2000(data=data)


@databases_file_router.post("/options", dependencies=[Depends(check_permission(["app:database-file:list"]))], 
                           summary="增强元数据文件选项列表==app:database-file:options")
async def databases_file_options(request_data: DatabasesFileOptions, db=Depends(get_db), _user=Depends(get_active_user)):
    """获取增强元数据文件的简化选项列表，用于下拉选择等场景"""
    filters = {}
    
    if request_data.database_id:
        filters['database_id'] = request_data.database_id
    if request_data.type:
        filters['type'] = request_data.type
    if request_data.data_type:
        filters['data_type'] = request_data.data_type
    
    # 只获取必要字段
    files = database_file_db.get_data(db=db, filters=filters)
    
    options = []
    for file in files:
        options.append({
            'id': file.id,
            'name': file.name,
            'path': file.path,
            'size': file.size
        })
    
    return response_2000(data=options)


@databases_file_router.post("/info", dependencies=[Depends(check_permission(["app:database-file:info"]))], 
                           summary="增强元数据文件详情==app:database-file:info")
async def databases_file_info(request_data: DatabasesFileInfo, db=Depends(get_db)):
    """获取单个增强元数据文件的详细信息"""
    file_info = database_file_db.get(db=db, id=request_data.id)
    if not file_info:
        return response_200(msg="文件不存在")
    
    # 转换为字典并添加关联的增强元数据信息
    file_dict = file_info.to_dict()
    if file_info.databases:
        file_dict['databases'] = file_info.databases.to_dict()
    
    return response_2000(data=file_dict)


@databases_file_router.post("/download", dependencies=[Depends(check_permission(["app:database-file:download"]))], 
                           summary="下载增强元数据文件")
async def download_databases_file(
    request_data: DatabasesFileInfo, 
    db=Depends(get_db), 
    _user=Depends(get_active_user), 
    user_agent: str = Header(None), 
    range: str = Header(None)
):
    """下载增强元数据文件，支持断点续传"""
    file_info = database_file_db.get(db=db, id=request_data.id)
    if not file_info:
        return response_200(message="文件不存在")
    
    file_path = file_info.path
    if not file_path or not os.path.exists(file_path):
        return response_200(message="文件路径不存在")
    
    # 获取文件信息
    file_size = os.path.getsize(file_path)
    file_name = file_info.name or os.path.basename(file_path)
    
    # 处理断点续传
    start = 0
    end = file_size - 1
    
    if range:
        range_match = range.replace('bytes=', '').split('-')
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1
    
    # 设置响应头
    headers = {
        'Content-Range': f'bytes {start}-{end}/{file_size}',
        'Accept-Ranges': 'bytes',
        'Content-Length': str(end - start + 1),
        'Content-Disposition': f'attachment; filename*=UTF-8\'\'{quote(file_name)}'
    }
    
    # 获取MIME类型
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type:
        headers['Content-Type'] = content_type
    
    return FileResponse(
        path=file_path,
        headers=headers,
        status_code=206 if range else 200
    )


@databases_file_router.post("/batch/add", dependencies=[Depends(check_permission(["app:database-file:add"]))], 
                           summary="批量添加增强元数据文件==app:database-file:add")
async def databases_file_batch_add(request_data: DatabasesFileBatchCreate, db=Depends(get_db), _user=Depends(get_active_user)):
    """批量添加增强元数据文件"""
    created_files = []
    current_time = int(time.time())
    
    for file_data in request_data.files:
        # 生成UID
        if not file_data.uid:
            file_data.uid = str(uuid.uuid4())
        
        # 设置创建时间和用户信息
        file_dict = file_data.dict()
        file_dict['create_time'] = current_time
        if request_data.database_id:
            file_dict['database_id'] = request_data.database_id
        
        # 创建文件记录
        created_file = database_file_db.create(db=db, obj_in=file_dict)
        created_files.append(created_file.to_dict())
    
    return response_2000(data=created_files, message=f"成功批量添加 {len(created_files)} 个文件")


@databases_file_router.post("/add", dependencies=[Depends(check_permission(["app:database-file:add"]))], 
                           summary="添加增强元数据文件==app:database-file:add")
async def databases_file_add(request_data: DatabasesFileCreate, db=Depends(get_db), _user=Depends(get_active_user)):
    """添加单个增强元数据文件"""
    # 生成UID
    if not request_data.uid:
        request_data.uid = str(uuid.uuid4())
    
    # 设置创建时间
    file_dict = request_data.dict()
    file_dict['create_time'] = int(time.time())
    
    # 创建文件记录
    created_file = database_file_db.create(db=db, obj_in=file_dict)
    
    return response_2000(data=created_file.to_dict(), message="文件添加成功")


@databases_file_router.post("/delete", dependencies=[Depends(check_permission(["app:database-file:delete"]))], 
                           summary="删除增强元数据文件==app:database-file:delete")
async def databases_file_delete(request_data: DatabasesFileDelete, db=Depends(get_db), _user=Depends(get_active_user)):
    """删除增强元数据文件（支持单个或批量删除）"""
    deleted_count = 0
    
    # 处理单个删除
    if request_data.id:
        file_info = database_file_db.get(db=db, id=request_data.id)
        if file_info:
            database_file_db.remove(db=db, id=request_data.id)
            deleted_count += 1
    
    # 处理批量删除
    if request_data.ids:
        for file_id in request_data.ids:
            file_info = database_file_db.get(db=db, id=file_id)
            if file_info:
                database_file_db.remove(db=db, id=file_id)
                deleted_count += 1
    
    return response_2000(message=f"成功删除 {deleted_count} 个文件")


@databases_file_router.post("/update", dependencies=[Depends(check_permission(["app:database-file:update"]))], 
                           summary="更新增强元数据文件==app:database-file:update")
async def databases_file_update(request_data: DatabasesFileUpdate, db=Depends(get_db), _user=Depends(get_active_user)):
    """更新增强元数据文件信息"""
    file_info = database_file_db.get(db=db, id=request_data.id)
    if not file_info:
        return response_200(message="文件不存在")
    
    # 更新文件信息
    update_data = request_data.dict(exclude_unset=True, exclude={'id'})
    updated_file = database_file_db.update(db=db, db_obj=file_info, obj_in=update_data)
    
    return response_2000(data=updated_file.to_dict(), message="文件更新成功")


@databases_file_router.post("/count", dependencies=[Depends(check_permission(["app:database-file:list"]))], 
                           summary="增强元数据文件统计==app:database-file:count")
async def databases_file_count(request_data: DatabasesFilePageList, db=Depends(get_db), _user=Depends(get_active_user)):
    """统计增强元数据文件的数量和大小信息"""
    filters = {}
    filters_exp = []
    
    # 处理 team_id 和 project_id 过滤逻辑（与 databases_file_list 方法完全一致）
    
    # 1. team_id 过滤在社区版已移除
    team_database_ids = None
    
    # 2. 总是处理 project_id（与原始方法一致，不管 project_id 是否为 None）
    from apps.services.databases import databases_service
    project_database_ids = databases_service.get_databases_by_project(db=db, project_id=request_data.project_id)
    
    # 3. 确定最终的 database_ids
    if team_database_ids is not None:
        # 如果指定了 team_id，需要取交集
        if project_database_ids:
            database_ids = list(set(team_database_ids) & set(project_database_ids))
        else:
            database_ids = team_database_ids
    else:
        # 如果没有指定 team_id，直接使用 project_id 的结果
        database_ids = project_database_ids
    
    # 4. 如果没有找到任何数据库，使用假 ID -1（与原始方法一致）
    if not database_ids:
        database_ids = [-1]
    
    # 如果没有找到任何数据库，使用假 ID -1（与原始方法一致）
    if database_ids:
        filters_exp.append({'name': 'database_id', 'exp': 'contain', 'value': database_ids})
    else:
        filters_exp.append({'name': 'database_id', 'exp': 'contain', 'value': [-1]})
    
    # 处理其他过滤条件
    if request_data.database_id:
        # 如果同时指定了 database_id，需要取交集
        if database_ids:
            if request_data.database_id in database_ids:
                filters['database_id'] = request_data.database_id
            else:
                # 指定的 database_id 不在允许范围内，返回空统计
                return response_2000(data={
                    'total_count': 0,
                    'total_size': 0,
                    'total_size_formatted': "0 B",
                    'type_stats': {},
                    'data_type_stats': {},
                    'status_stats': {}
                })
        else:
            filters['database_id'] = request_data.database_id
    
    if request_data.type:
        filters['type'] = request_data.type
    if request_data.data_type:
        filters['data_type'] = request_data.data_type
    if request_data.status is not None:
        filters['status'] = request_data.status
    
    # 获取所有符合条件的文件
    # 使用 get_list 方法来支持 filters_exp，设置 page=0, size=0 获取所有数据
    result = database_file_db.get_list(db=db, page=0, size=0, filters=filters, filters_exp=filters_exp)
    files = result['dataList']
    
    # 统计信息
    total_count = len(files)
    total_size = sum(file.size or 0 for file in files)
    
    # 按类型统计
    type_stats = {}
    data_type_stats = {}
    status_stats = {}
    
    for file in files:
        # 按type统计
        if file.type:
            type_stats[file.type] = type_stats.get(file.type, 0) + 1
        
        # 按data_type统计
        if file.data_type:
            data_type_stats[file.data_type] = data_type_stats.get(file.data_type, 0) + 1
        
        # 按status统计
        status_key = str(file.status) if file.status is not None else 'null'
        status_stats[status_key] = status_stats.get(status_key, 0) + 1
    
    stats = {
        'total_count': total_count,
        'total_size': total_size,
        'total_size_formatted': f"{total_size / (1024*1024*1024):.2f} GB" if total_size > 0 else "0 B",
        'type_stats': type_stats,
        'data_type_stats': data_type_stats,
        'status_stats': status_stats
    }
    
    return response_2000(data=stats)


@databases_file_router.post("/database-to-files", dependencies=[Depends(check_permission(["app:database-file:list"]))], 
                           summary="根据增强元数据ID获取文件列表")
async def get_files_by_database(request_data: DatabasesFileOptions, db=Depends(get_db), _user=Depends(get_active_user)):
    """根据增强元数据ID获取关联的文件列表"""
    if not request_data.database_id:
        return response_200(message="database_id 参数必填")
    
    filters = {'database_id': request_data.database_id}
    if request_data.type:
        filters['type'] = request_data.type
    if request_data.data_type:
        filters['data_type'] = request_data.data_type
    
    files = database_file_db.get_multi(db=db, filters=filters)
    
    file_list = []
    for file in files:
        file_dict = file.to_dict()
        if file.size:
            file_dict['size_formatted'] = f"{file.size / (1024*1024):.2f} MB"
        file_list.append(file_dict)
    
    return response_2000(data=file_list)