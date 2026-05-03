# taxonomy 初始化接口与前端页面草案

## 1. 文档目标

本文档承接：

- [taxonomy安装包与系统初始化设计草案](/Users/kentnf/projects/fan-ce/docs/taxonomy安装包与系统初始化设计草案.md)
- [taxonomy安装包初始化数据库DDL草案.sql](/Users/kentnf/projects/fan-ce/docs/taxonomy安装包初始化数据库DDL草案.sql)

用于把 taxonomy 安装能力继续细化成：

- 后端接口草案
- 前端菜单与页面草图
- 路由守卫与初始化锁定规则
- 实施顺序建议

---

## 2. 前端落位建议

## 2.1 菜单结构

在现有：

- `平台管理`

下面新增一项：

- `taxonomy 初始化`

建议路由：

- `/platform/setup/taxonomy`

同时保留：

- `平台管理 -> 平台设置`

中的一个卡片入口，作为当前状态概览和跳转入口。

## 2.2 页面分工

### A. taxonomy 初始化页

路由：

- `/platform/setup/taxonomy`

作用：

- 首次启动引导
- 手工重装入口
- 进度展示主页面

### B. 平台设置页中的 taxonomy 卡片

现有页面：

- [setting.vue](/Users/kentnf/projects/fan-ce/frontend/admin-web/apps/web-antd/src/views/platform/setting.vue)

作用：

- 展示当前状态
- 显示当前版本
- 跳转到 taxonomy 初始化页

---

## 3. 后端接口草案

所有接口建议统一挂在：

- `/platform/setup/taxonomy/*`

这样语义更稳定，也方便后续扩展其他“系统初始化包”。

## 3.1 初始化状态接口

### `GET /platform/setup/status`

用途：

- 返回平台级初始化状态

返回建议：

```json
{
  "taxonomy_ready": true,
  "taxonomy_status": "ready",
  "locks": [
    {
      "lock_code": "taxonomy_required",
      "is_locked": 0,
      "reason": "taxonomy 已安装",
      "required_action": "install_taxonomy"
    }
  ]
}
```

说明：

- 这个接口用于前端全局路由守卫
- 不只服务 taxonomy 页

## 3.2 当前 taxonomy 状态接口

### `GET /platform/setup/taxonomy/current`

用途：

- 返回当前 taxonomy 安装状态

返回建议：

```json
{
  "ready": true,
  "status": "ready",
  "current_package": {
    "id": 12,
    "package_code": "builtin-taxonomy-2026-04-05",
    "package_type": "taxonomy_bundle",
    "source": "builtin",
    "source_version": "2026-04-05"
  },
  "current_snapshot": {
    "id": 2,
    "source_name": "ncbi_new_taxdump",
    "source_version": "2026-04-05",
    "node_count": 2735827,
    "name_count": 3212928,
    "loaded_at": "2026-04-05T22:49:05+08:00"
  },
  "latest_job": {
    "id": 18,
    "status": "success",
    "stage": "completed",
    "progress_percent": 100
  }
}
```

## 3.3 安装包列表接口

### `GET /platform/setup/taxonomy/packages`

用途：

- 返回可用安装包列表

返回重点：

- 系统内置包
- 用户上传包
- 当前推荐包

## 3.4 注册内置包接口

### `POST /platform/setup/taxonomy/package/register-builtin`

输入建议：

```json
{
  "package_code": "builtin-taxonomy-2026-04-05",
  "package_name": "FAN taxonomy bundle 2026-04-05",
  "package_type": "taxonomy_bundle",
  "storage_path": "/opt/fan-ce/packages/taxonomy/fan-taxonomy-bundle-2026-04-05.tar.gz",
  "source": "builtin",
  "source_version": "2026-04-05",
  "sha256": "xxx",
  "manifest_json": "{...}"
}
```

用途：

- 启动时或管理员点击时，把内置包注册到 `sys_install_package`

