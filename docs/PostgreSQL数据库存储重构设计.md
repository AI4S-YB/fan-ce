# PostgreSQL 数据库存储重构设计

## 1. 目的

本文档用于指导当前项目从“旧 MySQL 资产模型”迁移到“面向组学 Dataset 平台的 PostgreSQL 存储模型”。

本次重构目标不是机械地把 MySQL 表搬到 PostgreSQL，而是：

- 参考旧表结构中仍然有价值的业务语义
- 结合已经确认的新 `dataset / version / asset / file / lineage` 设计
- 重新设计一版更适合 PostgreSQL 的正式存储模型

## 2. 当前代码库数据库配置现状

当前代码库的数据库配置链路如下：

- 环境配置入口：
  - [core/config.py](/Users/kentnf/projects/fan-ce/backend/api-server/core/config.py)
- 开发环境配置文件：
  - [conf/config.dev.yaml](/Users/kentnf/projects/fan-ce/backend/api-server/conf/config.dev.yaml)
- 数据库分支选择：
  - [db/database.py](/Users/kentnf/projects/fan-ce/backend/api-server/db/database.py)

当前结论：

- 当前 `dev` 环境默认读取 `config.dev.yaml`
- `config.dev.yaml` 里 `database.type = pgsql`
- `config.prod.yaml` 和 `config.example.yaml` 也已经切到 `pgsql`
- 目前代码只支持：
  - `pgsql`
  - `sqlite`
- 主数据库运行入口已经不再保留 MySQL 运行分支

也就是说：

- 当前主运行态数据库已经切到 PostgreSQL
- 本地开发默认使用 Docker PostgreSQL
- SQLite 仅作为 PostgreSQL 不可用时的本地兜底
- Kafka metadata 旁路也已复用主数据库 engine，不再单独绑定 MySQL
- 当前剩余迁移工作主要集中在兼容别名、过期生成物和后续生产数据迁移，而不再是主运行链路仍依赖 MySQL

## 3. 旧 MySQL 时代能从代码中推断出的核心表

以下内容不是完整生产库 DDL，而是根据 ORM 模型反推出的“当前后端仍依赖的核心事实表”。

## 3.1 旧资产主线

来自 [apps/databases/models.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/databases/models.py)：

### `databases`

语义：

- 旧时代的数据资产主表

关键字段：

- `id`
- `name`
- `user_id`
- `type`
- `status`
- `is_public`
- `is_active`
- `is_delete`
- `create_time`
- `remark`
- `team_id`

问题：

- 同时承载了资产、发布、团队归属、展示等多种语义
- 无法表达多版本
- 无法表达多文件

### `databases_file`

语义：

- 旧时代一条资产挂一个主文件

关键字段：

- `id`
- `uid`
- `size`
- `name`
- `file_name`
- `url`
- `path`
- `type`
- `data_type`
- `database_id`
- `status`
- `create_time`
- `meta_json`

问题：

- 仍然是“单文件中心”
- 无法正式表达索引文件、派生文件、多文件关系

### `databases_metadata`

语义：

- 旧时代数据库资产挂接的键值型元数据

关键字段：

- `id`
- `key`
- `value`
- `code`
- `type`
- `description`
- `create_time`
- `database_id`

问题：

- 更像松散标签表
- 适合保留“扩展元数据”思路，但不适合承载主业务结构

### `project_database`

语义：

- 项目与数据资产的关联表

关键字段：

- `id`
- `database_id`
- `project_id`

这个表的价值仍然存在，因为新模型依然需要：

- 数据与项目关联
- 项目内权限与可见范围控制

## 3.2 旧组织与权限上下文

来自：

- [apps/system/team/models.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/system/team/models.py)
- [apps/system/project/models.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/system/project/models.py)
- [apps/system/user/models.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/system/user/models.py)
- [apps/system/rbac/models.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/system/rbac/models.py)

核心表包括：

- `system_users`
- `system_role`
- `system_permission`
- `system_team`
- `system_team_user`
- `system_team_project`
- `system_team_role`
- `system_project`
- `system_project_meta`

这些表说明：

- 当前系统不是单纯“用户拥有数据”
- 而是“用户 - 团队 - 项目 - 角色”四层上下文共同决定权限

因此 PostgreSQL 重构时，不应把 Dataset 平台重新做成只面向用户的平面权限模型。

## 3.3 当前新增但仍属兼容层的 Dataset 表

来自 [apps/datasets/models.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/datasets/models.py)：

- `dataset_registry`
- `dataset_workflow_task`
- `dataset_publish_record`
- `dataset_version`
- `dataset_asset`
- `asset_file`
- `dataset_lineage_edge`
- `dataset_version_publish_record`

