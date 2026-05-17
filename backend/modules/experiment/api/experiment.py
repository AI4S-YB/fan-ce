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

from modules.common.depends import get_active_user,check_permission
from shared.database import get_db
from shared.responses import response_200
from ..crud import experiment_db
from ..schemas import PageList, DataInfo, DataDelete, UpdateModel, CreateModel, ExperimentMetaJsonRequest, SampleIdRequest
from sqlalchemy import and_, or_
import json

experiment_router = APIRouter(tags=['app:experiment:实验'])


@experiment_router.post("/list",dependencies=[Depends(check_permission(["app:experiment:list"]))], summary="实验列表==app:experiment:list")
async def experiment_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = experiment_db.get_list(db=db, page=request_data.page, size=request_data.size)
    return response_200(data=db_obj)


@experiment_router.post("/info",dependencies=[Depends(check_permission(["app:experiment:info"]))], summary="实验列表==app:experiment:list")
async def experiment_list(request_data: DataInfo, db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = experiment_db.get_one(db=db, id=request_data.id)
    return response_200(data=db_obj)


@experiment_router.post("/options",dependencies=[Depends(check_permission(["app:experiment:list"]))], summary="实验下拉列表==app:experiment:options")
async def experiment_list(db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = experiment_db.get_list(db=db, page=0)
    return response_200(data=db_obj)


@experiment_router.post("/add",dependencies=[Depends(check_permission(["app:experiment:add"]))], summary="实验添加==app:experiment:add")
async def experiment_list(request_data: CreateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    request_data.type = '1'
    request_data.create_time = int(time.time())
    request_data.is_deleted = False
    request_data.status = 1
    request_data.user_id = _user.id
    db_obj = experiment_db.create_one(db=db, obj_in=request_data)
    return response_200(data=db_obj)


@experiment_router.post("/update",dependencies=[Depends(check_permission(["app:experiment:update"]))], summary="实验修改==app:experiment:update")
async def experiment_list(request_data: UpdateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    one_obj = experiment_db.get(db=db, id=request_data.id)
    db_obj = experiment_db.update_one(db=db, db_obj=one_obj, obj_in=request_data)
    return response_200(data=db_obj)


@experiment_router.post("/delete",dependencies=[Depends(check_permission(["app:experiment:delete"]))], summary="实验删除==app:experiment:delete")
async def experiment_list(request_data: DataDelete, db=Depends(get_db), _user=Depends(get_active_user)):
    if request_data.ids:
        for i in request_data.ids:
            experiment_db.remove(db=db, id=int(i))
    else:
        experiment_db.remove(db=db, id=request_data.id)
    return response_200(data={})


@experiment_router.post("/meta-json", dependencies=[Depends(check_permission(["app:experiment:list"]))], summary="实验meta_json数据==app:experiment:meta-json")
async def get_experiment_meta_json(request_data: ExperimentMetaJsonRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    """获取实验meta_json数据，支持多种过滤条件"""
    
    # 构建查询条件
    filters = []
    
    # 样本过滤
    if request_data.sample_id:
        filters.append(experiment_db.model.sample_id == request_data.sample_id)
    
    # 实验ID过滤
    if request_data.experiment_id:
        filters.append(experiment_db.model.id == request_data.experiment_id)
    
    # 实验标题过滤（模糊匹配）
    if request_data.title:
        filters.append(experiment_db.model.title.like(f"%{request_data.title}%"))
    
    
    # 添加基础过滤条件（未删除）
    filters.append(experiment_db.model.is_deleted == False)
    
    # 执行查询
    query = db.query(experiment_db.model)
    if filters:
        query = query.filter(and_(*filters))
    
    # 分页
    total = query.count()
    offset = (request_data.page - 1) * request_data.size
    experiments = query.offset(offset).limit(request_data.size).all()
    
    # 处理返回数据
    result_list = []
    for experiment in experiments:
        # 检查meta_json是否有效
        has_meta_json = False
        if experiment.meta_json and experiment.meta_json.strip():
            try:
                # 尝试解析JSON以验证有效性
                json.loads(experiment.meta_json)
                has_meta_json = True
            except (json.JSONDecodeError, TypeError):
                # JSON无效，但仍然标记为有数据（原始Text）
                has_meta_json = True
        
        result_list.append({
            "id": experiment.id,
            "title": experiment.title,
            "meta_json": experiment.meta_json,
        })
    
    return response_200(data={
        "dataList": result_list,
        "total": total,
        "page": request_data.page,
        "size": request_data.size
    })


@experiment_router.post("/sample-to-experiments", dependencies=[Depends(check_permission(["app:experiment:list"]))], summary="根据样本ID查询实验ID列表")
async def get_experiment_ids_by_sample_id(request_data: SampleIdRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    根据样本ID查询实验ID列表
    请求参数: {"sample_id": 1} 或 {"sample_id": [1,2,3]}
    响应数据: {"experiment_ids": [1, 2, 3]}
    """
    try:
        if not request_data.sample_id:
            return response_200(data={'experiment_ids': []}, message="sample_id参数不能为空")
        
        # 处理单个或多个样本ID
        sample_ids = request_data.sample_id if isinstance(request_data.sample_id, list) else [request_data.sample_id]
        
        all_experiment_ids = []
        for sample_id in sample_ids:
            experiments = experiment_db.get_data(db=db, filters={'sample_id': sample_id})
            experiment_ids = [exp.id for exp in experiments]
            all_experiment_ids.extend(experiment_ids)
        
        # 去重并排序
        unique_experiment_ids = sorted(list(set(all_experiment_ids)))
        return response_200(data={'experiment_ids': unique_experiment_ids})
    except Exception as e:
        return response_200(data={'experiment_ids': []}, message=f"查询失败: {str(e)}")
