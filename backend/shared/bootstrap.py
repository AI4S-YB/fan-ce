import time

from modules.common.security import get_password_hash
from modules.system.rbac.models import Menu, RoleMenuLink, UserRoleLink
from modules.system.user.models import Role, User
from config.settings import settings
from shared.string_utils import random_str


def _get_bootstrap_options():
    return settings.app_options.get("bootstrap_options") or {}


def _ensure_role(db, *, name: str, code: str):
    role = db.query(Role).filter(Role.code == code).first()
    if role:
        return role

    now = int(time.time())
    role = Role(
        name=name,
        code=code,
        sort=1,
        type=1,
        is_active=True,
        is_deleted=False,
        status=1,
        create_time=now,
        remark="development bootstrap role",
    )
    db.add(role)
    db.flush()
    return role


def _ensure_user(
    db,
    *,
    username: str,
    password: str,
    email: str,
    nickname: str,
):
    user = db.query(User).filter(User.user_name == username).first()
    if user:
        changed = False
        if not user.is_superman:
            user.is_superman = True
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if user.user_status != 1:
            user.user_status = 1
            changed = True
        if changed:
            db.add(user)
            db.flush()
        return user

    now = int(time.time())
    salt = random_str(12)
    user = User(
        user_name=username,
        nickname=nickname,
        user_email=email,
        user_password=get_password_hash(password + salt),
        user_salt=salt,
        user_type=1,
        user_status=1,
        user_avatar="default.jpg",
        is_active=True,
        is_superman=True,
        is_deleted=False,
        create_time=now,
        update_time=now,
        remark="development bootstrap admin",
    )
    db.add(user)
    db.flush()
    return user


def _ensure_user_role_link(db, *, user_id: int, role_id: int):
    link = (
        db.query(UserRoleLink)
        .filter(UserRoleLink.user_id == user_id, UserRoleLink.role_id == role_id)
        .first()
    )
    if link:
        return link

    link = UserRoleLink(user_id=user_id, role_id=role_id)
    db.add(link)
    db.flush()
    return link


def _ensure_menu(
    db,
    *,
    name: str,
    title: str,
    path: str,
    component: str,
    pid: int = 0,
    icon: str = "",
    redirect: str = "",
    sort: int = 0,
    menu_type: int = 1,
):
    menu = db.query(Menu).filter(Menu.pid == pid, Menu.path == path).first()
    if menu:
        changed = False
        desired = {
            "name": name,
            "title": title,
            "component": component,
            "icon": icon,
            "redirect": redirect,
            "sort": sort,
            "type": menu_type,
            "status": 1,
            "is_visible": True,
            "is_frame": False,
            "is_cache": False,
            "is_hidden": False,
            "is_deleted": False,
        }
        for field, value in desired.items():
            if getattr(menu, field) != value:
                setattr(menu, field, value)
                changed = True
        if changed:
            db.add(menu)
            db.flush()
        return menu

    menu = Menu(
        name=name,
        icon=icon,
        component=component,
        title=title,
        path=path,
        redirect=redirect,
        sort=sort,
        type=menu_type,
        api_url="",
        web_url="",
        status=1,
        pid=pid,
        is_visible=True,
        is_frame=False,
        is_cache=False,
        is_hidden=False,
        is_deleted=False,
        meta=None,
        create_time=int(time.time()),
        remark="development bootstrap menu",
    )
    db.add(menu)
    db.flush()
    return menu


def _ensure_role_menu_link(db, *, role_id: int, menu_id: int):
    link = (
        db.query(RoleMenuLink)
        .filter(RoleMenuLink.role_id == role_id, RoleMenuLink.menu_id == menu_id)
        .first()
    )
    if link:
        return link

    link = RoleMenuLink(role_id=role_id, menu_id=menu_id)
    db.add(link)
    db.flush()
    return link


def _delete_menu_if_exists(db, *, pid: int, path: str):
    menu = db.query(Menu).filter(Menu.pid == pid, Menu.path == path).first()
    if not menu:
        return
    db.query(RoleMenuLink).filter(RoleMenuLink.menu_id == menu.id).delete()
    db.delete(menu)
    db.flush()