当前状态：

- `dataset_registry` 仍是兼容聚合视图
- `dataset_version` 已经承载部分工作版本语义
- `dataset_asset / asset_file / dataset_lineage_edge` 是本轮开始落地的新正式主线

## 4. PostgreSQL 重构的设计原则

### 4.1 不再以 `databases` 为主事实表

MySQL 时代的 `databases` 语义过重，只适合作为旧系统兼容来源。

PostgreSQL 时代建议：

- `dataset` 成为正式主事实表
- 旧 `databases` 可通过迁移映射进入新模型

### 4.2 不再以单文件为中心

核心关系应变为：

```text
dataset
  -> dataset_version
    -> dataset_asset
      -> asset_file
```

### 4.3 用 PostgreSQL 的类型能力增强约束

相比旧 MySQL 设计，PostgreSQL 建议更积极使用：

- `bigserial` / `bigint`
- `uuid`
- `jsonb`
- `timestamptz`
- 唯一索引
- 部分索引
- 外键
- 检查约束

### 4.4 平台级配置与业务数据分层

建议区分：

- 平台治理表
- 组织权限表
- Dataset 业务表
- 工作流/审计表

## 5. PostgreSQL 推荐逻辑分层

建议 PostgreSQL 中逻辑上分为四组表。

### 5.1 身份与组织层

沿用旧系统的核心组织模型：

- `system_users`
- `system_role`
- `system_permission`
- `system_team`
- `system_team_user`
- `system_team_project`
- `system_team_role`
- `system_project`
- `system_project_meta`

建议：

- 这一层先尽量兼容旧结构
- 不作为本次 Dataset 重构的首要改造对象

### 5.2 类型注册与平台治理层

建议新增：

- `dataset_kind_registry`
- `asset_type_registry`

说明：

- 这是 PostgreSQL 重构中真正新增的“平台内核配置”
- 只有系统管理员可以维护

### 5.3 Dataset 业务层

建议正式主表：

- `dataset`
- `dataset_version`
- `dataset_asset`
- `asset_file`
- `dataset_lineage_edge`

### 5.4 控制与审计层

建议正式控制表：

- `dataset_workflow_run`
- `dataset_workflow_task`
- `dataset_release_record`
- `dataset_acl_binding`

第一阶段可继续部分复用已有：

- `dataset_workflow_task`
- `dataset_publish_record`
- `dataset_version_publish_record`

## 6. PostgreSQL 正式主模型

## 6.1 `dataset`

作用：

- 逻辑数据集主表

建议字段：

- `id bigint primary key generated always as identity`
- `dataset_code varchar(128) not null unique`
- `name varchar(255) not null`
- `title varchar(255)`
- `dataset_kind_code varchar(128) not null`
- `dataset_kind_base_code varchar(128) not null`
- `summary text`
- `organism_id bigint`
- `organism_name varchar(255)`
- `owner_team_id bigint`
- `owner_project_id bigint`
- `current_version_id bigint`
- `default_public_version_id bigint`
- `status varchar(32) not null default 'active'`
- `meta_json jsonb`
- `create_user_id bigint`
- `create_time timestamptz not null default now()`
- `update_time timestamptz not null default now()`

建议索引：

- `uk_dataset_code`
- `idx_dataset_kind_base_code`
- `idx_dataset_owner_team`
- `idx_dataset_owner_project`

## 6.2 `dataset_version`

作用：

- 数据集版本主表

建议字段：

- `id bigint primary key generated always as identity`
- `dataset_id bigint not null references dataset(id)`
- `version_code varchar(128) not null`
- `version_name varchar(255) not null`
- `version_label varchar(255)`
- `workflow_state varchar(32) not null`
- `visibility_scope varchar(32) not null`
- `release_state varchar(32) not null`
- `is_current boolean not null default false`
- `is_default_public boolean not null default false`
- `assembly_name varchar(255)`
- `annotation_version varchar(255)`
- `source_type varchar(64)`
- `source_note text`
- `meta_json jsonb`
- `create_user_id bigint`
- `create_time timestamptz not null default now()`
- `update_time timestamptz not null default now()`

建议约束：

- `unique(dataset_id, version_code)`

建议 PostgreSQL 特有索引：

- 部分唯一索引：
  - `unique(dataset_id) where is_current = true`
  - `unique(dataset_id) where is_default_public = true`

说明：

- 这正适合 PostgreSQL，不必完全依赖应用层兜底

## 6.3 `dataset_asset`

作用：

