"""
@File    :   user.routers.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""
from fastapi import APIRouter
from .api.base import base_router
from .api.users import user_router
from .api.dict import dict_router
from .api.roles import role_router
from .api.menu import menu_router
from .api.permission import permission_router
from .api.project import project_router
from .api.team import team_router

system_routers = APIRouter()
system_routers.include_router(team_router, tags=['system:team:团队管理'], prefix='/team')
system_routers.include_router(project_router, tags=['system:project:项目管理'], prefix='/project')
system_routers.include_router(user_router, tags=['system:user:用户管理'], prefix='/user')
system_routers.include_router(menu_router, tags=['system:menu:菜单管理'], prefix='/menu')
system_routers.include_router(permission_router, tags=['system:permission:权限管理'], prefix='/permission')
system_routers.include_router(role_router, tags=['system:role:角色管理'], prefix='/role')
system_routers.include_router(dict_router, tags=['system:dict:字典管理'],prefix='/dict')
system_routers.include_router(base_router, tags=['system:base:基础管理'])