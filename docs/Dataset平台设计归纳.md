# Dataset 平台设计归纳

本文档用于把当前仓库中与 Dataset 平台相关的正式设计、实施过程和 backlog 状态归纳到一份总览中，便于后续重新启动讨论和持续推进。

它不是替代原文档，而是作为统一入口。详细设计、历史决策和任务拆分仍以原文档为准。

参考来源：

- `docs/组学Dataset平台后端正式设计文档.md`
- `docs/dataset平台checkpoint实施方案.md`
- `docs/Dataset平台开发任务Backlog.md`
- `docs/育种实验设计域与组学数据资产整合设计草案.md`
- `docs/育种实验设计域实施进度-2026-04-04.md`
- `docs/旧database兼容层迁移清单.md`
- `docs/PostgreSQL数据库存储重构设计.md`
- `docs/PostgreSQL生产迁移执行方案.md`

---

## 0. 当前主线（2026-04-01）

当前代码与文档状态已经可以明确分成两部分：

- 平台基础收口：已基本完成
- 核心业务扩展：下一主线已经收敛

当前已完成的基础收口包括：

- 主业务数据库已经切到 PostgreSQL
- MySQL 已退出主运行链路
- 后端 `apps/*`、`basis/schemas/*`、`core/config.py` 已完成 Pydantic V2 配置收口
- `asset-first` 查询主线、版本发布语义、public version 语义、基础 ingest 任务化和权限一期都已落地

这意味着当前不再需要继续围绕“底座是否可用”反复整理，后续主线应回到 Dataset 平台业务能力本身。

按 backlog 和现有实现状态，上一轮最明确的主线是：

- `P1-03 interaction` 的 `cool/mcool` 真正矩阵查询

这条主线当前已经完成到“稳定最小实现”，包括：

- `interaction` adapter 已支持 `cool / mcool` 的 `matrix_meta / matrix_slice / resolutions_list`
- ingest 已支持 `cool / mcool` 合法性校验与分辨率探测
- portal 已补 interaction matrix 查询参数与结构化矩阵结果展示
- 私有查询、公开查询、`asset_code` 切换与 ingest 分支均已有自动化回归

之所以当时优先做它，是因为它同时满足：

- 属于设计主线里的核心数据类型，不是边角增强
- 后端目前只完成了 `BEDPE` 最小闭环
- portal 端已经预留了 `matrix_slice` 交互骨架，但后端还没有真正能力
- 它会反向验证 `asset-first / version-aware / public query / adapter registry / ingest metadata` 这整条设计链是否足够稳定

因此，当前主线建议已从“补齐 interaction matrix 核心闭环”切换到：

1. 继续细化 `P1-03 interaction` 的结果聚合、admin 体验和版本对比
2. 回到 `P1-01 annotation` 与 `P1-02 signal` 的深层结果体验增强
3. 持续收缩旧兼容层和补平台化回归

---

## 1. 平台目标

Dataset 平台的核心目标，是把当前系统从“围绕单个 database/file 的资产模型”逐步收敛到“以 dataset 为业务核心对象”的平台模型。

希望解决的问题包括：

- 如何把一个组学对象表达成可管理、可发布、可查询的数据集
- 如何在同一个数据集下管理多个版本
- 如何在同一个版本下管理多个业务资产与物理文件
- 如何统一后台管理、前台受控查询、前台公开查询三类接口语义
- 如何在不推翻旧 `apps/databases` 的前提下渐进演进

平台当前采用的是：

- 文件为事实源
- 数据库为控制面
- 兼容式重构
- 增量建模

也就是说，真正的组学内容仍保留在文件中，例如 FASTA、VCF、HDF5、SQLite、BigWig、BEDPE 等；关系数据库主要承担元数据、版本、权限、工作流、发布和查询路由信息。

---

## 2. 核心设计原则

### 2.1 文件为事实源，数据库为控制面

平台不强制把组学内容导入关系数据库。数据库主要记录：

- 元数据登记
- 生命周期与工作流状态
- 发布与公开语义
- 资产、文件、索引、血缘关系
- 查询入口和查询适配器信息