- 版本下的一类业务资产

建议字段：

- `id bigint primary key generated always as identity`
- `dataset_version_id bigint not null references dataset_version(id)`
- `asset_code varchar(128) not null`
- `asset_name varchar(255) not null`
- `asset_type_code varchar(128) not null`
- `asset_type_base_code varchar(128) not null`
- `file_format varchar(64)`
- `query_engine varchar(128)`
- `storage_backend varchar(64)`
- `workflow_state varchar(32) not null`
- `status varchar(32) not null default 'active'`
- `is_required boolean not null default true`
- `is_query_entry boolean not null default false`
- `display_order integer not null default 0`
- `meta_json jsonb`
- `create_time timestamptz not null default now()`
- `update_time timestamptz not null default now()`

建议约束：

- `unique(dataset_version_id, asset_code)`

建议 PostgreSQL 特有索引：

- 部分唯一索引：
  - `unique(dataset_version_id) where is_query_entry = true`

说明：

- 第一阶段建议每个版本最多只有一个默认查询入口资产

## 6.4 `asset_file`

作用：

- 资产关联的物理文件表

建议字段：

- `id bigint primary key generated always as identity`
- `dataset_asset_id bigint not null references dataset_asset(id)`
- `file_role varchar(32) not null`
- `file_name varchar(255) not null`
- `storage_uri text not null`
- `local_path text`
- `file_format varchar(64)`
- `mime_type varchar(128)`
- `checksum_type varchar(32)`
- `checksum_value varchar(255)`
- `file_size bigint`
- `compress_type varchar(32)`
- `index_of_file_id bigint references asset_file(id)`
- `status varchar(32) not null default 'active'`
- `meta_json jsonb`
- `create_time timestamptz not null default now()`
- `update_time timestamptz not null default now()`

建议索引：

- `idx_asset_file_asset_id`
- `idx_asset_file_role`
- `idx_asset_file_index_of_file_id`
- `uk_asset_file_storage_uri`

## 6.5 `dataset_lineage_edge`

作用：

- 版本或资产之间的血缘边

建议字段：

- `id bigint primary key generated always as identity`
- `src_dataset_version_id bigint references dataset_version(id)`
- `src_asset_id bigint references dataset_asset(id)`
- `dst_dataset_version_id bigint references dataset_version(id)`
- `dst_asset_id bigint references dataset_asset(id)`
- `relation_type varchar(64) not null`
- `direction varchar(16) not null default 'forward'`
- `detail_json jsonb`
- `create_user_id bigint`
- `create_time timestamptz not null default now()`

建议约束：

- 第一阶段至少要求：
  - `src_dataset_version_id` 或 `dst_dataset_version_id` 不能同时为空

建议说明：

- 第一阶段优先支持版本级血缘
- 第二阶段再增强为资产级精细血缘

## 7. 类型注册表设计

## 7.1 `dataset_kind_registry`

建议字段：

- `id bigint primary key generated always as identity`
- `code varchar(128) not null unique`
- `name varchar(255) not null`
- `base_code varchar(128) not null`
- `builtin boolean not null default false`
- `status varchar(32) not null default 'active'`
- `scope varchar(32) not null default 'system'`
- `display_order integer not null default 0`
- `description text`
- `metadata_schema_json jsonb`
- `create_time timestamptz not null default now()`
- `update_time timestamptz not null default now()`

## 7.2 `asset_type_registry`

建议字段：

- `id bigint primary key generated always as identity`
- `code varchar(128) not null unique`
- `name varchar(255) not null`
- `base_code varchar(128) not null`
- `builtin boolean not null default false`
- `status varchar(32) not null default 'active'`
- `scope varchar(32) not null default 'system'`
- `description text`
- `allowed_formats_json jsonb`
- `default_query_adapter varchar(128)`
- `default_index_profile varchar(128)`
- `is_queryable boolean not null default true`
- `metadata_schema_json jsonb`
- `create_time timestamptz not null default now()`
- `update_time timestamptz not null default now()`

## 7.3 权限规则

类型注册表维护权限建议明确为：

- 系统管理员：可增删改停用
- 团队管理员：无权限
- 普通用户：无权限

## 8. 权限与可见性存储

基于你已经确认的方向，第一阶段建议：

- `dataset` 为主
- `dataset_version` 覆盖
- `dataset_asset` 级权限预留但不全面启用

建议新增：

### `dataset_acl_binding`

字段建议：