说明：

- 内置包本身不需要上传
- 只需要让数据库知道这个包可用

## 3.5 上传安装包接口

### `POST /platform/setup/taxonomy/package/upload`

表单字段建议：

- `file`

支持：

- `new_taxdump.tar.gz`
- `fan-taxonomy-bundle-*.tar.gz`

返回重点：

- `package_id`
- `package_code`
- `package_type`
- `source_version`
- `sha256`
- `status`

## 3.6 启动导入任务接口

### `POST /platform/setup/taxonomy/import/start`

输入建议：

```json
{
  "package_id": 12,
  "force_reinstall": false
}
```

返回建议：

```json
{
  "job_id": 18,
  "status": "running",
  "stage": "package_check",
  "progress_percent": 0
}
```

逻辑约束：

- 若当前已有进行中的 taxonomy 导入任务，直接拒绝
- 若 taxonomy 已 ready 且未指定 `force_reinstall`，提示确认

## 3.7 查询任务状态接口

### `GET /platform/setup/taxonomy/import/status?job_id=18`

返回建议：

```json
{
  "job_id": 18,
  "status": "running",
  "stage": "loading_names",
  "progress_percent": 68.4,
  "processed_count": 2180000,
  "total_count": 3212928,
  "message": "正在导入 taxonomy name",
  "error_message": null,
  "started_at": "2026-04-06T09:11:00+08:00",
  "finished_at": null
}
```

## 3.8 取消任务接口

### `POST /platform/setup/taxonomy/import/cancel`

输入建议：

```json
{
  "job_id": 18
}
```

说明：

- 第一阶段如果做不到真正中断数据库 COPY，可先做“标记取消，不启动后续阶段”
- 后续再增强为真正中断后台任务

## 3.9 重建索引接口

### `POST /platform/setup/taxonomy/rebuild-index`

用途：

- 管理员重建 `pg_trgm` 检索索引

说明：

- 用于索引损坏或升级后重建

---

## 4. 后端任务执行建议

## 4.1 任务执行链路

建议内部逻辑如下：

```text
register package
  ->
create install job
  ->
validate package
  ->
extract archive
  ->
load taxonomy dump
  ->
update taxonomy snapshot
  ->
sync compatibility cache
  ->
build search indexes
  ->
verify counts
  ->
unlock system
```

## 4.2 进度写回机制

建议所有阶段都写入 `sys_install_job`：

- `status`
- `stage`
- `progress_percent`
- `processed_count`
- `total_count`
- `message`

这样前端只需轮询一个接口。

## 4.3 解锁逻辑

当 taxonomy 导入完成且校验通过时：

- 更新 `sys_install_lock.taxonomy_required.is_locked = 0`
- `reason = 'taxonomy 已安装'`

若失败：

- `is_locked` 保持为 `1`
- `reason = 'taxonomy 导入失败'`

---

## 5. 前端页面草图

## 5.1 taxonomy 初始化页

建议页面结构：

### 顶部 Hero

- 标题：`taxonomy 初始化`
- 副标题：`系统尚未完成初始化，请先导入 taxonomy 数据包`

### 状态卡片

- 当前状态
- 当前版本
- node count
- name count
- 最近安装时间

### 安装包来源卡片

两种模式：

1. 使用内置包
2. 上传本地包

展示字段：

- 包名称
- 版本
- 文件大小
- 包类型

### 任务进度卡片

- 当前阶段
- 进度条
- 状态提示
- 处理条数
- 失败错误信息

### 完成卡片

- “taxonomy 已安装”
- “现在可以继续使用种质资源、项目管理等功能”
- 按钮：
  - `进入平台`
  - `查看平台设置`

## 5.2 页面交互建议

### 场景 A：首次初始化

- 系统检测未安装
- 自动进入初始化页
- 默认展示“内置包”
- 用户点击“开始安装”
- 页面进入实时进度状态
- 完成后显示“进入平台”

