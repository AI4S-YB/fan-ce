
# FAN-CE — FAN Community Edition

## 项目简介

FAN-CE 是一个面向组学数据管理、查询与展示的开源平台。

### 项目结构

| 目录 | 说明 |
|------|------|
| `backend/api-server` | 后台 API 服务（FastAPI + PostgreSQL） |
| `backend/sdk` | Python SDK |
| `frontend/admin-web` | 管理端前端（monorepo：Antd + Element + Naive） |
| `frontend/admin-web/apps/web-antd` | 管理后台（Ant Design Vue，端口 5666） |
| `frontend/admin-web/apps/web-public` | 公开门户（Element Plus，端口 5677） |
| `plugin/` | 分析工具插件（.whl） |
| `scripts/` | 安装、升级、开发脚本 |

### 开发环境端口

| 服务 | 端口 |
|------|------|
| 后端 API | 8002 |
| Admin 管理后台 (web-antd) | 5666 |
| Public 公开门户 (web-public) | 5677 |
| PostgreSQL | 5433 |

## 环境要求

| 依赖 | 用途 | 安装方式 |
|------|------|----------|
| [pixi](https://pixi.sh) | 生信工具 + Python 解释器 + uv 包管理器 | `curl -fsSL https://pixi.sh/install.sh \| bash` |
| [uv](https://docs.astral.sh/uv) | Python 虚拟环境与依赖管理（由 pixi 提供） | pixi 自动安装 |
| [pnpm](https://pnpm.io) | 前端包管理 | `npm install -g pnpm` |
| Node.js >= 20 | 前端构建 | 随 pnpm 环境 |
| PostgreSQL | 数据库 | 系统包管理器或 Docker |

**pixi** 管理生信工具（BLAST+、samtools、bcftools、bedtools、primer3、mafft、FastTree 等）和 Python 解释器。**uv** 管理 Python 依赖（FastAPI、SQLAlchemy 等 97 个包），两者职责分离，互不干扰。

## 安装

```bash
# 1. 克隆仓库
git clone <repo-url> && cd fan-ce

# 2. 创建配置文件（修改数据库连接等）
cp backend/api-server/conf/config.example.yaml backend/api-server/conf/config.dev.yaml

# 3. 运行安装脚本
bash scripts/install.sh
```

安装脚本自动完成：pixi 安装生信工具 + Python + uv → uv 安装 Python 依赖 → 数据库迁移 → 前端构建。

## 升级

```bash
bash scripts/upgrade.sh
```

升级脚本自动完成：停止服务 → 拉取最新代码 → pixi + uv 更新依赖 → 数据库迁移 → 更新插件 → 重建前端。

**升级不会影响数据**：PostgreSQL 数据库、数据集文件、BLAST 索引、配置文件均独立于代码仓库，升级过程不会覆盖或删除。

## 快速开始（开发）

```bash
# 启动后端
bash scripts/dev/start-backend.sh

# 启动管理端前端
bash scripts/dev/start-admin-web.sh

# 启动公开门户
cd frontend/admin-web && pnpm -F web-public dev

# 停止所有服务
bash scripts/dev/stop-dev.sh
```

### 访问应用

- **API 文档**：http://localhost:8002/docs
- **管理后台**：http://localhost:5666
- **公开门户**：http://localhost:5677
