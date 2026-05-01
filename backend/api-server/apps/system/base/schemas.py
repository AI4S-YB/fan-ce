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

from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class PageList(BaseModel):
    page: Optional[int] = 1
    size: Optional[int] = 10
    type_id: Optional[int] = None


class DataInfo(BaseModel):
    id: Optional[int]


class DataDelete(BaseModel):
    id: Optional[int] = None
    ids: Optional[list] = []


class SystemDictCreate(BaseModel):
    name: Optional[str] = None
    key: Optional[str] = None
    status: Optional[str] = None
    remark: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class SystemDictUpdate(SystemDictCreate):
    id: Optional[int]


class SystemDictFieldCreate(BaseModel):
    type_id: Optional[int]
    name: Optional[str] = None
    type: Optional[str] = None
    label: Optional[str] = None
    value: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    sort: Optional[int] = None
    is_default: Optional[int] = None
    status: Optional[str] = None
    create_time: Optional[int] = None
    remark: Optional[str] = None


class SystemDictFieldUpdate(SystemDictFieldCreate):
    id: Optional[int]


class DictOptions(BaseModel):
    type: Optional[str] = None
    key: Optional[str] = None
    extendFirst: Optional[str] = None
