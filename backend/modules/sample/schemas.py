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
    project_id: Optional[int] = 0
    team_id: Optional[int] = 0
    model_config = ConfigDict(extra="allow")


class PageList(TeamProject):
    page: Optional[int] = 1
    size: Optional[int] = 10
    database_id: Optional[int] = None
    sample_id: Optional[int] = None


class Search(BaseModel):
    search: Optional[str] = None


class FilterList(BaseModel):
    name: Optional[str] = None


class DataListPage(PageList, Search, FilterList):
    pass


class CreateModel(BaseModel):
    """创建"""
    type: Optional[str] = None
    name: Optional[str] = None
    remark: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class UpdateModel(CreateModel):
    """更新"""
    id: Optional[int]
    is_delete: Optional[int] = None
    is_active: Optional[int] = None


class DataInfo(BaseModel):
    id: Optional[int]


class DataDelete(BaseModel):
    id: Optional[int] = None
    ids: Optional[list] = []


# app

class SampleCreateModel(BaseModel):
    sample_name: Optional[str] = None
    sample_code: Optional[str] = None
    type: Optional[str] = None
    remark: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class SampleUpdateModel(SampleCreateModel):
    id: Optional[int] = None


class SampleMetaJsonRequest(BaseModel):
    """样本meta_json请求模型"""
    page: Optional[int] = 1
    size: Optional[int] = 10
    project_id: Optional[int] = None  # 所属项目过滤
    sample_id: Optional[int] = None   # 样本ID过滤
    sample_name: Optional[str] = None # 样本名称过滤
    status: Optional[int] = None      # 状态过滤
    model_config = ConfigDict(extra="allow")

class SampleMetaJsonResponse(BaseModel):
    """样本meta_json响应模型"""
    id: int
    sample_name: Optional[str] = None
    sample_code: Optional[str] = None
    project_id: Optional[int] = None
    meta_json: Optional[str] = None
    has_meta_json: bool = False
    create_time: Optional[int] = None
    model_config = ConfigDict(extra="allow")


class ProjectIdRequest(BaseModel):
    """根据项目ID查询样本ID的请求模型"""
    project_id: Union[int, List[int]]  # 支持单个或多个项目ID
    model_config = ConfigDict(extra="forbid")

class SampleIdsResponse(BaseModel):
    """样本ID列表响应模型"""
    sample_ids: List[int]
    model_config = ConfigDict(extra="allow")
