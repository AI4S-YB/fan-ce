# -*- coding: utf-8 -*-
"""
@Author  : Clark
@Time    : 2025-07-31
@Function:
@version :  1.0
@Desc    :  None
"""
import time

from fastapi import APIRouter, Depends

from apps.common.depends import get_active_user, check_permission
from db.database import get_db
from libs.responses.response import response_200, response_200
from ..crud import news_db
from ..schemas import PageList, News, CreateModel, UpdateModel, DataDelete
from sqlalchemy import and_, or_

news_router = APIRouter(tags=['app:news:信息管理'])

"""
@desc: 信息管理列表
@param: 
@return: 

"""
@news_router.post("/list", dependencies=[Depends(check_permission(["app:news:list"]))], summary="信息管理列表==app:news:list")
async def list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    filters_exp = []
    if request_data.type:
        filters_exp.append({'name': 'type', 'exp': 'equal', 'value': request_data.type})

    db_obj = news_db.get_list(db=db, page=request_data.page, size=request_data.size, filters_exp=filters_exp)
    return response_200(data=db_obj)

"""
@desc: 信息详情
@param: 
@return: 
"""
@news_router.post("/info", dependencies=[Depends(check_permission(["app:news:info"]))], summary="信息详情==app:news:info")
async def info(request_data: News, db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = news_db.get_one(db=db, id=request_data.id)
    return response_200(data=db_obj)

"""
@desc: 信息添加
@param: 
@return: 
"""
@news_router.post("/add", dependencies=[Depends(check_permission(["app:news:add"]))], summary="信息添加==app:news:add")
async def add(request_data: CreateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    request_data.create_time = int(time.time())
    request_data.user_id = _user.id
    db_obj = news_db.create_one(db=db, obj_in=request_data)
    return response_200(data=db_obj)

"""
@desc: 信息修改
@param: 
@return: 
"""
@news_router.post("/update", dependencies=[Depends(check_permission(["app:news:update"]))], summary="信息修改==app:news:update")
async def update(request_data: UpdateModel, db=Depends(get_db), _user=Depends(get_active_user)):
    one_obj = news_db.get(db=db, id=request_data.id)
    db_obj = news_db.update_one(db=db, db_obj=one_obj, obj_in=request_data)
    return response_200(data=db_obj)

"""
@desc: 信息删除
@param: 
@return: 
"""
@news_router.post("/delete", dependencies=[Depends(check_permission(["app:news:delete"]))], summary="信息删除==app:news:delete")
async def delete(request_data: DataDelete, db=Depends(get_db), _user=Depends(get_active_user)):
    if request_data.ids:
        for i in request_data.ids:
            news_db.remove(db=db, id=int(i))
    else:
        news_db.remove(db=db, id=request_data.id)
    return response_200(data={})


# ── Public endpoint (no auth) ──

public_news_router = APIRouter(tags=['public:news'])


@public_news_router.get("/news", summary="公开信息列表")
def public_news_list(type: str = None, db=Depends(get_db)):
    filters = {"is_public": True}
    if type:
        filters["type"] = type
    rows = news_db.get_data(db=db, filters=filters)
    # Filter out deleted and non-public in Python
    rows = [r for r in rows if r.is_public and not r.is_delete]
    rows = sorted(rows, key=lambda r: r.create_time or 0, reverse=True)
    return response_200(data=[
        {
            "id": r.id,
            "title": r.title,
            "type": r.type,
            "content": r.content,
            "author": r.author,
            "create_time": r.create_time,
        }
        for r in rows
    ])
