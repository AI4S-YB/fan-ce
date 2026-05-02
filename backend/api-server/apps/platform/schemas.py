#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project: oma
@File   : schemas.py
@IDE    : PyCharm
@Author  : Clark
@Time    : 2025-07-31
@version:  1.0
@Desc   : 
"""
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


class News(BaseModel):
    id: int


class PageList(News):
    page: Optional[int] = 1
    size: Optional[int] = 10
    type: Optional[str] = None
    is_public: Optional[bool] = None

class CreateModel(BaseModel):
    """创建"""
    is_public: Optional[bool] = 0
    is_delete: bool = 0
    model_config = ConfigDict(extra="allow")

class UpdateModel(CreateModel):
    """更新"""
    id: int
    model_config = ConfigDict(extra="allow")

class DataDelete(BaseModel):
    """删除"""
    id: Optional[int] = None
    ids: Optional[List[int]] = None
    is_delete: Optional[int] = 1


class PlatformSiteSettingInfoRequest(BaseModel):
    id: Optional[int] = None


class PlatformSiteSettingUpdateRequest(BaseModel):
    site_name: Optional[str] = ""
    site_title: Optional[str] = ""
    filing_no: Optional[str] = ""
    domain: Optional[str] = ""
    ip_address: Optional[str] = ""
    port: Optional[int] = 0
    extra_json: Optional[str] = "{}"


class PlatformModelApiListRequest(BaseModel):
    active_only: Optional[bool] = False


class PlatformModelApiCreateRequest(BaseModel):
    provider_code: str
    provider_name: str
    model_name: str
    api_base_url: str
    api_key: str
    is_primary: Optional[bool] = False
    is_active: Optional[bool] = True
    sort_order: Optional[int] = 0
    remark: Optional[str] = ""
    extra_json: Optional[str] = "{}"


class PlatformModelApiUpdateRequest(PlatformModelApiCreateRequest):
    id: int


class PlatformModelApiDeleteRequest(BaseModel):
    id: int


class PlatformModelApiSetPrimaryRequest(BaseModel):
    id: int


class PlatformSetupTaxonomyPackageRegisterBuiltinRequest(BaseModel):
    package_code: str
    package_name: str
    package_type: str
    storage_path: str
    source: Optional[str] = "builtin"
    source_version: Optional[str] = ""
    sha256: Optional[str] = ""
    manifest_json: Optional[str] = "{}"
    file_size: Optional[int] = None
    status: Optional[str] = "ready"


class PlatformSetupTaxonomyImportStartRequest(BaseModel):
    package_id: int
    force_reinstall: Optional[bool] = False


class ChatMessage(BaseModel):
    role: str
    content: str


class PlatformChatCompletionRequest(BaseModel):
    messages: list[ChatMessage]


class PlatformChatTestRequest(BaseModel):
    model_name: str
    api_base_url: str
    api_key: str


# FRP Tunnel schemas

class FrpConfigUpdateRequest(BaseModel):
    """Update frp config in site setting. All fields optional."""
    frp_server_addr: Optional[str] = Field(None, description="云服务器IP地址")
    frp_server_port: Optional[int] = Field(7000, description="frps绑定端口")
    frp_token: Optional[str] = Field(None, description="认证密钥")
    frp_public_port: Optional[int] = Field(80, description="对外HTTP端口")
    frp_config_json: Optional[str] = Field(None, description="高级自定义frpc配置")


class FrpStartResponse(BaseModel):
    frp_status: str
    public_url: str
    api_url: str
    pid: int


class FrpStopResponse(BaseModel):
    frp_status: str


class FrpStatusResponse(BaseModel):
    frp_status: str
    pid: Optional[int] = None
    public_url: Optional[str] = None
    api_url: Optional[str] = None
    last_error: Optional[str] = None
    uptime_seconds: Optional[int] = None
