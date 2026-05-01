#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ABD SDK 命令行接口
提供命令行工具来使用SDK功能
"""

import os
import sys
import json
import argparse
from typing import Optional, Dict, Any
from .client import ABDClient, create_client
from .exceptions import ABDException


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="ABD SDK 命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 获取用户信息
  abd-sdk user info --base-url http://localhost:8002 --username admin --password admin123
  
  # 获取系统状态
  abd-sdk system status --base-url http://localhost:8002 --username admin --password admin123
  
  # 搜索基因
  abd-sdk gene search BRCA1 --base-url http://localhost:8002 --username admin --password admin123
  
  # 使用配置文件
  abd-sdk user info --config config.json
        """
    )
    
    # 全局参数
    parser.add_argument(
        "--base-url",
        default=os.getenv("ABD_API_BASE_URL", "http://localhost:8002"),
        help="ABD API基础URL (默认: %(default)s)"
    )
    parser.add_argument(
        "--username",
        default=os.getenv("ABD_AUTH_USERNAME", ""),
        help="用户名"
    )
    parser.add_argument(
        "--password",
        default=os.getenv("ABD_AUTH_PASSWORD", ""),
        help="密码"
    )
    parser.add_argument(
        "--config",
        help="配置文件路径"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="请求超时时间(秒) (默认: %(default)s)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别 (默认: %(default)s)"
    )
    parser.add_argument(
        "--output",
        choices=["json", "table", "text"],
        default="json",
        help="输出格式 (默认: %(default)s)"
    )
    
    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 用户相关命令
    user_parser = subparsers.add_parser("user", help="用户管理")
    user_subparsers = user_parser.add_subparsers(dest="user_command", help="用户子命令")
    
    # 用户信息
    user_info_parser = user_subparsers.add_parser("info", help="获取用户信息")
    user_info_parser.add_argument("--user-id", help="用户ID (不指定则获取当前用户)")
    
    # 用户列表
    user_list_parser = user_subparsers.add_parser("list", help="获取用户列表")
    user_list_parser.add_argument("--page", type=int, default=1, help="页码")
    user_list_parser.add_argument("--size", type=int, default=20, help="每页大小")
    
    # 系统相关命令
    system_parser = subparsers.add_parser("system", help="系统管理")
    system_subparsers = system_parser.add_subparsers(dest="system_command", help="系统子命令")
    
    # 系统状态
    system_status_parser = system_subparsers.add_parser("status", help="获取系统状态")
    
    # 系统信息
    system_info_parser = system_subparsers.add_parser("info", help="获取系统信息")
    
    # 角色列表
    role_list_parser = system_subparsers.add_parser("roles", help="获取角色列表")
    role_list_parser.add_argument("--page", type=int, default=1, help="页码")
    role_list_parser.add_argument("--size", type=int, default=20, help="每页大小")
    
    # 数据库相关命令
    db_parser = subparsers.add_parser("database", help="数据库管理")
    db_subparsers = db_parser.add_subparsers(dest="db_command", help="数据库子命令")
    
    # 数据库列表
    db_list_parser = db_subparsers.add_parser("list", help="获取数据库列表")
    db_list_parser.add_argument("--page", type=int, default=1, help="页码")
    db_list_parser.add_argument("--size", type=int, default=20, help="每页大小")
    
    # 实验相关命令
    exp_parser = subparsers.add_parser("experiment", help="实验管理")
    exp_subparsers = exp_parser.add_subparsers(dest="exp_command", help="实验子命令")
    
    # 实验列表
    exp_list_parser = exp_subparsers.add_parser("list", help="获取实验列表")
    exp_list_parser.add_argument("--page", type=int, default=1, help="页码")
    exp_list_parser.add_argument("--size", type=int, default=20, help="每页大小")
    
    # 基因相关命令
    gene_parser = subparsers.add_parser("gene", help="基因管理")
    gene_subparsers = gene_parser.add_subparsers(dest="gene_command", help="基因子命令")
    
    # 基因搜索
    gene_search_parser = gene_subparsers.add_parser("search", help="搜索基因")
    gene_search_parser.add_argument("query", help="搜索查询")
    gene_search_parser.add_argument("--page", type=int, default=1, help="页码")
    gene_search_parser.add_argument("--size", type=int, default=20, help="每页大小")
    
    # 基因信息
    gene_info_parser = gene_subparsers.add_parser("info", help="获取基因信息")
    gene_info_parser.add_argument("gene_id", help="基因ID")
    
    # 样本相关命令
    sample_parser = subparsers.add_parser("sample", help="样本管理")
    sample_subparsers = sample_parser.add_subparsers(dest="sample_command", help="样本子命令")
    
    # 样本列表
    sample_list_parser = sample_subparsers.add_parser("list", help="获取样本列表")
    sample_list_parser.add_argument("--page", type=int, default=1, help="页码")
    sample_list_parser.add_argument("--size", type=int, default=20, help="每页大小")
    
    # 基础生物信息学命令
    basis_parser = subparsers.add_parser("basis", help="基础生物信息学")
    basis_subparsers = basis_parser.add_subparsers(dest="basis_command", help="基础生物信息学子命令")
    
    # 可用工具
    basis_tools_parser = basis_subparsers.add_parser("tools", help="获取可用工具列表")
    
    # 系统信息
    basis_system_parser = basis_subparsers.add_parser("system", help="获取系统信息")
    
    # 配置相关命令
    config_parser = subparsers.add_parser("config", help="配置管理")
    config_subparsers = config_parser.add_subparsers(dest="config_command", help="配置子命令")
    
    # 显示配置
    config_show_parser = config_subparsers.add_parser("show", help="显示当前配置")
    
    # 保存配置
    config_save_parser = config_subparsers.add_parser("save", help="保存配置到文件")
    config_save_parser.add_argument("file_path", help="配置文件路径")
    
    # 测试连接
    test_parser = subparsers.add_parser("test", help="测试连接")
    
    return parser


