# Dataset 平台 Checkpoint 实施方案

## 1. 目标

本轮改造的目标不是一次性替换旧的 `apps/databases`，而是在不打断现有后台的前提下，把后端核心域逐步提升为 `dataset`，为后续标准流程打基础：

- 上传
- 校验
- 建索引
- 发布

同时保留当前事实：

- 现有后台仍然依赖 `database/*` 接口
- 现有数据主表仍然是 `databases`
- 当前开发环境连接的是共享 MySQL

因此本轮采用“兼容式重构 + 增量建模”的方式。

## 2. 当前已完成 Checkpoint

### Checkpoint 0：后端结构收敛

已完成：

- 后端主运行目录收敛到 `backend/api-server/`
- SDK 收敛到 `backend/sdk/`
- MCP 收敛到 `backend/mcp/`
- 启动脚本与开发文档已同步更新

### Checkpoint 1：建立 Dataset 兼容层

已完成：

- 新增 `backend/api-server/apps/datasets/`
- 新增 `dataset` 路由并接入主路由树
- 旧权限码暂时复用 `app:database:*`
- 不替换旧 `database/*` 接口，只增加 `dataset/*` 新接口

当前新接口：

- `POST /api/v1/dataset/list`
- `POST /api/v1/dataset/options`
- `POST /api/v1/dataset/info`
- `POST /api/v1/dataset/update`
- `POST /api/v1/dataset/workflow/transition`
- `POST /api/v1/dataset/workflow/tasks`
- `POST /api/v1/dataset/publish/records`
- `POST /api/v1/dataset/publish`
- `POST /api/v1/dataset/unpublish`

### Checkpoint 2：建立 Dataset 控制面表

已完成新增表：

- `dataset_registry`
- `dataset_workflow_task`
- `dataset_publish_record`

设计意图：

- `databases` 继续作为当前资产事实表
- `dataset_registry` 作为新的控制面视图
- `dataset_workflow_task` 记录流程推进
- `dataset_publish_record` 记录发布/撤回公开审计

### Checkpoint 3：开发环境自动补齐新表

已完成：

- 启动时按需创建 `dataset_*` 新表
- 仅创建新增表，`checkfirst=True`
- 不触碰旧表，不依赖全量 `db_init`

原因：

- 当前 `config.dev.yaml` 里 `app.db_init=false`
- 如果不单独建表，新加的 `dataset` 能力无法在开发环境运行

### Checkpoint 4：打通 Dataset 工作流最小闭环

已完成：

- 支持 `uploaded -> validating -> validated -> indexing -> ready`
- 支持任务审计记录写入
- 支持 dataset 控制面元数据更新

已验证：

- `dataset/list` 可返回数据
- `dataset/info` 可返回详情
- `dataset/update` 可写入控制面字段
- `dataset/workflow/transition` 可推进状态
- `dataset/workflow/tasks` 可返回任务记录
- 旧接口 `database/list` 未回归

说明：

- `publish/unpublish` 代码已接入
- 由于当前开发环境连接共享数据源，本轮没有对公开状态做实际回归验证，避免误改真实数据的对外可见性

## 3. 当前落地后的架构含义

当前后端已经形成两层语义：

### 3.1 旧资产层

由 `apps/databases` 提供：

- 资产列表
- 文件挂接
- 项目关联
- 旧后台界面依赖

### 3.2 新 dataset 控制层

由 `apps/datasets` 提供：

- dataset 统一视图
- 生命周期状态
- 工作流审计
- 发布审计
- 查询引擎与格式等控制面属性

这意味着后续可以逐步把前台和后台的新功能优先接到 `dataset/*`，而不是继续向 `database/*` 增加语义负担。

## 4. 当前代码落点

核心文件：

- `backend/api-server/apps/datasets/models.py`
- `backend/api-server/apps/datasets/schemas.py`
- `backend/api-server/apps/datasets/services.py`
- `backend/api-server/apps/datasets/api/dataset.py`
- `backend/api-server/apps/datasets/routers.py`
- `backend/api-server/apps/datasets/init.py`

接入点：

- `backend/api-server/apps/routers.py`
- `backend/api-server/register/app_init.py`
- `backend/api-server/db/init.py`

## 5. Checkpoint 5 当前进展

### Checkpoint 5：引入 Dataset Type 与 Query Adapter

已完成的部分：

