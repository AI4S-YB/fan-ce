# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/10/8 17:48
@Function:
@version :  1.0
@Desc    :  None
"""
import time
import uuid

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder

from apps.common.depends import get_active_user, check_permission
from db.database import get_db
from libs.responses.response import response_200, response_2000
from ..schemas import PageList, DataInfo, DataDelete
from ..team.crud import team_db,team_project_db,team_role_db,team_user_db
from apps.system.project.crud import project_db
from ..team.schemas import UpdateModel, TeamCreate,TeamUserROleUpdate
from apps.services.project import team_service
team_router = APIRouter()


@team_router.post("/list", dependencies=[Depends(check_permission(["sys:team:list"]))], summary="团队列表")
async def team_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    filters_exp = []
    if request_data.name:
        filters_exp.append({"name": 'name','exp':'like','value':request_data.name})
    team_ids = team_service.get_team_by_user(db=db,user_id=_user.id,user=_user)
    if team_ids and not _user.is_superman:
        filters_exp.append({"name": 'id','exp':'contain','value': team_ids})
    obj = team_db.get_list(db=db, page=request_data.page, size=request_data.size,filters_exp=filters_exp)
    for i in obj['dataList']:
        tp = {}
        user_role_list = []
        for user in i.users:
            if user.user_id not in tp:
                tp[user.user_id] = [user.role_id]
            else:
                tp[user.user_id].append(user.role_id)
        for n in tp:
            user_role_list.append({'user_id': n, 'role_ids': tp[n]})
        i.user_role_list = user_role_list
    return response_200(data=obj)

"""
#2 【系统管理】-【团队管理】新增团队逻辑优化
Clark 2025-07-23
入参追加_user=Depends(get_active_user)，获取当前用户信息
"""
@team_router.post("/options", dependencies=[Depends(check_permission(["sys:team:list"]))], summary="团队列表")
async def team_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    new_data = []
    obj = team_db.get_list(db=db, page=0, size=request_data.size)
    for i in obj['dataList']:
        new_data.append({'value': i.id, 'label': i.name})
    return response_2000(data=new_data)


@team_router.post("/add", dependencies=[Depends(check_permission(["sys:team:add"]))], summary="团队添加")
async def team_add(request_data: TeamCreate, db=Depends(get_db), _user=Depends(get_active_user)):
    request_data.create_time = int(time.time())
    request_data.is_active = 1
    request_data.is_delete = 0
    request_data.code = uuid.uuid1().hex
    projects = request_data.project_ids or  []
    obj = team_db.create_one(db=db, obj_in=request_data)
    if projects:
        projects_list = [{'team_id': obj.id, 'project_id': project_id} for project_id in projects]
    else:
        """
        #2 【系统管理】-【团队管理】新增团队逻辑优化
        Clark 2025-07-23
        默认项目user_id值为当前用户
        """
        p = project_db.create_one(db=db,obj_in={'name':'Default','code':'Default','type':'1','status':1,'user_id':_user.id,'create_time':int(time.time())})
        projects_list = [{'team_id': obj.id, 'project_id': p.id}]
    team_project_db.create_batch(db=db,add_data=projects_list)

    return response_200(data=obj)


@team_router.post("/delete", dependencies=[Depends(check_permission(["sys:team:delete"]))], summary="团队删除")
async def team_delete(request_data: DataDelete, db=Depends(get_db), _user=Depends(get_active_user)):
    if request_data.ids:
        """
        #18 【系统管理】-【团队管理】-团队无法删除 
        2025-07-31 Clark
        """
        team_db.remove(db=db, ids=request_data.ids)
    if request_data.id:
        team_db.remove(db=db, id=request_data.id)
    return response_200(data={})


@team_router.post("/info", dependencies=[Depends(check_permission(["sys:team:info"]))], summary="团队详情")
async def team_info(request_data: DataInfo, db=Depends(get_db), _user=Depends(get_active_user)):
    obj = team_db.get(db=db, id=request_data.id)
    obj.user_ids = [user.user_id for user in obj.users]
    obj.project_ids = [project.project_id for project in obj.projects]
    obj.role_ids = [role.role_id for role in obj.roles]
    return response_200(data=obj)


@team_router.post("/update", dependencies=[Depends(check_permission(["sys:team:update"]))], summary="团队更新")
async def team_update(request_data: UpdateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = team_db.get(db=db, id=request_data.id)
    obj = team_db.update_one(db=db, db_obj=db_obj, obj_in=request_data)
    return response_200(data=obj)


@team_router.post("/user/role", dependencies=[Depends(check_permission(["sys:team:user:role"]))], summary="团队授权")
async def team_update(request_data: TeamUserROleUpdate, db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = team_db.get(db=db, id=request_data.id)
    team_user_db.remove_batch(db=db,filters={'team_id': db_obj.id})
    if request_data.user_role_list:
        user_role = []
        for i in request_data.user_role_list:
            user_id = i.get('user_id')
            role_ids = i.get('role_ids')
            if user_id:
                for role_id in role_ids:
                    d = {'team_id': db_obj.id, 'user_id': user_id,'role_id': role_id}
                    user_role.append(d)
        team_user_db.create_batch(db=db, add_data=user_role)
    return response_200(data=db_obj)