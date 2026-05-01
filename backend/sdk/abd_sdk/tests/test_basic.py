#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ABD SDK 基本功能测试
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# 添加SDK路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from abd_sdk import ABDClient, ABDConfig
from abd_sdk.exceptions import ABDException, ABDValidationError


class TestABDConfig(unittest.TestCase):
    """测试配置管理"""
    
    def test_config_creation(self):
        """测试配置创建"""
        config = ABDConfig()
        self.assertIsNotNone(config)
        self.assertEqual(config.get_base_url(), "http://localhost:8002")
        self.assertEqual(config.get_timeout(), 30)
    
    def test_config_set_get(self):
        """测试配置设置和获取"""
        config = ABDConfig()
        config.set("api.timeout", 60)
        self.assertEqual(config.get("api.timeout"), 60)
    
    def test_config_validation(self):
        """测试配置验证"""
        config = ABDConfig()
        self.assertTrue(config.validate())


class TestABDClient(unittest.TestCase):
    """测试客户端"""
    
    def setUp(self):
        """测试前准备"""
        self.client = ABDClient(
            base_url="http://localhost:8002",
            username="test_user",
            password="test_pass"
        )
    
    def test_client_creation(self):
        """测试客户端创建"""
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client.config.get_base_url(), "http://localhost:8002")
    
    def test_client_status(self):
        """测试客户端状态"""
        status = self.client.get_status()
        self.assertIn("base_url", status)
        self.assertIn("timeout", status)
    
    def test_api_modules_exist(self):
        """测试API模块是否存在"""
        self.assertIsNotNone(self.client.user)
        self.assertIsNotNone(self.client.system)
        self.assertIsNotNone(self.client.database)
        self.assertIsNotNone(self.client.experiment)
        self.assertIsNotNone(self.client.gene)
        self.assertIsNotNone(self.client.sample)
        self.assertIsNotNone(self.client.basis)


class TestExceptions(unittest.TestCase):
    """测试异常类"""
    
    def test_abd_exception(self):
        """测试基础异常"""
        exc = ABDException("测试错误")
        self.assertEqual(str(exc), "测试错误")
        self.assertIsNone(exc.error_code)
    
    def test_abd_exception_with_code(self):
        """测试带错误代码的异常"""
        exc = ABDException("测试错误", "TEST_ERROR")
        self.assertEqual(str(exc), "[TEST_ERROR] 测试错误")
        self.assertEqual(exc.error_code, "TEST_ERROR")
    
    def test_abd_exception_to_dict(self):
        """测试异常转字典"""
        exc = ABDException("测试错误", "TEST_ERROR", {"detail": "详细信息"})
        exc_dict = exc.to_dict()
        self.assertTrue(exc_dict["error"])
        self.assertEqual(exc_dict["error_code"], "TEST_ERROR")
        self.assertEqual(exc_dict["message"], "测试错误")
        self.assertEqual(exc_dict["details"]["detail"], "详细信息")


if __name__ == "__main__":
    unittest.main()