- 新增 `apps/datasets/adapters/`
- 引入 adapter registry
- 将 `dataset_type + file_format` 统一映射到 adapter
- 新增统一查询能力接口与统一查询执行入口

当前已接入 adapter：

- `sequence`
- `variant`
- `expression`
- `generic`

当前新增接口：

- `POST /api/v1/dataset/query/capabilities`
- `POST /api/v1/dataset/query/execute`

当前行为：

- `dataset/info` 会返回 `query_adapter`
- `query/capabilities` 会返回：
  - 选中的 adapter
  - 支持的操作
  - 示例请求
  - `file_access.exists_on_server`
- `query/execute` 会通过 adapter 分发到对应组学能力实现

当前已验证：

- HDF5 expression 数据集可被正确识别为 `expression adapter`
- 当数据库记录存在但本机未挂载真实数据文件时，接口会明确返回 `404`
- 不再以 `500` 隐式失败

当前边界：

- 这一步主要完成了“统一分发层”
- 还没有把 `basis/*` 的所有查询能力都完整迁移到 `dataset/query/*`
- 当前更像“dataset 统一入口 + 复用 basis 能力”，而不是完全替换 basis

## 6. Checkpoint 6 当前进展

### Checkpoint 6：把上传入口标准化

已完成的部分：

- 新增统一 ingest API：
  - `POST /api/v1/dataset/ingest/register`
  - `POST /api/v1/dataset/ingest/validate`
  - `POST /api/v1/dataset/ingest/index`
  - `POST /api/v1/dataset/ingest/pipeline`
- 把“已有服务器文件注册为 dataset”纳入统一入口
- 把“按 dataset type 做校验”纳入统一入口
- 把“按 dataset type 做建索引/转换”纳入统一入口
- `pipeline` 已打通 `validate + index`

当前已接入的低风险能力：

- `sequence`
  - FASTA 基本格式校验
  - `samtools faidx` 索引
- `variant`
  - VCF/VCF.GZ/BCF 格式识别
  - `bcftools` 索引/转换链路
- `expression`
  - HDF5 表达矩阵校验
  - 文本矩阵转换为 HDF5
- `generic`
  - 通用文件存在性校验
  - noop 索引占位

当前行为：

- `register` 支持 `dry_run=true`
- `validate/index/pipeline` 支持两种模式：
  - 基于 `dataset id`
  - 直接基于 `file_path`
- 当目标是直接文件路径时：
  - 不写共享 MySQL
  - 便于本地安全调试
- 当缺少外部二进制时：
  - FASTA 索引缺 `samtools` 返回 `503`
  - Variant 索引缺 `bcftools` 返回 `503`

当前已验证：

- 本地临时 FASTA 文件可完成 `register(dry_run)` 与 `validate`
- `index/pipeline` 在缺少 `samtools` 时会显式报错，不再隐式失败
- 已存在 expression dataset 在本机无真实挂载文件时，会在查询阶段明确返回 `404`

当前限制：

- 这一步还不是“浏览器上传到统一暂存区”
- 仍然是“已有文件进入标准流程”的第一版
- 文件角色目前还未拆成：
  - raw
  - index
  - metadata
  - derived

## 7. Checkpoint 7 当前进展

### Checkpoint 7：把发布语义逐步收敛到 Dataset Version

已完成的部分：

- 新增 `dataset_version` 表
- 新增版本接口：
  - `POST /api/v1/dataset/version/list`
  - `POST /api/v1/dataset/version/info`
  - `POST /api/v1/dataset/version/create`
  - `POST /api/v1/dataset/version/activate`
- `dataset/info` 已返回：
  - `current_version`
  - `version_count`
- 当前版本切换后，dataset 读模型会优先使用当前版本的：
  - `version`
  - `title`
  - `dataset_type`
  - `file_path`
  - `file_format`
  - `query_engine`

当前设计选择：

- 版本体系先承担“后台工作版本”语义
- `publish/unpublish` 现已开始同步到 `dataset_version`
- 但仍保留 dataset 顶层兼容语义，避免旧后台直接失效
- 当前已经把两个概念拆开：
  - `current_version`
  - `published_version`

当前已验证：

- `dataset/version/list` 可返回版本列表
- `dataset/version/create` 可创建草稿版本
- `dataset/info` 可返回 `current_version`
- 当前版本切换后，可驱动 `dataset info/query` 使用该版本的文件与查询配置
- 已验证“后台当前版本”和“前台公开版本”可不同步

