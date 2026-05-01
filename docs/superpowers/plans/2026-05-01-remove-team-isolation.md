# 去掉 Team 多租户隔离 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将系统从多 Team 多租户隔离转为社区版单租户架构，Team 概念完全移除，权限简化为 Admin/Owner/public 三级。

**Architecture:** 分 8 个任务。后端 6 个（权限核心 → 各模块清理 → RBAC/Auth → Auth Key → Schema → Migration），前端 2 个（API 类型 + Store → UI 删除 + 工作台更新）。

**Tech Stack:** FastAPI + SQLAlchemy + PostgreSQL + Alembic（后端），Vue 3 + Pinia + TypeScript（前端）

---

## 文件结构

**后端修改（~12 个源文件）：**

```
apps/datasets/services.py              # 核心权限逻辑简化
apps/databases/api/database.py         # 去掉 team_id 过滤
apps/gene/api/gene_set.py              # 去掉 team_id 过滤
apps/gene/crud.py                      # 去掉 team_id 参数
apps/platform/api/news.py              # 去掉 team_id 过滤
apps/services/rbd.py                   # RBAC 简化
apps/common/depends.py                 # Auth 依赖链简化
apps/auth/login.py                     # 登录响应清理
apps/auth/menus.py                     # 菜单清理
apps/services/auth_key_service.py      # Auth key 格式变更
apps/system/api/project.py             # 去掉 team 过滤
apps/system/api/users.py               # Auth key 去掉 team 过滤
```

**后端 Schema 修改（~5 个文件）：**

```
apps/databases/schemas.py
apps/gene/schemas.py
apps/platform/schemas.py
apps/datasets/schemas.py（DatasetListRequest）
apps/system/user/schemas.py（AuthKeyCreateRequest, AuthKeyListRequest）
```

**后端删除：**

```
apps/system/team/                      # 整个模块（models, schemas, crud, api, routers）
apps/system/router.py 中 team 路由注册
system_team / team_user_link / team_project_link / team_role_link 表（migration）
```

**前端修改（~5 个源文件）：**

```
src/api/apps/dataset.ts                # 去掉 team_id
src/api/apps/geneset.ts                # 去掉 team_id
src/api/system/user.ts                 # 去掉 team_id
src/store/modules/project.ts           # 去掉 teamInfo
src/store/auth.ts                      # 登录流程去掉 team
```

**前端删除：**

```
src/views/system/team/                 # Team 管理页
src/api/system/team.ts                 # Team API
src/layouts/project.vue                # Project 选择器
```

**前端 UI 修改（~4 个文件）：**

```
src/layouts/basic.vue                  # 去掉 Team 切换器
src/views/dashboard/workspace/index.vue # 去掉 team name
src/locales/langs/zh-CN/workspace.json  # 清理 team i18n
src/locales/langs/en-US/workspace.json  # 清理 team i18n
```

---

### Task 1: 简化 datasets 核心权限逻辑

**Files:**
- Modify: `backend/api-server/apps/datasets/services.py`

- [ ] **Step 1: 简化 `_can_access_dataset`**

删除 team/project 成员判断，改为 3 级：

```python
def _can_access_dataset(self, db, database_obj, user):
    # 1. 未认证用户 -> 允许（后续由 API 层做认证检查）
    if not user:
        return True
    # 2. 平台 admin -> 允许
    if self._is_platform_admin(user):
        return True
    # 3. 数据 owner -> 允许
    user_id = getattr(user, "id", None)
    if user_id and database_obj.user_id == user_id:
        return True
    # 4. public 数据 -> 任何认证用户可见
    if getattr(database_obj, 'is_public', False):
        return True
    # 5. 否则拒绝
    return False
```

- [ ] **Step 2: 删除 `_get_user_team_ids` 和 `_get_user_project_ids`**

删除这两个方法（第 525-553 行）。

- [ ] **Step 3: 简化 `static can_access_dataset`**

```python
@staticmethod
def can_access_dataset(*, db, dataset_visibility, dataset_team_id=None, dataset_project_id=None, user_team_ids=None, user_project_ids=None):
    if dataset_visibility == "public":
        return True
    # 社区版：不再检查 team/project 成员资格
    return False
```

