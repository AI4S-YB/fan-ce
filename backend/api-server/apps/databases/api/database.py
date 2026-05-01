# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/9/23 10:20
@Function:
@version :  1.0
@Desc    :  None
"""
import os
import time
from turtle import pd
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
from apps.common.depends import get_active_user, check_permission,users_db
from ..schemas import PageList, DataInfo, DataDelete, CreateModel, UpdateModel,CreateBatchModel, BuildMetaModel
from libs.tools import run_in_background
from ..crud import database_db, database_file_db, database_meta_db, project_database_db, sample_db, experiment_db
from ..models import Databases

from apps.services.databases import databases_service

databases_router = APIRouter(tags=['app:databases:数据'])


@databases_router.post("/field", summary="数据字段")
async def databases_file(_user=Depends(get_active_user)):
    data = Databases.get_field()
    return response_2000(data=data)


@databases_router.post("/list",dependencies=[Depends(check_permission(["app:database:list"]))], summary="数据列表==app:database:list")
async def databases_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    filters = {}
    filters_exp = []
    database_ids = databases_service.get_databases_by_project(db=db,project_id=request_data.project_id)

    # if the project has no data, using a fake database id -1 to filter data 
    if database_ids:
        filters_exp.append({'name':'id','exp':'contain','value':database_ids})
    else:
        filters_exp.append({'name':'id','exp':'contain','value':[-1]})
    if request_data.database_id:
      # 验证权限：确保请求的database_id在用户权限范围内
      if database_ids and request_data.database_id in database_ids:
          # 移除之前设置的范围查询条件，使用精确匹配
          filters_exp = [f for f in filters_exp if f.get('name') != 'id']
          filters['id'] = request_data.database_id
      elif database_ids and request_data.database_id not in database_ids:
          # 如果不在权限范围内，保持原有的filters_exp逻辑
          # 这样会自然返回空结果，避免权限错误提示
          pass
      elif not database_ids:
          # 如果项目没有任何数据库，保持原有逻辑（使用[-1]过滤）
          pass
    if request_data.name:
        filters_exp.append({'name': 'name', 'exp': 'like', 'value': request_data.name})
    if request_data.type:
        filters['type'] = request_data.type
    if request_data.status:
        filters['status'] = request_data.status
    if request_data.is_public:
        filters['is_public'] = request_data.is_public
    if request_data.database_id:
        filters['id'] = request_data.database_id
    databases_obj = database_db.get_list(db=db, page=request_data.page, size=request_data.size, filters=filters, filters_exp=filters_exp,
                                         sort='-id')
    for i in databases_obj['dataList']:
        user_obj = users_db.get_one(db=db, id=i.user_id)
        file_obj = database_file_db.get_filter(db=db, filters={'database_id': i.id})
        i.user_name = user_obj.user_name if user_obj.user_name else ''
        meta_obj = database_meta_db.get_data(db=db, filters={'database_id': i.id})
        i.meta = meta_obj
        i.files = file_obj
        i.file_path = file_obj.path if file_obj else ''
    return response_2000(data=jsonable_encoder(databases_obj))


@databases_router.post("/options",dependencies=[Depends(check_permission(["app:database:list"]))], summary="数据列表==app:database:options")
async def databases_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    new_data = []
    filters = {}
    filters_exp = []
    if request_data.type:
        filters['type'] = request_data.type
    if request_data.database_id:
        filters['id'] = request_data.database_id
    database_ids = databases_service.get_databases_by_project(db=db,project_id=request_data.project_id)
    if database_ids:
        filters_exp.append({'name':'id','exp':'contain','value':database_ids})
    databases_obj = database_db.get_list(db=db, page=0, size=request_data.size, filters=filters, sort='-id',filters_exp=filters_exp)
    for i in databases_obj['dataList']:
        file_obj = database_file_db.get_filter(db=db, filters={'database_id': i.id})
        new_data.append({'id': i.id, 'name': i.name,'file_path':file_obj.path if file_obj else '',})
    return response_2000(data=new_data)


@databases_router.post("/info",dependencies=[Depends(check_permission(["app:database:info"]))], summary="数据列表==app:database:info")
async def databases_info(request_data: DataInfo, db=Depends(get_db)):
# async def databases_info(request_data: DataInfo, db=Depends(get_db), _user=Depends(get_active_user)):
    databases_obj = database_db.get(db=db, id=request_data.id)
    files = database_file_db.get_data(db=db, filters={'database_id': databases_obj.id})
    databases_obj.file_list = files
    # databases_obj.user_name = _user.user_name
    return response_2000(data=jsonable_encoder(databases_obj))

@databases_router.post("/download", dependencies=[Depends(check_permission(["app:database:info"]))], summary="Download database file")
async def download_database_file(
    request_data: DataInfo, db=Depends(get_db), _user=Depends(get_active_user), 
    user_agent: str = Header(None), range: str = Header(None)  # 支持断点续传
    ):
    """
    Download database file endpoint
    
    Args:
        database_id: ID of the database to download
        db: Database session        
    Returns:
        FileResponse with the database file
    """
    # databases_obj = database_db.get(db=db, id=request_data.id)
    # files = database_file_db.get_data(db=db, filters={'database_id': databases_obj.id})
    # Get database files
    file_obj = database_file_db.get_filter(db=db, filters={'database_id': request_data.id})

    if not file_obj:
        raise HTTPException(status_code=404, detail="Database file not found")
        
    file_path = file_obj.path
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File does not exist on server")
        
    if not os.access(file_path, os.R_OK):
        raise HTTPException(status_code=403, detail="No permission to read file")
        
    # Auto detect MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'
        
    # URL encode filename to handle Chinese characters
    filename = os.path.basename(file_path)
    encoded_filename = quote(filename)
    
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
    }
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=mime_type,
        headers=headers
    )



@databases_router.post("/batch/add",dependencies=[Depends(check_permission(["app:database:add"]))], summary="数据批量添加==app:database:add")
async def databases_add(request_data: CreateBatchModel, db=Depends(get_db), _user=Depends(get_active_user)):
    file_list = request_data.file_list if request_data.file_list else []
    for file in file_list:
        request_data.create_time = int(time.time())
        request_data.status = 1
        request_data.user_id = _user.id
        request_data.is_active = 1
        request_data.name = file.name
        databases_obj = database_db.create_one(db=db, obj_in=request_data)
        databases_service.create_database(db=db, database_id=databases_obj.id,project_id=request_data.project_id)
        file.status = 1
        file.database_id = databases_obj.id
        file.uuid = uuid.uuid4()
        file.type = os.path.splitext(file.path)[1]
        file.data_type = file.file_type
        file.file_name = os.path.splitext(os.path.basename(file.path))[0]
        file.create_time = int(time.time())
        datafile_obj = database_file_db.create_one(db=db, obj_in=file)
        database_file_db.update_one(db=db, db_obj=datafile_obj, obj_in={'database_id': databases_obj.id})
    return response_200(data={})


@databases_router.post("/add",dependencies=[Depends(check_permission(["app:database:add"]))], summary="数据添加==app:database:add")
async def databases_add(request_data: CreateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    request_data.create_time = int(time.time())
    request_data.status = 1
    request_data.user_id = _user.id
    request_data.is_active = 1
    databases_obj = database_db.create_one(db=db, obj_in=request_data)
    for file in request_data.file_list:
        datafile_obj = database_file_db.get_filter(db=db, filters={'uid': file['uuid']})
        database_file_db.update_one(db=db, db_obj=datafile_obj, obj_in={'database_id': databases_obj.id})
    return response_200(data=databases_obj)


@databases_router.post("/delete",dependencies=[Depends(check_permission(["app:database:delete"]))], summary="数据删除==app:database:delete")
async def databases_delete(request_data: DataDelete, db=Depends(get_db), _user=Depends(get_active_user)):
    if request_data.ids:
        for i in request_data.ids:
            project_database_db.remove_batch(db=db,filters={'database_id': int(i)})
            database_db.remove(db=db, id=int(i))
    else:
        database_db.remove(db=db, id=request_data.id)
        project_database_db.remove_batch(db=db, filters={'database_id': request_data.id})
    return response_200(data={})


@databases_router.post("/update",dependencies=[Depends(check_permission(["app:database:update"]))], summary="数据更新==app:database:update")
async def databases_add(request_data: UpdateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    databases_obj = database_db.get(db=db, id=request_data.id)
    databases_obj = database_db.update_one(db=db, db_obj=databases_obj, obj_in=request_data)
    return response_2000(data=jsonable_encoder(databases_obj))


@databases_router.post("/rename",dependencies=[Depends(check_permission(["app:database:update"]))], summary="数据更新==app:database:update")
async def databases_add(request_data: UpdateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    databases_obj = database_db.get(db=db, id=request_data.id)
    databases_obj = database_db.update_one(db=db, db_obj=databases_obj, obj_in={'name': request_data.name})
    return response_2000(data=jsonable_encoder(databases_obj))


"""
#10【数据资产】-【数据管理】-构建关联并保存增强元数据：服务端 
Clark 2025-07-24
"""
@databases_router.post("/buildmeta",dependencies=[Depends(check_permission(["app:database:list"]))], summary="数据列表==app:database:list")
async def buildmeta(req_data: BuildMetaModel, db=Depends(get_db), _user=Depends(get_active_user)):
    # 获取当前用户
    user_id = _user.id
    # system_project removed — skip project lookup and meta_json update
    # 新增样本
    for sample in req_data.meta_json.samples:
        # 缓存当前实验
        current_experiments = sample.experiments
        sample.experiments = None
        # 样本元数据
        sample.meta_json = sample.model_dump_json(indent=2)
        sample.type = '1'
        sample.create_time = int(time.time())
        sample.is_public = req_data.is_public
        sample.is_deleted = req_data.is_delete
        sample.status = 1
        sample.project_id = req_data.project_id
        sample.user_id = user_id
        sample_obj = sample_db.create_one(db=db, obj_in=sample)
        print(f"--------样本创建完成-------{sample_obj.id}")

        # 新增实验
        for experiment in current_experiments:
            # 实验元数据
            experiment.meta_json = experiment.model_dump_json(indent=2)
            experiment.create_time = int(time.time())
            experiment.is_public = req_data.is_public
            experiment.is_deleted = req_data.is_delete
            experiment.status = 1
            experiment.sample_id = sample_obj.id
            experiment.user_id = user_id
            experiment_obj = experiment_db.create_one(db=db, obj_in=experiment)
            print(f"--------实验创建完成-------{experiment_obj.id}")

        # 关联项目与数据
        pd_list = []
        for file_id in req_data.file_ids:
            pd_obj = {'project_id': req_data.project_id, 'database_id': file_id}
            pd_list.append(pd_obj)  # 使用append方法添加元素
        # 批量创建
        project_database_db.create_batch(db=db, add_data=pd_list)
        
    return response_2000()

#
# @databases_router.post("/active/forma", summary="数据格式化==app:databases:update")
# async def databases_add(request_data: DataActive, db=Depends(get_db), _user=Depends(get_active_user)):
#     databases_obj = database_db.get(db=db, id=request_data.id)
#     run_in_background(data_format, args=(request_data, databases_obj))
#     return response_2000(data={})


# 在文件顶部添加导入
from ..schemas import PageList, DataInfo, DataDelete, CreateModel, UpdateModel, CreateBatchModel, BuildMetaModel, ProjectIdRequest, DatabaseIdsResponse, LinkProjectRequest, GetLinkedProjectsRequest, LinkedProjectsResponse

# 更新接口
@databases_router.post("/project-to-databases", dependencies=[Depends(check_permission(["app:database:list"]))], summary="根据项目ID获取数据库ID列表")
async def get_database_ids_by_project(request_data: ProjectIdRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    根据项目ID（单个或多个）获取数据库ID列表
    
    Args:
        request_data: 包含project_id的请求数据（支持单个int或int列表）
    
    Returns:
        包含database_ids列表的响应
    """
    project_id = request_data.project_id
    
    if not project_id:
        return response_2000(data=DatabaseIdsResponse(database_ids=[]).dict())
    
    # 支持单个ID或ID列表
    if isinstance(project_id, int):
        project_ids = [project_id]
    elif isinstance(project_id, list):
        project_ids = project_id
    else:
        return response_2000(data=DatabaseIdsResponse(database_ids=[]).dict())
    
    # 查询project_database表获取database_id列表
    database_ids = []
    for pid in project_ids:
        project_databases = project_database_db.get_data(db=db, filters={'project_id': pid})
        for pd in project_databases:
            if pd.database_id not in database_ids:
                database_ids.append(pd.database_id)
    
    return response_2000(data=DatabaseIdsResponse(database_ids=database_ids).dict())