当前限制：

- 旧 `databases` 公开字段还只是兼容层，不再作为公开查询主事实源

## 8. 当前后端设计含义

到目前为止，后端已经形成三层语义：

### 8.1 旧资产层

由 `apps/databases` 提供：

- 资产主表
- 文件挂接
- 项目关联
- 旧后台兼容

### 8.2 Dataset 控制层

由 `apps/datasets` 提供：

- dataset 统一视图
- 生命周期状态
- 工作流任务
- 发布审计
- ingest 标准流程
- adapter 查询分发

### 8.3 Dataset Version 工作层

由 `dataset_version` 提供：

- 草稿版本
- 当前工作版本切换
- 版本级文件路径与查询配置承载
- 已成为 version-level publish 的主落点

## 9. 下一阶段建议 Checkpoint

### Checkpoint 8：把公开查询 API 正式切到 public version

已完成的部分：

- 新增公开只读接口：
  - `POST /api/v1/public/dataset/list`
  - `POST /api/v1/public/dataset/info`
  - `POST /api/v1/public/dataset/query/capabilities`
  - `POST /api/v1/public/dataset/query/execute`
- 公开接口不再读取后台当前工作版本，而是读取 `published_version`
- 后台接口继续读取 `current_version`
- 已验证：
  - 发布后 `public/dataset/info` 可读取公开版本
  - 后台切换 `current_version` 后，`public/dataset/info` 仍保持原公开版本
  - 撤回公开后，`public/dataset/info` 返回 `404`

当前结论：

- 前后台查询语义已经开始分层
- 前台公开查询可以不再依赖后台当前正在编辑的版本

### Checkpoint 9：把 version-level publish 做完整

已完成的部分：

- 新增 `dataset_version_publish_record` 表
- 新增版本级发布审计接口：
  - `POST /api/v1/dataset/version/publish/records`
- `publish/unpublish` 现在会同步写入版本级审计
- 当发布新的当前版本时：
  - 目标版本写入 `publish` 记录
  - 被替换的公开版本写入 `unpublish` 记录
- 当撤回公开时：
  - 当前公开版本写入 `unpublish` 记录

当前设计含义：

- dataset 顶层发布记录保留，用于兼容 dataset 级审计视图
- version 级发布记录用于回答“哪个版本何时被公开/撤回”
- 后台继续读取 `current_version`
- 公开接口继续读取 `published_version`

当前限制：

- 目前仍通过应用层逻辑保证“单 dataset 单 public version”
- 数据库层面还没有唯一约束或独立发布指针表
- 如果未来要支持更强一致性，建议补：
  - 唯一索引
  - 或 `dataset_release_pointer` 之类的显式发布指针模型

### Checkpoint 10：引入文件角色与暂存区

目标：

- 把“浏览器上传 -> 暂存 -> 校验 -> 建索引 -> 发布”闭环补齐

建议：

- 引入统一 staging 目录
- 版本级文件角色建模：
  - raw
  - index
  - metadata
  - derived
- 支持任务失败重试与中间产物保留

### Checkpoint 11：把前台查询 API 正式分层

目标：

- 后台管理 API、前台受控查询 API、公开查询 API 边界清楚

建议未来分组：

- `/api/v1/admin/dataset/*`
- `/api/v1/query/dataset/*`
- `/api/v1/public/dataset/*`

## 10. 当前结论

本轮改造已经把系统从“只有 database 资产概念”推进到“database 作为底层资产事实，dataset 作为上层业务域”的状态。

这一步的价值在于：

- 没有推翻旧后台
- 后端已经能承载标准流程语义
- 上传、校验、索引已经有统一入口
- 版本体系已经可以承载后台工作版本
- 后续可以继续往 `version-level publish / staging / public query` 三条线收敛

如果下一步继续推进，我建议优先做：

1. 标准 ingest 流程
2. `dataset version` 正式建模
3. 将 `basis` 查询能力按 adapter 逐步迁入 `dataset/query`

## 11. 2026-04 现状补充

这份文档前半部分记录的是最初 checkpoint 推进时的状态。到 `2026-04`，实际落地已经继续向前推进，下面用“当前真实状态”补充说明。

### 11.1 Checkpoint 完成度总览