- [ ] **Step 4: 修改 `list_datasets`**

将 `filters = {"team_id": request_data.team_id}` 改为 `filters = {}`（不再按 team 过滤）。

- [ ] **Step 5: 删除 `_get_dataset_project_ids` 方法**

该方法不再需要（第 555-560 行）。

- [ ] **Step 6: Commit**

```bash
git add backend/api-server/apps/datasets/services.py
git commit -m "feat: simplify dataset access control to Admin/Owner/public

Remove team and project membership checks from _can_access_dataset.
Delete _get_user_team_ids, _get_user_project_ids, _get_dataset_project_ids.
Remove team_id filter from list_datasets.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: 清理 databases, gene, platform 模块

**Files:**
- Modify: `backend/api-server/apps/databases/api/database.py`
- Modify: `backend/api-server/apps/gene/api/gene_set.py`
- Modify: `backend/api-server/apps/gene/crud.py`
- Modify: `backend/api-server/apps/platform/api/news.py`

- [ ] **Step 1: databases — 去掉 team_id 过滤**

在 `database.py` 的 `database_list` 中，将 `filters = {'team_id': request_data.team_id}` 改为 `filters = {}`。

- [ ] **Step 2: gene — 去掉 team_id 过滤**

在 `gene/api/gene_set.py` 的列表端点中，移除 `team_id` 过滤条件。在 `gene/crud.py` 中，去掉函数签名中的 `team_id` 参数。

- [ ] **Step 3: platform — 去掉 team_id 过滤**

在 `platform/api/news.py` 的 news 列表端点中，移除 `team_id` 过滤条件。

- [ ] **Step 4: Commit**

```bash
git add backend/api-server/apps/databases/api/database.py \
        backend/api-server/apps/gene/api/gene_set.py \
        backend/api-server/apps/gene/crud.py \
        backend/api-server/apps/platform/api/news.py
git commit -m "feat: remove team_id filtering from databases, gene, platform modules

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: 简化 RBAC 和 Auth 链

**Files:**
- Modify: `backend/api-server/apps/services/rbd.py`
- Modify: `backend/api-server/apps/common/depends.py`
- Modify: `backend/api-server/apps/auth/login.py`
- Modify: `backend/api-server/apps/auth/menus.py`

- [ ] **Step 1: rbd.py — 简化 `get_user_default`**

```python
@staticmethod
def get_user_default(db, user):
    if not user:
        return {'team_info': {}, 'project_info': {}}
    # 社区版：不再返回 team/project 信息
    return {'team_info': {}, 'project_info': {}}
```

- [ ] **Step 2: rbd.py — 简化 `get_user_role_info`**

去掉 `team_id` 参数，只保留系统角色：

```python
@staticmethod
def get_user_role_info(db, user, team_id=None):
    team_list = []
    # 社区版：只查系统角色，不查 team 角色
    sys_role_ids = [role.role_id for role in user_role_db.get_data(db=db, filters={'user_id': user.id})]
    role_ids = sys_role_ids
    menu_ids = [i.menu_id for i in role_menu_db.get_filter_in(db=db, name='role_id', value=role_ids)]
    permission_ids = [i.permission_id for i in menu_permission_db.get_filter_in(db=db, name='menu_id', value=menu_ids)]
    permissions = [i.code for i in permission_db.get_filter_in(db=db, name='id', value=permission_ids)]
    data = {
        'team_list': team_list, 'permissions': permissions, 'role_ids': role_ids,
        'menu_ids': menu_ids, 'project_list': [],
        'userinfo': {'id': user.id, 'user_name': user.user_name, 'nickName': 'nickName'},
        'is_superman': bool(getattr(user, 'is_superman', False)),
        'user_type': getattr(user, 'user_type', 0),
    }
    return data
```

- [ ] **Step 3: rbd.py — 简化 `get_user_menu_ids`**

去掉 team 维度的 role 查询，只保留系统角色：

