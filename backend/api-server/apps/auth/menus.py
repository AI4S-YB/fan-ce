"""
@File    :   login.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""
import json
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from apps.common.depends import get_db, get_active_user,get_rbd_user
from apps.system.project.crud import project_db
from apps.system.rbac.crud import menu_db
from libs.dataes import get_menu_tree
from libs.responses.response import response_2000
from .schemas import TreeData,TeamUserInfo
from apps.services.rbd import rbd_service,menu_service

menu_router = APIRouter(tags=['auth:认证'])


LEGACY_OMICS_MENU_PATH_PREFIXES = (
    "/database",
    "/database-file",
    "/apps/database",
    "/apps/database-files",
    "/apps/genome",
    "/apps/rnaseq",
    "/apps/variant",
    "/apps/phenotype",
    "/data/genome",
    "/data/variome",
    "/genome",
    "/rnaseq",
    "/variant",
    "/phenotype",
)

LEGACY_OMICS_MENU_COMPONENT_KEYWORDS = (
    "/views/apps/database/",
    "/views/apps/database-files/",
    "/views/apps/databasewithmetadata/",
    "/views/apps/genome/",
    "/views/apps/rnaseq/",
    "/views/apps/variant/",
    "/views/apps/phenotype/",
)


def _is_legacy_omics_menu(menu_obj) -> bool:
    path = str(getattr(menu_obj, "path", "") or "").strip().lower()
    component = str(getattr(menu_obj, "component", "") or "").strip().lower()
    name = str(getattr(menu_obj, "name", "") or "").strip().lower()
    if any(path.startswith(prefix) for prefix in LEGACY_OMICS_MENU_PATH_PREFIXES):
        return True
    if any(keyword in component for keyword in LEGACY_OMICS_MENU_COMPONENT_KEYWORDS):
        return True
    if name in {
        "database",
        "databasefiles",
        "genome",
        "rnaseq",
        "variant",
        "phenotype",
        "databasewithmetadata",
    }:
        return True
    return False


@menu_router.post("/auth/menus/list", summary="路由菜单列表")
async def auth_menus(request_data: TreeData,db=Depends(get_db), _user=Depends(get_active_user)):
    filter_exp = [{'name': 'type', 'exp': 'contain', 'value': [1, 2]}]
    menu_ids = rbd_service.get_user_menu_ids(db=db, user=_user)
    if menu_ids:
        filter_exp.append({'name': 'id', 'exp': 'contain', 'value': menu_ids})
    menu_obj = menu_db.get_list(db=db, page=0, size=0,filters_exp=filter_exp)
    filtered_menu_list = [item for item in menu_obj['dataList'] if not _is_legacy_omics_menu(item)]
    for i in filtered_menu_list:
        is_hide = False if i.is_visible else True
        keep_alive = True if i.is_cache else False
        meta = {'title': i.title, 'icon': i.icon, 'hideInMenu': is_hide, 'keepAlive': keep_alive, 'order': i.sort}
        if i.meta:
            i.meta = json.loads(i.meta) if i.meta else meta
            i.meta = {**meta,**i.meta}
        else:
            i.meta = meta
    data = get_menu_tree(jsonable_encoder(filtered_menu_list))
    return response_2000(data=data)


@menu_router.post("/auth/user/info", summary="用户认证信息")
async def login_get_user(request_data: TeamUserInfo | None = None, db: Session = Depends(get_db), user=Depends(get_rbd_user)) -> Any:
    request_data = request_data or TeamUserInfo()
    user_info = rbd_service.get_user_role_info(db=db,user=user,team_id=request_data.team_id)
    return response_2000(data=user_info)
