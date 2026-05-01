
# FAN-CE — FAN Community Edition

## 项目简介
FAN-CE 是一个面向组学数据管理、查询与展示的开源平台。

当前目录规划：

- `backend/api-server`：后台后端代码、配置、静态资源与依赖描述
- `backend/sdk`：面向外部程序调用的 Python SDK
- `frontend/admin-web`：后台管理前端
- `frontend/portal-web`：前台门户前端占位目录

## 快速开始

### 环境要求

- Python 3.10+
- Conda (安装生物信息相关软件)
- UV (Python包管理器)

### 最简单的安装方式

#### 1. 创建并激活 Conda 环境, 安装生物信息相关软件

```bash
# 创建名为 fance 的 conda 环境
conda env create -f backend/api-server/environment.yml
```

#### 2. 安装项目依赖

```bash
cd backend/api-server
uv venv --python /opt/anaconda3/bin/python3.11 .venv
uv sync --python .venv/bin/python
```

#### 3. 数据库初始化

```bash
cd backend/api-server

# 初始化 Alembic
alembic init alembic

# 创建数据库迁移
alembic revision --autogenerate -m "create_user_table"

# 执行数据库迁移
alembic upgrade head
```

#### 4. 启动服务
```bash
cd /path/to/fan-ce
scripts/dev/start-backend.sh
```

#### 5. 访问应用
- **API 文档**：http://localhost:8002/docs
