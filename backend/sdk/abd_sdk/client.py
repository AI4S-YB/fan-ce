#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ABD SDK 主客户端模块
提供统一的API访问接口，整合所有功能模块
"""

import os
from typing import Optional, Dict, Any, List
from .config import ABDConfig, get_config
from .http_client import ABDHTTPClient
from .exceptions import ABDException, ABDAuthenticationError
from .logger import get_logger
from .api import (
    UserAPI, 
    SystemAPI, 
    DatabaseAPI, 
    ExperimentAPI, 
    GeneAPI, 
    SampleAPI,
    BasisAPI
)


class ABDClient:
    """ABD SDK 主客户端"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        config_file: Optional[str] = None,
        timeout: Optional[int] = None,
        log_level: Optional[str] = None,
        log_file: Optional[str] = None
    ):
        """
        初始化ABD客户端
        
        Args:
            base_url: API基础URL
            username: 用户名
            password: 密码
            config_file: 配置文件路径
            timeout: 请求超时时间
            log_level: 日志级别
            log_file: 日志文件路径
        """
        # 加载配置
        self.config = ABDConfig(config_file)
        print(444,self.config.to_dict())
        # 应用传入的参数
        if base_url:
            self.config.set("api.base_url", base_url)
        if username:
            self.config.set("auth.username", username)
        if password:
            self.config.set("auth.password", password)
        if timeout:
            self.config.set("api.timeout", timeout)
        if log_level:
            self.config.set("logging.level", log_level)
        if log_file:
            self.config.set("logging.log_file", log_file)
        
        # 验证配置
        self.config.validate()
        
        # 初始化日志
        self.logger = get_logger()
        
        # 应用日志开关设置
        self.logger.enable_logging(self.config.get("logging.enabled", True))
        self.logger.enable_console_logging(self.config.get("logging.console_enabled", True))
        self.logger.enable_file_logging(self.config.get("logging.file_enabled", True))
        self.logger.enable_api_logging(self.config.get("logging.api_logging_enabled", True))
        self.logger.enable_error_logging(self.config.get("logging.error_logging_enabled", True))
        
        # 设置日志级别
        self.logger.set_level(self.config.get_log_level())
        
        # 添加文件处理器（如果启用）
        if self.config.get_log_file() and self.config.get("logging.file_enabled", True):
            self.logger.add_file_handler(self.config.get_log_file())

        # 初始化HTTP客户端
        self.http_client = ABDHTTPClient(
            base_url=self.config.get_base_url(),
            timeout=self.config.get_timeout(),
            retry_count=self.config.get_retry_count(),
            retry_delay=self.config.get_retry_delay()
        )
        
        # 初始化API模块
        self._init_api_modules()
        
        # 认证状态
        self._authenticated = False
        self._access_token = None
        self.authenticate()
        self.logger.info("ABD Client initialized successfully")
    
    def _init_api_modules(self):
        """初始化API模块"""
        api_prefix = self.config.get_api_prefix()
        
        self.user = UserAPI(self.http_client, api_prefix)
        self.system = SystemAPI(self.http_client, api_prefix)
        self.database = DatabaseAPI(self.http_client, api_prefix)
        self.experiment = ExperimentAPI(self.http_client, api_prefix)
        self.gene = GeneAPI(self.http_client, api_prefix)
        self.sample = SampleAPI(self.http_client, api_prefix)
        self.basis = BasisAPI(self.http_client, api_prefix)
    
    def authenticate(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        进行身份认证
        
        Args:
            username: 用户名，如果不提供则使用配置中的用户名
            password: 密码，如果不提供则使用配置中的密码
            
        Returns:
            bool: 认证是否成功
        """
        try:
            # 使用传入的凭据或配置中的凭据
            auth_username = username or self.config.get_username()
            auth_password = password or self.config.get_password()
            
            if not auth_username or not auth_password:
                raise ABDAuthenticationError("Username and password are required for authentication")
            
            # 调用认证API
            auth_data = {
                "username": auth_username,
                "password": auth_password,
                "user_name": auth_username,
                "user_password": auth_password
            }
            response = self.http_client.post("/api/v1/auth/login", data=auth_data)
            if response.get("code") == 2000:
                if response.get("data").get("access_token"):
                    self._access_token = response.get("data").get("access_token")
                    self._authenticated = True
                    # 设置HTTP客户端的认证token
                    self.http_client.set_auth_token(self._access_token)
                    self.logger.info("Authentication successful")
                    return True
                else:
                    self.logger.error("Authentication failed: No access token received")
                    return False
            else:
                raise ABDAuthenticationError(response.get("message"))
            
        
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            self._authenticated = False
            self._access_token = None
            return False
    
    def logout(self):
        """登出并清除认证信息"""
        try:
            if self._authenticated:
                # 调用登出API
                self.http_client.post("/auth/logout")
        except Exception as e:
            self.logger.warning(f"Logout API call failed: {e}")
        finally:
            # 清除认证状态
            self._authenticated = False
            self._access_token = None
            self.http_client.clear_auth_token()
            self.logger.info("Logged out successfully")
    
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return self._authenticated
    
    def get_access_token(self) -> Optional[str]:
        """获取访问token"""
        return self._access_token

    
    def get_config(self) -> ABDConfig:
        """获取配置对象"""
        return self.config
    
    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            self.config.set(key, value)
        
        # 重新应用配置到HTTP客户端
        self.http_client.timeout = self.config.get_timeout()
        self.http_client.retry_count = self.config.get_retry_count()
        self.http_client.retry_delay = self.config.get_retry_delay()
    
    def save_config(self, file_path: Optional[str] = None):
        """保存配置到文件"""
        self.config.save_to_file(file_path)
    
    def get_status(self) -> Dict[str, Any]:
        """获取客户端状态信息"""
        return {
            "authenticated": self._authenticated,
            "base_url": self.config.get_base_url(),
            "timeout": self.config.get_timeout(),
            "log_level": self.config.get_log_level(),
            "api_prefix": self.config.get_api_prefix()
        }
    
    def close(self):
        """关闭客户端"""
        try:
            self.logout()
            self.http_client.close()
            self.logger.info("ABD Client closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing client: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 便捷函数
def create_client(
    base_url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    config_file: Optional[str] = None,
    **kwargs
) -> ABDClient:
    """
    创建ABD客户端的便捷函数
    
    Args:
        base_url: API基础URL
        username: 用户名
        password: 密码
        config_file: 配置文件路径
        **kwargs: 其他配置参数
        
    Returns:
        ABDClient: 配置好的客户端实例
    """
    return ABDClient(
        base_url=base_url,
        username=username,
        password=password,
        config_file=config_file,
        **kwargs
    )


def get_default_client() -> ABDClient:
    """获取默认配置的客户端"""
    config = get_config()
    return ABDClient(
        base_url=config.get_base_url(),
        username=config.get_username(),
        password=config.get_password()
    )
