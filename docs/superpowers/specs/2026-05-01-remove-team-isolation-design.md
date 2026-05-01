# 去掉 Team 多租户隔离 — 设计文档

> **目标:** 将系统从多 Team 多租户隔离架构，转为社区版单租户架构。Team 概念完全移除，Project 降为元数据标签，Dataset 成为权限主体。

**架构变更:** 从 "Team → Project → Dataset" 三层权限树，简化为 "Owner + public/private" 的 Dataset 级权限模型。Admin 可见全部，Owner 可见自己，认证用户可访问 public 数据。

**技术栈:** FastAPI + SQLAlchemy + PostgreSQL（后端），Vue 3 + Pinia + TypeScript（前端）

---

## 1. 权限模型

### 新模型

| 角色 | 权限 |
|------|------|
| Admin（`is_superman=True`） | 所有数据（无视 owner / visibility） |
| Owner | 自己的数据（不分 public/private） |
| 认证用户 | public 数据（可访问，不可管理） |
| 未认证/匿名 | public 数据（仅公开接口） |

### 去掉的概念

- Team 维度的数据隔离
- Team 成员权限传播（"同 team 可见"）
- Project 维度的权限控制
- `_get_user_team_ids()`、`_get_user_project_ids()` 权限判断

---

## 2. 后端改动

### 2.1 核心权限层

**`apps/datasets/services.py`：**

- `_can_access_dataset()` 简化为 3 级：admin（allow）→ owner（allow）→ public（allow 认证用户）
- 删除 `_get_user_team_ids()`
- 删除 `_get_user_project_ids()`
- `list_datasets()` 不再传 `team_id` 过滤
- `static can_access_dataset()` 去掉 team/project 判断

**`apps/databases/`：**
- `database.py` / `database_files.py` 去掉 team_id 过滤

**`apps/gene/`：**
- gene set 列表不再按 team 过滤

**`apps/platform/`：**
- news 列表不再按 team 过滤

**`apps/sample/`：**
- 去掉 team 维度

### 2.2 RBAC 和认证

**`apps/services/rbd.py`：**
- `get_user_default()` 不再返回 team_info/project_info
- `get_user_role_info()` 去掉 team_id 参数，去掉 team 维度角色查询
- `get_user_menu_ids()` 只保留系统级菜单

**`apps/common/depends.py`：**
- `get_rbd_user()` 不再需要 team_id 上下文

**`apps/auth/login.py`：**
- 登录响应 `team` / `project` 字段返回 null 或移除

**`apps/auth/menus.py`：**
- 菜单不再按 team_id 过滤

**`apps/services/auth_key_service.py`：**
- Auth key 格式从 `fandb_team{id}_{random}` → `fandb_{random}`
- 去掉 `extract_team_id_from_auth_key()`

### 2.3 Schema 清理

去掉 `team_id` 字段的 Pydantic Request：
- `DatabasesListRequest`
- `DatabasesFileListRequest`
- `GeneSetListRequest`
- `NewsListParams` / `NewsCreateType` / `NewsUpdateType`
- `DatasetListRequest`
- `ProjectListRequest`
- `AuthKeyCreateRequest` / `AuthKeyListRequest`

### 2.4 数据库 Migration

**删除列：**
- `databases.team_id`
- `dataset_registry.team_id`（如果存在）
- `gene_sets.team_id`（如果存在）
- `platform_news.team_id`

**删除表：**
- `system_team`
- `system_team_user`（`TeamUserLink`）
- `system_team_project`（`TeamProjectLink`）
- `system_team_role`（`TeamRoleLink`）

**删除路由/API（不再挂载）：**
- `apps/system/team/` 整个模块

---

## 3. 前端改动

### 3.1 删除

| 文件/目录 | 原因 |
|-----------|------|
| `src/views/system/team/` | Team 管理页面 |
| `src/api/system/team.ts` | Team API 模块 |
| `src/layouts/basic.vue` 中的 Team 切换器 | UI 组件 |
| `src/layouts/project.vue` | Project 选择器 |

### 3.2 Store 和 Auth

