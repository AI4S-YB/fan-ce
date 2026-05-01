#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ABD SDK 用户API模块
提供用户相关的API操作
"""

from typing import Optional, Dict, Any, List
from .base import BaseAPI


class UserAPI(BaseAPI):
    """用户API模块"""
    
    def __init__(self, http_client, api_prefix: str = "/api/v1"):
        super().__init__(http_client, api_prefix)
        self.base_endpoint = "/system/user"
    
    def get_current_user(self) -> Dict[str, Any]:
        """获取当前用户信息"""
        return self.post(f"{self.base_endpoint}/me")
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户资料"""
        data = {"id": user_id}
        return self.post(f"{self.base_endpoint}/profile", data=data)
    
    def update_user_profile(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新用户资料"""
        data["id"] = user_id
        return self.post(f"{self.base_endpoint}/update", data=data)
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """修改密码"""
        data = {
            "id": user_id,
            "old_password": old_password,
            "new_password": new_password
        }
        return self.post(f"{self.base_endpoint}/change-password", data=data)
    
    def list_users(
        self, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取用户列表"""
        return self.list_resources(
            self.base_endpoint + "/list",
            page=page,
            size=size,
            filters=filters,
            **kwargs
        )
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建用户"""
        return self.create_resource(self.base_endpoint, user_data)
    
    def delete_user(self, user_id: str) -> Dict[str, Any]:
        """删除用户"""
        data = {"id": user_id}
        return self.post(f"{self.base_endpoint}/delete", data=data)

    
    def get_user_avatar(self, user_id: str, save_path: str) -> str:
        """下载用户头像"""
        return self.download_file(f"{self.base_endpoint}/{user_id}/avatar", save_path)
    
    def upload_user_avatar(self, user_id: str, avatar_path: str) -> Dict[str, Any]:
        """上传用户头像"""
        return self.upload_file(f"{self.base_endpoint}/{user_id}/avatar", avatar_path)
    
    def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """获取用户权限"""
        data = {"id": user_id}
        return self.post(f"{self.base_endpoint}/permissions", data=data)
    
    def get_user_roles(self, user_id: str) -> Dict[str, Any]:
        """获取用户角色"""
        data = {"id": user_id}
        return self.post(f"{self.base_endpoint}/roles", data=data)
    
    def assign_role(self, user_id: str, role_id: str) -> Dict[str, Any]:
        """分配角色给用户"""
        data = {"user_id": user_id, "role_id": role_id}
        return self.post(f"{self.base_endpoint}/assign-role", data=data)
    
    def remove_role(self, user_id: str, role_id: str) -> Dict[str, Any]:
        """移除用户角色"""
        data = {"user_id": user_id, "role_id": role_id}
        return self.post(f"{self.base_endpoint}/remove-role", data=data)
    
    def get_user_teams(self, user_id: str) -> Dict[str, Any]:
        """获取用户所属团队"""
        data = {"id": user_id}
        return self.post(f"{self.base_endpoint}/teams", data=data)
    
    def join_team(self, user_id: str, team_id: str) -> Dict[str, Any]:
        """用户加入团队"""
        data = {"user_id": user_id, "team_id": team_id}
        return self.post(f"{self.base_endpoint}/join-team", data=data)
    
    def leave_team(self, user_id: str, team_id: str) -> Dict[str, Any]:
        """用户离开团队"""
        data = {"user_id": user_id, "team_id": team_id}
        return self.post(f"{self.base_endpoint}/leave-team", data=data)
    
    def get_user_projects(self, user_id: str) -> Dict[str, Any]:
        """获取用户参与的项目"""
        data = {"id": user_id}
        return self.post(f"{self.base_endpoint}/projects", data=data)
    
    def get_user_activities(self, user_id: str, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """获取用户活动记录"""
        data = {"id": user_id, "page": page, "size": size}
        return self.post(f"{self.base_endpoint}/activities", data=data)
