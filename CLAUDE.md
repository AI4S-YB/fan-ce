# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FAN-CE (FAN Community Edition) is a FastAPI-based web application for bioinformatics data management and analysis. It follows a modular architecture with separate apps for different functional areas.

## Development Commands

### Running the Application

```bash
# 启动后端 (port 8002)
bash scripts/dev/start-backend.sh

# 启动前端 Antd 管理后台 (port 5666)
bash scripts/dev/start-admin-web.sh

# 停止所有开发服务器
bash scripts/dev/stop-dev.sh
```

**开发环境端口规范：**

| 服务 | 端口 |
|------|------|
| 后端 API | 8002 |
| 前端 Antd | 5666 |
| 前端 Element | 5667 |
| 前端 Naive | 5668 |
| PostgreSQL | 5433 |

后端端口由两处共同决定，已统一为 8002：
- `backend/api-server/main.py:37` — `uvicorn.run(..., port=8002)`
- `frontend/admin-web/apps/web-antd/vite.config.mts` — 所有代理目标指向 `http://127.0.0.1:8002`

### Database Management

```bash
# Initialize Alembic (only needed once)
alembic init alembic

# Generate migration
alembic revision --autogenerate -m "description_of_changes"

# Apply migrations
alembic upgrade head
```

### Installing Dependencies

```bash
pip install -r requirements.txt
```

## Architecture

### Application Structure

- **main.py**: FastAPI application entry point with app registration
- **register/**: Application setup and configuration (CORS, middleware, routing, exceptions)
- **core/**: Core configuration, schemas, security, and response handling
- **apps/**: Modular application components
  - **auth/**: Authentication and authorization
  - **databases/**: Database file management and metadata
  - **sample/**: Sample data management
  - **experiment/**: Experiment tracking and metadata
  - **system/**: System administration (users, teams, projects, RBAC)
  - **gene/**: Gene data and gene set management
  - **platform/**: Platform-specific features (news, etc.)
  - **dify/**: Dify AI integration
- **basis/**: Core bioinformatics utilities and APIs
- **db/**: Database connection and ORM configuration
- **libs/**: Shared utility libraries
- **utils/**: Additional utility modules

### Database Configuration

The application uses PostgreSQL as the primary database, with SQLite kept only for local fallback and file-oriented workflows. Configuration is managed through:
- `conf/config.dev.yaml`, `conf/config.prod.yaml`, `conf/config.example.yaml`: Environment-specific configuration files
- `core/config.py`: Pydantic settings management

### Key Design Patterns

- **Modular Router System**: Each app module has its own routers that are included in the main application
- **CRUD Pattern**: Consistent Create, Read, Update, Delete operations for each data model
- **Schema-Model Separation**: Pydantic schemas for API validation, SQLAlchemy models for database
- **Service Layer**: Business logic separated into service modules

### API Structure

All API routes are prefixed with `/api/v1` and organized by module:
- `/api/v1/auth/*`: Authentication endpoints
- `/api/v1/databases/*`: Database management
- `/api/v1/sample/*`: Sample data endpoints
- `/api/v1/system/*`: System administration
- `/api/v1/dify/*`: AI integration endpoints

### Configuration Management

The application uses a hierarchical configuration system:
1. `conf/config.<env>.yaml`: Environment-specific settings
2. `core/config.py`: Application-wide defaults and validation
3. Environment variables for sensitive data

### Testing

Limited test coverage exists in:
- `basis/test/`: Core functionality tests
- `mcp/omics_server/`: MCP server integration tests

## File Organization Conventions

- Each app module follows the same structure: `models.py`, `schemas.py`, `crud.py`, `routers.py`, `api/`
- Database models use SQLAlchemy with declarative base
- Pydantic schemas for request/response validation
- CRUD operations are centralized in dedicated modules
- API endpoints are organized in `api/` subdirectories within each app

## Development Notes

- The application uses SQLAlchemy 2.0+ syntax
- Database migrations are managed through Alembic
- Authentication uses JWT tokens with configurable expiration
- Static files are served from the `static/` directory
- The application supports both development and production configurations
- The main runtime database is PostgreSQL
