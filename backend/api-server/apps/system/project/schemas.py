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
from typing import Optional, Union, List

from pydantic import BaseModel, ConfigDict


class TeamProject(BaseModel):
    project_id: Optional[int] = None
    team_id: Optional[int] = None


class Search(BaseModel):
    search: Optional[str] = None


class FilterList(BaseModel):
    name: Optional[str] = None


class PageList(TeamProject):
    page: Optional[int] = 1
    size: Optional[int] = 10
    name: Optional[str] = None
    code: Optional[str] = None


class DataListPage(PageList, Search, FilterList):
    pass


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
    model_config = ConfigDict(extra="allow")


class ProjectMetaJsonRequest(TeamProject):
    """项目元数据JSON请求模型"""
    page: Optional[int] = 1
    size: Optional[int] = 10
    project_id: Optional[int] = None  # 可选的具体项目ID
    name: Optional[str] = None  # 可选的项目名称过滤

class ProjectMetaJsonResponse(BaseModel):
    """项目元数据JSON响应模型"""
    id: int
    name: str
    code: str
    meta_json: Optional[str] = None
    create_time: Optional[int] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None


class TeamIdRequest(BaseModel):
    """根据团队ID查询项目ID的请求模型"""
    team_id: Union[int, List[int]]  # 支持单个或多个团队ID
    
    model_config = ConfigDict(extra="forbid")

class ProjectIdsResponse(BaseModel):
    """项目ID列表响应模型"""
    project_ids: List[int]
    
    model_config = ConfigDict(extra="allow")
