"""
@File    :   depends.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""

import json
import os
from typing import List, Optional

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.requests import Request
from typing_extensions import Annotated

from modules.common.schemas import TokenPayload, UserInfo
from shared.security import ALGORITHM
from modules.system.rbac.crud import user_role_db, role_menu_db, menu_permission_db, permission_db
from modules.platform.setup_state import is_taxonomy_ready
from config.settings import settings
from shared.database import get_db
from shared.crypto import read_pem_public_key, verify_license, get_serial_number
from shared.exceptions import ExceptionStatus
from . import User
from . import users_db
from modules.services.rbd import rbd_service

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_STR}/login/access-token")
db = Annotated[Session, Depends(get_db)]


# 得到当前用户
def get_auth_user(db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(status_code=ExceptionStatus.CODE_4003['code'], detail=ExceptionStatus.CODE_4003['msg'])
    user = users_db.get_one(db, id=token_data.user_id)
    if not user:
        raise HTTPException(status_code=ExceptionStatus.CODE_4003['code'], detail=ExceptionStatus.CODE_4003['msg'])
    return user


def get_rbd_user(db: Session = Depends(get_db), current_user: User = Depends(get_auth_user)) -> User:
    """
    基于rbac用户认证
    """
    if not users_db.is_active(current_user):
        raise HTTPException(status_code=4001, detail="用户已禁用！！！")
    # team
    user_info = rbd_service.get_user_role_info(db=db, user=current_user, team_id=None)
    current_user.permissions = user_info.get('permissions', [])
    current_user.roles = user_info.get('roles', [])
    current_user.menu_ids = user_info.get('menu_ids', [])
    return current_user


# 是否管理员
def is_admin(current_user: User = Depends(get_auth_user)) -> User:
    if current_user.user_type == 1:
        return current_user
    else:
        raise HTTPException(status_code=4030, detail="没有权限")


# 得到当前登录用户
def get_active_user(
    current_user: User = Depends(get_rbd_user),
) -> User:
    """Return the active user with actual RBAC permissions."""
    if not users_db.is_active(current_user):
        raise HTTPException(status_code=4010, detail="用户已禁用！！！")
    return current_user


async def require_superadmin(
    current_user: User = Depends(get_rbd_user),
) -> User:
    """Require superadmin role. Checks actual RBAC permissions via get_rbd_user."""
    admin_perm_codes = {"1", "11"}
    user_perms = set(current_user.permissions or [])
    if not (admin_perm_codes & user_perms):
        raise HTTPException(status_code=403, detail="Superadmin permission required")
    return current_user


def ensure_taxonomy_ready(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> User:
    if not is_taxonomy_ready(db):
        raise HTTPException(
            status_code=4230,
            detail="taxonomy 尚未初始化，请先在 /platform/setup/taxonomy 完成安装",
        )
    return current_user


def get_user_filters(current_user: UserInfo = Depends(get_active_user)):
    filters = {}
    if not current_user.is_superman and 'superman' not in current_user.role_keys:
        filters['user_id'] = current_user.id
    return filters


UserActive = Annotated[UserInfo, Depends(get_active_user)]
RbacUserActive = Annotated[UserInfo, Depends(get_rbd_user)]


def get_current_active_superuser(current_user: User = Depends(get_auth_user)) -> User:
    """得到当前超级用户"""
    if not users_db.is_superuser(current_user):
        raise HTTPException(status_code=4001, detail="这个用户没有足够的权限！！！")
    return current_user


def check_cookie(request: Request, db: db):
    """ 校验cookie -- 认证"""
    if request.get("path") in settings.COOKIE_NOT_CHECK:  # 不校验Cookie
        return
    session = request.cookies.get(settings.COOKIE_KEY)
    try:
        _user = ''
        return _user
    except AssertionError as e:
        raise ''


CheckCookie = Annotated[User, Depends(check_cookie)]


def check_permission(permission: Optional[List[str]] = None):
    """ 校验权限code -- 鉴权"""

    def wrapper(request: Request, db: db, current_user: RbacUserActive):
        if current_user.is_superman:
            return current_user
        if not permission:
            raise HTTPException(status_code=ExceptionStatus.CODE_4007['code'], detail=ExceptionStatus.CODE_4007['msg'])
        else:
            if not set(permission).issubset(set(current_user.permissions)):
                raise HTTPException(status_code=ExceptionStatus.CODE_4007['code'], detail=ExceptionStatus.CODE_4007['msg'])
        return current_user

    return wrapper


def filter_user_role(user):
    """基于用户角色筛选"""
    filters = {}
    return filters


def get_verify_license():
    license_dict = {}
    signature_str = ''
    tag = False
    if os.path.isfile(os.path.join(settings.BASE_PATH, 'license', 'license')):
        file = open(os.path.join(settings.BASE_PATH, 'license', 'license'), 'r')
        lines = file.readlines()
        file.close()
        for line in lines:
            line = line.strip()
            key, value = line.split(":")
            if key == 'sign':
                signature_str = value
            else:
                license_dict[key] = value
        public_key = read_pem_public_key(os.path.join(settings.BASE_PATH, 'license', 'public_key.pem'))
        ret = verify_license(json.dumps(license_dict), signature_str, public_key)
        if ret:
            if license_dict['SN'] == get_serial_number():
                tag = True
    return tag

def get_user_info(db, user):
    """获取用户信息"""
