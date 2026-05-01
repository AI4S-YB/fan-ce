from apps.system.rbac.crud import role_menu_db, menu_permission_db, permission_db, user_role_db
from apps.system.team.crud import team_user_db


class RBDService:

    @staticmethod
    def create_role_menus(db, role, request_data):
        """根据角色创建角色菜单权限"""
        add_data = []
        if request_data.permissions:
            for i in request_data.permissions:
                add_data.append({'role_id': role.id, 'menu_id': i})
            role_menu_db.create_batch(db=db, add_data=add_data)

    @staticmethod
    def update_role_menus(db, role, request_data):
        """根据角色更新角色菜单权限"""
        add_data = []
        role_menu_db.remove_batch(db=db, filters={'role_id': role.id})
        if request_data.permissions:
            for i in request_data.permissions:
                add_data.append({'role_id': role.id, 'menu_id': i})
            role_menu_db.create_batch(db=db, add_data=add_data)

    @staticmethod
    def del_role_menus(db, role_id):
        """根据角色删除角色菜单权限"""
        role_menu_db.remove_batch(db=db, filters={'role_id': role_id})

    @staticmethod
    def get_sys_user_permission(db, user):
        # 系统角色对应菜单权限
        sys_role_ids = [role.role_id for role in user_role_db.get_data(db=db, filters={'user_id': user.id})]
        sys_menu_ids = [i.menu_id for i in role_menu_db.get_filter_in(db=db, name='role_id', value=sys_role_ids)]
        sys_permission_ids = [i.permission_id for i in menu_permission_db.get_filter_in(db=db, name='menu_id', value=sys_menu_ids)]
        sys_permissions = [i.code for i in permission_db.get_filter_in(db=db, name='id', value=sys_permission_ids)]
        # 团队角色对应菜单权限
        data = {'sys_role_ids': sys_role_ids, 'sys_menu_ids': sys_menu_ids, 'sys_permissions': sys_permissions}
        return data

    @staticmethod
    def get_team_user_permission(db, team_id=None, user=None):
        # 系统角色对应菜单权限
        if team_id:
            team_id = int(team_id)
        else:
            team_ids = [team.team_id for team in team_user_db.get_data(db=db, filters={'user_id': user.id})]
            team_id = team_ids[0] if team_ids else 0
        team_role_ids = [role.role_id for role in team_user_db.get_data(db=db, filters={'user_id': user.id, 'team_id': team_id})]
        team_menu_ids = [i.menu_id for i in role_menu_db.get_filter_in(db=db, name='role_id', value=team_role_ids)]
        team_permission_ids = [i.permission_id for i in menu_permission_db.get_filter_in(db=db, name='menu_id', value=team_menu_ids)]
        team_permissions = [i.code for i in permission_db.get_filter_in(db=db, name='id', value=team_permission_ids)]
        # 团队角色对应菜单权限
        data = {'team_role_ids': team_role_ids, 'sys_menu_ids': team_menu_ids, 'sys_permissions': team_permissions}
        return data

    @staticmethod
    def get_user_menu_ids(db, team_id, user):
        # 系统角色
        sys_role_ids = [role.role_id for role in user_role_db.get_data(db=db, filters={'user_id': user.id})]
        menu_ids = [i.menu_id for i in role_menu_db.get_filter_in(db=db, name='role_id', value=sys_role_ids)]
        return menu_ids

    @staticmethod
    def get_user_role_all_ids(db, user):
        # 系统角色
        sys_role_ids = [role.role_id for role in user_role_db.get_data(db=db, filters={'user_id': user.id})]
        return sys_role_ids

    @staticmethod
    def get_user_default(db, user):
        # Community Edition: no team/project context
        return {'team_info': {}, 'project_info': {}}

    @staticmethod
    def get_user_role_info(db, user, team_id=None):
        """获取用户角色信息 - 社区版：仅系统角色"""
        team_list = []
        # 系统角色
        sys_role_ids = [role.role_id for role in user_role_db.get_data(db=db, filters={'user_id': user.id})]
        role_ids = sys_role_ids
        # 菜单权限
        menu_ids = [i.menu_id for i in role_menu_db.get_filter_in(db=db, name='role_id', value=role_ids)]
        permission_ids = [i.permission_id for i in menu_permission_db.get_filter_in(db=db, name='menu_id', value=menu_ids)]
        permissions = [i.code for i in permission_db.get_filter_in(db=db, name='id', value=permission_ids)]
        data = {
            'team_list': team_list, 'permissions': permissions, 'role_ids': role_ids,
            'menu_ids': menu_ids, 'project_list': [],
            'userinfo': {'id': user.id, 'user_name': user.user_name, 'nickName': 'nickName'},
            'is_superman': bool(getattr(user, 'is_superman', False)),
            'user_type': getattr(user, 'user_type', 0),
        }
        return data


class MenuService:
    @staticmethod
    def create_menu_permissions(db, menu_obj, request_data):
        permission_list = request_data.permission_list
        if not permission_list is None:
            menu_permission_list = []
            for permission in permission_list:
                if permission.get('isInput'):
                    menu_permission_list.append({'menu_id': menu_obj.id, 'permission_id': permission['id']})
                else:
                    menu_permission_list.append({'menu_id': menu_obj.id, 'permission_id': permission['id']})
            menu_permission_db.create_batch(db=db, add_data=menu_permission_list)

    @staticmethod
    def update_menu_permissions(db, menu_id, request_data):
        permission_list = request_data.permission_list
        if not permission_list is None:
            menu_permission_list = []
            for permission in permission_list:
                if permission.get('isInput'):
                    del permission['id']
                    permission_db.create_one(db=db, obj_in=permission)
                else:
                    menu_permission_list.append({'menu_id': menu_id, 'permission_id': permission['id']})
            menu_permission_db.remove_batch(db=db, filters={"menu_id": menu_id})
            menu_permission_db.create_batch(db=db, add_data=menu_permission_list)

    @staticmethod
    def get_menu_ids(db, request_data, user_id):
        # 系统角色
        role_ids = [i.role_id for i in user_role_db.get_data(db=db, filters={'user_id': user_id})]
        menu_ids = [i.menu_id for i in role_menu_db.get_filter_in(db=db, name='role_id', value=role_ids)]
        return menu_ids


menu_service = MenuService()
rbd_service = RBDService()