@databases_router.post("/link-project", dependencies=[Depends(check_permission(["app:database:update"]))], summary="关联项目到数据库")
async def link_to_project(request_data: LinkProjectRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    关联项目到数据库
    
    Args:
        request_data: 包含database_id和project_ids的请求数据
    
    Returns:
        操作结果
    """
    database_id = request_data.database_id
    project_ids = request_data.project_ids
    
    try:
        # 1. 获取当前数据库已关联的项目
        existing_project_databases = project_database_db.get_data(db=db, filters={'database_id': database_id})
        existing_project_ids = [pd.project_id for pd in existing_project_databases]
        
        # 2. 找出需要删除的关联（已存在但不在新列表中的）
        project_ids_to_remove = [pid for pid in existing_project_ids if pid not in project_ids]
        print(f"--------project_ids_to_remove-------{project_ids_to_remove}")
        # 3. 找出需要新增的关联（在新列表中但不存在于当前关联中的）
        project_ids_to_add = [pid for pid in project_ids if pid not in existing_project_ids]
        
        # 4. 删除不需要的关联
        if project_ids_to_remove:
            for project_id in project_ids_to_remove:
                project_database_db.remove_batch(db=db, filters={
                    'database_id': int(database_id),
                    'project_id': project_id
                })
        
        # 5. 新增需要的关联
        if project_ids_to_add:
            add_data = []
            for project_id in project_ids_to_add:
                add_data.append({
                    'database_id': database_id,
                    'project_id': project_id
                })
            project_database_db.create_batch(db=db, add_data=add_data)
        
        return response_2000(data={
            'message': '项目关联操作成功',
            'removed_count': len(project_ids_to_remove),
            'added_count': len(project_ids_to_add),
            'total_linked_projects': len(project_ids)
        })
        
    except Exception as e:
        return response_2000(data={
            'message': f'项目关联操作失败: {str(e)}',
            'error': True
        })


@databases_router.post("/get-linked-projects", dependencies=[Depends(check_permission(["app:database:info"]))], summary="查询数据库关联的项目")
async def get_linked_projects(request_data: GetLinkedProjectsRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    查询数据库关联的项目
    
    Args:
        request_data: 包含database_id的请求数据
    
    Returns:
        包含关联项目信息的响应
    """
    database_id = request_data.database_id
    
    try:
        # 使用get_data获取关联关系
        project_databases = project_database_db.get_data(db=db, filters={'database_id': database_id})
        
        # 提取项目ID列表 (system_project removed, return IDs only)
        # TODO(Task-4): restore rich project detail via brd_program lookup
        project_ids = [pd.project_id for pd in project_databases]
        projects = [{"id": pid} for pid in project_ids]

        return response_2000(data=LinkedProjectsResponse(
            project_ids=project_ids,
            projects=projects
        ).dict())
        
    except Exception as e:
        return response_2000(data={
            'message': f'查询关联项目失败: {str(e)}',
            'error': True,
            'project_ids': [],
            'projects': []
        })


@databases_router.post("/count", dependencies=[Depends(check_permission(["app:database:list"]))], 
                      summary="数据类型统计==app:database:count")
async def databases_count(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    获取数据库按类型的统计信息
    
    Args:
        request_data: 包含团队ID和项目ID的请求数据
        db: 数据库会话
        _user: 当前用户
    
    Returns:
        包含各数据类型统计信息的响应
    """
    # 数据类型映射
    TYPE_NAMES = {
        '1': 'Genome Files',
        '2': 'RNA-seq Expression Data', 
        '3': 'Variant Data',
        '4': 'Tabix Index Files',
        '5': 'Sequence Data',
        '6': 'Sequence Data (Extended)',
        '7': 'Germplasm Resource Data',
        '8': 'Phenotype Data'
    }
    
    # 基础过滤条件
    filters = {}
    filters_exp = []
    
    # 获取项目权限范围内的数据库ID
    if request_data.project_id:
        database_ids = databases_service.get_databases_by_project(db=db, project_id=request_data.project_id)
        if database_ids:
            filters_exp.append({'name':'id','exp':'contain','value':database_ids})
        else:
            # 如果指定了项目但没有关联数据库，返回空结果
            filters_exp.append({'name':'id','exp':'contain','value':[-1]})
    # 如果没有指定项目ID，则查询该团队下的所有数据库
    
    # 按类型统计
    database_types = {}
    total_count = 0
    
    for type_id, type_name in TYPE_NAMES.items():
        type_filters = {**filters, 'type': type_id}
        # 确保filters不为None，并处理is_delete字段
        safe_filters = type_filters if type_filters else {}
        safe_filters['is_delete'] = False  # 只查询未删除的记录
        
        count = database_db.get_count(db=db, filters=safe_filters, filters_exp=filters_exp)
        database_types[type_id] = {
            'name': type_name,
            'count': count
        }
        total_count += count
    
    result = {
        'database_types': database_types,
        'total_databases': total_count
    }
    
    return response_2000(data=result)
