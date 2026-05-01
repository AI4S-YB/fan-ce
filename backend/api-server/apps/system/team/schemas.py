#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project: oma
@File   : schemas.py
@IDE    : PyCharm
@Author: llq
@Date   : 2024/11/12 14:43
@version:  1.0
@Desc   : 
"""
from typing import Optional, List,Any

from pydantic import BaseModel, ConfigDict


class PageList(BaseModel):
    page: Optional[int] = 1
    size: Optional[int] = 10


class Search(BaseModel):
    search: Optional[str] = None


class FilterList(BaseModel):
    name: Optional[str] = None


class DataListPage(PageList, Search, FilterList):
    pass


class TeamCreate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    type: Optional[str] = "1"
    sort: Optional[int] = None
    remark: Optional[str] = None
    user_ids: Optional[List[int]] = None
    project_ids: Optional[List[int]] = None
    role_ids: Optional[List[int]] = None
    model_config = ConfigDict(extra="allow")

class TeamUpdate(TeamCreate):
    id: Optional[int] = None
    role_list:Optional[Any] = None


class TeamUserROleUpdate(BaseModel):
    id: Optional[int] = None
    user_role_list:Optional[Any] = None

class CreateModel(BaseModel):
    """创建"""
    name: Optional[str] = None
    code: Optional[str] = None
    type: Optional[str] = "1"
    sort: Optional[int] = None
    remark: Optional[str] = None
    is_public: Optional[int] = 0
    model_config = ConfigDict(extra="allow")


class UpdateModel(CreateModel):
    """更新"""
    id: Optional[int]
    is_delete: Optional[int] = None
    database_id: Optional[list] = None
    sample_id: Optional[list] = None


class DataInfo(BaseModel):
    id: Optional[int]


class DataDelete(BaseModel):
    id: Optional[int] = None
    ids: Optional[list] = []
