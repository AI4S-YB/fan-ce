# FAN-CE API Server

这里是当前项目的后台后端主目录。

后端运行所需内容已收敛到本目录，包括：

- FastAPI 应用入口 `main.py`
- 业务模块 `apps/`
- 组学与生物信息能力 `basis/`
- 核心配置与注册逻辑 `core/`、`register/`
- 数据库与共享库 `db/`、`libs/`、`utils/`
- 配置文件、静态资源与迁移文件 `conf/`、`static/`、`alembic/`
- Python 依赖描述 `pyproject.toml`、`uv.lock`

常用命令：

```bash
uv venv --python /opt/anaconda3/bin/python3.11 .venv
uv sync --python .venv/bin/python
APP_ENV=dev .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```
