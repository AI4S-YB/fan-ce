#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ABD SDK 数据库管理API模块
提供数据库相关的API操作
"""

from typing import Optional, Dict, Any, List
from .base import BaseAPI


class DatabaseAPI(BaseAPI):
    """数据库管理API模块"""
    
    def __init__(self, http_client, api_prefix: str = "/api/v1"):
        super().__init__(http_client, api_prefix)
        self.base_endpoint = "/databases"
    
    def list_databases(
        self, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取数据库列表"""
        return self.list_resources(
            self.base_endpoint,
            page=page,
            size=size,
            filters=filters,
            **kwargs
        )
    
    def get_database(self, database_id: str) -> Dict[str, Any]:
        """获取数据库信息"""
        data = {"id": database_id}
        return self.post(f"{self.base_endpoint}/profile", data=data)
    
    def create_database(self, database_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建数据库"""
        return self.create_resource(self.base_endpoint, database_data)
    
    def update_database(self, database_id: str, database_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新数据库"""
        database_data["id"] = database_id
        return self.post(f"{self.base_endpoint}/update", data=database_data)
    
    def delete_database(self, database_id: str) -> Dict[str, Any]:
        """删除数据库"""
        data = {"id": database_id}
        return self.post(f"{self.base_endpoint}/delete", data=data)
    
    def get_database_meta(self, database_id: str) -> Dict[str, Any]:
        """获取数据库元数据"""
        data = {"id": database_id}
        return self.post(f"{self.base_endpoint}/meta", data=data)
    
    def update_database_meta(self, database_id: str, meta_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新数据库元数据"""
        meta_data["id"] = database_id
        return self.post(f"{self.base_endpoint}/update-meta", data=meta_data)
    
    def get_database_files(
        self, 
        database_id: str,
        page: int = 1,
        size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取数据库文件列表"""
        data = {"id": database_id, "page": page, "size": size}
        if filters:
            data.update(filters)
        
        return self.post(f"{self.base_endpoint}/files", data=data)
    
    def get_database_file(self, database_id: str, file_id: str) -> Dict[str, Any]:
        """获取数据库文件信息"""
        data = {"database_id": database_id, "file_id": file_id}
        return self.post(f"{self.base_endpoint}/file-profile", data=data)
    
    def upload_database_file(self, database_id: str, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """上传数据库文件"""
        data = metadata or {}
        data["database_id"] = database_id
        return self.upload_file(f"{self.base_endpoint}/upload-file", file_path, metadata=data)
    
    def download_database_file(self, database_id: str, file_id: str, save_path: str) -> str:
        """下载数据库文件"""
        return self.download_file(f"{self.base_endpoint}/download-file", save_path)
    
    def delete_database_file(self, database_id: str, file_id: str) -> Dict[str, Any]:
        """删除数据库文件"""
        data = {"database_id": database_id, "file_id": file_id}
        return self.post(f"{self.base_endpoint}/delete-file", data=data)
    
    def get_database_actions(
        self, 
        database_id: str,
        page: int = 1,
        size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取数据库操作记录"""
        data = {"id": database_id, "page": page, "size": size}
        if filters:
            data.update(filters)
        
        return self.post(f"{self.base_endpoint}/actions", data=data)
    
    def execute_database_action(self, database_id: str, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行数据库操作"""
        data = {"database_id": database_id, "action": action}
        if params:
            data.update(params)
        
        return self.post(f"{self.base_endpoint}/execute-action", data=data)
    
    def get_database_status(self, database_id: str) -> Dict[str, Any]:
        """获取数据库状态"""
        data = {"id": database_id}
        return self.post(f"{self.base_endpoint}/status", data=data)
    
    def backup_database(self, database_id: str, backup_path: str) -> str:
        """备份数据库"""
        return self.download_file(f"{self.base_endpoint}/backup", backup_path)
    
    def restore_database(self, database_id: str, backup_file_path: str) -> Dict[str, Any]:
        """恢复数据库"""
        return self.upload_file(f"{self.base_endpoint}/restore", backup_file_path)
    
    def get_database_statistics(self, database_id: str) -> Dict[str, Any]:
        """获取数据库统计信息"""
        data = {"id": database_id}
        return self.post(f"{self.base_endpoint}/statistics", data=data)
    
    def search_databases(
        self, 
        query: str, 
        page: int = 1, 
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """搜索数据库"""
        return self.search_resources(
            self.base_endpoint,
            query=query,
            page=page,
            size=size,
            **kwargs
        )
    
    def get_database_types(self) -> Dict[str, Any]:
        """获取数据库类型列表"""
        return self.post(f"{self.base_endpoint}/types")
    
    def validate_database_connection(self, connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """验证数据库连接"""
        return self.post(f"{self.base_endpoint}/validate-connection", data=connection_params)
    
    def get_database_schema(self, database_id: str) -> Dict[str, Any]:
        """获取数据库模式"""
        data = {"id": database_id}
        return self.post(f"{self.base_endpoint}/schema", data=data)
    
    def get_database_tables(
        self, 
        database_id: str,
        page: int = 1,
        size: int = 100,
        **kwargs
    ) -> Dict[str, Any]:
        """获取数据库表列表"""
        data = {"id": database_id, "page": page, "size": size}
        return self.post(f"{self.base_endpoint}/tables", data=data)
    
    def get_table_structure(self, database_id: str, table_name: str) -> Dict[str, Any]:
        """获取表结构"""
        data = {"database_id": database_id, "table_name": table_name}
        return self.post(f"{self.base_endpoint}/table-structure", data=data)
    
    def get_table_data(
        self, 
        database_id: str, 
        table_name: str,
        page: int = 1,
        size: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取表数据"""
        data = {"database_id": database_id, "table_name": table_name, "page": page, "size": size}
        if filters:
            data.update(filters)
        
        return self.post(f"{self.base_endpoint}/table-data", data=data)
    
    def execute_sql_query(self, database_id: str, sql: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行SQL查询"""
        data = {"database_id": database_id, "sql": sql}
        if params:
            data["params"] = params
        
        return self.post(f"{self.base_endpoint}/query", data=data)
    
    def get_query_history(
        self, 
        database_id: str,
        page: int = 1,
        size: int = 50,
        **kwargs
    ) -> Dict[str, Any]:
        """获取查询历史"""
        data = {"id": database_id, "page": page, "size": size}
        return self.post(f"{self.base_endpoint}/query-history", data=data)
