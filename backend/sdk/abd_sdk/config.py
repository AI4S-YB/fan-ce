#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ABD SDK 配置管理模块
管理SDK的各种配置参数，支持环境变量和配置文件
"""

import os
import json
from typing import Optional, Dict, Any, Union
from pathlib import Path
from .exceptions import ABDValidationError


class ABDConfig:
    """ABD SDK 配置管理器"""
    
    def __init__(self, config_file: Optional[str] = 'config.yaml'):
        self.config_file = config_file
        self._config = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        # 默认配置
        self._config = {
            "api": {
                "base_url": "http://localhost:8002",
                "api_prefix": "/api/v1",
                "timeout": 30,
                "retry_count": 3,
                "retry_delay": 1
            },
            "auth": {
                "token_type": "Bearer",
                "token_header": "Authorization",
                "username": "admin",
                "password": "admin"
            },
            "logging": {
                "enabled": True,  # 日志总开关
                "level": "INFO",
                "log_file": None,
                "max_bytes": 10 * 1024 * 1024,  # 10MB
                "backup_count": 5,
                "console_enabled": True,  # 控制台日志开关
                "file_enabled": True,  # 文件日志开关
                "api_logging_enabled": True,  # API请求日志开关
                "error_logging_enabled": True  # 错误日志开关
            },
            "cache": {
                "enabled": True,
                "ttl": 300,  # 5 minutes
                "max_size": 1000
            }
        }
        
        # 从环境变量加载配置
        self._load_from_env()
        
        # 从配置文件加载配置
        if self.config_file and os.path.exists(self.config_file):
            self._load_from_file()
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        env_mapping = {
            "ABD_API_BASE_URL": ("api", "base_url"),
            "ABD_API_TIMEOUT": ("api", "timeout"),
            "ABD_API_RETRY_COUNT": ("api", "retry_count"),
            "ABD_AUTH_USERNAME": ("auth", "username"),
            "ABD_AUTH_PASSWORD": ("auth", "password"),
            "ABD_LOG_ENABLED": ("logging", "enabled"),
            "ABD_LOG_LEVEL": ("logging", "level"),
            "ABD_LOG_FILE": ("logging", "log_file"),
            "ABD_LOG_CONSOLE_ENABLED": ("logging", "console_enabled"),
            "ABD_LOG_FILE_ENABLED": ("logging", "file_enabled"),
            "ABD_LOG_API_ENABLED": ("logging", "api_logging_enabled"),
            "ABD_LOG_ERROR_ENABLED": ("logging", "error_logging_enabled"),
            "ABD_CACHE_ENABLED": ("cache", "enabled"),
            "ABD_CACHE_TTL": ("cache", "ttl")
        }
        
        for env_var, config_path in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_value(config_path, value)
    
    def _load_from_file(self):
        """从配置文件加载配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                self._merge_config(file_config)
        except (json.JSONDecodeError, IOError) as e:
            raise ABDValidationError(f"Failed to load config file: {e}")
    
    def _merge_config(self, new_config: Dict[str, Any]):
        """合并配置"""
        for key, value in new_config.items():
            if isinstance(value, dict) and key in self._config:
                self._config[key].update(value)
            else:
                self._config[key] = value
    
    def _set_nested_value(self, path: tuple, value: Any):
        """设置嵌套配置值"""
        current = self._config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # 类型转换
        key = path[-1]
        if key in ["timeout", "retry_count", "retry_delay", "max_bytes", "backup_count", "ttl", "max_size"]:
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass
        elif key in ["enabled"]:
            if isinstance(value, str):
                value = value.lower() in ["true", "1", "yes", "on"]
        
        current[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        current = self._config
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split('.')
        self._set_nested_value(tuple(keys), value)
    
    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置"""
        return self._config.get("api", {})
    
    def get_auth_config(self) -> Dict[str, Any]:
        """获取认证配置"""
        return self._config.get("auth", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self._config.get("logging", {})
    
    def get_cache_config(self) -> Dict[str, Any]:
        """获取缓存配置"""
        return self._config.get("cache", {})
    
    def get_base_url(self) -> str:
        """获取API基础URL"""
        return self.get("api.base_url")
    
    def get_api_prefix(self) -> str:
        """获取API前缀"""
        return self.get("api.api_prefix")
    
    def get_timeout(self) -> int:
        """获取请求超时时间"""
        return self.get("api.timeout")
    
    def get_retry_count(self) -> int:
        """获取重试次数"""
        return self.get("api.retry_count")
    
    def get_retry_delay(self) -> int:
        """获取重试延迟时间（秒）"""
        return self.get("api.retry_delay")
    
    def get_username(self) -> str:
        """获取用户名"""
        return self.get("auth.username")
    
    def get_password(self) -> str:
        """获取密码"""
        return self.get("auth.password")
    
    def get_token_type(self) -> str:
        """获取token类型"""
        return self.get("auth.token_type")
    
    def get_token_header(self) -> str:
        """获取token请求头"""
        return self.get("auth.token_header")
    
    def get_log_level(self) -> str:
        """获取日志级别"""
        return self.get("logging.level")
    
    def get_log_file(self) -> Optional[str]:
        """获取日志文件路径"""
        return self.get("logging.log_file")
    
    def is_cache_enabled(self) -> bool:
        """检查缓存是否启用"""
        return self.get("cache.enabled")
    
    def get_cache_ttl(self) -> int:
        """获取缓存TTL"""
        return self.get("cache.ttl")
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return self._config.copy()
    
    def save_to_file(self, file_path: Optional[str] = None):
        """保存配置到文件"""
        if file_path is None:
            file_path = self.config_file
        
        if file_path is None:
            raise ABDValidationError("No config file path specified")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise ABDValidationError(f"Failed to save config file: {e}")
    
    def validate(self) -> bool:
        """验证配置"""
        required_fields = [
            "api.base_url",
            "api.timeout",
            "logging.level"
        ]
        
        for field in required_fields:
            if self.get(field) is None:
                raise ABDValidationError(f"Required config field missing: {field}")
        
        return True


# 全局配置实例
_default_config = ABDConfig()


def get_config() -> ABDConfig:
    """获取默认配置实例"""
    return _default_config


def set_default_config(config: ABDConfig):
    """设置默认配置实例"""
    global _default_config
    _default_config = config
