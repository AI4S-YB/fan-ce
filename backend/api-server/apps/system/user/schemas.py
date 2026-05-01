"""
@File    :   user.schemas.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PageList(BaseModel):
    page: Optional[int] = 1
    size: Optional[int] = 10


class DataId(BaseModel):
    id: Optional[int]


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
    id: int
    user_name: Optional[str] = None
    nickname: Optional[str] = None
    user_email: Optional[str] = None
    user_phone: Optional[int] = None
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
    nickname: Optional[str] = Field(None, description="昵称")
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
    nickname: Optional[str] = None
    user_phone: Optional[int] = Field(None, description="手机")
    remark: Optional[str] = None
    user_roles: Optional[list] = []


class UserActiveUpdate(BaseModel):
    """user UserActiveUpdate"""
    id: int
    is_active: Optional[bool] = None


class UserPwdRest(BaseModel):
    id: int
    new_password: Optional[str]


class UserPwdUpdate(BaseModel):
    id: int
    new_password: Optional[str] = None
    old_password: Optional[str] = None


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
    user_name: Optional[str] = None
    user_email: Optional[str] = None


class UserGetToken(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    user_name: Optional[str] = None
    user_password: Optional[str] = None
    user_email: Optional[str] = None
