#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FAN-CE SDK 基本使用示例
演示SDK的基本功能和用法
"""

import os
import sys
import json
from datetime import datetime

# 添加SDK路径到Python路径
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from abd_sdk import ABDClient, create_client, get_default_client
from abd_sdk.exceptions import ABDException, ABDAuthenticationError, ABDConnectionError


def basic_client_usage():
    """基本客户端使用示例"""
    try:
        # 创建客户端
        client = ABDClient(
            base_url="http://localhost:8889",
            username="admin",
            password="admin",
            log_level="",
        )
        
        # 进行身份认证
        print(client.authenticate())
        user_list = client.sample.list_samples(page=1, size=1)
        print(user_list)
            
    except Exception as e:
        print(f"客户端创建失败: {e}")


def context_manager_usage():
    """上下文管理器使用示例"""
    print("\n=== 上下文管理器使用示例 ===")
    
    try:
        with ABDClient(
            base_url=os.getenv("FANCE_API_BASE_URL", "http://localhost:8889/"),
            username=os.getenv("FANCE_AUTH_USERNAME", "admin"),
            password=os.getenv("FANCE_AUTH_PASSWORD", "admin")
        ) as client:
            
            if client.authenticate():
                print("✅ 身份认证成功")
                
                # 获取数据库列表
                try:
                    databases = client.database.list_databases(page=1, size=5)
                    print(f"数据库列表: {len(databases.get('data', []))} 个数据库")
                except Exception as e:
                    print(f"获取数据库列表失败: {e}")
                
                # 获取实验列表
                try:
                    experiments = client.experiment.list_experiments(page=1, size=5)
                    print(f"实验列表: {len(experiments.get('data', []))} 个实验")
                except Exception as e:
                    print(f"获取实验列表失败: {e}")
                
            else:
                print("❌ 身份认证失败")
                
    except Exception as e:
        print(f"上下文管理器使用失败: {e}")


def api_module_usage():
    """API模块使用示例"""
    print("\n=== API模块使用示例 ===")
    
    try:
        client = create_client(
            base_url=os.getenv("FANCE_API_BASE_URL", "http://localhost:8889/"),
            username=os.getenv("FANCE_AUTH_USERNAME", "admin"),
            password=os.getenv("FANCE_AUTH_PASSWORD", "admin")
        )
        
        if client.authenticate():
            print("✅ 身份认证成功")
            
            # 用户管理API
            try:
                users = client.user.list_users(page=1, size=3)
                print(f"用户管理API: 获取到 {len(users.get('data', []))} 个用户")
            except Exception as e:
                print(f"用户管理API调用失败: {e}")
            
            # 系统管理API
            try:
                roles = client.system.list_roles(page=1, size=3)
                print(f"系统管理API: 获取到 {len(roles.get('data', []))} 个角色")
            except Exception as e:
                print(f"系统管理API调用失败: {e}")
            
            # 基因管理API
            try:
                genes = client.gene.search_genes("BRCA", page=1, size=3)
                print(f"基因管理API: 搜索到 {len(genes.get('data', []))} 个基因")
            except Exception as e:
                print(f"基因管理API调用失败: {e}")
            
            # 基础生物信息学API
            try:
                # 模拟序列数据
                test_sequence = "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCG"
                print(f"基础生物信息学API: 测试序列长度 {len(test_sequence)}")
                
                # 注意：这里只是演示，实际需要后端支持
                print("基础生物信息学API: 功能可用")
            except Exception as e:
                print(f"基础生物信息学API调用失败: {e}")
            
            client.close()
        else:
            print("❌ 身份认证失败")
            
    except Exception as e:
        print(f"API模块使用失败: {e}")


def configuration_usage():
    """配置管理示例"""
    print("\n=== 配置管理示例 ===")
    
    try:
        # 创建客户端
        client = create_client(
            base_url=os.getenv("FANCE_API_BASE_URL", "http://localhost:8889/"),
            username=os.getenv("FANCE_AUTH_USERNAME", "admin"),
            password=os.getenv("FANCE_AUTH_PASSWORD", "admin")
        )
        
        # 获取配置
        config = client.get_config()
        print(f"当前配置: {config.to_dict()}")
        
        # 更新配置
        client.update_config(
            timeout=60,
            log_level="DEBUG"
        )
        
        print("配置已更新")
        print(f"更新后的配置: {config.to_dict()}")
        
        # 保存配置到文件
        config_file = os.path.join(os.getcwd(), "abd_sdk_config.json")
        config.save_to_file(config_file)
        print(f"配置已保存到: {config_file}")
        
        # 从文件加载配置
        new_client = create_client(config_file=config_file)
        print("从配置文件创建客户端成功")
        
        # 清理配置文件
        if os.path.exists(config_file):
            os.remove(config_file)
            print("配置文件已清理")
        
        client.close()
        new_client.close()
        
    except Exception as e:
        print(f"配置管理失败: {e}")


def error_handling_example():
    """异常处理示例"""
    print("\n=== 异常处理示例 ===")
    
    try:
        # 创建客户端（使用错误的URL）
        client = create_client(
            base_url="http://invalid-url:9999",
            username="admin",
            password="admin123"
        )
        
        # 尝试认证（会失败）
        if client.authenticate():
            print("认证成功")
        else:
            print("认证失败")
            
    except ABDConnectionError as e:
        print(f"连接错误: {e}")
        print(f"错误代码: {e.error_code}")
        print(f"错误详情: {e.details}")
    except ABDAuthenticationError as e:
        print(f"认证错误: {e}")
    except ABDException as e:
        print(f"SDK错误: {e}")
    except Exception as e:
        print(f"其他错误: {e}")


def logging_example():
    """日志配置示例"""
    print("\n=== 日志配置示例 ===")
    
    try:
        # 创建带日志文件的客户端
        log_file = os.path.join(os.getcwd(), f"abd_sdk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        client = create_client(
            base_url=os.getenv("FANCE_API_BASE_URL", "http://localhost:8889/api/v1"),
            username=os.getenv("FANCE_AUTH_USERNAME", "admin"),
            password=os.getenv("FANCE_AUTH_PASSWORD", "admin"),
        
            log_level="DEBUG",
            log_file=log_file
        )
        
        print(f"日志文件: {log_file}")
        
        # 记录一些日志
        client.logger.info("这是一条信息日志")
        client.logger.warning("这是一条警告日志")
        client.logger.error("这是一条错误日志")
        
        # 动态调整日志级别
        client.logger.set_level("INFO")
        client.logger.info("日志级别已调整为INFO")
        
        # 关闭客户端
        client.close()
        
        # 检查日志文件是否创建
        if os.path.exists(log_file):
            print(f"日志文件已创建: {log_file}")
            # 清理日志文件
            os.remove(log_file)
            print("日志文件已清理")
        else:
            print("日志文件创建失败")
            
    except Exception as e:
        print(f"日志配置失败: {e}")


def main():
    """主函数"""
    # print("FAN-CE SDK 基本使用示例")
    # print("=" * 50)
    
    # 检查环境变量
    base_url = os.getenv("FANCE_API_BASE_URL", "http://localhost:8889/api/v1")
    username = os.getenv("FANCE_AUTH_USERNAME", "admin")
    password = os.getenv("FANCE_AUTH_PASSWORD", "admin")
    
    # print(f"使用配置:")
    # print(f"  API地址: {base_url}")
    # print(f"  用户名: {username}")
    # print(f"  密码: {'*' * len(password)}")
    # print()
    
    # 运行示例
    basic_client_usage()
    # context_manager_usage()
    # api_module_usage()
    # configuration_usage()
    # error_handling_example()
    # logging_example()
    
    # print("\n" + "=" * 50)
    # print("示例运行完成！")
    # print("\n提示:")
    # print("1. 确保ABD API服务正在运行")
    # print("2. 检查用户名和密码是否正确")
    # print("3. 查看日志文件了解详细错误信息")
    # print("4. 使用环境变量配置连接参数")


if __name__ == "__main__":
    main()
