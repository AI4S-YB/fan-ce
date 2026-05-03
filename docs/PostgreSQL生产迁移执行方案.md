# PostgreSQL 生产迁移执行方案

本文档对应当前仓库已经完成的代码侧收口工作，目标是把“代码已经切到 PostgreSQL”推进到“生产数据和上线流程也完成切换”。

适用范围：

- 主业务数据库从 MySQL 一次性迁移到 PostgreSQL
- 当前仓库 ORM 已定义的主业务表
- 不包含文件型 SQLite 数据

相关脚本：

- [migrate_mysql_to_pgsql.py](/Users/kentnf/projects/fan-ce/scripts/db/migrate_mysql_to_pgsql.py)

---

## 1. 当前策略

当前仓库运行时已经不再依赖 MySQL 驱动，因此迁移策略采用：

- 应用运行时只保留 PostgreSQL
- 数据迁移阶段临时通过外部 SQLAlchemy MySQL URL 连接旧库
- 迁移脚本只作为一次性运维工具，不把 MySQL 驱动重新带回主应用依赖

迁移脚本提供三个子命令：

- `plan`
- `copy`
- `verify`

对应三个阶段：

1. 盘点源库和目标库可迁移表
2. 按表把数据从 MySQL 复制到 PostgreSQL
3. 通过行数校验确认迁移结果

---

## 2. 迁移前准备

### 2.1 准备 PostgreSQL 目标库

要求：

- PostgreSQL 实例已创建
- 目标数据库已创建
- 仓库 schema 已提前建好

目标配置默认读取：

- [config.prod.yaml](/Users/kentnf/projects/fan-ce/backend/api-server/conf/config.prod.yaml)

如果不想走配置文件，也可以直接传：

- `--target-url`

### 2.2 准备 MySQL 源库访问

迁移脚本不内置 MySQL 驱动，因此执行环境需要自行满足 SQLAlchemy MySQL URL 可用。

例如：

```bash
export MYSQL_SOURCE_URL='mysql+pymysql://user:password@127.0.0.1:3306/fan_api_poc'
```

如果执行环境使用其他 MySQL DBAPI，也可以替换为对应 URL。

### 2.3 做迁移前备份

正式执行前至少保留两份备份：

1. MySQL 全库备份
2. PostgreSQL 目标库迁移前快照

建议命令示例：

```bash
mysqldump --single-transaction --routines --triggers fan_api_poc > mysql-pre-migration.sql
pg_dump -Fc -d "postgresql://fan_api:***@127.0.0.1:5432/fan_api_poc" -f pg-pre-migration.dump
```

---

## 3. 执行步骤

### 3.1 盘点迁移范围

先看哪些 ORM 表同时存在于源 MySQL 和目标 PostgreSQL：

```bash
python scripts/db/migrate_mysql_to_pgsql.py plan --with-counts
```

如果要限制表范围：

```bash
python scripts/db/migrate_mysql_to_pgsql.py \
  --tables system_users,system_role,system_menu,dataset_registry,dataset_version \
  plan --with-counts
```

这个阶段要确认两件事：

- 目标库 schema 已经齐全
- 需要迁移的表都能在源库中找到

### 3.2 执行复制

首次迁移建议在空 PostgreSQL 库上执行：

```bash
python scripts/db/migrate_mysql_to_pgsql.py copy --truncate-target
```

如果只迁移部分表：

```bash
python scripts/db/migrate_mysql_to_pgsql.py \
  --tables system_users,system_role,system_menu,dataset_registry,dataset_version \
  copy --truncate-target
```

脚本行为：

- 只迁移 ORM 已知且源库存在的表
- 按批次插入 PostgreSQL
- 默认批次大小 `1000`
- 完成后自动重置 PostgreSQL 自增序列

### 3.3 做迁移后校验

```bash
python scripts/db/migrate_mysql_to_pgsql.py verify
```

输出为逐表行数比对：

- `OK` 表示源库和目标库行数一致
- `MISMATCH` 表示需要进一步排查

---

## 4. 建议的上线切换顺序

建议按这个顺序收口：

1. 冻结 MySQL 写流量
2. 执行最后一次增量或全量迁移
3. 跑 `verify`
4. 用 PostgreSQL 配置启动后端并做 smoke test
5. 切换应用流量到 PostgreSQL
6. 保留 MySQL 只读观察窗口
7. 观察无误后下线 MySQL 主业务角色

推荐 smoke test 范围：

- 登录与权限查询
- Dataset 列表/详情
- 版本发布与撤回
- public 查询
- ingest 任务查询
- Kafka metadata 相关接口

---

## 5. 回滚策略

如果迁移或切换失败，回滚原则是：

- 应用立刻切回旧 MySQL 版本或旧环境
- PostgreSQL 迁移结果直接丢弃，不做反向写回
- 重新核对差异后再发起下一次迁移窗口

回滚前提：

- MySQL 冻结窗口内没有恢复写入
- 已保留 MySQL 迁移前备份
- PostgreSQL 只是候选目标，还未成为唯一写库

这意味着生产切换阶段应坚持：

- 不做双写
- 不做 MySQL 与 PostgreSQL 长期并行写入
- 切换窗口内保证唯一写入口

---

## 6. 已知限制

当前脚本做的是“通用表复制”，不是业务语义级迁移框架，因此有几个边界：

- 校验目前以行数为主，不做逐字段 diff
- 目标 schema 必须提前建好
- 源库如果有仓库 ORM 未覆盖的历史表，脚本不会迁移
- 非结构化文件内容和 SQLite 数据不在本次迁移范围内

如果后续需要更严格的上线保障，下一步应补：

- 逐表主键抽样校验
- 关键业务表 checksum 校验
- 切换窗口的增量迁移策略
- 自动化 smoke test 脚本