```python
@staticmethod
def get_menu_ids(db, request_data, user_id):
    role_ids = [i.role_id for i in user_role_db.get_data(db=db, filters={'user_id': user_id})]
    menu_ids = [i.menu_id for i in role_menu_db.get_filter_in(db=db, name='role_id', value=role_ids)]
    return menu_ids
```

- [ ] **Step 4: rbd.py — 简化 `get_user_role_all_ids`**

去掉 team 角色收集。

- [ ] **Step 5: rbd.py — 删除 `get_project_by_team_id`**

从 `MenuService` 中删除该方法。

- [ ] **Step 6: depends.py — 简化 `get_rbd_user`**

移除 `current_user.team_list` 赋值（或设为空列表），不再调用 `team_user_role_db`。

- [ ] **Step 7: login.py — 清理登录响应**

移除登录响应中的 `team` / `project` 字段，或设为 `None`。

- [ ] **Step 8: menus.py — 去掉 `team_id` 参数**

`auth_menus()` 调用 `rbd_service.get_user_menu_ids` 时不再传 `team_id`。

- [ ] **Step 9: Commit**

```bash
git add backend/api-server/apps/services/rbd.py \
        backend/api-server/apps/common/depends.py \
        backend/api-server/apps/auth/login.py \
        backend/api-server/apps/auth/menus.py
git commit -m "feat: simplify RBAC and auth chain for single-tenant

Remove team-based role collection, menu filtering, and login response
fields. Keep system-level roles and permissions only.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Auth key 和 system API 清理

**Files:**
- Modify: `backend/api-server/apps/services/auth_key_service.py`
- Modify: `backend/api-server/apps/system/api/project.py`
- Modify: `backend/api-server/apps/system/api/users.py`

- [ ] **Step 1: auth_key_service.py — 去掉 team_id 嵌入**

生成 auth key 从 `fandb_team{team_id}_{random_16}` 改为 `fandb_{random_20}`：

```python
def generate_auth_key(self, team_id=None):
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))
    return f"fandb_{random_part}"
```

删除 `extract_team_id_from_auth_key()` 方法或将其标记为废弃返回 `None`。

`validate_auth_key()` 去掉 team 匹配检查。

- [ ] **Step 2: project.py — 去掉 team 过滤**

在 `project_list()` 中去掉 `team_id` 过滤。在 `get_project_info()` 中去掉 team 成员检查。

- [ ] **Step 3: users.py — 去掉 auth key 的 team_id 过滤**

Auth key 批量查询不再按 `team_id` 过滤用户。

- [ ] **Step 4: Commit**

```bash
git add backend/api-server/apps/services/auth_key_service.py \
        backend/api-server/apps/system/api/project.py \
        backend/api-server/apps/system/api/users.py
git commit -m "feat: remove team from auth keys and system APIs

Change auth key format to remove embedded team_id. Remove team
filtering from project list and user auth key queries.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Schema 清理 + 删除 Team 模块

**Files:**
- Modify: `backend/api-server/apps/databases/schemas.py`
- Modify: `backend/api-server/apps/gene/schemas.py`
- Modify: `backend/api-server/apps/platform/schemas.py`
- Modify: `backend/api-server/apps/datasets/schemas.py`
- Modify: `backend/api-server/apps/system/user/schemas.py`
- Modify: `backend/api-server/apps/system/router.py`
- Delete: `backend/api-server/apps/system/team/` (whole directory)

- [ ] **Step 1: 清理 Pydantic Schema — 去掉 team_id 字段**

在以下 Schema 中移除 `team_id: Optional[int] = 0` 或类似字段：
- `DatabasesListRequest`
- `GeneSetListRequest`
- `NewsListParams`, `NewsCreateType`, `NewsUpdateType`
- `DatasetListRequest`（`DatasetContext` 中的 `team_id`）
- `AuthKeyCreateRequest`, `AuthKeyListRequest`

- [ ] **Step 2: 删除 Team 模块文件和路由注册**

```bash
rm -rf backend/api-server/apps/system/team/
```

在 `backend/api-server/apps/system/router.py` 中移除 team router 的 import 和注册（`app.include_router(team_router)` 行）。

- [ ] **Step 3: Commit**

