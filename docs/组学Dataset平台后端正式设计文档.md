# 组学 Dataset 平台后端正式设计文档

## 1. 文档目标

本文档定义组学数据基础平台后端的正式目标架构，用于指导当前 `backend/api-server/` 从“旧 `database` 资产模型”逐步收敛到“以 `dataset` 为核心业务域”的后续改造。

本文档重点解决以下问题：

- 如何把一个组学对象建模为可管理、可发布、可查询的数据集
- 如何表达一个 `dataset` 下的多个 `version`
- 如何表达一个 `version` 下的多个文件及其索引、派生文件
- 如何表达不同数据之间的血缘关系
- 如何统一后台管理、前台受控查询、前台公开查询三类接口语义
- 如何在不推翻现有后端的前提下平滑迁移

## 2. 适用范围

本设计面向以下组学数据类型：

- 参考基因组 FASTA
- 基因注释与功能注释 GFF/GTF/TSV/HDF5/SQLite
- 变异数据 VCF/BCF
- 表达矩阵与表达索引 HDF5
- 表观遗传区域与信号文件 BED/BigWig
- 互作组学与其它异构文件型数据

本设计默认：

- 后台是数据管理与流程控制入口
- 前台网站不直接写数据，只读后台 API
- 组学数据以文件为核心事实源，不强制落关系型数据库
- 查询接口主要依赖文件索引、HDF5、SQLite 及外部二进制工具

## 3. 设计原则

### 3.1 文件为事实源，数据库为控制面

本平台不把所有组学内容强制导入关系数据库。关系数据库主要承担：

- 元数据登记
- 工作流与发布控制
- 权限与可见性控制
- 文件索引与血缘关系登记
- 查询入口与路由信息维护

真正的组学数据内容仍保留在文件中，例如：

- FASTA + FAI
- VCF.GZ + TBI
- HDF5
- SQLite
- BigWig

### 3.2 业务对象不等于文件

平台的核心管理对象不是单个文件，而是一个可被理解、可被发布、可被查询的业务数据集。

因此要把以下几层语义拆开：

- `Dataset`：逻辑数据集
- `DatasetVersion`：数据集版本
- `DatasetAsset`：版本下的一类业务资产
- `AssetFile`：资产对应的物理文件

### 3.3 状态拆分，不混用

系统中“处理阶段”“可见性”“发布状态”不能混在同一个字段里。

建议拆为三类状态：

- `workflow_state`：数据处理阶段
- `visibility_scope`：谁有权访问
- `release_state`：是否作为前台可查询版本发布

### 3.4 兼容式重构

当前系统已存在：

- `apps/databases`
- 用户、团队、项目、角色、权限体系
- dataset 兼容层与部分 dataset 表

因此后续应坚持：

- 不直接推翻旧能力
- 先增加新控制层
- 再逐步把业务读写切到新模型

## 4. 核心术语

### 4.1 Dataset

一个具有业务意义的逻辑数据集，是平台内的一级核心对象。

示例：

- `A物种参考基因组`
- `A物种群体变异集`
- `A物种组织表达图谱`

### 4.2 DatasetVersion

一个 `dataset` 的一个版本，是实际发布、查询、追踪血缘的主要粒度。

示例：

- `IRGSP-1.0`
- `IRGSP-1.1`
- `panel_2025`

### 4.3 DatasetAsset

某个 `dataset version` 下的一类业务资产，用来承载“同一版本中的不同组成部分”。

示例：

- `reference_fasta`
- `gene_annotation`
- `functional_annotation`
- `variant_vcf`
- `expression_matrix`

### 4.4 AssetFile

一个资产实际对应的物理文件及其角色信息。

示例：

- `genome.fa`
- `genome.fa.fai`
- `genes.gff3`
- `genes.sqlite`
- `cohort.vcf.gz`
- `cohort.vcf.gz.tbi`

### 4.5 Lineage

数据间的来源、依赖、派生、参考关系。

示例：

- 某个 VCF 基于某个参考基因组版本产生
- 某个表达矩阵是根据某版注释量化得到
- 某个功能注释表由某版 GFF 派生得到

## 5. 领域模型

## 5.1 总体关系

```text
Dataset
  ├── DatasetVersion (1:N)
  │     ├── DatasetAsset (1:N)
  │     │     └── AssetFile (1:N)
  │     ├── WorkflowRun / WorkflowTask (1:N)
  │     ├── ReleaseRecord (1:N)
  │     └── LineageEdge (1:N or N:N through edge)
  └── ACL / Project / Team / Tags / Meta
```

## 5.2 Dataset

`Dataset` 表示一个逻辑业务对象，用于回答“这是什么数据”。

建议核心字段：

- `id`
- `dataset_code`
- `name`
- `title`
- `dataset_kind`
- `organism_id`
- `organism_name`
- `category`
- `summary`
- `owner_team_id`
- `owner_project_id`
- `default_public_version_id`
- `current_version_id`
- `status`
- `create_time`
- `update_time`

说明：

- `dataset_kind` 用于表示业务大类，如 `reference_genome`、`variant_collection`、`expression_set`
- `current_version_id` 表示后台当前工作版本，只能有一个
- `default_public_version_id` 表示前台默认展示版本，只能有一个

## 5.3 DatasetVersion

`DatasetVersion` 是实际查询、发布、血缘追踪的主粒度，用于回答“这份数据的哪个版本”。

建议核心字段：

- `id`
- `dataset_id`
- `version_code`
- `version_name`
- `version_label`
- `workflow_state`
- `visibility_scope`
- `release_state`
- `is_default_public`
- `is_current`
- `assembly_name`
- `annotation_version`
- `source_type`
- `source_note`
- `meta_json`
- `create_time`
- `update_time`

建议约束：

- 同一 `dataset_id` 下 `version_code` 唯一
- 同一 `dataset` 只能有一个 `is_current = 1`
- 同一 `dataset` 只能有一个 `is_default_public = 1`
- 允许同一 `dataset` 存在多个 `release_state = released`

这意味着：

- 可以同时公开多个版本供前台切换查询
- 但只能有一个默认公开版本
- 后台只能有一个当前编辑版本

## 5.4 DatasetAsset

`DatasetAsset` 解决“一个 version 下有多个文件和多个业务组成部分”的问题。

建议核心字段：

- `id`
- `dataset_version_id`
- `asset_code`
- `asset_name`
- `asset_type`
- `file_format`
- `query_engine`
- `storage_backend`
- `status`
- `is_required`
- `is_query_entry`
- `display_order`
- `meta_json`
- `create_time`
- `update_time`

建议典型 `asset_type`：

- `reference_fasta`
- `gene_annotation`
- `functional_annotation`
- `variant_vcf`
- `expression_matrix`
- `signal_track`
- `interaction_matrix`
- `metadata_table`

说明：

- 一个 `version` 下面可有多个 `asset`
- 一个 `asset` 承载一类业务能力
- 查询入口应优先挂在 `asset` 上，而不是继续挂在单一 `dataset_version.file_path` 上

## 5.5 AssetFile

`AssetFile` 解决“一个资产对应多个物理文件”的问题。

建议核心字段：

- `id`
- `dataset_asset_id`
- `file_role`
- `file_name`
- `storage_uri`
- `local_path`
- `file_format`
- `mime_type`
- `checksum_type`
- `checksum_value`
- `file_size`
- `compress_type`
- `index_of_file_id`
- `status`
- `meta_json`
- `create_time`
- `update_time`

建议典型 `file_role`：

- `primary`
- `index`
- `derived`
- `metadata`
- `preview`
- `log`
- `report`

### 5.5.1 示例一：参考基因组 FASTA

```text
Dataset: A物种参考基因组
Version: v2
Asset: reference_fasta
  - genome.fa            role=primary
  - genome.fa.fai        role=index
```

### 5.5.2 示例二：基因注释

```text
Dataset: A物种参考基因组
Version: v2
Asset: gene_annotation
  - genes.gff3           role=primary
  - genes.sqlite         role=derived
  - genes.summary.json   role=metadata
```

### 5.5.3 示例三：VCF

```text
Dataset: A物种群体变异集
Version: panel_2025
Asset: variant_vcf
  - cohort.vcf.gz        role=primary
  - cohort.vcf.gz.tbi    role=index
```

## 5.6 LineageEdge

