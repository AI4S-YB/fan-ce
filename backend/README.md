# FAN-CE Backend

FastAPI 后端 API 服务。提供管理后台接口、公开门户接口、组学数据引擎。

## 目录结构

```
backend/
├── main.py                       # FastAPI 应用入口
├── pyproject.toml                # Python 项目元数据 + 依赖
├── uv.lock                       # 依赖锁文件
├── alembic.ini                   # 数据库迁移配置
│
├── config/                       # 应用配置
│   ├── settings.py               # Pydantic Settings（读取 config.*.yaml）
│   ├── config.dev.yaml           # 开发环境配置
│   └── config.example.yaml       # 配置模版
│
├── app/                          # 应用组装（启动时执行）
│   ├── router.py                 # 顶层路由注册（modules/ + omics/）
│   ├── cors.py                   # CORS 跨域配置
│   ├── middleware.py              # 请求日志中间件
│   ├── exceptions.py             # 全局异常处理
│   └── init.py                   # 建表 + 种子数据 + 启动分析 worker
│
├── modules/                      # 业务模块
│   ├── auth/                     # 认证登录
│   ├── breeding/                 # 育种项目 + 种质资源管理
│   ├── datasets/                 # 数据集注册/导入/版本/公开
│   ├── platform/                 # 平台设置 / 多站点 / AI 对话 / FRP
│   ├── system/                   # 用户 / 角色 / 菜单 / 权限 / 字典
│   ├── analysis/                 # 分析任务 + 工具插件
│   ├── gene/                     # 基因集管理
│   ├── sample/                   # 生物样本管理
│   ├── experiment/               # 实验管理
│   ├── common/                   # 共享依赖（Depends / 鉴权）
│   ├── services/                 # 共享服务层（RBAC / 用户 / API Key）
│   └── routers.py               # 模块路由汇总
│
├── omics/                        # 组学数据引擎
│   ├── api/                      # 公开组学 API（基因组 / 序列 / 变异 / 表达 / 表型）
│   ├── core/                     # 生信处理工具（samtools / gffutils / tabix）
│   ├── models/                   # 组学 ORM 模型
│   ├── schemas/                  # 组学 Pydantic schemas
│   ├── db.py                     # 组学专用 SQLite 连接
│   └── routers.py               # 组学路由汇总
│
├── shared/                       # 共享库
│   ├── database.py               # SQLAlchemy 引擎 + 连接管理
│   ├── crud_base.py              # 通用 CRUD 基类
│   ├── bootstrap.py              # 种子数据（admin 用户 / 菜单）
│   ├── security.py               # JWT 令牌 + 密码哈希
│   ├── responses.py              # API 标准响应格式
│   ├── logger.py                 # 日志（loguru）
│   ├── exceptions.py             # 异常类定义
│   ├── filter.py                 # 动态查询过滤
│   ├── config_loader.py          # YAML 配置读取
│   ├── crypto.py                 # RSA 加密 / License 验证
│   ├── tree.py                   # 树结构工具
│   ├── tool_registry.py          # Chat 工具注册
│   ├── string_utils.py           # 随机字符串生成
│   ├── file_utils.py             # 文件操作工具
│   └── pgorm/ + sqliteorm/       # PG / SQLite ORM 适配
│
├── cli/                          # 命令行工具
│   ├── load_taxonomy.py          # 导入 NCBI taxonomy
│   ├── generate_germplasm_template.py  # 生成种质导入模版
│   └── ...                       # 数据迁移 / Demo 数据
│
├── tests/                        # 测试（pytest，38 个测试文件）
├── data/                         # 内置数据（植物 taxonomy 包）
├── static/                       # FastAPI 静态文件
├── alembic/                      # 数据库迁移脚本
└── .venv/                        # Python 虚拟环境（uv 管理）
```

## 新功能安插指南

| 需求 | 放在哪里 | 示例 |
|---|---|---|
| 加一个新的业务 REST API | `modules/` 下新建目录，含 `models.py` + `api/` | `modules/inventory/` |
| 加一个生信分析接口 | `omics/api/` 新建 `.py` 文件 | `omics/api/d_metabolome.py` |
| 加一个 CLI 工具 | `cli/` 新建 `.py` 文件 | `cli/export_users.py` |
| 加一个共享工具函数 | `shared/` 新建 `.py` 文件 | `shared/csv_utils.py` |
| 改数据库表结构 | `modules/<module>/models.py` + `alembic/versions/` 迁移 | |
| 改 API 响应格式 | `shared/responses.py` 的 `response_200()` | |
| 改认证 / 登录逻辑 | `shared/security.py` + `modules/auth/login.py` | |
| 加一个新的 LLM 工具 | `modules/<module>/tools.py` + `shared/tool_registry.py` | |
| 加平台设置项 | `modules/platform/models.py` + `api/setting.py` | |

## 启动流程

```
main.py
  ├── config/settings.py          → 读取 YAML 配置
  ├── app/init.py                 → 创建表 + 种子数据 + 启动 analysis worker
  ├── app/router.py               → 注册 modules/ + omics/ 全部路由
  ├── app/cors.py                 → 配置跨域
  ├── app/middleware.py            → 请求日志
  ├── app/exceptions.py           → 全局异常 handler
  └── uvicorn.run()               → 启动 HTTP 服务
```

## 单独安装与启动

### 安装依赖

```bash
# 在项目根目录执行（通过 pixi）
pixi run uv sync --directory backend

# 如果只装了 uv 没有 pixi
cd backend
uv sync
```

### 启动服务

```bash
# 开发模式（热重载，仅本机访问）
pixi run uv run --directory backend uvicorn main:app --host 127.0.0.1 --port 8002 --reload

# 调试模式（热重载，允许远程访问）
pixi run uv run --directory backend uvicorn main:app --host 0.0.0.0 --port 8002 --reload

# 生产模式（无热重载）
pixi run uv run --directory backend uvicorn main:app --host 0.0.0.0 --port 8002
```

### 数据库迁移

```bash
# 生成迁移
cd backend && alembic revision --autogenerate -m "description"

# 执行迁移
pixi run uv run --directory backend alembic upgrade head
```

### 运行测试

```bash
pixi run uv run --directory backend python -m pytest tests/ -v
```

## 技术栈

| 组件 | 技术 |
|---|---|
| Web 框架 | FastAPI |
| ORM | SQLAlchemy 2.0 |
| 数据库 | PostgreSQL（主） + SQLite（组学数据） |
| 认证 | JWT（HS256） |
| 配置 | Pydantic Settings + YAML |
| 日志 | Loguru |
| 包管理 | uv + pixi |
| 迁移 | Alembic |
| 测试 | pytest |

---

> 2026-05-17：目录重组（apps→modules, basis→omics, libs+db→shared, register→app, core+conf→config, bin→cli）
