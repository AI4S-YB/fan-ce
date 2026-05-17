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

from apps.common.depends import get_active_user, check_permission
from db.database import get_db
from libs.responses.response import response_200, response_200
from ..crud import sample_db, sample_meta_db
from ..schemas import PageList, SampleCreateModel, SampleUpdateModel, DataInfo, DataDelete, SampleMetaJsonRequest, ProjectIdRequest
from sqlalchemy import and_, or_
import json

sample_router = APIRouter(tags=['app:sample:样本'])


@sample_router.post("/list", dependencies=[Depends(check_permission(["app:sample:list"]))], summary="样本列表==app:sample:list")
async def databases_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    filters = {}
    if request_data.project_id:
        filters['project_id'] = request_data.project_id
    db_obj = sample_db.get_list(db=db, page=request_data.page, size=request_data.size, filters=filters)
    for i in db_obj['dataList']:
        i.meta_count = sample_meta_db.get_count(db=db, filters={'sample_id': i.id})
    return response_200(data=db_obj)


@sample_router.post("/info", dependencies=[Depends(check_permission(["app:sample:info"]))], summary="样本列表==app:sample:list")
async def databases_list(request_data: DataInfo, db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = sample_db.get_one(db=db, id=request_data.id)
    return response_200(data=db_obj)


@sample_router.post("/options", dependencies=[Depends(check_permission(["app:sample:list"]))], summary="样本下拉列表==app:sample:options")
async def databases_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    new_data = []
    filters = {}
    # if request_data.project_id:
    #     filters['project_id'] = request_data.project_id
    db_obj = sample_db.get_list(db=db, page=0, filters=filters)
    for i in db_obj['dataList']:
        new_data.append({'id': i.id, 'name': i.sample_name})
    return response_200(data=new_data)


@sample_router.post("/add", dependencies=[Depends(check_permission(["app:sample:add"]))], summary="样本添加==app:sample:add")
async def databases_list(request_data: SampleCreateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    request_data.type = '1'
    request_data.create_time = int(time.time())
    request_data.is_deleted = False
    request_data.status = 1
    request_data.user_id = _user.id
    db_obj = sample_db.create_one(db=db, obj_in=request_data)
    return response_200(data=db_obj)


@sample_router.post("/update", dependencies=[Depends(check_permission(["app:sample:update"]))], summary="样本修改==app:sample:update")
async def databases_list(request_data: SampleUpdateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    one_obj = sample_db.get(db=db, id=request_data.id)
    db_obj = sample_db.update_one(db=db, db_obj=one_obj, obj_in=request_data)
    return response_200(data=db_obj)


@sample_router.post("/delete", dependencies=[Depends(check_permission(["app:sample:delete"]))], summary="样本删除==app:sample:delete")
async def databases_list(request_data: DataDelete, db=Depends(get_db), _user=Depends(get_active_user)):
    if request_data.ids:
        for i in request_data.ids:
            sample_db.remove(db=db, id=int(i))
    else:
        sample_db.remove(db=db, id=request_data.id)
    return response_200(data={})


@sample_router.post("/meta-json", dependencies=[Depends(check_permission(["app:sample:list"]))], summary="样本meta_json数据==app:sample:meta-json")
async def get_sample_meta_json(request_data: SampleMetaJsonRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    """获取样本meta_json数据，支持多种过滤条件"""
    
    # 构建查询条件
    filters = []
    
    # 项目过滤
    if request_data.project_id:
        filters.append(sample_db.model.project_id == request_data.project_id)
    
    # 样本ID过滤
    if request_data.sample_id:
        filters.append(sample_db.model.id == request_data.sample_id)
    
    # 样本名称过滤（模糊匹配）
    if request_data.sample_name:
        filters.append(sample_db.model.sample_name.like(f"%{request_data.sample_name}%"))
    
    
    # 添加基础过滤条件（未删除）
    filters.append(sample_db.model.is_delete == False)
    
    # 执行查询
    query = db.query(sample_db.model)
    if filters:
        query = query.filter(and_(*filters))
    
    # 分页
    total = query.count()
    offset = (request_data.page - 1) * request_data.size
    samples = query.offset(offset).limit(request_data.size).all()
    
    # 处理返回数据
    result_list = []
    for sample in samples:
        # 检查meta_json是否有效
        has_meta_json = False
        if sample.meta_json and sample.meta_json.strip():
            try:
                # 尝试解析JSON以验证有效性
                json.loads(sample.meta_json)
                has_meta_json = True
            except (json.JSONDecodeError, TypeError):
                # JSON无效，但仍然标记为有数据（原始Text）
                has_meta_json = True
        
        result_list.append({
            "sample_id": sample.id,
            "sample_name": sample.sample_name,
            "meta_json": sample.meta_json
        })
    
    return response_200(data={
        "dataList": result_list,
        "total": total,
        "page": request_data.page,
        "size": request_data.size
    })


@sample_router.post("/project-to-samples", dependencies=[Depends(check_permission(["app:sample:list"]))], summary="根据项目ID查询样本ID列表")
async def get_sample_ids_by_project_id(request_data: ProjectIdRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    根据项目ID查询样本ID列表
    请求参数: {"project_id": 1} 或 {"project_id": [1,2,3]}
    响应数据: {"sample_ids": [1, 2, 3]}
    """
    try:
        if not request_data.project_id:
            return response_200(data={'sample_ids': []}, message="project_id参数不能为空")
        
        # 处理单个或多个项目ID
        project_ids = request_data.project_id if isinstance(request_data.project_id, list) else [request_data.project_id]
        
        all_sample_ids = []
        for project_id in project_ids:
            samples = sample_db.get_data(db=db, filters={'project_id': project_id})
            sample_ids = [sample.id for sample in samples]
            all_sample_ids.extend(sample_ids)
        
        # 去重并排序
        unique_sample_ids = sorted(list(set(all_sample_ids)))
        return response_200(data={'sample_ids': unique_sample_ids})
    except Exception as e:
        return response_200(data={'sample_ids': []}, message=f"查询失败: {str(e)}")