`LineageEdge` 用于表达数据间血缘，不建议再塞入备注或 JSON 字段作为唯一事实源。

建议核心字段：

- `id`
- `src_dataset_version_id`
- `src_asset_id`
- `dst_dataset_version_id`
- `dst_asset_id`
- `relation_type`
- `direction`
- `detail_json`
- `create_time`

建议关系类型：

- `uses_reference`
- `derived_from`
- `annotated_by`
- `quantified_against`
- `called_against`
- `lifted_from`
- `converted_from`

### 5.6.1 推荐做法

第一阶段先支持 `version` 级血缘。

示例：

```text
rice_population_variants:panel_2025
  --uses_reference-->
rice_reference_genome:IRGSP-1.1
```

第二阶段再补 `asset` 级血缘。

示例：

```text
variant_vcf asset
  --called_against-->
reference_fasta asset
```

这样可以在不增加过多复杂度的前提下，先解决主要业务问题。

补充说明：

- 当前代码实现已经允许在 `lineage_edge` 中可选填写 `src_asset_id` / `dst_asset_id`
- 但平台主视角仍建议保持在 `version` 级，`asset` 级血缘只在确有业务价值时再使用

## 5.7 WorkflowTask

`WorkflowTask` 用于记录标准流程执行轨迹。

建议核心字段：

- `id`
- `dataset_version_id`
- `dataset_asset_id`
- `task_type`
- `task_status`
- `workflow_state_before`
- `workflow_state_after`
- `operator_id`
- `run_id`
- `detail`
- `log_uri`
- `create_time`
- `finish_time`

建议 `task_type`：

- `register`
- `upload`
- `validate`
- `index`
- `convert`
- `publish`
- `unpublish`
- `archive`

## 5.8 ReleaseRecord

`ReleaseRecord` 记录版本级发布与撤回记录。

建议核心字段：

- `id`
- `dataset_id`
- `dataset_version_id`
- `action`
- `visibility_before`
- `visibility_after`
- `release_state_before`
- `release_state_after`
- `operator_id`
- `note`
- `create_time`

说明：

- 发布审计应以 `dataset_version` 为主
- `dataset` 顶层发布记录仅作为聚合视图或兼容视图保留

## 5.9 ACL / PermissionBinding

权限控制建议从一开始就纳入正式模型。

建议核心字段：

- `id`
- `resource_type`
- `resource_id`
- `subject_type`
- `subject_id`
- `permission_code`
- `effect`
- `create_time`
- `update_time`

资源粒度建议支持：

- `dataset`
- `dataset_version`
- `dataset_asset`

默认继承规则建议：

- `dataset` 级权限作为默认规则
- `version` 可覆盖 `dataset`
- `asset` 可进一步细化

## 6. 生命周期与状态模型

## 6.1 为什么要拆分状态

当前系统里容易混淆的根因是，把“处理状态”“是否公开”“是否可发布”混在了一起。

正式设计中建议拆成以下三类：

### 6.1.1 workflow_state

表示数据处理流程进行到哪一步。

建议值：

- `draft`
- `registered`
- `uploaded`
- `validating`
- `validated`
- `indexing`
- `ready`
- `failed`
- `archived`

### 6.1.2 visibility_scope

表示谁有权限看到这条数据。

建议值：

- `private`
- `team`
- `project`
- `public`

### 6.1.3 release_state

表示这个版本是否作为前台可查询对象被发布。

建议值：

- `unreleased`
- `released`
- `deprecated`
- `withdrawn`

## 6.2 一个完整例子

以 `A物种参考基因组 v2` 为例：

1. 刚登记完成
   - `workflow_state = uploaded`
   - `visibility_scope = project`
   - `release_state = unreleased`

2. 校验和建索引完成
   - `workflow_state = ready`
   - `visibility_scope = project`
   - `release_state = unreleased`

3. 发布给前台查询
   - `workflow_state = ready`
   - `visibility_scope = public`
   - `release_state = released`

4. 被新版本替代，但历史版本仍保留访问
   - `workflow_state = ready`
   - `visibility_scope = public`
   - `release_state = deprecated`

5. 撤回前台公开访问
   - `workflow_state = ready`
   - `visibility_scope = project`
   - `release_state = withdrawn`

## 6.3 推荐约束

- `workflow_state` 不负责表示“是否公开”
- `visibility_scope` 不负责表示“是否是默认公开版本”
- `release_state` 不负责表示“是否校验完成”

三者必须分离。

## 6.4 第一阶段状态机建议

第一阶段建议只把状态机做成“稳定、可解释、可实现”的最小集合，不追求一步覆盖所有异常分支。

### 6.4.1 `workflow_state` 推荐流转

建议主链路：

```text
draft
  -> registered
  -> uploaded
  -> validating
  -> validated
  -> indexing
  -> ready
```

失败与收尾分支：

```text
validating -> failed
indexing -> failed
failed -> validating
failed -> indexing
ready -> archived
withdrawn version -> archived
```

第一阶段推荐规则：

- `publish` 之前必须满足 `workflow_state = ready`
- `released` 或 `deprecated` 的版本，不应回退到 `draft`
- `failed` 允许重试，但必须记录新的任务记录

### 6.4.2 `visibility_scope` 推荐流转

建议流转：

```text
private <-> team <-> project <-> public
```

第一阶段推荐规则：

- `public` 只应在版本发布时由系统显式设置
- 撤回公开后建议回退到 `project` 或发布前保存的原值
- 普通版本编辑不应隐式把 `visibility_scope` 改成 `public`

### 6.4.3 `release_state` 推荐流转

建议流转：

```text
unreleased -> released
released -> deprecated
released -> withdrawn
deprecated -> withdrawn
withdrawn -> released
```

第一阶段推荐规则：

- `release_state = released` 必须同时满足：
  - `workflow_state = ready`
  - `visibility_scope = public`
- `deprecated` 表示仍可查询，但不再是主推荐版本
- `withdrawn` 表示前台不再可查

### 6.4.4 默认公开版本切换规则

对于同一个 `dataset`：

- 可以有多个 `released_versions`
- 但只能有一个 `default_public_version`

推荐切换规则：

1. 发布一个新版本时，可选择：
   - 仅 `released`
   - `released + set_default_public`
2. 如果设置为新的默认公开版本：
   - 原 `default_public_version` 保持 `released` 或变为 `deprecated`
   - 不必强制撤回原版本

示例：

```text
v1 = released
v2 = released
v3 = released + default_public
```

此时前台默认走 `v3`，但仍允许用户切换查看 `v1`、`v2`。

## 6.5 第一阶段标准流程建议

第一阶段建议把后台管理流程固定为：

```text
register
  -> validate
  -> index
  -> release
  -> set_default_public
```

其中：

- `register`
  - 建立 `dataset`、`dataset_version`、`dataset_asset`、`asset_file`
- `validate`
  - 校验文件存在性、格式合法性、元数据完整性
- `index`
  - 生成索引文件或派生查询文件
- `release`
  - 将 `release_state` 设为 `released`
- `set_default_public`
  - 只修改 `dataset.default_public_version_id`

第一阶段不建议把“发布”和“设为默认公开版本”强绑定为一个不可分动作。

## 7. 发布模型

## 7.1 推荐规则

对于一个 `dataset`：

- 只能有一个 `current_version`
- 可以有多个 `released_versions`
- 只能有一个 `default_public_version`

## 7.2 设计含义

这套规则适合组学平台的现实需求：

- 后台人员始终围绕一个当前工作版本进行修改
- 前台可以同时开放多个历史版本给用户选择
- 门户首页和默认查询落到一个默认公开版本

## 7.3 典型例子

`A物种参考基因组` 有三个版本：

- `v1`
- `v2`
- `v3`

其中：

- `current_version = v3`
- `released_versions = {v1, v2, v3}`
- `default_public_version = v3`

此时前台可以：

- 默认展示 `v3`
- 允许用户切换到 `v1` 或 `v2`

后台则继续只在 `v3` 上进行维护。

## 8. 文件组织与存储设计

## 8.1 设计目标

需要同时解决：

- 一个 `version` 下多个资产
- 一个 `asset` 下多个物理文件
- 文件、索引、派生物、日志清晰分离
- 未来支持本地磁盘、NAS、对象存储

## 8.2 逻辑目录建议

建议按 `dataset -> version -> asset` 组织：

