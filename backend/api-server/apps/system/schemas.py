# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/10/8 17:35
@Function:
@version :  1.0
@Desc    :  None
"""
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class PageList(BaseModel):
    page: Optional[int] = 1
    size: Optional[int] = 10
    name:Optional[str] = None


class DataInfo(BaseModel):
    id: Optional[int] = None
    ids: Optional[List[int]] = None


class DataDelete(BaseModel):
    id: Optional[int] = None
    ids: Optional[list] = []

class PageFilterList(PageList):
    name: Optional[str] = None
    method: Optional[str] = None
    type: Optional[str] = None


class SystemDictCreate(BaseModel):
    name: Optional[str] = None
    key: Optional[str] = None
    status: Optional[str] = None
    remark: Optional[str] = None
    model_config = ConfigDict(extra="allow")

