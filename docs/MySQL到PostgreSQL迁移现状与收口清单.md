# MySQL 到 PostgreSQL 迁移现状与收口清单

本文档用于基于当前仓库代码快照，回答三个问题：

1. 系统主数据库现在是不是 PostgreSQL
2. 还剩哪些 MySQL 遗留没有清掉
3. 下一步应该如何持续推进

说明：

- 本文档只讨论系统主业务数据库迁移
- `sqlite` 仍保留为本地兜底和文件型数据处理能力，不属于本次主数据库迁移范围
- 本文档反映的是仓库当前代码状态，不直接等同于线上环境已经完成同样切换

---

## 1. 当前结论

截至当前代码状态，系统主运行链路已经完成从 MySQL 到 PostgreSQL 的切换。

更准确地说：

- 开发配置默认使用 PostgreSQL
- 生产示例配置也已经切到 PostgreSQL
- 主数据库运行入口只保留 `pgsql` 和 `sqlite`
- Kafka metadata 旁路也已经不再直接绑定 MySQL
- `pymysql` 和 MySQL 运行时代码已经从主代码路径移除

因此当前状态应定义为：

```text
主业务数据库：PostgreSQL
本地文件型/兜底：SQLite
MySQL 状态：已退出主运行链路，仅剩少量历史命名和生成物待清理
```

---

## 2. 已经完成的迁移项

### 2.1 运行配置已切到 PostgreSQL

当前以下配置都已明确使用 `pgsql`：

- `backend/api-server/conf/config.dev.yaml`
- `backend/api-server/conf/config.prod.yaml`
- `backend/api-server/conf/config.example.yaml`

现状：

- `database.type` 已统一为 `pgsql`
- 连接参数改为 `pgsql_options`
- 主配置层已不再要求 `mysql_options`

这意味着配置认知已经从“双栈”切为“PostgreSQL 主库”。

### 2.2 主数据库入口已移除 MySQL 运行分支

当前入口文件：

- `backend/api-server/db/database.py`

当前只保留两类数据库分支：

- `pgsql`
- `sqlite`

这意味着：

- 主业务系统不再支持以 MySQL 作为正式运行分支启动
- 非法 `database.type` 会直接抛出异常，而不是悄悄回退到 MySQL

### 2.3 PostgreSQL 驱动已成为唯一主库驱动

当前依赖文件：

- `backend/api-server/pyproject.toml`

现状：

- 保留 `psycopg[binary]`
- 已移除 `pymysql`

锁文件也已同步更新：

- `backend/api-server/uv.lock`

### 2.4 Kafka metadata 旁路已切到主数据库 engine

当前相关文件：

- `backend/api-server/kafka/config.py`
- `backend/api-server/kafka/metadata_repository.py`

现状：

- `get_database_config()` 不再只读取 `mysql_options`
- `MetadataRepository` 不再依赖 `MySQLTool`
- metadata 读写改为复用 `db.database.engine`
- 当前可跟随主库配置运行在 PostgreSQL，保留 SQLite 兼容

这是本次迁移里最关键的旁路收口点之一，因为它解决了“主业务已上 PostgreSQL，但 Kafka metadata 仍绑 MySQL”的结构性问题。

### 2.5 服务部署描述已切到 PostgreSQL

当前：

- `backend/api-server/conf/service/hytcloud.service`

现状：

- `After=network.target postgresql.service`

说明部署层脚本默认假设已经切换到 PostgreSQL，而不是继续等待 `mysqld.target`。

### 2.6 活跃查询基础层已完成去 MySQL 命名

当前：

- `backend/api-server/libs/filter/filters.py`
- `backend/api-server/libs/filter/__init__.py`
- `backend/api-server/db/base.py`

现状：

- 活跃调用方已改为使用 `apply_filters`
- `libs/filter/mysql.py` 已删除

这一步不改变行为，但把主调用路径从 MySQL 命名中解耦出来，避免后续设计讨论和新代码继续沿用旧概念。

### 2.7 已移除的 MySQL 旧代码

当前已删除：

- `backend/api-server/db/mysqlorm/connect.py`
- `backend/api-server/db/mysqlorm/__init__.py`
- `backend/api-server/utils/mpysql/mysql.py`
- `backend/api-server/utils/mpysql/__init__.py`
- `backend/api-server/libs/filter/mysql.py`

这些文件的删除意味着：

- MySQL ORM 接入层已经不再保留
- Kafka 的 MySQL 小工具已经退出代码库
- 基础过滤层不再通过单独的 MySQL 模块暴露

---

## 3. 当前还剩的遗留项

### 3.1 文档与外部集成仍可能提及旧 MySQL 名称

当前仓库内的 MySQL 关键字命中，已经主要来自：

- 本迁移说明文档自身
- 一次性迁移脚本和迁移执行文档
- 历史设计文档中对旧系统的描述

也就是说，当前剩余痕迹已经主要是说明性内容，而不是运行依赖。

如果后续要做到“仓库内关键字几乎清零”，可以继续：

- 随设计文档演进逐步减少对历史名称的引用

### 3.2 线上部署与真实数据迁移仍需单独执行

代码切换完成，不等于线上环境自动完成迁移。

如果目标是最终生产收口，仍需要单独确认：

- PostgreSQL 生产实例已就位
- 生产配置已同步更新
- MySQL 历史数据已完成迁移或冻结
- 运维脚本、备份、监控、巡检已经切到 PostgreSQL

这部分是交付与上线问题，不是仓库代码层面的问题。

---

## 4. 当前状态分层判断

如果按层次划分，当前迁移状态可以概括为：

### 4.1 已完成

- 主配置层切到 PostgreSQL
- 主数据库入口移除 MySQL 运行分支
- PostgreSQL 驱动成为唯一主库驱动
- Kafka metadata 旁路不再依赖 MySQL
- 服务依赖声明切到 PostgreSQL

### 4.2 已基本完成，但还可继续收口

- 基础过滤层已切到中性命名
- 设计文档已基本与实现对齐，但仍需随后续数据库演进持续维护

### 4.3 尚需在上线层继续收口

- 制定并执行生产数据迁移方案
- 复核部署、备份、监控、巡检链路是否已经完全切到 PostgreSQL

---

## 5. 建议的下一步

建议按以下顺序推进：

1. 制定生产 MySQL 到 PostgreSQL 的数据迁移和回滚方案
2. 对接线上配置、备份、监控和运维脚本的 PostgreSQL 化收口
3. 继续推进 Dataset 平台 backlog 中剩余的功能项

如果只从“代码主运行链路是否已迁到 PostgreSQL”这个问题来回答，当前答案已经是：

```text
是，已经迁到 PostgreSQL。
```

如果从“仓库里是否已经完全没有任何 MySQL 痕迹”这个问题来回答，当前答案则是：

```text
还没有完全清零，但剩余部分已经主要是兼容命名和历史说明，而不是主运行依赖。
```
