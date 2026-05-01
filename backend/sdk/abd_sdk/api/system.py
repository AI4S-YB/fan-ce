#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ABD SDK 系统管理API模块
提供系统管理相关的API操作
"""

from typing import Optional, Dict, Any, List
from .base import BaseAPI


class SystemAPI(BaseAPI):
    """系统管理API模块"""
    
    def __init__(self, http_client, api_prefix: str = "/api/v1"):
        super().__init__(http_client, api_prefix)
        self.base_endpoint = "/system"
    
    # 角色管理
    def list_roles(
        self, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取角色列表"""
        return self.list_resources(
            f"{self.base_endpoint}/roles",
            page=page,
            size=size,
            filters=filters,
            **kwargs
        )
    
    def get_role(self, role_id: str) -> Dict[str, Any]:
        """获取角色信息"""
        data = {"id": role_id}
        return self.post(f"{self.base_endpoint}/roles/profile", data=data)
    
    def create_role(self, role_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建角色"""
        return self.create_resource(f"{self.base_endpoint}/roles", role_data)
    
    def update_role(self, role_id: str, role_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新角色"""
        role_data["id"] = role_id
        return self.post(f"{self.base_endpoint}/roles/update", data=role_data)
    
    def delete_role(self, role_id: str) -> Dict[str, Any]:
        """删除角色"""
        data = {"id": role_id}
        return self.post(f"{self.base_endpoint}/roles/delete", data=data)
    
    def get_role_permissions(self, role_id: str) -> Dict[str, Any]:
        """获取角色权限"""
        data = {"id": role_id}
        return self.post(f"{self.base_endpoint}/roles/permissions", data=data)
    
    def assign_permissions_to_role(self, role_id: str, permission_ids: List[str]) -> Dict[str, Any]:
        """为角色分配权限"""
        data = {"role_id": role_id, "permission_ids": permission_ids}
        return self.post(f"{self.base_endpoint}/roles/assign-permissions", data=data)
    
    # 权限管理
    def list_permissions(
        self, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取权限列表"""
        return self.list_resources(
            f"{self.base_endpoint}/permissions",
            page=page,
            size=size,
            filters=filters,
            **kwargs
        )
    
    def get_permission(self, permission_id: str) -> Dict[str, Any]:
        """获取权限信息"""
        data = {"id": permission_id}
        return self.post(f"{self.base_endpoint}/permissions/profile", data=data)
    
    def create_permission(self, permission_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建权限"""
        return self.create_resource(f"{self.base_endpoint}/permissions", permission_data)
    
    def update_permission(self, permission_id: str, permission_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新权限"""
        permission_data["id"] = permission_id
        return self.post(f"{self.base_endpoint}/permissions/update", data=permission_data)
    
    def delete_permission(self, permission_id: str) -> Dict[str, Any]:
        """删除权限"""
        data = {"id": permission_id}
        return self.post(f"{self.base_endpoint}/permissions/delete", data=data)
    
    # 团队管理
    def list_teams(
        self, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取团队列表"""
        return self.list_resources(
            f"{self.base_endpoint}/teams",
            page=page,
            size=size,
            filters=filters,
            **kwargs
        )
    
    def get_team(self, team_id: str) -> Dict[str, Any]:
        """获取团队信息"""
        data = {"id": team_id}
        return self.post(f"{self.base_endpoint}/teams/profile", data=data)
    
    def create_team(self, team_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建团队"""
        return self.create_resource(f"{self.base_endpoint}/teams", team_data)
    
    def update_team(self, team_id: str, team_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新团队"""
        team_data["id"] = team_id
        return self.post(f"{self.base_endpoint}/teams/update", data=team_data)
    
    def delete_team(self, team_id: str) -> Dict[str, Any]:
        """删除团队"""
        data = {"id": team_id}
        return self.post(f"{self.base_endpoint}/teams/delete", data=data)
    
    def get_team_members(self, team_id: str) -> Dict[str, Any]:
        """获取团队成员"""
        data = {"id": team_id}
        return self.post(f"{self.base_endpoint}/teams/members", data=data)
    
    def add_team_member(self, team_id: str, user_id: str, role: str = "member") -> Dict[str, Any]:
        """添加团队成员"""
        data = {"team_id": team_id, "user_id": user_id, "role": role}
        return self.post(f"{self.base_endpoint}/teams/add-member", data=data)
    
    def remove_team_member(self, team_id: str, user_id: str) -> Dict[str, Any]:
        """移除团队成员"""
        data = {"team_id": team_id, "user_id": user_id}
        return self.post(f"{self.base_endpoint}/teams/remove-member", data=data)
    
    # 项目管理
    def list_projects(
        self, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取项目列表"""
        return self.list_resources(
            f"{self.base_endpoint}/projects",
            page=page,
            size=size,
            filters=filters,
            **kwargs
        )
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """获取项目信息"""
        data = {"id": project_id}
        return self.post(f"{self.base_endpoint}/projects/profile", data=data)
    
    def create_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建项目"""
        return self.create_resource(f"{self.base_endpoint}/projects", project_data)
    
    def update_project(self, project_id: str, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新项目"""
        project_data["id"] = project_id
        return self.post(f"{self.base_endpoint}/projects/update", data=project_data)
    
    def delete_project(self, project_id: str) -> Dict[str, Any]:
        """删除项目"""
        data = {"id": project_id}
        return self.post(f"{self.base_endpoint}/projects/delete", data=data)
    
    def get_project_members(self, project_id: str) -> Dict[str, Any]:
        """获取项目成员"""
        data = {"id": project_id}
        return self.post(f"{self.base_endpoint}/projects/members", data=data)
    
    def add_project_member(self, project_id: str, user_id: str, role: str = "member") -> Dict[str, Any]:
        """添加项目成员"""
        data = {"project_id": project_id, "user_id": user_id, "role": role}
        return self.post(f"{self.base_endpoint}/projects/add-member", data=data)
    
    def remove_project_member(self, project_id: str, user_id: str) -> Dict[str, Any]:
        """移除项目成员"""
        data = {"project_id": project_id, "user_id": user_id}
        return self.post(f"{self.base_endpoint}/projects/remove-member", data=data)
    
    # 菜单管理
    def list_menus(
        self, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取菜单列表"""
        return self.list_resources(
            f"{self.base_endpoint}/menus",
            page=page,
            size=size,
            filters=filters,
            **kwargs
        )
    
    def get_menu(self, menu_id: str) -> Dict[str, Any]:
        """获取菜单信息"""
        data = {"id": menu_id}
        return self.post(f"{self.base_endpoint}/menus/profile", data=data)
    
    def create_menu(self, menu_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建菜单"""
        return self.create_resource(f"{self.base_endpoint}/menus", menu_data)
    
    def update_menu(self, menu_id: str, menu_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新菜单"""
        menu_data["id"] = menu_id
        return self.post(f"{self.base_endpoint}/menus/update", data=menu_data)
    
    def delete_menu(self, menu_id: str) -> Dict[str, Any]:
        """删除菜单"""
        data = {"id": menu_id}
        return self.post(f"{self.base_endpoint}/menus/delete", data=data)
    
    # 字典管理
    def list_dicts(
        self, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取字典列表"""
        return self.list_resources(
            f"{self.base_endpoint}/dicts",
            page=page,
            size=size,
            filters=filters,
            **kwargs
        )
    
    def get_dict(self, dict_id: str) -> Dict[str, Any]:
        """获取字典信息"""
        data = {"id": dict_id}
        return self.post(f"{self.base_endpoint}/dicts/profile", data=data)
    
    def create_dict(self, dict_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建字典"""
        return self.create_resource(f"{self.base_endpoint}/dicts", dict_data)
    
    def update_dict(self, dict_id: str, dict_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新字典"""
        dict_data["id"] = dict_id
        return self.post(f"{self.base_endpoint}/dicts/update", data=dict_data)
    
    def delete_dict(self, dict_id: str) -> Dict[str, Any]:
        """删除字典"""
        data = {"id": dict_id}
        return self.post(f"{self.base_endpoint}/dicts/delete", data=data)
    
    # 系统信息
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return self.post(f"{self.base_endpoint}/info")
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return self.post(f"{self.base_endpoint}/status")
    
    def get_system_logs(
        self, 
        level: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: int = 1,
        size: int = 100
    ) -> Dict[str, Any]:
        """获取系统日志"""
        data = {
            "page": page,
            "size": size
        }
        if level:
            data["level"] = level
        if start_time:
            data["start_time"] = start_time
        if end_time:
            data["end_time"] = end_time
        
        return self.post(f"{self.base_endpoint}/logs", data=data)
