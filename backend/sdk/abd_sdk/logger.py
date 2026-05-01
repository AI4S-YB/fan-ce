#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FAN-CE SDK 日志管理模块
统一管理SDK的日志记录，支持多种日志级别和输出格式
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class ABDLogger:
    """FAN-CE SDK 日志管理器"""
    
    def __init__(
        self,
        name: str = "fance_sdk",
        level: str = "INFO",
        log_file: Optional[str] = None,
        log_format: Optional[str] = None,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        enabled: bool = True,
        console_enabled: bool = True,
        file_enabled: bool = True,
        api_logging_enabled: bool = True,
        error_logging_enabled: bool = True
    ):
        self.name = name
        self.level = getattr(logging, level.upper())
        self.log_file = log_file
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        # 日志开关设置
        self.enabled = enabled
        self.console_enabled = console_enabled
        self.file_enabled = file_enabled
        self.api_logging_enabled = api_logging_enabled
        self.error_logging_enabled = error_logging_enabled
        
        # 默认日志格式
        if log_format is None:
            log_format = (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(filename)s:%(lineno)d - %(funcName)s - %(message)s"
            )
        
        self.log_format = log_format
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(self.name)
        logger.setLevel(self.level)
        
        # 清除现有的处理器
        logger.handlers.clear()
        
        # 控制台处理器（根据开关决定是否添加）
        if self.console_enabled and self.enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.level)
            console_formatter = logging.Formatter(self.log_format)
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # 文件处理器（根据开关决定是否添加）
        if self.file_enabled and self.enabled and self.log_file:
            # 确保日志目录存在
            log_dir = os.path.dirname(self.log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            # 使用RotatingFileHandler进行日志轮转
            try:
                from logging.handlers import RotatingFileHandler
                file_handler = RotatingFileHandler(
                    self.log_file,
                    maxBytes=self.max_bytes,
                    backupCount=self.backup_count,
                    encoding='utf-8'
                )
            except ImportError:
                # 如果没有RotatingFileHandler，使用普通的FileHandler
                file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            
            file_handler.setLevel(self.level)
            file_formatter = logging.Formatter(self.log_format)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def debug(self, message: str, **kwargs):
        """记录调试日志"""
        if self.enabled:
            self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """记录信息日志"""
        if self.enabled:
            self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """记录警告日志"""
        if self.enabled:
            self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """记录错误日志"""
        if self.enabled and self.error_logging_enabled:
            self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """记录严重错误日志"""
        if self.enabled and self.error_logging_enabled:
            self.logger.critical(message, extra=kwargs)
    
    def exception(self, message: str, **kwargs):
        """记录异常日志（包含堆栈跟踪）"""
        if self.enabled and self.error_logging_enabled:
            self.logger.exception(message, extra=kwargs)
    
    def log_request(self, method: str, url: str, status_code: int, response_time: float, **kwargs):
        """记录API请求日志"""
        if self.enabled and self.api_logging_enabled:
            self.info(
                f"API Request: {method} {url} - Status: {status_code} - Time: {response_time:.3f}s",
                method=method,
                url=url,
                status_code=status_code,
                response_time=response_time,
                **kwargs
            )
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """记录错误日志"""
        if self.enabled and self.error_logging_enabled:
            error_info = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {}
            }
            self.error(f"Error occurred: {error}", **error_info)
    
    def set_level(self, level: str):
        """设置日志级别"""
        self.level = getattr(logging, level.upper())
        self.logger.setLevel(self.level)
        for handler in self.logger.handlers:
            handler.setLevel(self.level)
    
    def enable_logging(self, enabled: bool = True):
        """启用或禁用日志记录"""
        self.enabled = enabled
        self._setup_logger()
    
    def enable_console_logging(self, enabled: bool = True):
        """启用或禁用控制台日志"""
        self.console_enabled = enabled
        self._setup_logger()
    
    def enable_file_logging(self, enabled: bool = True):
        """启用或禁用文件日志"""
        self.file_enabled = enabled
        self._setup_logger()
    
    def enable_api_logging(self, enabled: bool = True):
        """启用或禁用API请求日志"""
        self.api_logging_enabled = enabled
    
    def enable_error_logging(self, enabled: bool = True):
        """启用或禁用错误日志"""
        self.error_logging_enabled = enabled
    
    def get_logging_status(self) -> Dict[str, Any]:
        """获取日志状态信息"""
        return {
            "enabled": self.enabled,
            "level": logging.getLevelName(self.level),
            "console_enabled": self.console_enabled,
            "file_enabled": self.file_enabled,
            "api_logging_enabled": self.api_logging_enabled,
            "error_logging_enabled": self.error_logging_enabled,
            "log_file": self.log_file,
            "handlers_count": len(self.logger.handlers)
        }
    
    def add_file_handler(self, log_file: str):
        """添加文件日志处理器"""
        if not os.path.exists(os.path.dirname(log_file)):
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        try:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
        except ImportError:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
        
        file_handler.setLevel(self.level)
        file_formatter = logging.Formatter(self.log_format)
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)


# 全局日志实例
_default_logger = ABDLogger()


def get_logger(name: str = "fance_sdk") -> ABDLogger:
    """获取日志记录器实例"""
    if name == "fance_sdk":
        return _default_logger
    return ABDLogger(name)


def set_default_logger(logger: ABDLogger):
    """设置默认日志记录器"""
    global _default_logger
    _default_logger = logger


def enable_global_logging(enabled: bool = True):
    """全局启用或禁用日志记录"""
    _default_logger.enable_logging(enabled)


def enable_global_console_logging(enabled: bool = True):
    """全局启用或禁用控制台日志"""
    _default_logger.enable_console_logging(enabled)


def enable_global_file_logging(enabled: bool = True):
    """全局启用或禁用文件日志"""
    _default_logger.enable_file_logging(enabled)


def enable_global_api_logging(enabled: bool = True):
    """全局启用或禁用API请求日志"""
    _default_logger.enable_api_logging(enabled)


def enable_global_error_logging(enabled: bool = True):
    """全局启用或禁用错误日志"""
    _default_logger.enable_error_logging(enabled)


def get_global_logging_status() -> Dict[str, Any]:
    """获取全局日志状态"""
    return _default_logger.get_logging_status()


def set_global_log_level(level: str):
    """设置全局日志级别"""
    _default_logger.set_level(level)