```text
/data/omics/
  datasets/
    {dataset_code}/
      versions/
        {version_code}/
          assets/
            {asset_code}/
              primary/
              index/
              derived/
              metadata/
              logs/
```

示例：

```text
/data/omics/datasets/rice_reference_genome/versions/irgsp_1_1/assets/reference_fasta/primary/genome.fa
/data/omics/datasets/rice_reference_genome/versions/irgsp_1_1/assets/reference_fasta/index/genome.fa.fai
/data/omics/datasets/rice_reference_genome/versions/irgsp_1_1/assets/gene_annotation/primary/genes.gff3
/data/omics/datasets/rice_reference_genome/versions/irgsp_1_1/assets/gene_annotation/derived/genes.sqlite
```

## 8.3 为什么不建议只存一个 `file_path`

只存单个 `file_path` 会带来以下问题：

- 无法表达多个文件
- 无法表达主文件和索引文件关系
- 无法表达派生文件
- 无法支持一个版本下多个不同业务资产

因此后续应逐步把当前的单文件思路迁移到 `asset + asset_file`。

## 8.4 存储 URI 建议

建议统一使用 `storage_uri` 抽象物理位置，例如：

- `file:///data/omics/...`
- `nas://cluster-a/...`
- `s3://omics-bucket/...`

这样可以让未来的存储后端切换成本更低。

## 9. 血缘关系设计

## 9.1 需要解决的问题

组学平台中很多数据都依赖其它数据：

- VCF 依赖参考基因组版本
- 表达量化依赖基因注释版本
- 功能注释可能依赖某版基因注释或蛋白序列
- 某些派生表格是由 HDF5、SQLite 或 GFF 转换得到

如果不正式建模：

- 前台无法明确告诉用户“这份数据基于什么”
- 后台无法做影响分析
- 重新发布参考版本后，无法判断哪些数据需要重建

## 9.2 设计建议

第一阶段以 `dataset_version` 为主做血缘建模。

原因：

- 足够覆盖大部分业务语义
- 模型更稳，复杂度更低
- 能较快落地影响分析和前台展示

## 9.3 典型场景

### 9.3.1 VCF 依赖参考基因组

```text
Dataset: A物种群体变异集
Version: panel_2025

Lineage:
panel_2025 --uses_reference--> reference_genome:v2
```

### 9.3.2 表达矩阵依赖注释版本

```text
Dataset: A物种组织表达图谱
Version: expr_2025

Lineage:
expr_2025 --quantified_against--> reference_genome:v2
expr_2025 --annotated_by--> gene_annotation:v2
```

### 9.3.3 功能注释来自 GFF 派生

```text
functional_annotation:v2
  --derived_from-->
gene_annotation:v2
```

## 9.4 后续扩展

如果将来需要更细粒度的追踪，可以把血缘下钻到 `asset` 级别，但不建议第一阶段就一次做满。

补充说明：

- 当前实现层面已经支持可选 `asset` 级血缘登记
- 设计上仍应避免把所有关系都下钻到资产粒度，优先保留“版本主干、资产补充”的表达方式
- 当前产品决策是：公开前台暂不展示 lineage，后续如需开放，应单独评估公开版本对私有依赖关系的暴露边界

## 10. 权限设计

## 10.1 权限目标

需要满足以下要求：

- 后台每条数据都有权限控制
- 公开后的版本可被前台查询
- 同一 `dataset` 的不同版本可见范围可能不同
- 某些敏感资产可只在后台可见，不对前台放开

## 10.2 推荐权限层级

建议权限以 `dataset` 为默认层，以 `version` 和 `asset` 为覆盖层。

同时，类型体系管理权限单独定义，不属于团队级业务权限。

### 10.2.1 Dataset 层

控制谁可以：

- 查看该数据集
- 修改元数据
- 创建新版本
- 执行发布与撤回

### 10.2.2 Version 层

控制谁可以：

- 查看某个版本
- 启动校验与索引
- 发布某个版本
- 将某版本设为默认公开版本

### 10.2.3 Asset 层

控制谁可以：

- 查看某类资产
- 下载文件
- 使用查询接口
- 修改派生文件

### 10.2.4 类型注册表管理权限

类型注册表包括：

- `dataset_kind_registry`
- `asset_type_registry`

这两类注册表的维护权限建议严格限制为：

- 仅系统管理员可以新增
- 仅系统管理员可以修改
- 仅系统管理员可以停用
- 默认系统项由平台启动时自动补齐
- 但默认系统项只在“缺失”时补种，不应在启动时覆盖管理员已经调整过的配置

明确不开放给：

- 团队管理员
- 普通用户

原因：

- 类型定义会影响前端分类
- 类型定义会影响默认适配器、文件格式约束、工作流模板
- 类型一旦被大量数据使用，修改成本很高

因此类型体系属于平台级治理能力，而不是团队自治能力。

实现落地建议补充为：

- 业务侧表单接口只暴露“已启用”的类型 options
- 注册表列表、创建、修改、删除接口统一走系统管理员鉴权
- `dataset` 创建、更新、版本创建时必须校验 `dataset_kind` 是否存在
- `asset` 创建、更新时必须校验 `asset_type` 是否存在且是否允许挂到对应 `dataset_kind`

## 10.3 公开查询规则

建议前台公开查询遵循以下条件：

- `dataset_version.release_state in {released, deprecated}`
- `dataset_version.visibility_scope = public`
- 对应 `asset.is_query_entry = true`
- 对应 `asset` 或 `asset_file` 状态为可用

## 11. API 分层设计

## 11.1 总体分层

建议把 API 语义分成三层：

- 后台管理 API
- 前台受控查询 API
- 前台公开查询 API

建议命名：

- `/api/v1/admin/*`
- `/api/v1/query/*`
- `/api/v1/public/*`

## 11.2 后台管理 API

职责：

- 数据集 CRUD
- 版本管理
- 资产管理
- 文件登记
- 工作流触发
- 发布控制
- 权限控制
- 血缘维护

建议资源：

- `/admin/dataset/*`
- `/admin/dataset-version/*`
- `/admin/dataset-asset/*`
- `/admin/lineage/*`
- `/admin/workflow/*`

## 11.3 前台受控查询 API

职责：

- 面向登录用户
- 按权限查询指定版本或指定资产
- 支持多版本切换

建议资源：

- `/query/dataset/{dataset_code}`
- `/query/dataset/{dataset_code}/versions`
- `/query/dataset/{dataset_code}/versions/{version_code}`
- `/query/dataset/{dataset_code}/versions/{version_code}/assets/{asset_code}/capabilities`
- `/query/dataset/{dataset_code}/versions/{version_code}/assets/{asset_code}/execute`

## 11.4 前台公开查询 API

职责：

- 面向未登录用户
- 仅查询已公开发布的版本

建议规则：

- 不传版本时，默认走 `default_public_version`
- 传版本时，只允许访问 `released_versions`

建议资源：

- `/public/dataset/{dataset_code}`
- `/public/dataset/{dataset_code}/versions`
- `/public/dataset/{dataset_code}/versions/{version_code}`
- `/public/dataset/{dataset_code}/versions/{version_code}/assets/{asset_code}/capabilities`
- `/public/dataset/{dataset_code}/versions/{version_code}/assets/{asset_code}/execute`

## 11.5 第一阶段最小 API 草案

第一阶段不建议一次把全部分层接口做满，建议按“后台先完整，前台查询先够用”的策略推进。

### 11.5.1 后台管理 API 第一阶段

建议第一阶段优先落地以下接口组：

#### Dataset

- `POST /api/v1/admin/dataset/list`
- `POST /api/v1/admin/dataset/info`
- `POST /api/v1/admin/dataset/create`
- `POST /api/v1/admin/dataset/update`

#### Dataset Version

- `POST /api/v1/admin/dataset-version/list`
- `POST /api/v1/admin/dataset-version/info`
- `POST /api/v1/admin/dataset-version/create`
- `POST /api/v1/admin/dataset-version/activate`
- `POST /api/v1/admin/dataset-version/release`
- `POST /api/v1/admin/dataset-version/withdraw`
- `POST /api/v1/admin/dataset-version/set-default-public`

#### Dataset Asset

- `POST /api/v1/admin/dataset-asset/list`
- `POST /api/v1/admin/dataset-asset/info`
- `POST /api/v1/admin/dataset-asset/create`
- `POST /api/v1/admin/dataset-asset/update`

