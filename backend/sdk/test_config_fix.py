#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试配置修复是否成功
验证ABDConfig和ABDClient是否能正常工作
"""

def test_config_methods():
    """测试配置方法"""
    print("🧪 测试配置方法...")
    
    try:
        from fance_sdk.config import FANCEConfig
        
        config = ABDConfig()
        
        # 测试基本方法
        print("✅ 基本配置方法:")
        print(f"  - base_url: {config.get_base_url()}")
        print(f"  - timeout: {config.get_timeout()}")
        print(f"  - retry_count: {config.get_retry_count()}")
        print(f"  - retry_delay: {config.get_retry_delay()}")
        print(f"  - username: {config.get_username()}")
        print(f"  - password: {config.get_password()}")
        
        # 测试get方法
        print("✅ get方法测试:")
        print(f"  - api.retry_delay: {config.get('api.retry_delay')}")
        print(f"  - api.retry_count: {config.get('api.retry_count')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置方法测试失败: {e}")
        return False

def test_client_initialization():
    """测试客户端初始化"""
    print("\n🧪 测试客户端初始化...")
    
    try:
        from fance_sdk import FANCEClient
        
        # 创建客户端
        client = ABDClient(
            base_url="http://localhost:8002",
            username="test",
            password="test123"
        )
        
        print("✅ 客户端初始化成功")
        print(f"  - 配置: {client.config.to_dict()}")
        print(f"  - HTTP客户端: {type(client.http_client)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 客户端初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_imports():
    """测试导入"""
    print("\n🧪 测试导入...")
    
    try:
        # 测试主要模块导入
        from fance_sdk import FANCEClient
        from fance_sdk.config import FANCEConfig
        from abd_sdk.http_client import ABDHTTPClient
        from abd_sdk.exceptions import ABDException
        from abd_sdk.logger import get_logger
        
        print("✅ 所有主要模块导入成功")
        
        # 测试API模块导入
        from abd_sdk.api import (
            UserAPI, SystemAPI, DatabaseAPI, 
            ExperimentAPI, GeneAPI, SampleAPI, BasisAPI
        )
        
        print("✅ 所有API模块导入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("ABD SDK 配置修复验证测试")
    print("=" * 50)
    
    tests = [
        test_config_methods,
        test_client_initialization,
        test_imports
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！配置修复成功")
        print("\n现在您可以:")
        print("  1. 正常创建ABDClient实例")
        print("  2. 使用所有配置方法")
        print("  3. 运行测试套件")
    else:
        print("❌ 部分测试失败，配置问题仍然存在")
    
    return passed == total

if __name__ == "__main__":
    main()
