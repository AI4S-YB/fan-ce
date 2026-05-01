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

from apps.common.depends import get_active_user, check_permission,users_db
from apps.databases.crud import project_database_db
from apps.sample.crud import sample_db
from apps.services.project import project_service
from db.database import get_db
from libs.responses.response import response_2000, response_200
from ..project.crud import project_db
from ..project.models import Project
# 需要添加导入
from ..project.schemas import PageList, DataInfo, DataDelete, CreateModel, UpdateModel, ProjectMetaJsonRequest, TeamIdRequest

project_router = APIRouter()


@project_router.post("/field", summary="项目字段")
async def project_file():
    data = Project.get_field()
    return response_2000(data=data)


@project_router.post("/list", dependencies=[Depends(check_permission(["sys:project:list"]))], summary="项目列表==sys:project:list")
async def project_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    filters_exp = []
    if request_data.name:
        filters_exp.append({'name': 'name', 'exp': 'like', 'value': request_data.name})
    if request_data.code:
        filters_exp.append({'name': 'code', 'exp': 'like', 'value': request_data.code})
    project_obj = project_db.get_list(db=db, page=request_data.page, size=request_data.size, filters_exp=filters_exp)
    for i in project_obj['dataList']:
        user = users_db.get_one(db=db, id=i.user_id)
        i.database_id = [d.database_id for d in project_database_db.get_data(db=db, filters={'project_id': i.id})]
        i.sample_id = [sample.id for sample in sample_db.get_data(db=db, filters={'project_id': i.id})]
        i.user_name = user.user_name if user else 'sys'
    return response_2000(data=jsonable_encoder(project_obj))


@project_router.post("/options", dependencies=[Depends(check_permission(["sys:project:list"]))], summary="项目列表==sys:project:list")
async def project_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    options = []
    filters_exp = []
    project_obj = project_db.get_list(db=db, page=0,filters_exp=filters_exp)
    for i in project_obj['dataList']:
        options.append({'label': i.name, 'value': i.id, 'name': i.name, 'id': i.id})
    return response_2000(data=options)


@project_router.post("/info", dependencies=[Depends(check_permission(["sys:project:info"]))], summary="项目列表==sys:project:info")
async def project_info(request_data: DataInfo, db=Depends(get_db)):
    project_obj = project_db.get(db=db, id=request_data.id)
    project_obj.database_id = [d.database_id for d in project_database_db.get_data(db=db, filters={'project_id': project_obj.id})]
    project_obj.sample_id = [sample.id for sample in sample_db.get_data(db=db, filters={'project_id': project_obj.id})]
    return response_2000(data=jsonable_encoder(project_obj))