### 2.2 业务对象不等于文件

平台不再把“单个文件”当作顶层业务对象，而是拆成四层：

- `Dataset`：逻辑数据集
- `DatasetVersion`：数据集版本
- `DatasetAsset`：版本下的业务资产
- `AssetFile`：资产对应的物理文件

### 2.3 状态拆分，不混用

平台显式区分三类状态：

- `workflow_state` / `lifecycle_state`：处理流程进行到哪一步
- `visibility`：谁能访问
- `release_state`：是否作为前台可查询版本发布

### 2.4 兼容式重构

当前仓库仍有大量旧 `apps/databases` 语义和旧前端页面，因此策略不是一次性替换，而是：

1. 先增加 `apps/datasets` 新控制层
2. 逐步把新功能接到 dataset 主线
3. 再持续收缩旧 `database/*` 兼容面

---

## 3. 领域模型

### 3.1 总体关系

```text
Dataset
  ├── DatasetVersion (1:N)
  │     ├── DatasetAsset (1:N)
  │     │     └── AssetFile (1:N)
  │     ├── WorkflowTask (1:N)
  │     ├── ReleaseRecord (1:N)
  │     └── LineageEdge (1:N / N:N)
  └── ACL / Project / Team / Meta
```

### 3.2 Dataset

`Dataset` 回答“这是什么数据”，是平台一级业务对象。

当前语义上主要承载：

- 稳定 dataset 标识
- 标题、类型、物种等元信息
- 当前工作版本
- 默认公开版本
- 聚合视图与后台入口

### 3.3 DatasetVersion

`DatasetVersion` 回答“这份数据的哪个版本”，是发布、查询、追踪血缘的主粒度。

当前版本语义包括：

- 当前工作版本 `is_current`
- 发布状态 `release_state`
- 默认公开版本标记 `is_default_public`
- 版本级查询配置
- 版本级工作流与发布审计

### 3.4 DatasetAsset

`DatasetAsset` 解决“一个版本下有多个业务组成部分”的问题。

典型资产类型包括：

- `reference_fasta`
- `gene_annotation`
- `functional_annotation`
- `variant_vcf`
- `expression_matrix`
- `signal_track`
- `interaction_matrix`
- `metadata_table`

资产是查询入口的核心挂点。当前主线已经明确优先以 `asset` 为查询入口，而不是继续围绕单一 `dataset_version.file_path`。

### 3.5 AssetFile

`AssetFile` 解决“一个资产对应多个物理文件”的问题。

典型文件角色包括：

- `primary`
- `index`
- `derived`
- `metadata`
- `preview`

这层用于表达主文件、索引文件、派生文件之间的关系，例如：

- `genome.fa` + `genome.fa.fai`
- `cohort.vcf.gz` + `cohort.vcf.gz.tbi`
- `genes.gff3` + `genes.sqlite`

### 3.6 LineageEdge

`LineageEdge` 用于表达数据之间的来源、依赖和派生关系。

当前推荐主视角仍然以 `version` 级血缘为主，`asset` 级血缘作为增强能力按需使用。

---

## 4. 当前平台分层

当前仓库实际上已经形成三层语义：

### 4.1 旧资产层

由 `apps/databases` 提供，主要承担：

- 历史主表与旧资产事实
- 文件挂接
- 项目关联
- 旧后台兼容接口与页面

### 4.2 Dataset 控制层

由 `apps/datasets` 提供，主要承担：

- dataset 统一视图
- 生命周期状态
- 发布与公开语义
- adapter 查询分发
- ingest 标准流程
- 权限边界
- 血缘与注册表管理

### 4.3 Dataset Version 工作层

由 `dataset_version` 相关模型与接口承载，主要承担：

- 草稿版本
- 当前工作版本切换
- 版本级查询配置
- 版本级发布与默认公开版本
- 前后台不同版本视角

---

## 5. 状态与发布模型

### 5.1 状态模型

平台当前已经基本收敛到三轴语义：