#### Asset File

- `POST /api/v1/admin/asset-file/list`
- `POST /api/v1/admin/asset-file/register`
- `POST /api/v1/admin/asset-file/update`

#### Workflow

- `POST /api/v1/admin/workflow/validate`
- `POST /api/v1/admin/workflow/index`
- `POST /api/v1/admin/workflow/pipeline`
- `POST /api/v1/admin/workflow/tasks`

#### Lineage

- `POST /api/v1/admin/lineage/list`
- `POST /api/v1/admin/lineage/create`
- `POST /api/v1/admin/lineage/delete`

### 11.5.2 前台受控查询 API 第一阶段

建议第一阶段优先落地：

- `POST /api/v1/query/dataset/info`
- `POST /api/v1/query/dataset/versions`
- `POST /api/v1/query/dataset/assets`
- `POST /api/v1/query/dataset/query/capabilities`
- `POST /api/v1/query/dataset/query/execute`

第一阶段建议请求参数允许：

- `dataset_code`
- `version_code`
- `asset_code`
- `operation`
- `params`

推荐行为：

- 如果不传 `version_code`
  - 登录查询默认走 `dataset.current_version` 或前端显式指定的版本策略
- 如果传了 `version_code`
  - 必须先校验该版本权限
- 如果不传 `asset_code`
  - 当且仅当该版本下有唯一 `is_query_entry = true` 的资产时允许自动推断

### 11.5.3 前台公开查询 API 第一阶段

建议第一阶段优先落地：

- `POST /api/v1/public/dataset/info`
- `POST /api/v1/public/dataset/versions`
- `POST /api/v1/public/dataset/assets`
- `POST /api/v1/public/dataset/query/capabilities`
- `POST /api/v1/public/dataset/query/execute`

推荐行为：

- 不传 `version_code`
  - 默认使用 `dataset.default_public_version_id`
- 传了 `version_code`
  - 仅当该版本 `release_state in {released, deprecated}` 且 `visibility_scope = public` 时允许访问
- 不传 `asset_code`
  - 仅当存在唯一公开查询入口资产时允许自动推断

## 11.6 第一阶段关键接口语义

### 11.6.1 `release`

接口目标：

- 把一个 `dataset_version` 标记为对前台可查询

推荐前置条件：

- `workflow_state = ready`
- 版本权限允许发布
- 必需资产已齐备

推荐副作用：

- `release_state = released`
- `visibility_scope = public`
- 写入 `dataset_release_record`

### 11.6.2 `withdraw`

接口目标：

- 撤回某个公开版本

推荐副作用：

- `release_state = withdrawn`
- `visibility_scope` 回退到 `project` 或原记录值
- 如果该版本是 `default_public_version`
  - 需要清空默认值或切换到新的默认公开版本

### 11.6.3 `set-default-public`

接口目标：

- 设置某个已发布版本为前台默认版本

推荐前置条件：

- 目标版本必须已 `released` 或 `deprecated`
- 目标版本必须是 `visibility_scope = public`

推荐副作用：

- 更新 `dataset.default_public_version_id`
- 原默认公开版本不必自动撤回

### 11.6.4 查询接口

推荐统一查询参数：

- `dataset_code`
- `version_code`
- `asset_code`
- `operation`
- `params`

推荐统一查询解析顺序：

1. 找到 `dataset`
2. 确定 `version`
3. 确定 `asset`
4. 解析 `asset_type_base_code`
5. 选择对应 `query_adapter`
6. 基于 `asset_file` 找到主文件和索引文件
7. 执行查询

## 12. 典型业务场景建模

## 12.1 参考基因组

```text
Dataset: rice_reference_genome

Version: IRGSP-1.0
  Asset: reference_fasta
    - genome.fa
    - genome.fa.fai
  Asset: gene_annotation
    - genes.gff3
    - genes.sqlite
  Asset: functional_annotation
    - function.tsv
    - function.h5

Version: IRGSP-1.1
  Asset: reference_fasta
  Asset: gene_annotation
  Asset: functional_annotation
```

这是一组 `dataset`，两个 `version`，每个 `version` 下多个 `asset`。

## 12.2 群体变异

```text
Dataset: rice_population_variants

Version: panel_2025
  Asset: variant_vcf
    - cohort.vcf.gz
    - cohort.vcf.gz.tbi

Lineage:
panel_2025 --uses_reference--> rice_reference_genome:IRGSP-1.1
```

## 12.3 表达图谱

```text
Dataset: rice_expression_atlas

Version: expr_2025
  Asset: expression_matrix
    - matrix.h5
  Asset: sample_metadata
    - sample.tsv

Lineage:
expr_2025 --quantified_against--> rice_reference_genome:IRGSP-1.1
expr_2025 --annotated_by--> rice_reference_genome:IRGSP-1.1
```

## 13. 与当前后端的映射关系

## 13.1 当前已有能力

当前系统已具备：

- `dataset_registry`
- `dataset_workflow_task`
- `dataset_publish_record`
- `dataset_version`
- `dataset_version_publish_record`
- 基础 ingest API
- 轻量异步 ingest task 能力
- 基础 query adapter
- `current_version`
- `public` 只读 API

这些能力可以视为正式架构的第一阶段雏形。

## 13.2 当前不足

当前仍存在以下结构性缺口：

- `dataset_version` 仍偏单文件模型
- 缺少 `dataset_asset`
- 缺少 `asset_file`
- 缺少正式 `lineage_edge`
- 生命周期仍未完全拆成三类状态
- 顶层 `dataset` 与 `version` 状态仍有混叠
- ingest 仍是单进程内后台执行，尚未演进到独立 worker/queue

## 13.2.1 ingest 任务化现状补充

当前后端已经在不引入外部队列的前提下，完成一版低风险的 ingest 任务化：

- 保留同步接口：
  - `POST /api/v1/admin/dataset/ingest/validate`
  - `POST /api/v1/admin/dataset/ingest/index`
  - `POST /api/v1/admin/dataset/ingest/pipeline`
- 新增异步任务接口：
  - `POST /api/v1/admin/dataset/ingest/task/submit`
  - `POST /api/v1/admin/dataset/ingest/task/info`
  - `POST /api/v1/admin/dataset/ingest/task/retry`
- `dataset_workflow_task` 不再只是“事后写一条历史”，而是开始承载：
  - request
  - result
  - error
  - attempt
  - retry_of_task_id
  - started_at / finished_at

这意味着平台已经具备最小可用的“上传后进入校验/索引任务流”的基础框架。

但这仍然只是一期实现，当前边界要明确：

- 任务执行仍依赖 API 进程内的后台任务，不适合真正的大规模并发
- 没有取消、暂停、恢复到 step 的能力
- 没有独立的调度器、worker 池和任务清理策略

## 13.3 建议演进方向

### 阶段 1：稳定现有 dataset 控制层

- 保留现有 `dataset/*`
- 保留现有 `public/dataset/*`
- 明确 `current_version`、`released_versions`、`default_public_version`
- 将状态字段拆分为三类语义

### 阶段 2：引入资产层

新增表：

- `dataset_asset`
- `asset_file`

目标：

- 从单 `file_path` 模型迁移到多资产、多文件模型
- 让查询入口从 `dataset` 逐步下沉到 `asset`

### 阶段 3：引入血缘层

新增表：

- `lineage_edge`

目标：

- 支持查询依赖
- 支持影响分析
- 支持前台展示“该数据基于什么版本”

### 阶段 4：正式分层 API

目标：

- 后台管理 API
- 前台受控查询 API
- 前台公开查询 API

边界清晰，语义稳定。

## 14. 建议的数据库表草案

推荐核心表：

- `dataset`
- `dataset_version`
- `dataset_asset`
- `asset_file`
- `dataset_lineage_edge`
- `dataset_workflow_run`
- `dataset_workflow_task`
- `dataset_release_record`
- `dataset_acl_binding`

推荐兼容保留：

- `databases`
- `database_file`
- `dataset_registry`

其中：

- `dataset_registry` 可逐步收敛成 `dataset` 聚合视图
- `databases` 在迁移完成前仍作为旧资产兼容层

### 14.1 第一阶段优先落地的 5 张核心表

第一阶段建议优先落地以下 5 张表：

- `dataset`
- `dataset_version`
- `dataset_asset`
- `asset_file`
- `dataset_lineage_edge`

