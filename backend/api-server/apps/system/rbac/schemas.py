# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/10/8 17:35
@Function:
@version :  1.0
@Desc    :  None
"""
from typing import Optional,List

from pydantic import BaseModel, ConfigDict


class PageList(BaseModel):
    page: Optional[int] = 1
    size: Optional[int] = 10


class DictCreate(BaseModel):
    pass


class MenuCreate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    icon: Optional[str] = None
    component: Optional[str] = None
    redirect: Optional[str] = None
    path: Optional[str] = None
    sort: Optional[int] = 1
    type: Optional[int] = 1
    is_frame: Optional[int] = 1
    is_cache: Optional[int] = 1
    is_hidden: Optional[int] = 0
    api_url: Optional[str] = None
    web_url: Optional[str] = None
    status: Optional[int] = 0
    pid: Optional[int] = 0
    remark: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class MenuDelete(BaseModel):
    id: Optional[int] = None
    ids: Optional[List[int]] = None


class MenuInfo(BaseModel):
    id: Optional[int] = None


class MenuUpdate(MenuCreate):
    permission_list:Optional[list] = None
    id: Optional[int]
    model_config = ConfigDict(extra="allow")

class RoleCreate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    permissions: Optional[list] = []
    model_config = ConfigDict(extra="allow")


class RoleMenuUpdate(BaseModel):
    role_id: Optional[int] = None
    menu_map: Optional[list] = None


class RoleUpdate(RoleCreate):
    id: Optional[int] = None
    model_config = ConfigDict(extra="allow")


class PermissionCreate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    sort: Optional[int] = 1
    pid: Optional[int] = 0
    method: Optional[str] = None
    uri: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class PageFilterList(PageList):
    name: Optional[str] = None


class PermissionUpdate(PermissionCreate):
    id: Optional[int] = None
    model_config = ConfigDict(extra="allow")