def format_output(data: Any, output_format: str) -> str:
    """格式化输出"""
    if output_format == "json":
        return json.dumps(data, indent=2, ensure_ascii=False)
    elif output_format == "table":
        # 简单的表格格式
        if isinstance(data, dict):
            lines = []
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                lines.append(f"{key:<20} {value}")
            return "\n".join(lines)
        else:
            return str(data)
    else:  # text
        return str(data)


def handle_user_commands(client: ABDClient, args: argparse.Namespace) -> Dict[str, Any]:
    """处理用户相关命令"""
    if args.user_command == "info":
        if args.user_id:
            return client.user.get_user_profile(args.user_id)
        else:
            return client.user.get_current_user()
    elif args.user_command == "list":
        return client.user.list_users(page=args.page, size=args.size)
    else:
        raise ValueError(f"未知的用户命令: {args.user_command}")


def handle_system_commands(client: ABDClient, args: argparse.Namespace) -> Dict[str, Any]:
    """处理系统相关命令"""
    if args.system_command == "status":
        return client.system.get_system_status()
    elif args.system_command == "info":
        return client.system.get_system_info()
    elif args.system_command == "roles":
        return client.system.list_roles(page=args.page, size=args.size)
    else:
        raise ValueError(f"未知的系统命令: {args.system_command}")


def handle_database_commands(client: ABDClient, args: argparse.Namespace) -> Dict[str, Any]:
    """处理数据库相关命令"""
    if args.db_command == "list":
        return client.database.list_databases(page=args.page, size=args.size)
    else:
        raise ValueError(f"未知的数据库命令: {args.db_command}")


def handle_experiment_commands(client: ABDClient, args: argparse.Namespace) -> Dict[str, Any]:
    """处理实验相关命令"""
    if args.exp_command == "list":
        return client.experiment.list_experiments(page=args.page, size=args.size)
    else:
        raise ValueError(f"未知的实验命令: {args.exp_command}")


def handle_gene_commands(client: ABDClient, args: argparse.Namespace) -> Dict[str, Any]:
    """处理基因相关命令"""
    if args.gene_command == "search":
        return client.gene.search_genes(args.query, page=args.page, size=args.size)
    elif args.gene_command == "info":
        return client.gene.get_gene(args.gene_id)
    else:
        raise ValueError(f"未知的基因命令: {args.gene_command}")


def handle_sample_commands(client: ABDClient, args: argparse.Namespace) -> Dict[str, Any]:
    """处理样本相关命令"""
    if args.sample_command == "list":
        return client.sample.list_samples(page=args.page, size=args.size)
    else:
        raise ValueError(f"未知的样本命令: {args.sample_command}")


def handle_basis_commands(client: ABDClient, args: argparse.Namespace) -> Dict[str, Any]:
    """处理基础生物信息学相关命令"""
    if args.basis_command == "tools":
        return client.basis.get_available_tools()
    elif args.basis_command == "system":
        return client.basis.get_system_info()
    else:
        raise ValueError(f"未知的基础生物信息学命令: {args.basis_command}")


def handle_config_commands(client: ABDClient, args: argparse.Namespace) -> Dict[str, Any]:
    """处理配置相关命令"""
    if args.config_command == "show":
        return client.get_config().to_dict()
    elif args.config_command == "save":
        client.get_config().save_to_file(args.file_path)
        return {"message": f"配置已保存到 {args.file_path}"}
    else:
        raise ValueError(f"未知的配置命令: {args.config_command}")


def test_connection(args: argparse.Namespace) -> Dict[str, Any]:
    """测试连接"""
    try:
        client = ABDClient(
            base_url=args.base_url,
            username=args.username,
            password=args.password,
            config_file=args.config,
            timeout=args.timeout,
            log_level=args.log_level
        )
        
        # 尝试认证
        if client.authenticate():
            # 获取系统信息
            system_info = client.system.get_system_info()
            client.close()
            return {
                "status": "success",
                "message": "连接成功",
                "system_info": system_info
            }
        else:
            client.close()
            return {
                "status": "error",
                "message": "认证失败"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"连接失败: {str(e)}"
        }


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 如果没有指定命令，显示帮助
    if not args.command:
        parser.print_help()
        return
    
    try:
        # 测试连接命令不需要创建客户端
        if args.command == "test":
            result = test_connection(args)
            print(format_output(result, args.output))
            return
        
        # 创建客户端
        client = ABDClient(
            base_url=args.base_url,
            username=args.username,
            password=args.password,
            config_file=args.config,
            timeout=args.timeout,
            log_level=args.log_level
        )
        
        # 进行身份认证
        if not client.authenticate():
            print("认证失败，请检查用户名和密码", file=sys.stderr)
            sys.exit(1)
        
        # 根据命令类型处理
        if args.command == "user":
            result = handle_user_commands(client, args)
        elif args.command == "system":
            result = handle_system_commands(client, args)
        elif args.command == "database":
            result = handle_database_commands(client, args)
        elif args.command == "experiment":
            result = handle_experiment_commands(client, args)
        elif args.command == "gene":
            result = handle_gene_commands(client, args)
        elif args.command == "sample":
            result = handle_sample_commands(client, args)
        elif args.command == "basis":
            result = handle_basis_commands(client, args)
        elif args.command == "config":
            result = handle_config_commands(client, args)
        else:
            print(f"未知命令: {args.command}", file=sys.stderr)
            sys.exit(1)
        
        # 输出结果
        print(format_output(result, args.output))
        
        # 关闭客户端
        client.close()
        
    except ABDException as e:
        print(f"ABD SDK错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
