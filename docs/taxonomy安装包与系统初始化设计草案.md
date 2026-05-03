# taxonomy 安装包与系统初始化设计草案

## 1. 文档目标

本文档用于定义 `taxonomy 基础数据包` 在 FAN-CE 中的产品形态、安装方式、运行状态和前后端实现边界。

这项功能要解决的不是“普通数据导入”，而是“系统级基础数据初始化”：

- taxonomy 数据需要作为 FAN-CE 的一部分交付给用户
- 用户首次使用系统时，必须先把 taxonomy 安装到 PostgreSQL
- 安装过程必须有前端引导、任务状态和进度展示
- taxonomy 安装完成后，系统才开放依赖 taxonomy 的业务功能

本文档承接当前已完成的 taxonomy 主库能力：

- `brd_taxonomy_source_snapshot`
- `brd_taxonomy_node`
- `brd_taxonomy_name`
- `brd_taxonomy_cache`
- 本地 taxonomy 搜索已切到 PostgreSQL 主库

---

## 2. 需求判断

## 2.1 为什么它不是普通业务功能

taxonomy 与 dataset、种质资源、育种项目不同，它是平台运行所依赖的基础参考数据。

它有几个特点：

- 数据体量大
- 更新频率不高，但不能没有
- 导入时间长，必须任务化
- 一旦未安装，多个功能模块都不可正常使用
- 用户不应该每次都自己去研究 NCBI taxdump 的格式

因此 taxonomy 更合理的定位是：

- 平台安装包的一部分
- 首次启动初始化流程的一部分
- 平台设置中的一个“系统基础组件”

## 2.2 设计目标

### 业务目标

- 用户首次进入系统时，可以被明确引导完成 taxonomy 初始化
- 系统可以使用“内置包”一键安装 taxonomy
- 也允许管理员上传本地 taxonomy 包进行安装或升级
- 安装完成后，种质资源、breeding、依赖 taxonomy 的数据导入功能才能继续使用

### 技术目标

- taxonomy 安装必须任务化，不能走长同步请求
- 安装过程必须可观察，前端能看到阶段和进度
- 安装结果必须可审计，能看到版本、节点数、名称数、安装时间
- 安装状态必须可机读，供前端菜单和路由守卫判断
- 后续支持 taxonomy 升级、重装、重建索引

---

## 3. 功能定位

taxonomy 安装功能建议放在两个位置：

### 3.1 平台管理入口

在现有：

- `平台管理 -> 平台设置`

下面新增一个区域：

- `系统初始化`

其中第一项就是：

- `taxonomy 数据包`

### 3.2 首次启动引导页

新增独立页面：

- `/platform/setup/taxonomy`

使用场景：

- 用户登录后，系统检测 taxonomy 未安装
- 路由守卫强制跳转到这个页面
- 只有完成 taxonomy 初始化后，才允许继续进入依赖 taxonomy 的业务页

这样设计的好处是：

- 管理员后续仍可以从“平台设置”进入维护
- 首次使用时又不会让用户在菜单里自己摸索

---

## 4. 状态模型

taxonomy 安装建议定义以下平台状态：

| 状态 | 含义 |
|---|---|
| `not_installed` | 系统未安装 taxonomy |
| `package_ready` | 已选择或上传安装包，尚未开始导入 |
| `importing` | 正在导入 |
| `ready` | taxonomy 已安装，可正常使用 |
| `failed` | 导入失败，需要重试 |

平台级判断建议收敛成一个布尔状态：

- `taxonomy_ready = true/false`

系统是否开放依赖功能，按此字段判断即可。

---

## 5. 系统锁定策略

taxonomy 未安装时，建议采用“软锁定”。

## 5.1 允许访问的模块

- 登录页
- 平台设置
- API 管理
- 系统基础管理页

## 5.2 禁止访问的模块

- 种质资源导入
- breeding 项目中的材料创建
- 任何需要 taxonomy 锚点的导入页
- 依赖 taxonomy 过滤或锚点选择的页面

## 5.3 路由行为

若 taxonomy 未安装：

- 登录后默认跳到 `/platform/setup/taxonomy`
- 访问受限页面时自动重定向
- 页面显示：
  - “系统尚未完成初始化”
  - “请先导入 taxonomy 数据包”

说明：

- 不需要把全站彻底锁死
- 但 taxonomy 相关业务必须挡住

---

## 6. 安装包设计

## 6.1 支持两类包

### A. NCBI 官方原始包

直接支持：

- `new_taxdump.tar.gz`

优点：

- 与官方源一致
- 最低兼容路径

缺点：

- 用户需要自己知道去哪里下载
- 包里没有平台特定元信息

### B. FAN taxonomy 安装包

推荐平台长期主推这种包，例如：

- `fan-taxonomy-bundle-2026-04-05.tar.gz`

建议内容：

```text
fan-taxonomy-bundle-2026-04-05.tar.gz
├── manifest.json
├── payload/
│   └── new_taxdump.tar.gz
└── checksums.txt
```

优点：

