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
from pydantic import BaseModel, ConfigDict
from typing import Optional, Union, List


class PageList(BaseModel):
    page: Optional[int] = 1
    size: Optional[int] = 10
    database_id: Optional[int] = None
    experiment_id: Optional[int] = None


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
    model_config = ConfigDict(extra="allow")

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


class ExperimentMetaJsonRequest(BaseModel):
    """实验meta_json请求模型"""
    page: Optional[int] = 1
    size: Optional[int] = 10
    sample_id: Optional[int] = None      # 所属样本过滤
    experiment_id: Optional[int] = None  # 实验ID过滤
    title: Optional[str] = None          # 实验标题过滤
    model_config = ConfigDict(extra="allow")

class ExperimentMetaJsonResponse(BaseModel):
    """实验meta_json响应模型"""
    id: int
    title: Optional[str] = None
    accession: Optional[str] = None
    sample_id: Optional[int] = None
    status: Optional[int] = None
    meta_json: Optional[str] = None
    has_meta_json: bool = False
    create_time: Optional[int] = None
    model_config = ConfigDict(extra="allow")


class SampleIdRequest(BaseModel):
    """根据样本ID查询实验ID的请求模型"""
    sample_id: Union[int, List[int]]  # 支持单个或多个样本ID
    model_config = ConfigDict(extra="forbid")

class ExperimentIdsResponse(BaseModel):
    """实验ID列表响应模型"""
    experiment_ids: List[int]
    model_config = ConfigDict(extra="allow")
