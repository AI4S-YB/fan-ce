#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FAN-CE SDK HTTP客户端模块
处理与ABD API的HTTP通信，包括请求重试、错误处理等
"""

import time
import json
import requests
from typing import Optional, Dict, Any, Union, Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .exceptions import (
    ABDException,
    ABDConnectionError, 
    ABDAuthenticationError, 
    ABDValidationError,
    ABDRateLimitError,
    ABDTimeoutError
)
from .logger import get_logger


class ABDHTTPClient:
    """FAN-CE SDK HTTP客户端"""
    
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        retry_count: int = 3,
        retry_delay: int = 1,
        headers: Optional[Dict[str, str]] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.headers = headers or {}
        self.logger = get_logger()
        
        # 创建session并配置重试策略
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """创建并配置requests session"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=self.retry_count,
            backoff_factor=self.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 设置默认headers
        session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "FAN-CE-SDK/1.0.0"
        })
        session.headers.update(self.headers)
        
        return session
    
    def _build_url(self, endpoint: str) -> str:
        """构建完整的URL"""
        if endpoint.startswith('http'):
            return endpoint
        return f"{self.base_url}{endpoint}"
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """处理HTTP响应"""
        try:
            # 记录请求日志
            response_time = response.elapsed.total_seconds()
            self.logger.log_request(
                method=response.request.method,
                url=response.request.url,
                status_code=response.status_code,
                response_time=response_time
            )
            
            # 检查HTTP状态码
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"data": response.text}
            
            elif response.status_code == 201:
                return {"success": True, "message": "Resource created successfully"}
            
            elif response.status_code == 204:
                return {"success": True, "message": "Resource deleted successfully"}
            
            elif response.status_code == 400:
                error_data = response.json() if response.content else {}
                raise ABDValidationError(
                    message=error_data.get("message", "Bad request"),
                    details=error_data
                )
            
            elif response.status_code == 401:
                raise ABDAuthenticationError(
                    message="Authentication failed. Please check your credentials."
                )
            
            elif response.status_code == 403:
                raise ABDAuthenticationError(
                    message="Access denied. You don't have permission to access this resource."
                )
            
            elif response.status_code == 404:
                raise ABDConnectionError(
                    message="Resource not found",
                    url=response.request.url,
                    status_code=response.status_code
                )
            
            elif response.status_code == 405:
                raise ABDConnectionError(
                    message="Method not allowed. The requested HTTP method is not supported for this endpoint.",
                    url=response.request.url,
                    status_code=response.status_code
                )
            
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise ABDRateLimitError(
                    message="Rate limit exceeded",
                    retry_after=int(retry_after) if retry_after else None
                )
            
            elif response.status_code >= 500:
                raise ABDConnectionError(
                    message="Server error occurred",
                    url=response.request.url,
                    status_code=response.status_code
                )
            
            else:
                raise ABDConnectionError(
                    message=f"Unexpected status code: {response.status_code}",
                    url=response.request.url,
                    status_code=response.status_code
                )
        
        except (ABDValidationError, ABDAuthenticationError, ABDRateLimitError):
            raise
        except Exception as e:
            if not isinstance(e, ABDException):
                raise ABDConnectionError(
                    message=f"Unexpected error: {str(e)}",
                    url=response.request.url,
                    status_code=response.status_code
                )
            raise
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送HTTP请求"""
        url = self._build_url(endpoint)
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data if data and not files else None,
                data=data if files else None,
                params=params,
                headers=request_headers,
                files=files,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
        
        except requests.exceptions.Timeout:
            raise ABDTimeoutError(
                message=f"Request timeout after {self.timeout} seconds",
                timeout=self.timeout
            )
        
        except requests.exceptions.ConnectionError:
            raise ABDConnectionError(
                message="Connection failed. Please check your network connection.",
                url=url
            )
        
        except requests.exceptions.RequestException as e:
            raise ABDConnectionError(
                message=f"Request failed: {str(e)}",
                url=url
            )
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """发送GET请求"""
        return self._make_request("GET", endpoint, params=params, **kwargs)
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """发送POST请求"""
        return self._make_request("POST", endpoint, data=data, **kwargs)
    
    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """发送PUT请求"""
        return self._make_request("PUT", endpoint, data=data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送DELETE请求"""
        return self._make_request("DELETE", endpoint, **kwargs)
    
    def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """发送PATCH请求"""
        return self._make_request("PATCH", endpoint, data=data, **kwargs)
    
    def upload_file(self, endpoint: str, file_path: str, field_name: str = "file", **kwargs) -> Dict[str, Any]:
        """上传文件"""
        try:
            with open(file_path, 'rb') as f:
                files = {field_name: f}
                return self._make_request("POST", endpoint, files=files, **kwargs)
        except IOError as e:
            raise ABDValidationError(f"Failed to open file {file_path}: {e}")
    
    def download_file(self, endpoint: str, save_path: str, **kwargs) -> str:
        """下载文件"""
        url = self._build_url(endpoint)
        
        try:
            response = self.session.get(url, stream=True, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            
            # 确保保存目录存在
            import os
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return save_path
        
        except requests.exceptions.RequestException as e:
            raise ABDConnectionError(f"Failed to download file: {e}")
    
    def set_auth_token(self, token: str, token_type: str = "Bearer"):
        """设置认证token"""
        auth_header = f"{token_type} {token}"
        self.session.headers.update({"Authorization": auth_header})
    
    def clear_auth_token(self):
        """清除认证token"""
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]
    
    def close(self):
        """关闭session"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
