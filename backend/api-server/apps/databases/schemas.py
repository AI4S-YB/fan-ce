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
from typing import Optional, List, Any, Union

from pydantic import BaseModel, ConfigDict


class TeamProject(BaseModel):
    project_id: Optional[int] = 0
    team_id: Optional[int] = 0


class PageList(TeamProject):
    page: Optional[int] = 1
    size: Optional[int] = 10
    type: Optional[str] = None
    name: Optional[str] = None
    status: Optional[int] = None
    database_id: Optional[int] = None
    is_public: Optional[bool] = None


class DatabaseFormatModel(BaseModel):
    id: Optional[int] = None


class Search(BaseModel):
    search: Optional[str] = None


class FilterList(BaseModel):
    name: Optional[str] = None


class DataListPage(PageList, Search, FilterList):
    pass


class FileScan(TeamProject):
    path: Optional[str] = None
    name: Optional[str] = None
    file_type: Optional[str] = None
    size: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class CreateModel(BaseModel):
    """创建"""
    type: Optional[str] = None
    name: Optional[str] = None
    remark: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class CreateBatchModel(BaseModel):
    file_list: Optional[List[FileScan]] = None
    data_type: Optional[str] = None
    is_public: Optional[bool] = None
    type: Optional[str] = None

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


class DataActive(BaseModel):
    id: Optional[int] = None
    operation: Optional[str] = None
    file_path: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class DatabasesMetaCreate(BaseModel):
    key: Optional[str] = None
    value: Optional[Any] = None
    code: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class DatabasesMetaBatchCreate(BaseModel):
    items: List[DatabasesMetaCreate]

    model_config = ConfigDict(extra="allow")
"""
#10【数据资产】-【数据管理】-构建关联并保存增强元数据：服务端 
Clark 2025-07-24
"""
# 项目描述模型
class ProjectDescrData(BaseModel):
    Title: Optional[str] = None
    Description: Optional[str] = None

class PublicationData(BaseModel):
    pass

# 项目模型
class ProjectData(BaseModel):
    ProjectDescr: Optional[ProjectDescrData] = None
    Publication: Optional[List[PublicationData]] = None

class ExperimentData(BaseModel):
    title: str
    sample_name: Optional[str] = None
    library_ID: Optional[str] = None
    library_strategy: Optional[str] = None
    library_source: Optional[str] = None
    library_selection: Optional[str] = None
    library_layout: Optional[str] = None
    platform: Optional[str] = None
    instrument_model: Optional[str] = None
    design_description: Optional[str] = None
    filetype: Optional[str] = None
    filename: Optional[str] = None
    filename2: Optional[str] = None
    filename3: Optional[str] = None
    filename4: Optional[str] = None
    assembly: Optional[str] = None
    fasta_file: Optional[str] = None
    model_config = ConfigDict(extra="allow")

class SampleData(BaseModel):
    sample_name: str
    sample_title: Optional[str] = None
    organism: Optional[str] = None
    isolate: Optional[str] = None
    cultivar: Optional[str] = None
    ecotype: Optional[str] = None
    age: Optional[str] = None
    dev_stage: Optional[str] = None
    geo_loc_name: Optional[str] = None
    tissue: Optional[str] = None
    biomaterial_provider: Optional[str] = None
    cell_line: Optional[str] = None
    cell_type: Optional[str] = None
    collected_by: Optional[str] = None
    collection_date: Optional[str] = None
    culture_collection: Optional[str] = None
    disease: Optional[str] = None
    disease_stage: Optional[str] = None
    genotype: Optional[str] = None
    growth_protocol: Optional[str] = None
    height_or_length: Optional[str] = None
    isolation_source: Optional[str] = None
    lat_lon: Optional[str] = None
    phenotype: Optional[str] = None
    population: Optional[str] = None
    sample_type: Optional[str] = None
    sex: Optional[str] = None
    specimen_voucher: Optional[str] = None
    temp: Optional[str] = None
    treatment: Optional[str] = None
    description: Optional[str] = None
    experiments: Optional[List[ExperimentData]] = None  # 嵌套实验列表
    model_config = ConfigDict(extra="allow")