| Checkpoint | 当前状态 | 说明 |
| --- | --- | --- |
| 0 | 已完成 | 后端结构已稳定收敛到 `backend/api-server` |
| 1 | 已完成 | `dataset/*` 与 `admin/public/query` 路由已长期可用 |
| 2 | 已完成 | 控制面表、版本表、资产表、文件表、血缘表、发布记录表均已落地 |
| 3 | 已完成 | 开发环境启动时会自动补齐 dataset 新表与必要字段 |
| 4 | 已完成 | `dataset` 生命周期、任务审计、状态推进已打通 |
| 5 | 已完成并超出原定义 | adapter 已从早期的 `sequence/variant/expression/generic` 扩展到 `annotation/signal/interaction/functional_annotation` |
| 6 | 第一阶段完成 | ingest/register/staging/pipeline 已可用，但浏览器上传到正式发布的完整产品闭环仍可继续收口 |
| 7 | 已完成 | `dataset_version` 已成为后台工作版本主语义 |
| 8 | 已完成 | 公开查询已正式读取 `public version`，不再跟随后台 current version |
| 9 | 已完成 | 版本级发布/撤回/默认公开语义与审计已稳定 |
| 10 | 第一阶段完成 | 已有文件角色与 staging，但还未把所有资产生产流程都产品化 |
| 11 | 基本完成 | 路由已分层为 `/admin`、`/query`、`/public`，但前端体验仍可继续整理 |

当前判断：

- 如果只按原 checkpoint 文档判断，主体工作已经基本完成。
- 真正还没完成的是原文档后面没有展开的“更深一层业务能力”，尤其是功能注释平台化检索与更完整的前端管理体验。

### 11.2 当前 adapter 与资产能力

当前系统已经支持以下 dataset asset-first 查询主线：

- `reference_fasta`
- `gene_annotation`
- `functional_annotation`
- `variant_vcf`
- `expression_matrix`
- `signal_track`
- `interaction_matrix`

对应 adapter 当前已接入：

- `sequence`
- `annotation`
- `functional_annotation`
- `variant`
- `expression`
- `signal`
- `interaction`
- `generic`

其中：

- `functional_annotation` 已支持 `gene_detail / transcript_detail / gene_function_summary`
- `signal` 已支持 BED 与 BigWig 查询
- `interaction` 已支持 BEDPE 最小主线与 cool/mcool 基础矩阵读取

### 11.3 functional_annotation 当前落地状态

这一块已经不再停留在设计讨论，当前已完成第一阶段整合：

- `functional_annotation` 已成为正式 `asset_type`
- `genome.db` 已可作为 `functional_annotation` 主文件挂到 `sequence dataset` 的某个 version 下
- 后端已有真实 adapter：
  - `backend/api-server/apps/datasets/adapters/functional_annotation.py`
- portal 与 admin 的版本查询工作台已可直接执行功能注释查询
- 旧 `genome` 基因/转录本详情页已开始优先读取 Dataset 平台中的 `functional_annotation` 资产

当前已继续落地第二阶段：

- 已新增 PostgreSQL `functional_gene / functional_term / functional_term_assignment` 三张索引表
- 已新增索引重建器：
  - `backend/api-server/apps/datasets/functional_indexing.py`
- `functional_annotation` adapter 已新增：
  - `term_lookup`
  - `term_gene_list`
  - `term_aggregation`
- 索引会在 `functional_annotation` 主文件注册/更新时自动重建
- 也提供手动 CLI：
  - `scripts/dev/rebuild-functional-annotation-index.py`

当前真实状态应更新为：

- “版本内功能详情查询已落地”
- “单版本平台级 term 检索 / 反查 / 聚合已落地”
- “跨版本 / 跨物种功能检索仍待后续实施”

### 11.4 genome bundle 纳管现状

当前已经补上了 genome 目录级别的 bundle 发现与注册能力，可把一个真实基因组目录自动注册为：

- 一个 `sequence dataset`
- 一个 `dataset version`
- 三个核心资产：
  - `reference_fasta`
  - `gene_annotation`
  - `functional_annotation`

当前实现：

- bundle 发现与注册：
  - `backend/api-server/apps/datasets/bundle_provisioning.py`
- CLI：
  - `scripts/dev/provision-sequence-bundle.py`

已验证的真实数据：

- `/Users/kentnf/projects/data/test_data/genome/dataset01`

已成功登记为：