原因：

- 这 5 张表已经能支撑核心业务结构
- 可以先把“逻辑数据集 -> 版本 -> 资产 -> 文件 -> 血缘”主干立起来
- 工作流、发布记录、ACL 可以继续部分复用现有表，后续再逐步收敛

### 14.2 `dataset` 表草案

用途：

- 表示一个逻辑业务数据集
- 负责承载平台级元数据、默认公开版本、当前工作版本

建议字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 是 | 主键 |
| `dataset_code` | varchar(128) | 是 | 稳定编码，全局唯一 |
| `name` | varchar(255) | 是 | 内部名称 |
| `title` | varchar(255) | 否 | 展示标题 |
| `dataset_kind_code` | varchar(128) | 是 | 关联 `dataset_kind_registry.code` |
| `dataset_kind_base_code` | varchar(128) | 是 | 系统标准类型，用于程序逻辑 |
| `summary` | text | 否 | 数据集说明 |
| `organism_id` | bigint | 否 | 物种 ID，可与外部物种表关联 |
| `organism_name` | varchar(255) | 否 | 冗余物种名，便于检索 |
| `owner_team_id` | bigint | 否 | 所属团队 |
| `owner_project_id` | bigint | 否 | 所属项目 |
| `current_version_id` | bigint | 否 | 当前工作版本 |
| `default_public_version_id` | bigint | 否 | 默认公开版本 |
| `status` | varchar(32) | 是 | 数据集总体状态，如 `active/inactive` |
| `meta_json` | json/text | 否 | 扩展元数据 |
| `create_user_id` | bigint | 否 | 创建人 |
| `create_time` | bigint | 是 | 创建时间 |
| `update_time` | bigint | 是 | 更新时间 |

建议约束：

- `uk_dataset_code(dataset_code)`
- `idx_dataset_kind_base_code(dataset_kind_base_code)`
- `idx_owner_team_id(owner_team_id)`
- `idx_owner_project_id(owner_project_id)`

建议说明：

- `dataset_kind_code` 用于展示和注册表绑定
- `dataset_kind_base_code` 用于程序行为判断
- 第一阶段建议保留这两个字段，避免运行时频繁 join 注册表

### 14.3 `dataset_version` 表草案

用途：

- 表示 `dataset` 的一个具体版本
- 负责承载生命周期、可见性、发布状态

建议字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 是 | 主键 |
| `dataset_id` | bigint | 是 | 关联 `dataset.id` |
| `version_code` | varchar(128) | 是 | 版本稳定编码，如 `irgsp_1_1` |
| `version_name` | varchar(255) | 是 | 版本名称，如 `IRGSP-1.1` |
| `version_label` | varchar(255) | 否 | 前端展示标签 |
| `workflow_state` | varchar(32) | 是 | `draft/uploaded/validated/ready/...` |
| `visibility_scope` | varchar(32) | 是 | `private/team/project/public` |
| `release_state` | varchar(32) | 是 | `unreleased/released/deprecated/withdrawn` |
| `is_current` | tinyint | 是 | 是否当前工作版本 |
| `is_default_public` | tinyint | 是 | 是否默认公开版本 |
| `assembly_name` | varchar(255) | 否 | 组装版本名 |
| `annotation_version` | varchar(255) | 否 | 注释版本名 |
| `source_type` | varchar(64) | 否 | 来源类型，如 `import/manual/pipeline` |
| `source_note` | text | 否 | 来源说明 |
| `meta_json` | json/text | 否 | 扩展元数据 |
| `create_user_id` | bigint | 否 | 创建人 |
| `create_time` | bigint | 是 | 创建时间 |
| `update_time` | bigint | 是 | 更新时间 |

建议约束：

- `uk_dataset_version_code(dataset_id, version_code)`
- `idx_dataset_release(dataset_id, release_state)`
- `idx_dataset_visibility(dataset_id, visibility_scope)`
- `idx_dataset_workflow(dataset_id, workflow_state)`

建议业务约束：

- 同一 `dataset` 只能有一个 `is_current = 1`
- 同一 `dataset` 只能有一个 `is_default_public = 1`
- 同一 `dataset` 可以有多个 `release_state = released`

建议实现方式：

- 第一阶段可先用应用层保证唯一性
- 第二阶段再补数据库唯一约束或部分唯一索引

### 14.4 `dataset_asset` 表草案

用途：

- 表示某个版本下的一类业务资产
- 负责承载查询入口、资产类型、默认适配器和排序

建议字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 是 | 主键 |
| `dataset_version_id` | bigint | 是 | 关联 `dataset_version.id` |
| `asset_code` | varchar(128) | 是 | 资产稳定编码 |
| `asset_name` | varchar(255) | 是 | 资产名称 |
| `asset_type_code` | varchar(128) | 是 | 关联 `asset_type_registry.code` |
| `asset_type_base_code` | varchar(128) | 是 | 系统标准资产类型 |
| `file_format` | varchar(64) | 否 | 资产主文件格式 |
| `query_engine` | varchar(128) | 否 | 查询引擎 |
| `storage_backend` | varchar(64) | 否 | `local/nas/s3/...` |
| `workflow_state` | varchar(32) | 是 | 资产级流程状态 |
| `status` | varchar(32) | 是 | 资产可用状态 |
| `is_required` | tinyint | 是 | 是否为该 version 必需资产 |
| `is_query_entry` | tinyint | 是 | 是否可作为查询入口 |
| `display_order` | int | 是 | 展示顺序 |
| `meta_json` | json/text | 否 | 扩展配置 |
| `create_time` | bigint | 是 | 创建时间 |
| `update_time` | bigint | 是 | 更新时间 |

建议约束：

- `uk_version_asset_code(dataset_version_id, asset_code)`
- `idx_asset_type_base_code(asset_type_base_code)`
- `idx_asset_query_entry(dataset_version_id, is_query_entry)`

建议说明：

- `asset_type_code` 用于注册表和展示
- `asset_type_base_code` 用于查询适配器和工作流分发
- `workflow_state` 可以与 `dataset_version.workflow_state` 分离，便于未来支持“版本已存在，但单资产重建中”

### 14.5 `asset_file` 表草案

用途：

- 表示某个资产关联的一个具体物理文件
- 解决主文件、索引文件、派生文件、多文件并存的问题

建议字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 是 | 主键 |
| `dataset_asset_id` | bigint | 是 | 关联 `dataset_asset.id` |
| `file_role` | varchar(32) | 是 | `primary/index/derived/metadata/preview/log` |
| `file_name` | varchar(255) | 是 | 文件名 |
| `storage_uri` | varchar(1024) | 是 | 统一存储 URI |
| `local_path` | varchar(1024) | 否 | 本地挂载路径 |
| `file_format` | varchar(64) | 否 | 文件格式 |
| `mime_type` | varchar(128) | 否 | MIME 类型 |
| `checksum_type` | varchar(32) | 否 | `md5/sha256/...` |
| `checksum_value` | varchar(255) | 否 | 校验值 |
| `file_size` | bigint | 否 | 文件大小 |
| `compress_type` | varchar(32) | 否 | 压缩类型 |
| `index_of_file_id` | bigint | 否 | 如果本文件是索引文件，指向主文件 |
| `status` | varchar(32) | 是 | `active/inactive/missing/broken` |
| `meta_json` | json/text | 否 | 扩展信息 |
| `create_time` | bigint | 是 | 创建时间 |
| `update_time` | bigint | 是 | 更新时间 |

建议约束：

- `idx_dataset_asset_id(dataset_asset_id)`
- `idx_file_role(dataset_asset_id, file_role)`
- `idx_index_of_file_id(index_of_file_id)`
- `uk_storage_uri(storage_uri)` 或按存储后端设计为弱唯一

建议说明：

- `storage_uri` 是正式事实字段
- `local_path` 是为了兼容当前本地运行与既有工具链
- 第一阶段可以两者并存，第二阶段逐步统一到 `storage_uri`

### 14.6 `dataset_lineage_edge` 表草案

用途：

- 记录版本之间或资产之间的血缘关系
- 第一阶段以 `dataset_version` 级为主