def init_dev_seed_data(db):
    bootstrap_options = _get_bootstrap_options()
    if not bootstrap_options.get("enabled", False):
        return

    role = _ensure_role(
        db,
        name=bootstrap_options.get("admin_role_name", "超级管理员"),
        code=bootstrap_options.get("admin_role_code", "superman"),
    )
    user = _ensure_user(
        db,
        username=bootstrap_options.get("admin_username", "admin"),
        password=bootstrap_options.get("admin_password", "Admin123456"),
        email=bootstrap_options.get("admin_email", "admin@local.dev"),
        nickname=bootstrap_options.get("admin_nickname", "系统管理员"),
    )
    _ensure_user_role_link(db, user_id=user.id, role_id=role.id)

    dashboard = _ensure_menu(
        db,
        name="Dashboard",
        title="探索",
        path="/",
        component="BasicLayout",
        icon="lucide:compass",
        redirect="/workspace",
        sort=-1,
        menu_type=1,
    )
    _delete_menu_if_exists(db, pid=dashboard.id, path="/analytics")
    workspace = _ensure_menu(
        db,
        name="Workspace",
        title="工作台",
        path="/workspace",
        component="/dashboard/workspace/index",
        pid=dashboard.id,
        icon="carbon:workspace",
        sort=1,
        menu_type=2,
    )

    apps_root = _ensure_menu(
        db,
        name="Apps",
        title="数据管理",
        path="/apps",
        component="BasicLayout",
        icon="lucide:database",
        redirect="/apps/dataset-registry",
        sort=10,
        menu_type=1,
    )
    dataset_registry_menu = _ensure_menu(
        db,
        name="DatasetTypeRegistry",
        title="类型注册",
        path="/apps/dataset-registry",
        component="/apps/dataset-registry/index",
        pid=apps_root.id,
        icon="lucide:table-properties",
        sort=1,
        menu_type=2,
    )
    dataset_scan_menu = _ensure_menu(
        db,
        name="DatasetStagingScan",
        title="数据扫描",
        path="/apps/dataset-staging",
        component="/apps/dataset-staging/index",
        pid=apps_root.id,
        icon="lucide:folder-search-2",
        sort=2,
        menu_type=2,
    )
    dataset_candidate_menu = _ensure_menu(
        db,
        name="DatasetRegistrationCandidate",
        title="注册候选",
        path="/apps/dataset-candidate",
        component="/apps/dataset-candidate/index",
        pid=apps_root.id,
        icon="lucide:clipboard-check",
        sort=3,
        menu_type=2,
    )
    dataset_menu = _ensure_menu(
        db,
        name="DatasetManagement",
        title="Dataset 中心",
        path="/apps/dataset",
        component="/apps/dataset/index",
        pid=apps_root.id,
        icon="lucide:database-backup",
        sort=4,
        menu_type=2,
    )
    database_menu = _ensure_menu(
        db,
        name="DatabaseManagement",
        title="组学数据",
        path="/apps/database",
        component="/apps/database/index",
        pid=apps_root.id,
        icon="lucide:database-zap",
        sort=5,
        menu_type=2,
    )
    breeding_root = _ensure_menu(
        db,
        name="Breeding",
        title="项目管理",
        path="/breeding",
        component="BasicLayout",
        icon="lucide:folder-kanban",
        redirect="/breeding/program",
        sort=20,
        menu_type=1,
    )
    germplasm_root = _ensure_menu(
        db,
        name="Germplasm",
        title="种质资源",
        path="/germplasm",
        component="BasicLayout",
        icon="lucide:leaf",
        redirect="/germplasm/list",
        sort=15,
        menu_type=1,
    )
    germplasm_list_menu = _ensure_menu(
        db,
        name="GermplasmList",
        title="种质列表",
        path="/germplasm/list",
        component="/apps/germplasm/index",
        pid=germplasm_root.id,
        icon="lucide:sprout",
        sort=1,
        menu_type=2,
    )
    germplasm_import_menu = _ensure_menu(
        db,
        name="GermplasmImport",
        title="导入种质资源",
        path="/germplasm/import",
        component="/apps/germplasm/import",
        pid=germplasm_root.id,
        icon="lucide:file-up",
        sort=2,
        menu_type=2,
    )
    germplasm_import_batch_menu = _ensure_menu(
        db,
        name="GermplasmImportBatch",
        title="导入记录",
        path="/germplasm/import-batches",
        component="/apps/germplasm/import-batches",
        pid=germplasm_root.id,
        icon="lucide:history",
        sort=3,
        menu_type=2,
    )
    breeding_program_menu = _ensure_menu(
        db,
        name="BreedingProgramManagement",
        title="项目列表",
        path="/breeding/program",
        component="/breeding/program/index",
        pid=breeding_root.id,
        icon="lucide:list-tree",
        sort=1,
        menu_type=2,
    )

    analysis_root = _ensure_menu(
        db,
        name="AnalysisParent",
        title="数据分析",
        path="/analysis",
        component="BasicLayout",
        icon="lucide:flask-conical",
        redirect="/analysis/tools",
        sort=500,
        menu_type=1,
    )
    analysis_tools_menu = _ensure_menu(
        db,
        name="AnalysisTools",
        title="工具插件",
        path="/analysis/tools",
        component="/apps/analysis/index",
        pid=analysis_root.id,
        icon="lucide:package",
        sort=1,
        menu_type=2,
    )
    analysis_jobs_menu = _ensure_menu(
        db,
        name="AnalysisJobs",
        title="任务管理",
        path="/analysis/jobs",
        component="/apps/analysis/jobs",
        pid=analysis_root.id,
        icon="lucide:list-checks",
        sort=2,
        menu_type=2,
    )

    platform = _ensure_menu(
        db,
        name="Platform",
        title="平台管理",
        path="/platform",
        component="BasicLayout",
        icon="lucide:settings",
        redirect="/platform/setting",
        sort=1000,
        menu_type=1,
    )
    platform_setting = _ensure_menu(
        db,
        name="PlatformSettingManagement",
        title="平台设置",
        path="/platform/setting",
        component="/platform/setting",
        pid=platform.id,
        icon="lucide:sliders-horizontal",
        sort=1,
        menu_type=2,
    )
    news = _ensure_menu(
        db,
        name="NewsManagement",
        title="消息管理",
        path="/platform/news",
        component="/platform/news/index",
        pid=platform.id,
        icon="lucide:message-square",
        sort=3,
        menu_type=2,
    )
    api_docs = _ensure_menu(
        db,
        name="PlatformApiManagement",
        title="API管理",
        path="/platform/api",
        component="/platform/api/index",
        pid=platform.id,
        icon="lucide:blocks",
        sort=2,
        menu_type=2,
    )

    system = _ensure_menu(
        db,
        name="System",
        title="系统管理",
        path="/system",
        component="BasicLayout",
        icon="lucide:shield-check",
        redirect="/system/user",
        sort=2000,
        menu_type=1,
    )
    system_children = [
        _ensure_menu(
            db,
            name="SystemUser",
            title="用户管理",
            path="/system/user",
            component="/system/user/index",
            pid=system.id,
            icon="lucide:users",
            sort=1,
            menu_type=2,
        ),
        _ensure_menu(
            db,
            name="SystemRole",
            title="角色管理",
            path="/system/role",
            component="/system/role/index",
            pid=system.id,
            icon="lucide:user-cog",
            sort=2,
            menu_type=2,
        ),
        _ensure_menu(
            db,
            name="SystemMenu",
            title="菜单管理",
            path="/system/menu",
            component="/system/menus/index",
            pid=system.id,
            icon="lucide:menu-square",
            sort=5,
            menu_type=2,
        ),
        _ensure_menu(
            db,
            name="SystemPermission",
            title="权限管理",
            path="/system/permission",
            component="/system/permission/index",
            pid=system.id,
            icon="lucide:key-round",
            sort=6,
            menu_type=2,
        ),
        _ensure_menu(
            db,
            name="SystemDict",
            title="字典管理",
            path="/system/dict",
            component="/system/dict/index",
            pid=system.id,
            icon="lucide:book-marked",
            sort=7,
            menu_type=2,
        ),
    ]

    # Clean up stale menus from removed features
    _delete_menu_if_exists(db, pid=system.id, path="/system/team")
    _delete_menu_if_exists(db, pid=system.id, path="/system/project")
    _delete_menu_if_exists(db, pid=analysis_root.id, path="/analysis/blast-db")

    for menu in [
        dashboard,
        workspace,
        apps_root,
        dataset_registry_menu,
        dataset_scan_menu,
        dataset_candidate_menu,
        dataset_menu,
        database_menu,
        germplasm_root,
        germplasm_list_menu,
        germplasm_import_menu,
        germplasm_import_batch_menu,
        breeding_root,
        breeding_program_menu,
        analysis_root,
        analysis_tools_menu,
        analysis_jobs_menu,
        platform,
        platform_setting,
        news,
        api_docs,
        system,
        *system_children,
    ]:
        _ensure_role_menu_link(db, role_id=role.id, menu_id=menu.id)

    db.commit()