- dataset: `arabidopsis_dataset01`
- version: `TAIR10`
- 资产：
  - `reference_fasta`
  - `gene_annotation`
  - `functional_annotation`

并已验证：

- 真实 `functional_annotation` 查询链路可返回 `AT1G01010` 的详情
- 已为真实 `TAIR10` 版本重建 PostgreSQL term 索引，当前规模约为：
  - `functional_gene`: `27654`
  - `functional_term`: `22241`
  - `functional_term_assignment`: `1850802`
- 真实 `term_lookup` 已可返回 GO 反查结果

### 11.4.1 variome bundle 纳管现状

当前已补上 `variome` 作为正式 `dataset_type` 的第一阶段接入能力：

- `variome` 已作为外部可见 dataset kind 注册
- 内部继续复用 `variant` 的资产与查询语义：
  - 默认主资产类型为 `variant_vcf`
  - 继续走 `tabix/bcftools` 这一套索引/查询能力
- bundle 发现与注册：
  - `backend/api-server/apps/datasets/bundle_provisioning.py`
- CLI：
  - `scripts/dev/provision-variome-bundle.py`

本轮已补上的关键行为：

- 目录发现时优先选择“带索引的主变异文件”
  - 例如优先 `*.vcf.gz + .csi/.tbi`
  - 其次 `*.bcf + .csi`
- 注册后会生成：
  - 一个 `variome dataset`
  - 一个 `dataset version`
  - 一个查询主资产：
    - `variant_calls`
- 当提供 `reference_version_id` 时，会自动补 `called_against` 血缘关系

当前已完成验证：

- 自动化回归已通过：
  - `backend/api-server/tests/test_dataset_variome_alias.py`
  - `backend/api-server/tests/test_dataset_public_semantics.py::test_variome_bundle_provisioning_registers_indexed_variant_asset_and_reference_lineage`
- 真实目录 dry-run 已通过：
  - `/Users/kentnf/projects/data/test_data/variome`
- 当前 dry-run 识别结果为：
  - 主文件：`gwas358_AB.snp.mafgeno.test.vcf.gz`
  - 索引：`gwas358_AB.snp.mafgeno.test.vcf.gz.csi`
- 已明确暂不纳管：
  - `test.bcf.json`
  - `test.h5`

这意味着当前状态是：

- `variome` 已具备“真实目录 -> 正式 dataset/version/asset” 的代码能力
- 真实测试目录的自动识别结果已验证正确
- 下一步只剩把它正式注册进当前开发库，并和 `SMT2024` 参考基因组版本绑定

### 11.5 前端当前状态

当前前端并非完全空白，已有以下能力：

- admin Dataset 工作台可查看版本、资产、文件、血缘、发布记录、查询能力
- admin 版本工作台可直接执行 `functional_annotation` 查询
- portal 公共查询页已支持 `functional_annotation`
- 旧 `genome` 基因/转录本详情页已开始接入 Dataset 资产语义

本轮已继续补齐：

- admin 版本工作台已新增 `term_lookup / term_gene_list / term_aggregation` 的结构化输入与结果展示
- portal 公共查询页已新增同样三类 `functional_annotation` term 查询入口
- admin 旧变异查询页已开始兼容 `variome` dataset：
  - 变异数据选择框会同时读取 `variant` 与 `variome`
  - 当 dataset 已登记 `called_against` 等 lineage 时，页面顶部会显示它绑定的参考基因组
- 用户现在可以直接在前端做：
  - term 检索
  - term 反查 gene
  - term 聚合查看

当前缺口主要变成：

- term 查询已经能用，但还停留在“查询工作台”层，不是独立功能页
- 真实 genome bundle 的入口虽然已补顺，但功能检索页仍可继续做成更清晰的专用界面
- 跨版本 / 跨物种功能检索还没有前端承接

### 11.6 下一阶段建议

按当前系统状态，后续优先级建议调整为：

1. 继续把前端功能检索页补出来，让用户直接使用 `term_lookup / term_gene_list / term_aggregation`
2. 再做跨版本检索语义，而不是只停留在单 version
3. 最后再评估跨物种检索与更复杂的 faceted search

一句话总结当前 checkpoint 状态：

- 原 checkpoint 主干已经基本完成；
- 现在真正的主线已经从“搭骨架”进入“把真实组学资产接进来，并补功能注释平台化检索”阶段。