建议字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | bigint | 是 | 主键 |
| `src_dataset_version_id` | bigint | 否 | 来源版本 |
| `src_asset_id` | bigint | 否 | 来源资产，第一阶段可为空 |
| `dst_dataset_version_id` | bigint | 否 | 目标版本 |
| `dst_asset_id` | bigint | 否 | 目标资产，第一阶段可为空 |
| `relation_type` | varchar(64) | 是 | `uses_reference/derived_from/...` |
| `direction` | varchar(16) | 是 | 默认 `forward` |
| `detail_json` | json/text | 否 | 血缘说明 |
| `create_user_id` | bigint | 否 | 创建人 |
| `create_time` | bigint | 是 | 创建时间 |

建议约束：

- `idx_src_dataset_version_id(src_dataset_version_id)`
- `idx_dst_dataset_version_id(dst_dataset_version_id)`
- `idx_relation_type(relation_type)`

第一阶段建议规则：

- 要求至少有一端是 `dataset_version`
- 优先维护 `version -> version` 关系
- `asset -> asset` 关系作为第二阶段增强能力

### 14.7 第一阶段关键关系与约束

第一阶段建议明确以下关系：

- `dataset 1:N dataset_version`
- `dataset_version 1:N dataset_asset`
- `dataset_asset 1:N asset_file`
- `dataset_version N:N dataset_version` 通过 `dataset_lineage_edge`

第一阶段建议明确以下关键约束：

- `dataset.dataset_code` 全局唯一
- `dataset_version(dataset_id, version_code)` 唯一
- `dataset_asset(dataset_version_id, asset_code)` 唯一
- `dataset` 下仅一个 `current_version`
- `dataset` 下仅一个 `default_public_version`

### 14.8 与当前旧模型的映射建议

为了平滑迁移，第一阶段建议保持以下映射：

| 旧模型 | 新模型落点 | 说明 |
| --- | --- | --- |
| `databases` | `dataset` | 先作为兼容来源，不立即替换 |
| `dataset_version` 现有表 | `dataset_version` | 保留并逐步扩展字段 |
| `database_file.path` | `asset_file.local_path` | 先作为兼容导入源 |
| `dataset_registry.file/query` 信息 | `dataset_asset + asset_file` | 逐步拆开 |

建议迁移顺序：

1. 先补新表
2. 新增资产层写入逻辑
3. 新接口优先读新模型
4. 旧接口继续走兼容聚合

## 15. 关键设计决策

### 15.1 一个参考基因组三个版本，算几组数据

推荐答案：

- 算一组 `dataset`
- 下面有三个 `dataset_version`

原因：

- 用户认知上是同一个对象的不同版本
- 查询与发布时通常围绕版本切换，而不是围绕完全不同数据集切换

### 15.2 一个版本下 FASTA 和 GFF 是否拆开

推荐答案：

- 默认不拆成两个 `dataset`
- 放在同一个 `dataset_version` 下的不同 `asset`

原因：

- 它们通常是同一版本参考数据的配套组成部分
- 这样更适合统一发布、统一展示、统一血缘表达

### 15.3 是否允许一个 dataset 同时公开多个版本

推荐答案：

- 允许

但需要同时规定：

- 只能有一个 `default_public_version`
- 只能有一个 `current_version`

这比“单一 published_version”更符合组学平台实际使用方式。

### 15.4 `dataset_kind` 第一版建议枚举

`dataset_kind` 用来回答“这一整组数据在业务上是什么”。

这里建议采用“双层模型”：

- 系统标准类型
- 系统管理员维护的扩展类型

但系统运行逻辑始终依赖标准基类，不直接依赖任意自由文本。

第一版建议先收敛到以下大类，不求一次覆盖全部组学对象，但要求命名稳定、前后台都能复用：

| dataset_kind | 适用场景 | 典型包含的 asset |
| --- | --- | --- |
| `reference_genome` | 参考基因组、组装版本 | `reference_fasta`、`gene_annotation`、`functional_annotation` |
| `annotation_set` | 独立维护的结构注释或功能注释集 | `gene_annotation`、`transcript_annotation`、`functional_annotation` |
| `variant_collection` | 群体变异、重测序变异、群体 SNP/Indel 集 | `variant_vcf`、`sample_metadata` |
| `expression_set` | 表达矩阵、转录组定量结果 | `expression_matrix`、`sample_metadata` |
| `epigenome_track_set` | 甲基化、可及性、ChIP-seq、区域/信号类结果 | `region_set`、`signal_track` |
| `interaction_set` | Hi-C、染色质互作、网络互作矩阵 | `interaction_matrix`、`contact_track` |
| `phenotype_set` | 表型与性状矩阵 | `phenotype_matrix`、`sample_metadata` |
| `population_resource` | 种质资源、材料、群体集合 | `sample_metadata`、`membership_table` |

建议理解方式：

- `dataset_kind` 是“业务大类”
- 它决定：
  - 前端分类入口
  - 默认展示卡片
  - 哪些 `asset_type` 合法
  - 常见血缘关系类型

示例一：

```text
Dataset: 水稻参考基因组
dataset_kind: reference_genome
```

示例二：

```text
Dataset: 水稻群体变异集
dataset_kind: variant_collection
```

建议第一阶段不要同时出现：

- `genome`
- `reference`
- `assembly`
- `reference_genome`

这种同义混用会直接导致后续类型治理失控。

#### 15.4.1 `dataset_kind` 注册表设计建议

建议新增：

- `dataset_kind_registry`

建议字段：

- `id`
- `code`
- `name`
- `base_code`
- `builtin`
- `status`
- `description`
- `scope`
- `display_order`
- `metadata_schema_json`
- `create_time`
- `update_time`

字段说明：

- `code`
  - 系统内唯一编码
- `name`
  - 展示名称
- `base_code`
  - 归属的系统标准类型
- `builtin`
  - 是否系统内置
- `scope`
  - 第一阶段建议固定为 `system`

第一阶段建议规则：

- 允许扩展类型
- 但扩展类型必须映射到某个 `base_code`
- 系统查询、流程、适配器、统计逻辑只认 `base_code`
- `name` 和扩展 `code` 主要用于业务表达和展示

示例：

```text
用户看到的类型: rice_japonica_reference
base_code: reference_genome
```

这表示：

- 业务上可以表达“粳稻参考基因组”
- 系统层仍把它作为 `reference_genome` 处理

#### 15.4.2 为什么不建议完全自由添加

如果完全自由输入，最终很容易出现：

- `genome`
- `reference`
- `reference_genome`
- `assembly`

这些本质同义，但系统无法稳定归类。

因此推荐策略是：

- 用户不能自由维护类型注册表
- 只有系统管理员可新增或调整扩展类型
- 团队管理员和普通用户只能从已有类型中选择
- 普通业务用户如果有新类型诉求，应走管理员治理流程

#### 15.4.3 第一阶段最小启用集合建议

虽然候选 `dataset_kind` 可以更多，但第一阶段真正启用的系统标准类型建议先压缩到以下 4 类：

| dataset_kind | 第一阶段是否启用 | 说明 |
| --- | --- | --- |
| `reference_genome` | 是 | 直接覆盖 FASTA、GFF、功能注释这条主线 |
| `variant_collection` | 是 | 覆盖 VCF/BCF 及其索引查询 |
| `expression_set` | 是 | 覆盖表达矩阵与样本元数据 |
| `annotation_set` | 是 | 处理独立于参考基因组维护的注释数据集 |
| `epigenome_track_set` | 否，第二阶段 | 等 `region_set/signal_track` 工作流稳定后再启用 |
| `interaction_set` | 否，第二阶段 | 等互作矩阵查询能力稳定后再启用 |
| `phenotype_set` | 否，第二阶段 | 当前不是后端文件查询主线 |
| `population_resource` | 否，第二阶段 | 更适合等样本/材料主数据模型稳定后启用 |

这样收敛的原因是：

- 你当前最核心的数据主线就是参考基因组、注释、变异、表达
- 这四类已经能支撑大多数第一期门户查询场景
- 可以避免第一版类型体系过宽，导致工作流和适配器同步失控

第一阶段推荐理解：

- `reference_genome`
  - 代表“一个参考版本及其配套注释”
- `annotation_set`
  - 代表“需要独立维护和独立发布的注释类数据”
- `variant_collection`
  - 代表“基于某参考版本产生的变异数据集合”
- `expression_set`
  - 代表“基于某参考版本和/或注释版本量化得到的表达数据集合”

### 15.5 `asset_type` 第一版建议枚举