**`src/store/modules/project.ts`：**
- 去掉 `teamInfo` 状态
- 去掉 `setTeamInfo()` action
- 去掉 `fetchTeamInfo()` action
- 保留 `projectInfo` 仅作元数据标签（若需要）

**`src/store/auth.ts`：**
- `loginApi` 回调不再处理 `team` / `project` 返回值
- `fetchUserInfo()` 不再从 `team_list[0]` 设默认 team

### 3.3 API 类型清理

去掉 TypeScript 接口中的 `team_id` 字段：
- `src/api/apps/dataset.ts`
- `src/api/apps/geneset.ts`
- `src/api/system/user.ts`
- `src/api/platform/news.ts`

### 3.4 探索工作台

**`src/views/dashboard/workspace/index.vue`：**
- `workspaceDescription` 去掉 team name 显示
- 只显示 project 名称（作为元数据标签）或默认欢迎语

**`src/locales/langs/zh-CN/workspace.json`：**
- 去掉 `currentTeam`、`currentTeamProject` keys（或标记废弃）

**`src/locales/langs/en-US/workspace.json`：**
- 同上

---

## 4. 不做的事

- 不删除 `project` 相关代码（project 保留为育种项目元数据，不做权限控制）
- 不改动 `apps/breeding/`（育种模块独立演进）
- 不删除 `user_type` 和 `is_superman`（保留 Admin/Owner 区分）
- 不改变 Menu 权限系统（只去掉 team 维度的菜单过滤）

---

## 5. 文件变更清单

### 新建

| 文件 | 职责 |
|------|------|
| Migration 文件 | Alembic migration 删除 team 列和表 |

### 修改（后端 ~15 文件）

| 文件 | 改动 |
|------|------|
| `apps/datasets/services.py` | 简化 `_can_access_dataset`，去掉 team 过滤 |
| `apps/databases/api/database.py` | 去掉 team_id 过滤 |
| `apps/databases/api/database_files.py` | 去掉 team_id 过滤 |
| `apps/gene/api/gene_set.py` | 去掉 team_id 过滤 |
| `apps/gene/crud.py` | 去掉 team_id 参数 |
| `apps/platform/api/news.py` | 去掉 team_id 过滤 |
| `apps/services/rbd.py` | 简化 RBAC 查询 |
| `apps/common/depends.py` | 简化 auth 依赖链 |
| `apps/auth/login.py` | 登录响应去掉 team/project |
| `apps/auth/menus.py` | 菜单去掉 team 过滤 |
| `apps/services/auth_key_service.py` | Auth key 格式变更 |
| `apps/system/api/project.py` | 去掉 team 过滤 |
| `apps/system/api/users.py` | Auth key 去掉 team 过滤 |
| `apps/datasets/dataset_model.py` | 去掉 team_id 列 |
| `apps/databases/models.py` | 去掉 team_id 列 |

### 删除（后端）

| 文件/目录 | 说明 |
|-----------|------|
| `apps/system/team/` | 整个 team 模块 |
| `apps/system/router.py` 中 team 路由注册 | 去掉挂载 |
| `system_team` + 3 张 link 表 | DB migration |

### 修改（前端 ~10 文件）

| 文件 | 改动 |
|------|------|
| `src/api/apps/dataset.ts` | 去掉 team_id 字段 |
| `src/api/apps/geneset.ts` | 去掉 team_id 字段 |
| `src/api/system/user.ts` | 去掉 team_id 字段 |
| `src/api/platform/news.ts` | 去掉 team_id 字段 |
| `src/store/modules/project.ts` | 去掉 teamInfo |
| `src/store/auth.ts` | 登录流程去掉 team 处理 |
| `src/layouts/basic.vue` | 去掉 Team 切换器 |
| `src/views/dashboard/workspace/index.vue` | 去掉 team name 显示 |
| `src/locales/langs/zh-CN/workspace.json` | 清理 team 相关 i18n |
| `src/locales/langs/en-US/workspace.json` | 同上 |

### 删除（前端）

| 文件/目录 | 说明 |
|-----------|------|
| `src/views/system/team/` | Team 管理页面 |
| `src/api/system/team.ts` | Team API 模块 |
| `src/layouts/project.vue` | Project 选择器 |

