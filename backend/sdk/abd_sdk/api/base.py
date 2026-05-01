#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ABD SDK API基础类
所有API模块的基类，提供通用的API操作方法
"""

from typing import Optional, Dict, Any, List
from ..http_client import ABDHTTPClient
from ..logger import get_logger


class BaseAPI:
    """API基础类"""
    
    def __init__(self, http_client: ABDHTTPClient, api_prefix: str = "/api/v1"):
        self.http_client = http_client
        self.api_prefix = api_prefix.rstrip('/')
        self.logger = get_logger()
    
    def _build_endpoint(self, path: str) -> str:
        """构建完整的API端点"""
        if path.startswith('http'):
            return path
        return f"{self.api_prefix}{path}"
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """发送GET请求"""
        full_endpoint = self._build_endpoint(endpoint)
        return self.http_client.get(full_endpoint, params=params, **kwargs)
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """发送POST请求"""
        full_endpoint = self._build_endpoint(endpoint)
        return self.http_client.post(full_endpoint, data=data, **kwargs)
    
    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """发送PUT请求"""
        full_endpoint = self._build_endpoint(endpoint)
        return self.http_client.put(full_endpoint, data=data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送DELETE请求"""
        full_endpoint = self._build_endpoint(endpoint)
        return self.http_client.delete(full_endpoint, **kwargs)
    
    def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """发送PATCH请求"""
        full_endpoint = self._build_endpoint(endpoint)
        return self.http_client.patch(full_endpoint, data=data, **kwargs)
    
    def upload_file(self, endpoint: str, file_path: str, field_name: str = "file", **kwargs) -> Dict[str, Any]:
        """上传文件"""
        full_endpoint = self._build_endpoint(endpoint)
        return self.http_client.upload_file(full_endpoint, file_path, field_name, **kwargs)
    
    def download_file(self, endpoint: str, save_path: str, **kwargs) -> str:
        """下载文件"""
        full_endpoint = self._build_endpoint(endpoint)
        return self.http_client.download_file(full_endpoint, save_path, **kwargs)
    
    def list_resources(
        self, 
        endpoint: str, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        **kwargs
    ) -> Dict[str, Any]:
        """
        获取资源列表
        
        Args:
            endpoint: API端点
            page: 页码，从1开始
            size: 每页大小
            filters: 过滤条件
            sort_by: 排序字段
            sort_order: 排序方向 (asc/desc)
            **kwargs: 其他参数
            
        Returns:
            Dict: 包含资源列表和分页信息的响应
        """
        params = {
            "page": page,
            "size": size
        }
        
        if filters:
            params.update(filters)
        
        if sort_by:
            params["sort_by"] = sort_by
            params["sort_order"] = sort_order
        
        return self.post(endpoint, data=params, **kwargs)
    
    def get_resource(self, endpoint: str, resource_id: str, **kwargs) -> Dict[str, Any]:
        """
        获取单个资源
        
        Args:
            endpoint: API端点
            resource_id: 资源ID
            **kwargs: 其他参数
            
        Returns:
            Dict: 资源信息
        """
        data = {"id": resource_id}
        return self.post(f"{endpoint}/profile", data=data, **kwargs)
    
    def create_resource(self, endpoint: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        创建资源
        
        Args:
            endpoint: API端点
            data: 资源数据
            **kwargs: 其他参数
            
        Returns:
            Dict: 创建结果
        """
        return self.post(endpoint, data=data, **kwargs)
    
    def update_resource(self, endpoint: str, resource_id: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        更新资源
        
        Args:
            endpoint: API端点
            resource_id: 资源ID
            data: 更新数据
            **kwargs: 其他参数
            
        Returns:
            Dict: 更新结果
        """
        data["id"] = resource_id
        return self.post(f"{endpoint}/update", data=data, **kwargs)
    
    def delete_resource(self, endpoint: str, resource_id: str, **kwargs) -> Dict[str, Any]:
        """
        删除资源
        
        Args:
            endpoint: API端点
            resource_id: 资源ID
            **kwargs: 其他参数
            
        Returns:
            Dict: 删除结果
        """
        data = {"id": resource_id}
        return self.post(f"{endpoint}/delete", data=data, **kwargs)
    
    def search_resources(
        self, 
        endpoint: str, 
        query: str, 
        page: int = 1, 
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """
        搜索资源
        
        Args:
            endpoint: API端点
            query: 搜索查询
            page: 页码
            size: 每页大小
            **kwargs: 其他参数
            
        Returns:
            Dict: 搜索结果
        """
        params = {
            "q": query,
            "page": page,
            "size": size
        }
        
        return self.post(endpoint, data=params, **kwargs)