`asset_type` 用来回答“这个版本下面的某个组成部分是什么”。

`asset_type` 比 `dataset_kind` 更敏感，因为它直接影响：

- 支持哪些文件格式
- 默认使用哪个 query adapter
- 是否需要索引
- 是否允许作为查询入口
- 默认工作流模板

第一版建议如下：

| asset_type | 典型文件 | 典型查询方式 | 是否常见依赖血缘 |
| --- | --- | --- | --- |
| `reference_fasta` | `fa`、`fasta`、`fna` | `samtools/faidx` | 是 |
| `gene_annotation` | `gff3`、`gtf`、`sqlite` | 区间检索、ID 检索 | 是 |
| `functional_annotation` | `tsv`、`sqlite`、`h5` | 基因功能检索、聚合检索 | 是 |
| `variant_vcf` | `vcf.gz`、`bcf` | `bcftools/tabix` | 是 |
| `expression_matrix` | `h5`、`hdf5`、`tsv` | 矩阵切片、基因/样本检索 | 是 |
| `sample_metadata` | `tsv`、`csv`、`json` | 条件筛选 | 否 |
| `region_set` | `bed`、`bed.gz` | 区间检索 | 是 |
| `signal_track` | `bw`、`bigwig` | 区域信号提取 | 是 |
| `interaction_matrix` | `h5`、`cool`、`mcool` | 区域互作查询 | 是 |
| `metadata_table` | `json`、`tsv` | 辅助展示 | 否 |

建议理解方式：

- `asset_type` 是“版本内部的部件类型”
- 它决定：
  - 默认支持哪些文件格式
  - 默认走哪个 query adapter
  - 是否需要索引文件
  - 是否适合挂血缘关系

示例一：

```text
Dataset: 水稻参考基因组
dataset_kind: reference_genome

Version: IRGSP-1.1
Assets:
  - asset_type = reference_fasta
  - asset_type = gene_annotation
  - asset_type = functional_annotation
```

示例二：

```text
Dataset: 水稻群体变异集
dataset_kind: variant_collection

Version: panel_2025
Assets:
  - asset_type = variant_vcf
  - asset_type = sample_metadata
```

建议第一阶段先把 `asset_type` 控制在 8 到 12 个左右，不要一开始把所有组学细分名词都拉进来。

#### 15.5.1 `asset_type` 注册表设计建议

建议新增：

- `asset_type_registry`

建议字段：

- `id`
- `code`
- `name`
- `base_code`
- `builtin`
- `status`
- `description`
- `scope`
- `allowed_formats_json`
- `default_query_adapter`
- `default_index_profile`
- `is_queryable`
- `metadata_schema_json`
- `create_time`
- `update_time`

第一阶段建议规则：

- 允许扩展 `asset_type`
- 但扩展类型必须挂到某个 `base_code`
- 真正执行逻辑依赖：
  - `base_code`
  - `allowed_formats_json`
  - `default_query_adapter`
  - `default_index_profile`

示例：

```text
扩展 asset_type: transposable_element_annotation
base_code: functional_annotation
default_query_adapter: generic-table
```

含义是：

- 业务上单独区分了 TE 注释
- 但在系统第一阶段仍按 `functional_annotation` 大类处理

#### 15.5.2 `asset_type` 的维护权限

与 `dataset_kind` 一样，`asset_type` 注册表只允许系统管理员维护。

明确规则：

- 系统管理员：可新增、修改、停用
- 团队管理员：无此权限
- 普通用户：无此权限

原因是 `asset_type` 一旦改动，会直接影响：

- 文件上传校验
- 索引任务选择
- 查询入口生成
- 适配器分发逻辑

这类能力必须视为平台内核配置，而不是普通业务配置。

#### 15.5.3 第一阶段最小启用集合建议

第一阶段真正启用的 `asset_type` 建议控制在以下 7 类：

| asset_type | 第一阶段是否启用 | 原因 |
| --- | --- | --- |
| `reference_fasta` | 是 | 参考基因组最核心入口 |
| `gene_annotation` | 是 | GFF/GTF 是基因组平台主线能力 |
| `functional_annotation` | 是 | 功能注释是常见配套数据 |
| `variant_vcf` | 是 | 直接支撑 VCF/BCF 查询 |
| `expression_matrix` | 是 | 直接支撑表达矩阵查询 |
| `sample_metadata` | 是 | 变异和表达都常需要样本元数据 |
| `metadata_table` | 是 | 作为通用补充元数据资产，降低第一期建模阻力 |
| `region_set` | 否，第二阶段 | 依赖更成熟的区间模型与流程 |
| `signal_track` | 否，第二阶段 | 依赖 BigWig 等查询适配器继续完善 |
| `interaction_matrix` | 否，第二阶段 | 依赖互作矩阵能力补齐 |

这组最小集合的优点是：

- 能覆盖你当前最主要的数据类型
- 已能支撑 `FASTA + GFF + 功能注释 + VCF + 表达矩阵`
- 可以让 `dataset_asset` 的第一版字段和工作流更稳定

第一阶段如果遇到特殊资产，建议走两种方式之一：

- 先落到 `metadata_table`
- 或由系统管理员新增扩展 `asset_type`，但必须挂到现有 `base_code`

示例：

```text
Dataset: 水稻参考基因组
dataset_kind: reference_genome

Version: IRGSP-1.1
Assets:
  - reference_fasta
  - gene_annotation
  - functional_annotation
```

```text
Dataset: 水稻群体变异集
dataset_kind: variant_collection

Version: panel_2025
Assets:
  - variant_vcf
  - sample_metadata
```

```text
Dataset: 水稻表达图谱
dataset_kind: expression_set

Version: expr_2025
Assets:
  - expression_matrix
  - sample_metadata
```

### 15.6 权限控制第一阶段建议

第一阶段建议采用：

- `dataset` 为主
- `version` 覆盖
- `asset` 级先预留，不全面启用

#### 15.6.1 例子一：只用 `dataset` 级权限

```text
Dataset: 水稻参考基因组
  Version: v1
  Version: v2
  Version: v3
```

规则：

- 有这个 `dataset` 的查看权限
- 就默认能看它下面所有 version 和 asset

适用场景：

- 数据整体对同一批人开放
- 不需要区分不同版本的可见范围

#### 15.6.2 例子二：`dataset` 为主，`version` 覆盖

```text
Dataset: 水稻参考基因组
  Version: v1 released
  Version: v2 released
  Version: v3 drafting
```

规则：

- 默认继承 `dataset` 权限
- 但 `v3` 可单独设为仅项目成员可见
- 因此普通前台用户只能看到 `v1`、`v2`
- 后台特定团队可以看到 `v3`

这正适合：

- 新版本正在整理
- 历史版本已公开
- 但未完成的新版本不能提前暴露

#### 15.6.3 例子三：为什么先不全面启用 `asset` 级权限

```text
Dataset: 水稻参考基因组
Version: v2
Assets:
  - reference_fasta
  - gene_annotation
  - functional_annotation
```

如果启用 `asset` 级权限，可以做到：

- `reference_fasta` 公开
- `gene_annotation` 公开
- `functional_annotation` 仅合作团队可见

这个模型很灵活，但第一阶段会明显增加复杂度：

- 接口鉴权要下钻到 asset
- 前端展示要区分哪些 asset 可见
- 继承和覆盖规则更复杂

因此更稳妥的策略是：

- 表设计预留 `asset` 作为资源类型
- 第一阶段实际启用：
  - `dataset`
  - `dataset_version`
- 第二阶段再补 `asset` 级精细化权限

结论：

- 第一阶段正式规则建议定为：`dataset` 为主，`version` 覆盖
- `asset` 级权限保留扩展位，但不作为第一阶段强制能力
- 类型注册表管理权限只属于系统管理员，团队管理员和普通用户不具备此权限

## 16. 非目标

本阶段不强制解决以下问题：

- 立刻拆微服务
- 立刻把所有组学内容导入关系型数据库
- 一次性替换全部旧 `database/*` 接口
- 一次性完成所有 `basis/*` 能力迁移

## 17. 下一步实施建议

建议按以下顺序推进：

1. 把状态语义正式拆分为 `workflow_state / visibility_scope / release_state`
2. 把当前“单 published_version”语义调整为“多 released_versions + 一个 default_public_version”
3. 新增 `dataset_asset` 与 `asset_file`
4. 让查询能力从 `dataset_version.file_path` 逐步迁移到 `asset`
5. 新增 `lineage_edge`
6. 再推进前后台 API 的正式分层