- 用户体验更好
- 可以附带版本、校验、兼容性信息
- 后续支持平台官方发布

## 6.2 manifest 建议字段

```json
{
  "package_type": "taxonomy_bundle",
  "source": "ncbi",
  "source_version": "2026-04-05",
  "built_at": "2026-04-05T22:49:05+08:00",
  "file_name": "new_taxdump.tar.gz",
  "sha256": "xxxxx",
  "expected_node_count": 2735827,
  "expected_name_count": 3212928,
  "min_system_version": "fan-ce-0.1.0"
}
```

---

## 7. 数据库设计

taxonomy 实际业务数据仍然落在已存在的四张表中：

- `brd_taxonomy_source_snapshot`
- `brd_taxonomy_node`
- `brd_taxonomy_name`
- `brd_taxonomy_cache`

为了支持“安装包 + 任务化 + 初始化锁定”，建议增加三张系统表。

## 7.1 `sys_install_package`

用途：

- 记录一个可用于安装的包
- 支持内置包和用户上传包统一管理

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | bigint PK | 主键 |
| `package_code` | varchar(64) unique | 包编码 |
| `package_type` | varchar(32) | `taxonomy_bundle` / `taxonomy_raw_dump` |
| `package_name` | varchar(256) | 包名称 |
| `source` | varchar(32) | `builtin` / `upload` / `downloaded` |
| `source_version` | varchar(128) | taxonomy 版本 |
| `storage_path` | text | 包路径 |
| `file_size` | bigint | 文件大小 |
| `sha256` | varchar(128) | 校验值 |
| `manifest_json` | text | manifest |
| `status` | varchar(32) | `ready` / `invalid` / `archived` |
| `created_by` | bigint null | 操作人 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

## 7.2 `sys_install_job`

用途：

- 记录一次 taxonomy 安装任务
- 给前端提供进度查询

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | bigint PK | 主键 |
| `job_type` | varchar(32) | `taxonomy_import` |
| `package_id` | bigint FK | 关联安装包 |
| `status` | varchar(32) | `pending` / `running` / `success` / `failed` / `cancelled` |
| `stage` | varchar(64) | 当前阶段 |
| `progress_percent` | numeric(5,2) | 总进度 |
| `message` | text | 当前状态说明 |
| `error_message` | text | 错误信息 |
| `result_json` | text | 结果信息 |
| `created_by` | bigint null | 操作人 |
| `started_at` | datetime | 开始时间 |
| `finished_at` | datetime | 结束时间 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

## 7.3 `sys_install_lock`

用途：

- 作为平台初始化锁定开关

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `lock_code` | varchar(64) PK | 如 `taxonomy_required` |
| `is_locked` | integer | 1/0 |
| `reason` | varchar(256) | 锁定原因 |
| `required_action` | varchar(128) | 如 `install_taxonomy` |
| `updated_at` | datetime | 更新时间 |

说明：

- 如果你不想单独建 `sys_install_lock`，也可以把这个状态落进平台设置表
- 但独立表更清晰，也更适合未来扩展其他初始化锁

---

## 8. 任务模型与进度设计

taxonomy 安装必须异步任务化。

## 8.1 导入阶段建议

建议拆成下面这些 stage：

| stage | 含义 |
|---|---|
| `package_check` | 校验安装包 |
| `extracting` | 解压 |
| `parsing_nodes` | 解析 `nodes.dmp` |
| `parsing_names` | 解析 `names.dmp` |
| `loading_snapshot` | 写入 snapshot |
| `loading_nodes` | 导入 taxonomy node |
| `loading_names` | 导入 taxonomy name |
| `syncing_cache` | 同步兼容 cache |
| `building_indexes` | 建立检索索引 |
| `verifying` | 导入校验 |
| `completed` | 完成 |
| `failed` | 失败 |

## 8.2 前端进度展示建议

不要只显示一个进度条，建议至少同时显示：

- 总体百分比
- 当前阶段
- 当前阶段说明
- 已处理量 / 总量
- 开始时间
- 最近刷新时间

示例：

```text
当前阶段：loading_names
总进度：68%
处理进度：2,180,000 / 3,212,928
说明：正在导入 taxonomy 名称索引
```

## 8.3 任务执行方式

第一阶段建议继续沿用现有“轻任务化”思路：

- 后端提交任务
- 任务记录入库
- 后台线程或进程执行导入
- 前端轮询任务状态

后续如果全平台任务越来越多，再抽独立 job runner。

---

## 9. 后端接口草案

## 9.1 状态接口

### `GET /platform/setup/status`

用途：

- 返回平台初始化状态

返回重点：

- `taxonomy_ready`
- `taxonomy_status`
- `current_taxonomy_version`
- `current_job`

## 9.2 安装包接口

### `GET /platform/setup/taxonomy/packages`

用途：

- 返回可用安装包列表

### `POST /platform/setup/taxonomy/package/upload`

用途：

- 上传 taxonomy 包

说明：

- 支持 `new_taxdump.tar.gz`
- 支持 `fan-taxonomy-bundle-*.tar.gz`

