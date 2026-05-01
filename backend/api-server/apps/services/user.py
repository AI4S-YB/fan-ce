
from apps.system.rbac.crud import user_role_db,role_db

class UserService:
    @staticmethod
    def get_user_role(db,user_id):
        user_roles = []
        for i in user_role_db.get_data(db=db,filters={'user_id':user_id}):
            user_roles.append(i.role_id)
        return user_roles

    @staticmethod
    def add_user_role(db,user_id,request_data):
        if request_data.user_roles:
            add_data = []
            for i in request_data.user_roles:
                add_data.append({'user_id': user_id, 'role_id': i})
            """
            #19【系统管理】-【用户管理】-无法新增用户
            Clark 2025-07-30
            """
            user_role_db.create_batch(db=db, add_data=add_data)

    @staticmethod
    def update_user_role(db,user_id,request_data):
        """根据用户更新用户角色"""
        user_role_db.remove_batch(db=db,filters={'user_id':user_id})
        if request_data.user_roles:
            add_data = []
            for i in request_data.user_roles:
                add_data.append({'user_id':user_id,'role_id':i})
            user_role_db.create_batch(db=db,add_data=add_data)

user_service = UserService()