## 18. 结论

组学平台后端的核心对象，不应是单文件，也不应只是单层 `dataset`，而应是以下正式模型：

```text
Dataset
DatasetVersion
DatasetAsset
AssetFile
LineageEdge
Workflow
Release
Permission
```

这套模型可以同时支撑：

- 多版本组学数据管理
- 一个版本多个配套文件
- 文件型查询与索引驱动查询
- 血缘关系追踪
- 后台工作版本与前台公开版本分离
- 精细权限控制
- 平滑兼容现有后端系统

## 19. 第一期实施清单

本节把前述设计压缩成第一期可执行实施计划，目标不是一次做满，而是优先把主干能力立起来，并保持对现有后端的兼容。

### 19.1 第一期范围

第一期建议只覆盖以下内容：

- 类型体系第一版落地
- 三类状态字段落地
- `dataset_asset` 与 `asset_file` 落地
- `dataset_lineage_edge` 落地
- 后台管理接口补齐最小闭环
- 前台查询接口逐步从 `dataset_version.file_path` 迁移到 `asset`

第一期暂不强制做：

- 全量 `asset` 级权限
- 所有组学数据类型一次支持完成
- 所有旧接口立即替换
- 所有查询能力一次迁移到新查询模型

### 19.2 实施顺序

建议按以下 6 个阶段推进。

#### 阶段 1：状态语义收敛

目标：

- 把现有 `dataset` / `dataset_version` 的状态语义拆清

具体动作：

- 在 `dataset_version` 上正式引入：
  - `workflow_state`
  - `visibility_scope`
  - `release_state`
- 保留现有兼容字段，但新逻辑优先读新字段
- 将“发布”和“默认公开版本”语义拆开

产出：

- 新状态字段
- 新状态读写逻辑
- 兼容映射逻辑

验收标准：

- 后台能区分：
  - 处理阶段
  - 可见范围
  - 发布状态
- 同一个 `dataset` 可存在多个 `released_versions`
- 仅一个 `default_public_version`

#### 阶段 2：资产层落地

目标：

- 把单文件模型扩展为“版本下多个资产、资产下多个文件”

具体动作：

- 新增 `dataset_asset`
- 新增 `asset_file`
- 新增最小写入逻辑
- 为现有 `dataset_version.file_path` 提供向 `asset_file` 的兼容导入逻辑

产出：

- 资产表和文件表
- `reference_fasta / gene_annotation / functional_annotation / variant_vcf / expression_matrix / sample_metadata / metadata_table` 的第一版支持

验收标准：

- 一个 `dataset_version` 能挂多个 `asset`
- 一个 `asset` 能挂多个 `asset_file`
- 能正确表达：
  - FASTA + FAI
  - GFF3 + SQLite
  - VCF.GZ + TBI
  - HDF5 + 样本表

#### 阶段 3：查询入口迁移

目标：

- 查询不再依赖单一 `dataset_version.file_path`

具体动作：

- 将现有 adapter 路由逻辑下沉到 `asset`
- 查询参数增加 `asset_code`
- 当版本只有唯一 `is_query_entry = true` 资产时，允许自动推断

产出：

- 新查询解析逻辑
- 资产级查询能力描述

验收标准：

- 参考基因组查询可基于 `reference_fasta` 执行
- VCF 查询可基于 `variant_vcf` 执行
- 表达查询可基于 `expression_matrix` 执行

#### 阶段 4：血缘层落地

目标：

- 支持版本间依赖关系表达

具体动作：

- 新增 `dataset_lineage_edge`
- 提供最小增删查接口
- 先支持 `version -> version`

产出：

- 血缘关系表
- 后台维护接口

验收标准：

- 可以表达：
  - `variant_collection --uses_reference--> reference_genome`
  - `expression_set --quantified_against--> reference_genome`
  - `annotation_set --derived_from--> reference_genome`

#### 阶段 5：发布模型收敛

目标：

- 把当前“单 published_version”升级为“多 released_versions + 一个 default_public_version”

具体动作：

- 增加：
  - `release`
  - `withdraw`
  - `set-default-public`
- 调整公开查询逻辑，优先走：
  - `default_public_version`
  - 或显式指定的已发布版本

产出：

- 新发布控制接口
- 新公开查询规则

验收标准：

- 一个 `dataset` 可同时公开多个版本
- 前台默认进入 `default_public_version`
- 历史公开版本仍可切换访问

#### 阶段 6：前后台 API 分层

目标：

- 形成正式的后台管理接口与前台查询接口边界

具体动作：

- 将后台管理能力统一归到 `/api/v1/admin/*`
- 将受控查询统一归到 `/api/v1/query/*`
- 将公开查询统一归到 `/api/v1/public/*`

产出：

- 第一阶段正式 API 目录
- 旧接口兼容策略

验收标准：

- 后台、登录查询、公开查询三类接口语义清晰
- 旧 `dataset/*` 能继续跑
- 新前端优先对接新接口

### 19.3 第一期代码改造顺序建议

结合当前代码库，建议实际改造顺序如下：

1. 先改模型层
   - `apps/datasets/models.py`
   - `apps/datasets/init.py`
   - `apps/datasets/crud.py`
2. 再改 service 层
   - `apps/datasets/services.py`
3. 再补后台管理 API
   - `apps/datasets/api/*`
4. 再迁移查询入口
   - `apps/datasets/adapters/*`
5. 最后补公开查询和兼容逻辑

这样做的原因是：

- 先稳定数据模型
- 再改业务逻辑
- 最后再调整 API 出口

### 19.4 第一期测试建议

第一期至少要覆盖以下测试场景：

#### 数据结构

- 创建一个 `dataset`
- 创建两个 `dataset_version`
- 每个版本创建多个 `asset`
- 每个 `asset` 创建多个 `asset_file`

#### 状态流转

- `uploaded -> validating -> validated -> indexing -> ready`
- `ready -> released`
- `released -> deprecated`
- `released -> withdrawn`

#### 发布模型

- 同一个 `dataset` 允许多个 `released_versions`
- 同一时刻只有一个 `default_public_version`
- 切换默认公开版本时，旧版本不必撤回

#### 查询模型

- FASTA 查询走 `reference_fasta`
- VCF 查询走 `variant_vcf`
- 表达查询走 `expression_matrix`

#### 血缘模型

- 创建 `uses_reference`
- 创建 `quantified_against`
- 查询某个版本的上游依赖

### 19.5 第一期风险点

第一期最容易出问题的地方有 4 个：

#### 1. 旧单文件模型和新多资产模型并存

风险：

- 同一条数据可能同时存在旧 `file_path` 和新 `asset_file`

建议：

- 第一阶段统一规定：
  - 新写入优先写 `asset_file`
  - 旧字段只做兼容回填

#### 2. 状态字段混用

风险：

- 发布状态仍被误写入生命周期字段

建议：

- service 层统一封装状态变更方法
- 禁止在路由层直接拼状态逻辑

#### 3. 查询入口不唯一

风险：

- 一个版本下可能有多个可查询资产，前端不传 `asset_code` 时无法确定

建议：

- 第一阶段要求每个版本最多只有一个默认 `is_query_entry = true`
- 多查询入口场景由第二阶段再扩展

#### 4. 共享 MySQL 上做回归测试

风险：

- 误操作真实业务数据的公开状态

建议：

- 第一阶段继续使用临时测试数据集做回归
- 发布/撤回应在测试后恢复为私有状态

### 19.6 第一期完成标志

当满足以下条件时，可认为第一期主干完成：

- `dataset -> version -> asset -> file` 主结构已跑通
- 三类状态字段已替代旧混合语义
- 多已发布版本 + 单默认公开版本已可用
- 查询入口已能基于 `asset` 工作
- 版本血缘关系已可登记和查询
- 可选的 `asset` 级血缘关系已可登记和查询
- 后台与前台接口边界已初步稳定

### 19.7 建议的直接下一步

如果按实施优先级继续推进，建议直接开始：

1. 新增 `dataset_asset`
2. 新增 `asset_file`
3. 把当前 `dataset_version.file_path` 兼容迁移到 `asset_file`

这是第一期最关键的结构性一步，也是后续查询迁移和血缘建模的基础。
