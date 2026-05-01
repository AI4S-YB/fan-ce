# FAN-CE SDK

**FAN Community Edition SDK**

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-3.0.1-blue.svg)](setup.py)

## 📚 项目简介

FAN-CE SDK 是一个专为FAN-CE平台设计的Python SDK，提供统一的API访问接口、异常处理、日志管理和配置管理功能。

## 🏗️ 目录结构

```
abd_sdk/
├── 📁 abd_sdk/                    # 核心包目录
│   ├── 📄 __init__.py            # 包初始化文件
│   ├── 📄 client.py              # 主客户端类
│   ├── 📄 config.py              # 配置管理
│   ├── 📄 exceptions.py          # 异常处理
│   ├── 📄 http_client.py         # HTTP客户端
│   ├── 📄 logger.py              # 日志管理
│   ├── 📄 cli.py                 # 命令行接口
│   │
│   ├── 📁 api/                   # API模块
│   │   ├── 📄 __init__.py        # API模块初始化
│   │   ├── 📄 base.py            # 基础API类
│   │   ├── 📄 user.py            # 用户管理API
│   │   ├── 📄 system.py          # 系统管理API
│   │   ├── 📄 database.py        # 数据库API
│   │   ├── 📄 experiment.py      # 实验管理API
│   │   ├── 📄 gene.py            # 基因管理API
│   │   ├── 📄 sample.py          # 样本管理API
│   │   └── 📄 basis.py           # 基础数据API
│   │
│   ├── 📁 examples/              # 使用示例
│   │   ├── 📄 __init__.py        # 示例模块初始化
│   │   └── 📄 basic_usage.py     # 基础使用示例
│   │
│   └── 📁 tests/                 # 测试文件
│       ├── 📄 __init__.py        # 测试模块初始化
│       └── 📄 test_basic.py      # 基础测试
│
├── 📄 setup.py                   # 包安装配置
├── 📄 pyproject.toml             # 项目配置文件
├── 📄 requirements.txt            # 依赖包列表
├── 📄 build_complete.sh          # 完整构建脚本
├── 📄 Makefile                   # 构建工具配置
├── 📄 LICENSE                    # 许可证文件
└── 📄 README.md                  # 项目说明文档
```

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd fan-ce/backend/sdk

# 构建和安装
./build_complete.sh
```

### 基本使用

```python
from abd_sdk import ABDClient

# 创建客户端
client = ABDClient(
    base_url="http://localhost:8002",
    username="admin",
    password="admin123"
)

# 使用API
users = client.user.get_users()
print(f"找到 {len(users)} 个用户")
```

### 命令行使用

```bash
# 显示帮助
abd_sdk --help

# 获取用户信息
abd_sdk user info --base-url http://localhost:8002 --username admin --password admin123

# 获取系统状态
abd_sdk system status --base-url http://localhost:8002 --username admin --password admin123
```

## 🔧 核心功能

### 1. 统一客户端 (ABDClient)
- 自动认证管理
- 请求重试和超时处理
- 配置管理
- 日志记录

### 2. API模块化设计
- **用户管理**: 用户CRUD、认证、权限
- **系统管理**: 系统状态、配置、监控
- **数据库管理**: 数据库操作、查询、管理
- **实验管理**: 实验创建、执行、结果
- **基因管理**: 基因搜索、分析、注释
- **样本管理**: 样本处理、分析、存储
- **基础数据**: 生物数据、元数据管理

### 3. 异常处理
- 统一的异常类层次
- HTTP状态码映射
- 详细的错误信息
- 异常恢复建议

### 4. 配置管理
- 环境变量支持
- 配置文件支持
- 运行时配置更新
- 配置验证

### 5. 日志管理
- 多级别日志
- 结构化日志
- 日志轮转
- 性能监控

## 📖 API 参考

### 客户端类

```python
class ABDClient:
    def __init__(self, base_url, username=None, password=None, config_file=None)
    def authenticate(self, username, password)
    def logout(self)
    def get_status(self)
    def close(self)
```

### API模块

```python
# 用户管理
client.user.get_users()
client.user.get_user(user_id)
client.user.create_user(user_data)
client.user.update_user(user_id, user_data)
client.user.delete_user(user_id)

# 系统管理
client.system.get_status()
client.system.get_config()
client.system.update_config(config_data)

# 数据库管理
client.database.list_databases()
client.database.get_database(db_id)
client.database.query_database(db_id, query)

# 实验管理
client.experiment.list_experiments()
client.experiment.get_experiment(exp_id)
client.experiment.create_experiment(exp_data)
client.experiment.run_experiment(exp_id)

# 基因管理
client.gene.search_genes(query)
client.gene.get_gene(gene_id)
client.gene.analyze_gene(gene_id)

# 样本管理
client.sample.list_samples()
client.sample.get_sample(sample_id)
client.sample.process_sample(sample_id, process_type)

# 基础数据
client.basis.get_organisms()
client.basis.get_features()
client.basis.get_sequences()
```

## 🧪 测试

```bash
# 运行所有测试
python -m pytest abd_sdk/tests/

# 运行特定测试
python -m pytest abd_sdk/tests/test_basic.py

# 运行测试并生成覆盖率报告
python -m pytest abd_sdk/tests/ --cov=abd_sdk --cov-report=html
```

## 📦 构建和分发

### 开发构建
```bash
# 清理构建文件
make clean

# 构建包
make build

# 安装开发版本
make install-dev
```

### 生产构建
```bash
# 完整构建和安装
./build_complete.sh

# 或使用Makefile
make install
```

## 🔍 故障排除

### 常见问题

1. **导入错误**: 确保已正确安装包
2. **认证失败**: 检查用户名、密码和API地址
3. **连接超时**: 检查网络连接和超时设置
4. **权限错误**: 确认用户具有相应权限

### 调试模式

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 创建客户端时会显示详细日志
client = ABDClient(base_url="...", log_level="DEBUG")
```

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

如果您遇到问题或有建议，请：

- 创建 [Issue](../../issues)
- 发送邮件到: abd@example.com
- 查看文档: https://abd-sdk.readthedocs.io/

## 🏷️ 版本历史

- **3.0.1** - 优化目录结构，修复循环导入问题
- **2.0.0** - 重构API模块，增强异常处理
- **1.0.0** - 初始版本发布

---

**kentnf, llq, kasper1995** (c) 2024-present - FAN-CE SDK