- `lifecycle_state`：数据处理阶段，例如 `draft`、`uploaded`、`ready`
- `visibility`：访问范围，例如 `private`、`public`
- `release_state`：发布状态，例如 `unreleased`、`released`

其中，当前实现里真正作为公开语义主判断的是：

- `dataset_version.release_state`
- `dataset_registry.default_public_version_id`
- `dataset_version.is_default_public`

### 5.2 发布语义

当前平台已经收敛为三类动作：

- `release`
- `withdraw`
- `set-default-public`

它们的职责分别是：

- `release`：把版本变成 released
- `withdraw`：撤回一个已公开版本
- `set-default-public`：切换默认公开版本

当前已确认的设计含义：

- 一个 dataset 可以有多个已 released 版本
- 但只能有一个默认公开版本
- 默认公开版本被 `withdraw` 后，系统允许进入“无公开版本”状态
- 后台当前工作版本与前台默认公开版本可以不同步

---

## 6. 查询模型

### 6.1 asset-first 查询

平台当前查询主线已经转为 asset-first：

1. 先确定 dataset
2. 再确定 version
3. 再确定 query entry asset
4. 再从 `asset_file` 解析主文件与索引文件
5. 由对应 adapter 执行查询

这意味着：

- `dataset_version.file_path` 仍存在，但主要作为兼容信息
- 查询能力、查询执行、public query、version payload 都优先从 `asset + asset_file` 解析
- 支持显式传入 `asset_code` 对指定资产下钻查询

### 6.2 Query Adapter

平台通过统一 adapter registry，根据 `dataset_type + file_format + query_engine` 选择查询适配器。

当前已接入的主线类型包括：

- `sequence`
- `variant`
- `expression`
- `annotation`
- `signal`
- `interaction`
- `generic`

### 6.3 当前类型能力

当前已实现情况可以概括为：

- `annotation`
  - 支持 sqlite
  - 支持 GFF/GTF
  - 已支持 `table_stats / gene_lookup / region_features`
- `signal`
  - 支持 BED `region_features`
  - 支持 BigWig `describe_signal / region_signal`
- `interaction`
  - 当前只到 BEDPE / pairs 级别
  - 已支持 `region_contacts`
  - `cool/mcool` 真正矩阵查询尚未完成

---

## 7. API 分层

平台设计上有三类 API 语义：

### 7.1 后台管理 API

面向后台管理与数据控制，职责包括：

- dataset / version / asset / file 管理
- 工作流触发
- 发布控制
- 权限控制
- 血缘维护

当前实际接口仍以 `/api/v1/dataset/*` 为主，而不是完全切到 `/api/v1/admin/*` 命名。

### 7.2 前台受控查询 API

面向登录用户，按权限读取指定 dataset / version / asset。

当前设计目标是：

- 可以按版本查询
- 可以按资产查询
- 可以围绕 capability + execute 统一分发

### 7.3 前台公开查询 API

面向未登录用户，只允许访问公开版本。

当前语义已经成型：

- 不指定版本时默认走 `default_public_version`
- 指定版本时只能访问已 released 版本
- 支持公开版本列表、详情、capabilities 和查询执行

---

## 8. Ingest 与标准流程

平台当前已经有统一 ingest 主线：

- `register`
- `validate`
- `index`
- `pipeline`

后续又增加了任务化能力：

- 异步 ingest task 提交
- 任务详情查询
- 失败任务重试

当前 ingest 设计重点是：

- 已有服务器文件先进入标准流程
- 允许基于 `dataset id` 或直接基于 `file_path`
- 直接 `file_path` 模式不写共享数据源，便于安全调试
- `dataset_workflow_task` 已开始承载运行态明细

---

## 9. 权限模型

权限设计的目标是：

- 后台每条数据都要有访问边界
- 公开后的版本可以对前台开放
- dataset 是默认权限边界
- version / asset / file / lineage / task 在此基础上继承或覆盖

当前第一阶段实现为：

- 超级管理员可全量访问
- 普通后台用户按 dataset owner、team、project 归属获得访问权
- registry 管理区仅超级管理员可见、可维护
- 公开 API 不走后台私有鉴权，而按 released/default-public 语义开放