```bash
git add backend/api-server/apps/databases/schemas.py \
        backend/api-server/apps/gene/schemas.py \
        backend/api-server/apps/platform/schemas.py \
        backend/api-server/apps/datasets/schemas.py \
        backend/api-server/apps/system/user/schemas.py \
        backend/api-server/apps/system/router.py
git rm -r backend/api-server/apps/system/team/
git commit -m "feat: remove team_id from schemas and delete team module

Clean up Pydantic request models. Delete entire system/team module
(models, schemas, crud, api, routers) and its route registration.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 6: 数据库 Migration

**Files:**
- Create: `backend/api-server/alembic/versions/xxxx_remove_team_tables.py`

- [ ] **Step 1: 检查 Team 相关表名和列名**

```bash
cd backend/api-server && python3 -c "
from apps.databases.models import Databases
from apps.datasets.dataset_model import Dataset
print('databases columns:', [c.name for c in Databases.__table__.columns])
print('dataset columns:', [c.name for c in Dataset.__table__.columns])
"
```

- [ ] **Step 2: 创建 Alembic migration**

```bash
cd backend/api-server && alembic revision --autogenerate -m "remove_team_tables"
```

然后手动编辑 migration 文件的 `upgrade()` 和 `downgrade()`：

```python
def upgrade():
    # 删除 team 相关外键（如果有）
    op.drop_constraint('fk_databases_team_id', 'databases', type_='foreignkey')
    # 删除列
    op.drop_column('databases', 'team_id')
    # 删除表
    op.drop_table('system_team_user')
    op.drop_table('system_team_project')
    op.drop_table('system_team_role')
    op.drop_table('system_team')

def downgrade():
    # 社区版不做回滚（breaking change）
    pass
```

- [ ] **Step 3: 运行 migration 验证**

```bash
cd backend/api-server && alembic upgrade head
```

Expected: Migration 成功，无报错。

- [ ] **Step 4: Commit**

```bash
git add backend/api-server/alembic/versions/xxxx_remove_team_tables.py
git commit -m "feat: add migration to remove team tables and columns

Drop system_team, team_user_link, team_project_link, team_role_link
tables. Drop team_id column from databases and dataset tables.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 7: 前端 — API 类型 + Store 清理

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/api/apps/dataset.ts`
- Modify: `frontend/admin-web/apps/web-antd/src/api/apps/geneset.ts`
- Modify: `frontend/admin-web/apps/web-antd/src/api/system/user.ts`
- Modify: `frontend/admin-web/apps/web-antd/src/api/platform/news.ts`
- Modify: `frontend/admin-web/apps/web-antd/src/store/modules/project.ts`
- Modify: `frontend/admin-web/apps/web-antd/src/store/auth.ts`

- [ ] **Step 1: 清理 API type 接口中的 team_id**

在以下文件中搜索 `team_id` 字段并移除：
- `dataset.ts` — `RegisterCandidateRequest` 等接口
- `geneset.ts` — 所有含 `team_id` 的接口
- `user.ts` — `AuthKeyInfo` 等接口
- `news.ts` — `NewsCreateType`, `NewsUpdateType`, `NewsListParams`

- [ ] **Step 2: 清理 project store**

在 `project.ts` 中：
- 删除 `teamInfo` 状态
- 删除 `setTeamInfo()` action
- 删除 `fetchTeamInfo()` action
- 保留 `projectInfo`（作为元数据标签）

```typescript
// state 中删除 teamInfo
state: (): ProjectState => ({
  projectInfo: {},
  projectOptions: [],
  // teamInfo: {},   ← 删除
}),
```

- [ ] **Step 3: 清理 auth store**

在 `auth.ts` 中：
- `loginApi` 回调不再处理 `team` / `project` 返回值
- `fetchUserInfo()` 不再从 `team_list[0]` 取默认 team

```typescript
// loginApi 回调中删除:
// proStore.setTeamInfo(team || {});
// proStore.setProjectInfo(project || {});
```

- [ ] **Step 4: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/api/apps/dataset.ts \
        frontend/admin-web/apps/web-antd/src/api/apps/geneset.ts \
        frontend/admin-web/apps/web-antd/src/api/system/user.ts \
        frontend/admin-web/apps/web-antd/src/api/platform/news.ts \
        frontend/admin-web/apps/web-antd/src/store/modules/project.ts \
        frontend/admin-web/apps/web-antd/src/store/auth.ts
git commit -m "feat: remove team_id from frontend API types and stores

Clean up team_id fields from TypeScript interfaces. Remove teamInfo
from project store and team handling from auth login flow.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 8: 前端 — UI 删除 + 工作台更新

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/layouts/basic.vue`
- Modify: `frontend/admin-web/apps/web-antd/src/views/dashboard/workspace/index.vue`
- Modify: `frontend/admin-web/apps/web-antd/src/locales/langs/zh-CN/workspace.json`
- Modify: `frontend/admin-web/apps/web-antd/src/locales/langs/en-US/workspace.json`
- Delete: `frontend/admin-web/apps/web-antd/src/views/system/team/`
- Delete: `frontend/admin-web/apps/web-antd/src/api/system/team.ts`
- Delete: `frontend/admin-web/apps/web-antd/src/layouts/project.vue`