- `id bigint primary key generated always as identity`
- `resource_type varchar(32) not null`
- `resource_id bigint not null`
- `subject_type varchar(32) not null`
- `subject_id bigint not null`
- `permission_code varchar(128) not null`
- `effect varchar(16) not null default 'allow'`
- `create_time timestamptz not null default now()`
- `update_time timestamptz not null default now()`

资源类型第一阶段建议仅启用：

- `dataset`
- `dataset_version`

## 9. 工作流与发布审计存储

建议保留并 PostgreSQL 化：

### `dataset_workflow_task`

建议字段：

- `id bigint primary key generated always as identity`
- `dataset_id bigint`
- `dataset_version_id bigint`
- `dataset_asset_id bigint`
- `task_type varchar(64) not null`
- `task_status varchar(32) not null`
- `workflow_state_before varchar(32)`
- `workflow_state_after varchar(32)`
- `operator_id bigint`
- `detail text`
- `log_uri text`
- `create_time timestamptz not null default now()`
- `finish_time timestamptz`

### `dataset_release_record`

建议字段：

- `id bigint primary key generated always as identity`
- `dataset_id bigint not null`
- `dataset_version_id bigint not null`
- `action varchar(32) not null`
- `visibility_before varchar(32)`
- `visibility_after varchar(32)`
- `release_state_before varchar(32)`
- `release_state_after varchar(32)`
- `operator_id bigint`
- `note text`
- `create_time timestamptz not null default now()`

## 10. 旧表到新表的映射建议

## 10.1 `databases` 到 `dataset`

旧字段映射建议：

| 旧表字段 | 新表字段 | 说明 |
| --- | --- | --- |
| `databases.id` | `legacy_database_id` 或迁移映射表 | 不建议继续作为正式主键语义 |
| `name` | `dataset.name` / `dataset.title` | 迁移时需区分内部名和展示名 |
| `type` | `dataset_kind_code/base_code` | 需要重新归类 |
| `team_id` | `owner_team_id` | 可直接映射 |
| `is_public` | 不直接沿用 | 改由 `dataset_version.visibility_scope + release_state` 承载 |

建议新增一张兼容映射表：

### `legacy_database_map`

- `id`
- `legacy_database_id`
- `dataset_id`
- `migrate_status`
- `create_time`

## 10.2 `databases_file` 到 `asset_file`

旧字段映射建议：

| 旧表字段 | 新表字段 |
| --- | --- |
| `path` | `asset_file.local_path` |
| `url` | `asset_file.storage_uri` |
| `type` | `asset_file.file_format` |
| `size` | `asset_file.file_size` |
| `meta_json` | `asset_file.meta_json` |

同时新增：

- `dataset_asset`
- `file_role`
- `index_of_file_id`

## 10.3 `project_database` 到 Dataset 项目归属

建议保留“数据与项目可关联”的思路，但在新模型里改成以下两层：

- `dataset.owner_project_id`
- 如有一对多需要，再补 `dataset_project_link`

第一阶段如果平台要求一个数据集只属于一个主项目，可先不单独建 link 表。

## 11. 为什么 PostgreSQL 更适合这次重构

原因主要有五点：

- 更适合做复杂唯一约束，例如“同一个 dataset 只有一个默认公开版本”
- 更适合做 `jsonb` 元数据和 schema-less 扩展字段
- 更适合做部分索引和复杂过滤
- 更适合未来支持血缘查询和图状关系的递归查询
- 更适合把 MySQL 时代松散的布尔/状态语义收敛为更严格的约束

## 12. 第一阶段 PostgreSQL 实施建议

建议第一阶段按下面顺序推进：

1. 新增 PostgreSQL 连接分支
   - `database.type = pgsql`
2. 定义 PostgreSQL 新模型
   - 先不删除 MySQL 兼容模型
3. 建 `dataset / dataset_version / dataset_asset / asset_file / dataset_lineage_edge`
4. 补 `dataset_kind_registry / asset_type_registry`
5. 建 `legacy_database_map`
6. 写迁移脚本，把旧 `databases` 和 `databases_file` 导入新模型
7. 新接口优先读 PostgreSQL 新表
8. 旧接口在兼容期继续做映射读取

## 13. 直接结论

对于当前项目，建议不要再延续 MySQL 时代的以下模式：

- `databases` 单表扛全部语义
- `databases_file` 单文件中心模型
- `is_public` 作为唯一公开事实源

建议 PostgreSQL 正式主干改为：

```text
dataset
dataset_version
dataset_asset
asset_file
dataset_lineage_edge
dataset_kind_registry
asset_type_registry
dataset_acl_binding
dataset_workflow_task
dataset_release_record
legacy_database_map
```

这才是更适合你当前组学平台目标的正式数据库存储模型。