尚未完全展开的是：

- asset 级覆盖权限是否需要启用
- 其它页面是否统一沿用当前的权限拒绝 UX

---

## 10. 与旧系统的关系

当前平台不是完全替换旧系统，而是做桥接式演进。

现状可以概括为：

- `apps/datasets` 已建立 `legacy_bridge.py`
- dataset 主线对旧 `database/file/meta/project_link` 的兼容访问已统一收口到 bridge
- 一部分旧前端页面已经改为读取 `dataset options`
- 工作台中的主要“数据管理”入口已切到 `/apps/dataset`

但旧兼容层还没有完全收完，仍存在：

- 某些旧页面仍直接依赖 `apps/databases/*`
- 一些旧 `/database/*` 页面仍处于兼容提示态

因此，旧兼容层收缩仍然是平台化收敛的一条长期主线。

---

## 11. 当前实现状态归纳

按当前 backlog，可概括为：

### 11.1 已完成或已进入稳定最小实现

- `P0-01` 版本状态模型：基本完成
- `P0-02` 发布语义：已完成
- `P0-03` 查询层 asset-first：已完成
- `P0-04` 后台版本工作台：基本完成
- `P1-01` annotation：已进入稳定最小实现
- `P1-02` signal：已进入稳定最小实现
- `P1-04` public 版本感知：已进入稳定最小实现
- `P2-01` ingest 任务化：第一阶段可用
- `P2-02` 权限模型：第一阶段可用
- `P2-03` 旧兼容层收缩：第一阶段已做

### 11.2 仍明显未完成的核心项

- `P1-03 interaction`
  - 当前只完成了 BEDPE / pairs 最小主线
  - `cool/mcool` 真正矩阵查询未落地
  - 这是当前最明确的核心业务缺口

### 11.3 已做但仍可继续增强的方向

- `annotation`
  - 更多注释类型
  - 更深的结构化结果体验
- `signal`
  - 更强的区域聚合
  - 更好的展示方式
- `public portal`
  - lineage 仍未开放
  - smart query 和版本浏览仍有增强空间

---

## 12. 建议的后续推进顺序

如果重新启动持续推进，我建议按以下顺序继续：

### 12.1 第一优先级

先完成 `P1-03 interaction`，重点补齐：

- `cool/mcool` 查询能力模型
- 查询参数与结果结构
- private/public query 一致性
- admin 工作台与 portal 的 interaction 展示能力

原因：

- 它是当前最明确的主线缺口
- 已有 BEDPE 最小实现，适合顺着现有模型扩展
- 做完后，Dataset 平台对主流组学文件类型的覆盖会更完整

### 12.2 第二优先级

继续增强 `annotation / signal` 的结果体验：

- 更强聚合
- 更好的结构化展示
- 更清晰的查询模板与结果导出

### 12.3 第三优先级

继续推进 `P2-03` 兼容层收缩：

- 减少其它旧页面对 `apps/databases/*` 的直接耦合
- 冻结纯兼容页
- 把主入口和主读写路径进一步收口到 dataset 主线

---

## 13. 如何使用这份文档

建议后续这样使用：

1. 先读这份总览，快速恢复项目上下文
2. 再根据关心的主题展开看原文档
3. 如果要进入新一轮设计或实施，优先围绕单个 backlog 主题开讨论

推荐对应关系：

- 想看正式目标模型：`组学Dataset平台后端正式设计文档.md`
- 想看历史实施过程：`dataset平台checkpoint实施方案.md`
- 想看当前完成度与下一步：`Dataset平台开发任务Backlog.md`
- 想看旧系统迁移面：`旧database兼容层迁移清单.md`

---

## 14. 当前一句话结论

这个平台已经从“旧 database 资产接口”演进到了“dataset 作为上层业务域、version/asset/file 作为正式建模、发布/公开/查询/ingest/权限都有主线实现”的阶段；当前最值得优先继续推进的核心缺口，是 interaction 的 `cool/mcool` 真正矩阵查询能力。
