# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/10/8 17:34
@Function:
@version :  1.0
@Desc    :  None
"""
from typing import TypeVar

from db.base import CRUDBase
from db.database import Base
from .models import Menu, Permission, MenuPermissionLink, RoleMenuLink, UserRoleLink
from .schemas import MenuCreate, PermissionCreate, RoleCreate
from ..user.models import Role

ModelType = TypeVar("ModelType", bound=Base)


class CRUDMenu(CRUDBase[Menu, MenuCreate, MenuCreate]):
    pass


class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionCreate]):
    pass


class CRUDRole(CRUDBase[Role, RoleCreate, RoleCreate]):
    pass


class CRUDMenuPermissionLink(CRUDBase[MenuPermissionLink, RoleCreate, RoleCreate]):
    pass


class CRUDMenuRoleMenuLink(CRUDBase[RoleMenuLink, RoleCreate, RoleCreate]):
    pass


class CRUDMenuUserRoleLink(CRUDBase[UserRoleLink, RoleCreate, RoleCreate]):
    pass


menu_db = CRUDMenu(Menu)
permission_db = CRUDPermission(Permission)
role_db = CRUDRole(Role)
menu_permission_db = CRUDMenuPermissionLink(MenuPermissionLink)
role_menu_db = CRUDMenuRoleMenuLink(RoleMenuLink)
user_role_db = CRUDMenuUserRoleLink(UserRoleLink)
