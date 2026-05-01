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
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


class PageList(BaseModel):
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


class GeneSetCreate(BaseModel):
    """创建基因集的Schema"""
    name: str = Field(..., description="基因集名称")
    description: Optional[str] = Field(None, description="基因集描述")
    file_path: str = Field(..., description="基因组文件路径")
    gene_list: List[str] = Field(..., min_items=1, description="基因ID列表")
    team_id: int = Field(..., description="团队ID")
    project_id: int = Field(..., description="项目ID")
    model_config = ConfigDict(extra="allow")


class GeneSetListByGenome(BaseModel):
    """按基因组文件路径查询基因集列表的Schema"""
    file_path: str = Field(..., description="基因组文件路径")
    team_id: int = Field(..., description="团队ID")
    project_id: int = Field(..., description="项目ID")
    page: Optional[int] = Field(1, ge=1, description="页码")
    size: Optional[int] = Field(10, ge=1, le=100, description="每页大小")


class GeneSetDetail(BaseModel):
    """基因集详情查询的Schema"""
    file_path: str = Field(..., description="基因组文件路径")
    geneset_id: int = Field(..., description="基因集ID")
    team_id: int = Field(..., description="团队ID")
    project_id: int = Field(..., description="项目ID")
    page: Optional[int] = Field(1, ge=1, description="页码") 
    size: Optional[int] = Field(10, ge=1, le=100, description="每页大小")


# 保留原有的Schema以保证兼容性
class GeneSetCrate(BaseModel):
    name: Optional[str] = None
    gene_id: Optional[str] = None
    description: Optional[str] = None
    gene_list:Optional[list] = []
    model_config = ConfigDict(extra="allow")


class GeneSetUpdate(GeneSetCrate):
    id: Optional[int] = None


# 基因集选项查询参数
class GeneSetOptionsQuery(BaseModel):
    file_path: Optional[str] = Field(None, description="基因组文件路径，用于过滤特定基因组下的基因集")
    team_id: Optional[int] = Field(None, description="团队ID，用于权限控制")  
    project_id: Optional[int] = Field(None, description="项目ID，用于权限控制")
