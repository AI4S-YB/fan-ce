"""
@File    :   user.schemas.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TeamProject(BaseModel):
    project_id: Optional[int] = None
    team_id: Optional[int] = None


class PageList(BaseModel):
    page: Optional[int] = 1
    size: Optional[int] = 10


class TreeData(TeamProject):
    name: Optional[str] = None
    model_config = ConfigDict(extra="allow")

class TeamUserInfo(BaseModel):
    team_id: Optional[int] = None
    model_config = ConfigDict(extra="allow")
class DataId(BaseModel):
    id: Optional[int] = None


class UserLogin(BaseModel):
    user_name: Optional[str]
    user_password: Optional[str]


class UserRest(BaseModel):
    id: int
    user_password: Optional[str]
    old_password: Optional[str]
    new_password: Optional[str]
    confirm_password: Optional[str]


class UserOut(BaseModel):
    user_name: Optional[str] = None
    nickname: Optional[str] = None
    user_email: Optional[str] = None
    user_type: Optional[int] = None
    user_status: Optional[int] = None
    user_avatar: Optional[str] = None
    is_active: Optional[int] = None
    is_superman: Optional[int] = None
    create_time: Optional[int] = None
    update_time: Optional[int] = None
    remark: Optional[str] = None
    user_roles: Optional[list] = []
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """user add"""
    user_name: str = Field(..., description="登录名")
    user_password: Optional[str] = Field(..., description="密码")
    nickname: Optional[str] = Field(..., description="昵称")
    user_email: Optional[str] = Field(None, description="邮箱")
    user_phone: Optional[int] = Field(None, description="手机")
    remark: Optional[str] = Field(None, description="角色名")
    user_roles: Optional[list] = []


class UserDelete(BaseModel):
    id: Optional[int] = None
    ids: Optional[list] = []


class UserUpdate(BaseModel):
    """user UserUpdate"""
    id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    nickname: str
    user_phone: Optional[int] = Field(None, description="手机")
    remark: Optional[str] = None
    user_roles: Optional[list] = []


class UserInfo(BaseModel):
    id: int


class UserRegister(BaseModel):
    """user UserRegister"""
    user_name: str
    user_email: str
    user_password: str


class UserList(BaseModel):
    page: int = 1
    size: int = 10


class UserGetToken(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    user_name: Optional[str] = None
    user_password: Optional[str] = None
    user_email: Optional[str] = None


# === 认证密钥相关Schema ===

class AuthKeyLoginRequest(BaseModel):
    """认证密钥登录请求"""
    auth_key: str = Field(..., description="认证密钥")


class UserInfo(BaseModel):
    """用户信息"""
    id: int
    username: str
    team_id: int
    project_id: int


class AuthKeyLoginResponse(BaseModel):
    """认证密钥登录响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(default=3600, description="过期时间(秒)")
    user_info: UserInfo = Field(..., description="用户信息")


class AuthKeyVerifyRequest(BaseModel):
    """认证密钥验证请求"""
    auth_key: str = Field(..., description="认证密钥")


class AuthKeyVerifyResponse(BaseModel):
    """认证密钥验证响应"""
    valid: bool = Field(..., description="是否有效")
    user_id: Optional[int] = Field(None, description="用户ID")
    team_id: Optional[int] = Field(None, description="团队ID")
    status: Optional[str] = Field(None, description="密钥状态")


class AuthKeyInfo(BaseModel):
    """认证密钥信息"""
    auth_key: str = Field(..., description="认证密钥")
    status: str = Field(..., description="密钥状态")
    user_id: int = Field(..., description="用户ID")
    team_id: int = Field(..., description="团队ID")
    has_key: bool = Field(default=True, description="是否有密钥")


class AuthKeyCreateResponse(BaseModel):
    """认证密钥创建响应"""
    auth_key: str = Field(..., description="认证密钥")
    status: str = Field(..., description="密钥状态")
    user_id: int = Field(..., description="用户ID")
    team_id: int = Field(..., description="团队ID")


class AuthKeyUpdateRequest(BaseModel):
    """认证密钥状态更新请求"""
    status: str = Field(..., description="新状态", pattern="^(active|disabled)$")


class AuthKeyUpdateResponse(BaseModel):
    """认证密钥状态更新响应"""
    auth_key: str = Field(..., description="认证密钥")
    status: str = Field(..., description="新状态")
    updated: bool = Field(default=True, description="是否更新成功")


class AuthKeyDeleteResponse(BaseModel):
    """认证密钥删除响应"""
    deleted: bool = Field(default=True, description="是否删除成功")
    user_id: int = Field(..., description="用户ID")


class AuthKeyBatchQueryRequest(BaseModel):
    """批量查询认证密钥请求"""
    page: int = Field(default=1, description="页码", ge=1)
    size: int = Field(default=20, description="每页大小", ge=1, le=100)
    team_id: Optional[int] = Field(None, description="团队ID过滤")
    status: Optional[str] = Field(None, description="状态过滤", pattern="^(active|disabled)$")


class AuthKeyBatchItem(BaseModel):
    """批量查询密钥项"""
    user_id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    auth_key: str = Field(..., description="认证密钥(部分脱敏)")
    status: str = Field(..., description="密钥状态")
    team_id: int = Field(..., description="团队ID")


class AuthKeyBatchQueryResponse(BaseModel):
    """批量查询认证密钥响应"""
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    size: int = Field(..., description="每页大小")
    items: list[AuthKeyBatchItem] = Field(..., description="密钥列表")