### 场景 B：管理员重装

- 从平台设置页进入
- 页面顶部显示当前版本
- 点击“重新安装”
- 需二次确认

### 场景 C：上传外部包

- 用户上传包
- 系统先做 package 校验
- 校验通过后，出现“开始安装”

---

## 6. 平台设置页草案

现有页面：

- [setting.vue](/Users/kentnf/projects/fan-ce/frontend/admin-web/apps/web-antd/src/views/platform/setting.vue)

建议新增一个卡片：

### 卡片标题

- `taxonomy 数据包`

### 卡片字段

- 当前状态
- 当前版本
- 节点数
- 名称数
- 最近安装时间

### 卡片按钮

- `进入初始化页`
- `重新安装`
- `重建索引`

说明：

- 平台设置页只做管理入口
- 不承担复杂进度交互

---

## 7. 路由守卫建议

## 7.1 全局状态缓存

前端登录后建议先拉一次：

- `GET /platform/setup/status`

并缓存在全局 store。

## 7.2 路由守卫规则

如果：

- `taxonomy_ready = false`

则：

- 允许访问：
  - `/platform/setting`
  - `/platform/api`
  - `/platform/setup/taxonomy`
- 禁止访问：
  - `/germplasm/*`
  - 后续 breeding 和 taxonomy 锚点依赖页

处理方式：

- 自动重定向到 `/platform/setup/taxonomy`

## 7.3 登录后跳转

若 taxonomy 未安装：

- 登录成功后不去默认工作台
- 直接跳：
  - `/platform/setup/taxonomy`

---

## 8. 前端页面状态机建议

taxonomy 初始化页建议采用下列状态机：

| 页面状态 | 含义 |
|---|---|
| `idle` | 尚未开始 |
| `package_selected` | 已选内置包或已上传包 |
| `installing` | 安装中 |
| `success` | 安装完成 |
| `failed` | 安装失败 |

页面按钮逻辑：

- `idle`
  - 可选包
  - 可上传
  - 不显示完成按钮
- `package_selected`
  - 可点击开始安装
- `installing`
  - 禁止重复操作
  - 显示取消任务
- `success`
  - 显示进入平台
- `failed`
  - 显示重试

---

## 9. 与当前代码的衔接建议

## 9.1 后端

当前已具备：

- taxonomy 主表
- taxdump 装载脚本
- taxonomy 搜索能力
- `pg_trgm` 索引

所以下一步不是重写 taxonomy，而是新增：

- `sys_install_package`
- `sys_install_job`
- `sys_install_lock`
- 初始化状态接口
- taxonomy 任务化导入接口

## 9.2 前端

当前已具备：

- 平台管理菜单
- 平台设置页
- germplasm 导入页

所以下一步是新增：

- taxonomy 初始化页
- 平台设置中的 taxonomy 卡片
- 路由守卫

---

## 10. 建议实施顺序

## Step 1

- 建系统表
- 实现 `GET /platform/setup/status`
- 实现 `GET /platform/setup/taxonomy/current`

## Step 2

- 实现内置包注册
- 实现 taxonomy 导入任务接口
- 后端落任务状态更新

## Step 3

- 新建 taxonomy 初始化页
- 登录后未初始化跳转
- 前端进度轮询

## Step 4

- 平台设置页加 taxonomy 卡片
- 支持重装和重建索引

---

## 11. 最终结论

taxonomy 初始化应该被正式定义成：

- 平台基础安装流程
- 平台设置的一部分
- 首次登录引导的一部分
- 后端任务系统的一个系统级 job

从实现角度看，最直接的落地方式是：

1. 先建 `sys_install_*` 三张表
2. 再实现初始化状态接口和导入任务接口
3. 然后做前端初始化页和路由守卫

这样可以最短路径把“taxonomy 主库已完成”提升成“taxonomy 安装功能已完成”。
