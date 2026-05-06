
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

### 开发环境端口

| 服务 | 端口 |
|------|------|
| 后端 API | 8002 |
| Admin 管理后台 (web-antd) | 5666 |
| Public 公开门户 (web-public) | 5677 |
| PostgreSQL | 5433 |

## 快速开始

### 环境要求

- Python 3.10+
- Conda（安装生物信息相关软件）
- pnpm（前端包管理）

### 启动开发服务器

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