# meta_json结构模型
class MetaJsonData(BaseModel):
    project: ProjectData
    samples: List[SampleData]

class BuildMetaModel(BaseModel):
    """
    构建关联并保存增强元数据：入参
    """
    project_id: int
    file_ids: List[int]
    meta_json: MetaJsonData
    is_public: Optional[int] = 0
    is_delete: Optional[int] = 0


class ProjectIdRequest(BaseModel):
    """根据项目ID查询database_id的请求模型"""
    project_id: Union[int, List[int]]  # 支持单个或多个项目ID
    
    model_config = ConfigDict(extra="forbid")

class DatabaseIdsResponse(BaseModel):
    """数据库ID列表响应模型"""
    database_ids: List[int]
    
    model_config = ConfigDict(extra="allow")

class DatabaseIdRequest(BaseModel):
    """根据数据库ID查询文件路径的请求模型"""
    database_id: Union[int, List[int]]  # 支持单个或多个数据库ID
    
    model_config = ConfigDict(extra="forbid")

class FilePathsResponse(BaseModel):
    """文件路径列表响应模型"""
    file_paths: List[str]

    model_config = ConfigDict(extra="allow")


class LinkProjectRequest(BaseModel):
    """关联项目请求模型"""
    database_id: int
    project_ids: List[int]

    model_config = ConfigDict(extra="allow")


class GetLinkedProjectsRequest(BaseModel):
    """查询数据库关联项目请求模型"""
    database_id: int

    model_config = ConfigDict(extra="allow")


class LinkedProjectsResponse(BaseModel):
    """获取数据库关联项目的响应"""
    project_ids: List[int]
    projects: List[dict]  # 包含项目详细信息

    model_config = ConfigDict(extra="allow")


# ==================== DatabasesFile 相关 Schemas ====================

class DatabasesFilePageList(TeamProject):
    """数据库文件分页列表查询参数"""
    page: Optional[int] = 1
    size: Optional[int] = 10
    database_id: Optional[int] = None
    type: Optional[str] = None
    data_type: Optional[str] = None
    status: Optional[int] = None
    name: Optional[str] = None


class DatabasesFileCreate(BaseModel):
    """创建数据库文件"""
    uid: Optional[str] = None
    size: Optional[int] = None
    name: Optional[str] = None
    file_name: Optional[str] = None
    url: Optional[str] = None
    path: Optional[str] = None
    type: Optional[str] = None
    data_type: Optional[str] = None
    database_id: Optional[int] = None
    status: Optional[int] = 0
    meta_json: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class DatabasesFileUpdate(DatabasesFileCreate):
    """更新数据库文件"""
    id: int


class DatabasesFileResponse(BaseModel):
    """数据库文件响应模型"""
    id: Optional[int] = None
    uid: Optional[str] = None
    size: Optional[int] = None
    name: Optional[str] = None
    file_name: Optional[str] = None
    url: Optional[str] = None
    path: Optional[str] = None
    type: Optional[str] = None
    data_type: Optional[str] = None
    database_id: Optional[int] = None
    status: Optional[int] = None
    create_time: Optional[int] = None
    meta_json: Optional[str] = None
    databases: Optional[dict] = None  # 关联的数据库信息

    model_config = ConfigDict(extra="allow")


class DatabasesFileDelete(BaseModel):
    """删除数据库文件"""
    id: Optional[int] = None
    ids: Optional[List[int]] = []


class DatabasesFileBatchCreate(BaseModel):
    """批量创建数据库文件"""
    files: List[DatabasesFileCreate]
    database_id: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class DatabasesFileInfo(BaseModel):
    """数据库文件详情查询"""
    id: int


class DatabasesFileOptions(BaseModel):
    """数据库文件选项查询"""
    database_id: Optional[int] = None
    type: Optional[str] = None
    data_type: Optional[str] = None


class DatabasesFileOptionsResponse(BaseModel):
    """数据库文件选项响应"""
    id: int
    name: str
    path: Optional[str] = None
    size: Optional[int] = None

    model_config = ConfigDict(extra="allow")
