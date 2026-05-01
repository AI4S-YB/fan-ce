"""
@File    :   schemas.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""
from typing import Optional,List,Any
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    user_avatar: str
    user_name: str
    team:Any = None
    project:Any = None


class TokenDoc(BaseModel):
    access_token: str


class TokenAdmin(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    user_id: Optional[int] = None


class UserInfo(BaseModel):
    id: Optional[int]
    is_superman: Optional[int] = None
    role_keys: Optional[list] = None
    permissions: Optional[list] = None
    menus: Optional[List[int]] = None
    roles: Optional[List[int]] = None
    teams: Optional[List[int]] = None