- [ ] **Step 1: 删除 Team 管理页面和 API**

```bash
rm -rf frontend/admin-web/apps/web-antd/src/views/system/team/
rm frontend/admin-web/apps/web-antd/src/api/system/team.ts
```

- [ ] **Step 2: 删除 Project 选择器**

```bash
rm frontend/admin-web/apps/web-antd/src/layouts/project.vue
```

- [ ] **Step 3: basic.vue — 删除 Team 切换器**

删除 `basic.vue` 中的 Team 下拉菜单（`<Dropdown>` / `<Menu>` 组件），以及对应的 `handleTeamSelect` 函数和 `team_list` 相关代码。

在模板中，找到类似这样的代码块并删除：
```vue
<Dropdown v-if="userStore.userInfo?.team_list?.length > 1">
  <!-- team switcher -->
</Dropdown>
```

- [ ] **Step 4: 更新 workspace/index.vue**

简化 `workspaceDescription`，去掉 team name：

```typescript
const workspaceDescription = computed(() => {
  const projectName = projectStore.getProjectInfo?.name?.trim?.();
  if (projectName) {
    return $t('workspace.currentProject', { name: projectName });
  }
  return $t('workspace.fallbackDesc');
});
```

- [ ] **Step 5: 清理 i18n**

在 `zh-CN/workspace.json` 和 `en-US/workspace.json` 中删除：
- `currentTeam`
- `currentTeamProject`

- [ ] **Step 6: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/layouts/basic.vue \
        frontend/admin-web/apps/web-antd/src/views/dashboard/workspace/index.vue \
        frontend/admin-web/apps/web-antd/src/locales/langs/zh-CN/workspace.json \
        frontend/admin-web/apps/web-antd/src/locales/langs/en-US/workspace.json
git rm -r frontend/admin-web/apps/web-antd/src/views/system/team/
git rm frontend/admin-web/apps/web-antd/src/api/system/team.ts
git rm frontend/admin-web/apps/web-antd/src/layouts/project.vue
git commit -m "feat: remove team UI components and update workspace

Delete team management pages, team API, project selector, and team
switcher from header. Update workspace description to remove team name.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 9: 集成验证

- [ ] **Step 1: 后端启动验证**

```bash
cd backend/api-server && python -c "from main import app; print('Backend imports OK')"
```

- [ ] **Step 2: 前端类型检查**

```bash
cd frontend/admin-web/apps/web-antd && pnpm run typecheck 2>&1 | tail -10
```

Expected: 无新增类型错误。

- [ ] **Step 3: 前端 dev 服务器**

```bash
cd frontend/admin-web && pnpm dev:antd
```

打开 http://127.0.0.1:5666/ ，验证：
1. 登录后 Header 不再显示 Team 切换器
2. 左侧菜单不再有 Team 管理入口
3. 探索工作台描述不再显示 team name
4. 数据集列表可见所有数据（不再仅限某个 team）
5. 切换语言后 workspace 页面文本正确