@project_router.post("/add", dependencies=[Depends(check_permission(["sys:project:add"]))], summary="项目添加==sys:project:add")
async def project_add(request_data: CreateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    request_data.user_id = _user.id
    request_data.create_time = int(time.time())
    request_data.status = 1
    request_data.type = "1"
    request_data.is_delete = 0
    project_obj = project_db.create_one(db=db, obj_in=request_data)
    project_service.create_project(db=db, project_id=project_obj.id,team_id=request_data.team_id)
    return response_200(data=project_obj)


@project_router.post("/delete", dependencies=[Depends(check_permission(["sys:project:delete"]))], summary="项目删除==sys:project:delete")
async def project_delete(request_data: DataDelete, db=Depends(get_db)):
    if request_data.ids:
        for i in request_data.ids:
            project_service.delete_project(db=db, project_id=i, team_id=request_data.team_id)
    else:
        project_service.delete_project(db=db, project_id=request_data.id, team_id=request_data.team_id)
    return response_200(data={})


@project_router.post("/update", dependencies=[Depends(check_permission(["sys:project:update"]))], summary="项目更新==sys:project:update")
async def project_add(request_data: UpdateModel, db=Depends(get_db)):
    project_obj = project_db.get(db=db, id=request_data.id)
    if not request_data.database_id is None:
        add_data = [{'database_id': i, 'project_id': request_data.id} for i in request_data.database_id]
        project_database_db.remove_batch(db=db, filters={"project_id": request_data.id})
        project_database_db.create_batch(db=db, add_data=add_data)
    if request_data.sample_id:
        if sample_db.get_data(db=db, filters={'project_id': request_data.id}):
            sample_db.update_batch(db=db, filters={"project_id": request_data.id}, update={'project_id': None})
        for sample_id in request_data.sample_id:
            sample_db.update_batch(db=db, filters={"id": sample_id}, update={'project_id': request_data.id})
    project_obj = project_db.update_one(db=db, db_obj=project_obj, obj_in=request_data)
    return response_200(data=project_obj)

@project_router.post("/meta-json", dependencies=[Depends(check_permission(["sys:project:list"]))], summary="获取项目元数据JSON==sys:project:meta-json")
async def get_project_meta_json(request_data: ProjectMetaJsonRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    获取项目表中的meta_json字段数据
    """
    # 构建过滤条件
    filters = {}
    filters_exp = []
    
    # 如果指定了具体的项目ID（且不为0）
    if request_data.project_id and request_data.project_id > 0:
        filters_exp.append({'name': 'id', 'exp': 'equal', 'value': request_data.project_id})
    
    # 项目名称过滤
    if request_data.name:
        filters_exp.append({'name': 'name', 'exp': 'like', 'value': request_data.name})
    
    # 查询项目数据
    project_obj = project_db.get_list(
        db=db, 
        page=request_data.page, 
        size=request_data.size, 
        filters=filters, 
        filters_exp=filters_exp,
        sort='-create_time'
    )
    
    # 处理返回数据，添加用户信息
    result_data = []
    for project in project_obj['dataList']:
        user = users_db.get_one(db=db, id=project.user_id)
        
        # 处理meta_json字段（Text类型可能为None或空字符串）
        meta_json_value = project.meta_json if project.meta_json else None
        
        project_data = {
            'id': project.id,
            'name': project.name,
            'meta_json': meta_json_value,
        }
        result_data.append(project_data)
    
    return response_2000(data={
        'dataList': result_data,
        'total': project_obj['total'],
        'page': request_data.page,
        'size': request_data.size
    })

@project_router.post("/meta-json/detail", dependencies=[Depends(check_permission(["sys:project:info"]))], summary="获取单个项目元数据JSON详情==sys:project:meta-json:detail")
async def get_project_meta_json_detail(request_data: DataInfo, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    获取单个项目的meta_json详细信息
    """
    # 获取项目信息
    project_obj = project_db.get(db=db, id=request_data.id)
    if not project_obj:
        return response_2000(data=None, message="项目不存在")
    # 获取用户信息
    user = users_db.get_one(db=db, id=project_obj.user_id)
    
    # 处理meta_json字段（Text类型）
    meta_json_value = project_obj.meta_json if project_obj.meta_json else None
    
    # 尝试解析JSON格式（如果是有效的JSON字符串）
    parsed_meta_json = None
    if meta_json_value and meta_json_value.strip():
        try:
            import json
            parsed_meta_json = json.loads(meta_json_value)
        except json.JSONDecodeError:
            # 如果不是有效的JSON，保持原始字符串
            parsed_meta_json = meta_json_value
    
    # 构建返回数据
    result_data = {
        'id': project_obj.id,
        'name': project_obj.name,
        'code': project_obj.code,
        'meta_json': meta_json_value,  # 原始Text数据
        'parsed_meta_json': parsed_meta_json,  # 解析后的数据（如果是JSON格式）
        'create_time': project_obj.create_time,
        'user_id': project_obj.user_id,
        'user_name': user.user_name if user else 'sys',
        'status': project_obj.status,
        'type': project_obj.type,
        'remark': project_obj.remark,
        'has_meta_json': bool(meta_json_value and meta_json_value.strip())
    }
    
    return response_2000(data=result_data)

@project_router.post("/meta-json/filter", dependencies=[Depends(check_permission(["sys:project:list"]))], summary="筛选有meta_json数据的项目==sys:project:meta-json:filter")
async def get_projects_with_meta_json(request_data: ProjectMetaJsonRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    专门获取有meta_json数据的项目列表
    """
    # 构建过滤条件
    filters = {}
    filters_exp = []
    
    # 项目名称过滤
    if request_data.name:
        filters_exp.append({'name': 'name', 'exp': 'like', 'value': request_data.name})
    
    # 查询所有项目数据
    project_obj = project_db.get_list(
        db=db, 
        page=0,  # 获取所有数据进行过滤
        size=0, 
        filters=filters, 
        filters_exp=filters_exp,
        sort='-create_time'
    )
    
    # 手动过滤有meta_json数据的项目
    filtered_projects = []
    for project in project_obj['dataList']:
        if project.meta_json and project.meta_json.strip():  # Text类型非空且非空白字符串
            user = users_db.get_one(db=db, id=project.user_id)
            project_data = {
                'project_id': project.id,
                'name': project.name,
                'meta_json': project.meta_json
            }
            filtered_projects.append(project_data)
    
    # 分页处理
    total = len(filtered_projects)
    start_idx = (request_data.page - 1) * request_data.size
    end_idx = start_idx + request_data.size
    paginated_data = filtered_projects[start_idx:end_idx] if request_data.size > 0 else filtered_projects
    
    return response_2000(data={
        'dataList': paginated_data,
        'total': total,
        'page': request_data.page,
        'size': request_data.size
    })

@project_router.post("/team-to-projects", dependencies=[Depends(check_permission(["sys:project:list"]))], summary="根据团队ID查询项目ID列表")
async def get_project_ids_by_team_id(request_data: TeamIdRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    根据团队ID查询项目ID列表
    请求参数: {"team_id": 1} 或 {"team_id": [1,2,3]}
    响应数据: {"project_ids": [1, 2, 3]}
    """
    try:
        if not request_data.team_id:
            return response_2000(data={'project_ids': []}, message="team_id参数不能为空")
        
        # 处理单个或多个团队ID
        team_ids = request_data.team_id if isinstance(request_data.team_id, list) else [request_data.team_id]
        
        all_project_ids = []
        for team_id in team_ids:
            project_ids = project_service.get_project_by_team(db=db, team_id=team_id)
            if project_ids:
                all_project_ids.extend(project_ids)
        
        # 去重并排序
        unique_project_ids = sorted(list(set(all_project_ids)))
        return response_2000(data={'project_ids': unique_project_ids})
    except Exception as e:
        return response_2000(data={'project_ids': []}, message=f"查询失败: {str(e)}")