### `POST /platform/setup/taxonomy/package/register-builtin`

用途：

- 注册系统内置包

说明：

- 对于随系统分发的内置文件，不需要用户手工上传
- 用户只需选择“使用内置包”

## 9.3 导入任务接口

### `POST /platform/setup/taxonomy/import/start`

输入：

- `package_id`
- `force_reinstall`

用途：

- 启动导入任务

### `GET /platform/setup/taxonomy/import/status`

输入：

- `job_id`

用途：

- 查询导入任务状态

### `POST /platform/setup/taxonomy/import/cancel`

输入：

- `job_id`

用途：

- 取消未完成任务

## 9.4 当前版本接口

### `GET /platform/setup/taxonomy/current`

用途：

- 返回当前已安装 taxonomy 版本、节点数、名称数、安装时间

## 9.5 管理员维护接口

### `POST /platform/setup/taxonomy/rebuild-index`

用途：

- 重建 `pg_trgm` 检索索引

### `POST /platform/setup/taxonomy/reinstall`

用途：

- 管理员重新安装 taxonomy

---

## 10. 前端页面设计

## 10.1 页面结构

建议新增独立页：

- `/platform/setup/taxonomy`

页面分 4 个区域：

### A. 当前状态卡片

展示：

- 当前状态
- 当前版本
- 节点数
- 名称数
- 最近安装时间

### B. 安装包选择

支持：

- 使用系统内置包
- 上传本地包

### C. 导入进度

展示：

- 步骤条
- 总进度条
- 当前阶段
- 日志信息

### D. 完成后结果卡片

展示：

- taxonomy 版本
- node count
- name count
- 可开始使用系统

## 10.2 平台设置页中的展示

在现有 [platform/setting.vue](/Users/kentnf/projects/fan-ce/frontend/admin-web/apps/web-antd/src/views/platform/setting.vue) 中新增一个 `taxonomy 数据包` 卡片。

展示：

- 当前安装状态
- 当前版本
- “进入初始化页”
- “重新安装”
- “查看任务状态”

说明：

- 平台设置页用于管理
- 独立初始化页用于真正执行安装

---

## 11. 路由与菜单行为

## 11.1 菜单

建议在现有：

- `平台管理`

下新增子菜单：

- `系统初始化`

其中先放：

- `taxonomy 初始化`

## 11.2 登录后跳转规则

若：

- `taxonomy_ready = false`

则：

- 登录成功后重定向到 `/platform/setup/taxonomy`

## 11.3 受限页面守卫

对于以下页面，加前端路由守卫：

- 种质资源导入
- 依赖 taxonomy 的 breeding 页面
- 未来依赖 taxonomy 的导入页

处理逻辑：

- 若 taxonomy 未就绪，则跳转初始化页

---

## 12. 与当前 taxonomy 主库方案的关系

这项功能不替换已经做好的 taxonomy 主库，只是在它之上加一层“安装与初始化”。

关系如下：

### 系统安装层

- 安装包
- 任务
- 初始化锁

### taxonomy 主数据层

- `brd_taxonomy_source_snapshot`
- `brd_taxonomy_node`
- `brd_taxonomy_name`
- `brd_taxonomy_cache`

### 业务使用层

- 种质资源 taxonomy 锚点选择
- breeding 物种过滤
- 未来 dataset/phenome/variome 等按物种锚点挂接

一句话总结：

- 安装层负责“把 taxonomy 放进系统”
- 主数据层负责“把 taxonomy 作为本地标准参考库”
- 业务层负责“在页面中使用 taxonomy”

---

## 13. 建议实施顺序

## Checkpoint 1：最小可用初始化闭环

- 增加平台初始化状态接口
- 增加 taxonomy 初始化页
- 支持“使用内置包”
- 后端异步导入任务
- 前端显示任务进度
- taxonomy 导入完成后解除锁定

## Checkpoint 2：安装包管理

- 支持上传 taxonomy 包
- 支持 manifest 校验
- 支持失败重试
- 支持查看当前已安装版本

## Checkpoint 3：运维增强

- 支持 taxonomy 升级
- 支持重装
- 支持重建索引
- 支持保留历史安装记录

---

## 14. 本阶段不做的内容

以下内容建议暂不放进第一阶段：

- 中文 taxonomy 别名字典
- taxonomy 跨版本回滚 UI
- 多源 taxonomy 合并
- 在线从 NCBI 实时下载并导入
- 分布式任务调度系统

这些都可以后续再补。

---

## 15. 最终建议

taxonomy 数据包应该被正式定义为：

- FAN-CE 的系统安装包之一
- 首次启动初始化的必经步骤
- 平台基础参考数据，而不是普通业务导入文件

推荐产品形态是：

- 系统预置一个官方推荐 taxonomy 包
- 用户首次进入系统时一键导入
- 前端可见任务进度
- 导入完成后自动解除系统锁定
- 后续管理员可以上传新版包做升级

如果按这个方向实施，taxonomy 将从“后端已有能力”变成“用户可理解、可安装、可维护的正式平台功能”。
