#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ABD SDK 异常处理模块
统一处理SDK中可能出现的各种异常
"""


class ABDException(Exception):
    """ABD SDK 基础异常类"""
    
    def __init__(self, message: str = None, error_code: str = None, details: dict = None):
        self.message = message or "ABD SDK error occurred"
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message
    
    def to_dict(self):
        """将异常转换为字典格式"""
        return {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ABDConnectionError(ABDException):
    """连接相关异常"""
    
    def __init__(self, message: str = None, url: str = None, status_code: int = None):
        self.url = url
        self.status_code = status_code
        super().__init__(
            message=message or f"Connection failed to {url or 'unknown endpoint'}",
            error_code="CONNECTION_ERROR"
        )


class ABDAuthenticationError(ABDException):
    """认证相关异常"""
    
    def __init__(self, message: str = None, token: str = None):
        self.token = token
        super().__init__(
            message=message or "Authentication failed",
            error_code="AUTHENTICATION_ERROR"
        )


class ABDValidationError(ABDException):
    """数据验证异常"""
    
    def __init__(self, message: str = None, field: str = None, value: any = None):
        self.field = field
        self.value = value
        super().__init__(
            message=message or f"Validation failed for field: {field}",
            error_code="VALIDATION_ERROR"
        )


class ABDRateLimitError(ABDException):
    """速率限制异常"""
    
    def __init__(self, message: str = None, retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(
            message=message or "Rate limit exceeded",
            error_code="RATE_LIMIT_ERROR"
        )


class ABDTimeoutError(ABDException):
    """超时异常"""
    
    def __init__(self, message: str = None, timeout: float = None):
        self.timeout = timeout
        super().__init__(
            message=message or f"Request timeout after {timeout or 'unknown'} seconds",
            error_code="TIMEOUT_ERROR"
        )


class ABDResourceNotFoundError(ABDException):
    """资源未找到异常"""
    
    def __init__(self, message: str = None, resource_type: str = None, resource_id: str = None):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(
            message=message or f"Resource {resource_type or 'unknown'} with id {resource_id or 'unknown'} not found",
            error_code="RESOURCE_NOT_FOUND"
        )
