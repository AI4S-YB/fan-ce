# 组学数据平台设计补丁 — 场景走查汇总

> 日期：2026-04-28
> 范围：Dataset 平台 + Breeding 域 + 跨域整合
> 方法：6 个业务场景走查 + 4 个横切关注面审查

---

## 1. 执行摘要

通过对 6 个核心业务场景（基因组数据管理、变异数据查询、基因表达数据管理、表型数据查询、育种实验管理、跨组学 GWAS 整合）的逐项走查，共计发现 **38 个设计缺口**，按性质分为：

| 缺口性质 | 数量 | 说明 |
|----------|------|------|
| 架构断层 | 9 | 两个 domain 或两个 layer 之间有数据模型但缺编排/聚合 |
| 流程断点 | 10 | 有上游能力，无下游消费——流程可以走但关键步骤缺失 |
| 查询缺失 | 10 | 用户/分析需要但 API 未暴露的查询能力 |
| 权限/安全 | 3 | 权限模型在跨 domain 场景下未定义 |
| 数据质量 | 4 | 无自动化校验、一致性检查 |
| 格式/能力限制 | 2 | adapter 或 service 支持的格式不足 |

**核心结论**：单体 adapter 能力基本就绪（P0-P1 完成度 ~70%），但跨 adapter、跨 domain 的编排层完全空白。从"能查数据"到"能分析"之间存在工程断层。

---

## 2. 场景走查发现汇总

### S1：基因组数据管理全流程（Genome + Annotation + Functional Annotation）

| ID | 缺口 | 性质 | 严重度 |
|----|------|------|--------|
| S1-1 | **Dataset 主表缺失** — `DatasetRegistry` 同时充当聚合视图和旧兼容桥，没有独立的 `dataset` 主表。导致数据集的核心标识字段（name、type、organism、assembly）与版本化实体（DatasetVersion）职责不清 | 架构断层 | P0 |
| S1-2 | **Lineage 约束未执行** — `DatasetLineageEdge` 记录了 `src_version_id` → `dst_version_id` 的关系，但对 relation_type 的可选值没有约束、对两端 asset 类型没有兼容性校验 | 数据质量 | P1 |
| S1-3 | **Assembly 一致性无校验** — 多个 DatasetVersion 声称同一 assembly 时，系统不会检查其基因组序列文件的实际一致性（如 reference.fa 的 checksum），完全依赖人工填写 | 数据质量 | P1 |
| S1-4 | **Asset Type 解析硬编码** — `services.py` 中存在 `DATASET_TYPE_TO_ASSET_TYPE` 硬编码字典，未使用 `AssetTypeRegistry` 表的已注册值。registry 表形同虚设 | 架构断层 | P1 |
| S1-5 | **Index 新鲜度检测缺失** — .fai / .tbi / .csi 等索引文件可能因源文件更新而失效。系统在查询时仅检测文件存在，不检测时间戳或 checksum 的新鲜度 | 流程断点 | P2 |
| S1-6 | **Public Lineage 无端点** — 公开 API (`/public/dataset/`) 提供了 list/info/version/query，但没有 `/public/dataset/lineage`，外部无法追溯公开数据的谱系关系 | 查询缺失 | P2 |

### S2：群体变异数据查询与管理（VCF + bcftools）

| ID | 缺口 | 性质 | 严重度 |
|----|------|------|--------|
| S2-1 | **Sample 列表自动化提取缺失** — variant adapter 提供 `samples_list`（调用 `bcftools query -l`），但结果不会自动写入任何 catalog 表。Breeding 的 `VariantSampleMap` 需要手动填充 | 流程断点 | P0 |
| S2-2 | **Variant → Material 反向查询缺失** — 给定一个染色体位置，可以查到 variant，但查不到 "哪些 germplasm 在这个位置有变异"——缺少从 genomic coordinate → variant → sample_id → material_id 的反向查询链 | 查询缺失 | P1 |
| S2-3 | **跨 VCF Dataset 联合查询缺失** — 无法对两个 variant dataset 做 "找共有变异" 或 "找私有变异" 的集合操作 | 查询缺失 | P2 |
| S2-4 | **Permission 边界模糊** — variant dataset 的 visibility 是 project/team 级，但通过 `VariantSampleMap` 可以被 breeding program 引用。跨 domain 的读权限传递规则未定义 | 权限/安全 | P1 |
| S2-5 | **Sample 名称规范化缺失** — VCF 中的 sample ID 可能有多种命名惯例（如 `SAM001`、`BR123_SAM001`、`Pool_1`），与 breeding 中的 material_name 之间没有规范化映射机制 | 数据质量 | P2 |

### S3：基因表达数据管理（Expression Matrix + Sample/Experiment）

| ID | 缺口 | 性质 | 严重度 |
|----|------|------|--------|
| S3-1 | **旧模型与新模型断层** — 旧 `abd_sample` + `abd_experiment` (SRA-style) 仍然存在，新的 `BreedingBioSample` + `BreedingAssay` 已经定义，但两者之间没有迁移路径或统一抽象层 | 架构断层 | P0 |
| S3-2 | **Expression Matrix → BioSample 映射缺失** — 表达矩阵中的列名（sample ID）如何映射到 BioSample 记录，缺少自动化工具。需要类似 `VariantSampleMap` 的 `ExpressionSampleMap` | 流程断点 | P1 |
| S3-3 | **格式支持仅 HDF5** — `expression.py` adapter 仅支持 HDF5（`.h5`、`.hdf5`）。RNA-seq 常见的 count matrix（TSV/CSV）、10X 的 mtx 格式均不支持 | 格式限制 | P1 |
| S3-4 | **Sample Metadata Asset 未定义** — expression dataset 需要配套的样本元数据（分组、条件、批次），当前 asset type 体系中没有 `sample_metadata` 类型 | 架构断层 | P1 |
| S3-5 | **跨条件/跨 Dataset 表达量比较缺失** — 无法对两个 expression dataset 做 "找差异表达基因" 或 "某基因在多个 dataset 中的表达谱" | 查询缺失 | P2 |

### S4：表型数据查询（Phenome Adapter + Breeding Phenotype）

| ID | 缺口 | 性质 | 严重度 |
|----|------|------|--------|
| S4-1 | **phn_* Index → Breeding Phenotype 桥接缺失** — phenome adapter 构建了 `phn_subject`/`phn_trait`/`phn_observation` PostgreSQL 索引表，但 `BreedingObservation` 没有消费这些索引数据。phenome dataset 的 observation 与 breeding plot-level observation 之间存在语义重叠但未统一 | 架构断层 | P0 |
| S4-2 | **Phenotype 格式覆盖不足** — phenome adapter 支持 SQLite（从 phenome indexing pipeline 构建），但育种领域常见的 Excel/CSV 格式没有直接导入路径 | 格式限制 | P1 |
| S4-3 | **Subject Type 自动推断缺失** — phenome adapter 将 subject 分为 `plant`、`plot`、`accession`、`line` 等类型，但与 breeding domain 的 `Material`、`Plot` 实体之间没有自动类型推断逻辑 | 流程断点 | P2 |
| S4-4 | **Trait Type 覆盖/纠正机制缺失** — phenome indexing 自动推断 trait 类型（numeric/text/category），但推断错误时没有 UI 或 API 来纠正 | 流程断点 | P2 |
| S4-5 | **Phenome ↔ Sample Annotation 边界不清** — phenome 数据（定量性状）与 sample annotation（样本标签如 "control"/"drought"）在查询层面无区分，但两者语义不同 | 架构断层 | P2 |

### S5：育种实验管理（Breeding Domain Core）

| ID | 缺口 | 性质 | 严重度 |
|----|------|------|--------|
| S5-1 | **Material/Trial 聚合视图缺失** — 单个 material 或 trial 的详情页需要看到关联的 datasets、observations、assays 汇总。当前只有 `program/overview` 做了聚合，material 和 trial 级别的聚合完全没有 | 查询缺失 | P0 |
| S5-2 | **用户面关联 API 缺失** — 将一个 dataset 关联到 breeding program（创建 link table 记录）的操作只能通过通用 CRUD 完成。用户需要的是 `POST /breeding/program/{id}/link-dataset` 这样的业务面端点 | 流程断点 | P0 |
| S5-3 | **Trial/Program 状态机缺失** — Dataset 有完整的状态流转（draft→active→archived），Breeding 的 Trial、Program 没有生命周期状态定义 | 流程断点 | P1 |
| S5-4 | **DataFile 双向链接不对称** — `BreedingDataFile` 有 `assay_id` 指向 Assay，但没有直接指向 `BioSample` 的外键。如果 data file 属于 biosample 而非 assay（如样本照片），无法直接表达 | 架构断层 | P2 |
| S5-5 | **Breeding 侧分析就绪度缺失** — 从 breeding program 视角，无法获知"哪些 material 既有 variant 又有 phenotype 数据"——即 breeding 域的分析就绪度（对称于 S6 的 dataset 侧就绪度） | 查询缺失 | P1 |

### S6：跨组学整合 — GWAS 就绪度

| ID | 缺口 | 性质 | 严重度 |
|----|------|------|--------|
| S6-1 | **Material → Dataset 反向查询缺失** — `VariantSampleMap`、`PhenotypeSubjectMap`、`DatasetAssayLink` 已有 `dataset_id` 外键，但没有聚合查询方法汇总某个 material 关联的全部 dataset | 查询缺失 | P0 |
| S6-2 | **Assembly 跨 Dataset 一致性校验缺失** — 做 GWAS 前需要确认 variant dataset 和 phenotype dataset 基于同一 assembly，系统无此检查 | 流程断点 | P0 |
| S6-3 | **Sample ID 映射对齐检查缺失** — 无自动化检查配对样本覆盖率（variant 中有多少样本在 phenotype 中也有对应记录） | 数据质量 | P1 |
| S6-4 | **GWAS 输入矩阵组装入口缺失** — 无统一的 "给定 variant dataset + phenotype dataset → 返回分析就绪矩阵" 的编排层 | 查询缺失 | P0 |
| S6-5 | **Analysis Readiness 概念未落地** — 设计文档定义的 "最低绑定要求" 和 "分析就绪度" 零实现 | 架构断层 | P1 |
| S6-6 | **跨 Dataset 联合查询完全缺失** — variant+annotation overlap、functional+expression pathway query、phenotype+expression correlation 全部空白 | 查询缺失 | P1 |

---

## 3. 横切关注面审查

### 3.1 权限模型（Permission）

| ID | 缺口 | 严重度 |
|----|------|--------|
| X-1 | **Dataset Visibility × Breeding Program 权限交叠** — Dataset 使用 team/project/visibility 三级权限，Breeding 使用 program 权限。当 breeding link table 引用了 restricted dataset 时，访问权限如何传递未定义 | P0 |
| X-2 | **API 三层权限未差异化** — `/dataset/`（后台）、`/admin/dataset/`（超管）、`/public/dataset/`（公开）复用了同一套 router，admin 端点没有额外的管理能力（强制删除、状态回滚、审计日志） | P1 |

### 3.2 版本生命周期（Version Lifecycle）

| ID | 缺口 | 严重度 |
|----|------|--------|
| X-3 | **Withdraw 级联检查缺失** — 当 DatasetVersion 被 withdraw 时，系统不检查是否有活跃的 breeding link 引用。应有级联通知/阻止机制 | P1 |
| X-4 | **Public Version 的 release_state 流转无审计** — activate/release/withdraw 有 PublishRecord，但 public side 没有变更通知（RSS/Webhook），外部依赖方无法感知 | P2 |

### 3.3 旧兼容层收尾

| ID | 缺口 | 严重度 |
|----|------|--------|
| X-5 | **apps/databases + apps/sample + apps/experiment 存量未清** — `DatasetLegacyBridge` 和 `DatasetRegistry.database_id` 仍在代码中。需要：① 统计 `database_id IS NOT NULL` 残留量；② 确定旧数据是否全部迁移；③ 制定下线时间表 | P2 |

### 3.4 API 分层一致性

| ID | 缺口 | 严重度 |
|----|------|--------|
| X-6 | **Query 端点重复暴露** — `/query/dataset/` 前缀下的 query 端点同时也挂载在 `/dataset/` 下，造成端点冗余 | P2 |

---

## 4. 修复方案汇总

### 4.1 架构层修复（第一优先级）

#### F-1：Dataset 主表重建

遵循 PostgreSQL 存储重构设计文档的 DDL 方案，将 `DatasetRegistry` 拆分为：
- `dataset` — 数据集主表（name, type, organism, assembly, team_id, project_id）
- `dataset_version` — 版本表（保持现有结构，`dataset_id` → `dataset.id`）
- 删除 `DatasetRegistry.database_id`（迁移完毕后）

**涉及文件**：`apps/datasets/models.py`、`services.py` 中所有 `DatasetRegistry` CRUD

#### F-2：统一 Sample/Experiment 抽象层

在 Dataset 和 Breeding 之间插入抽象层 `BiologicalSample` + `SequencingExperiment`：

```
旧 abd_sample ──→ BiologicalSample ←── BreedingBioSample
旧 abd_experiment ──→ SequencingExperiment ←── BreedingAssay
                             │
                       DatasetLink
```

`BiologicalSample` 作为旧 SRA 样本和新 Breeding BioSample 的统一视图，`DatasetLink` 表达 sample 与 dataset 之间的关联。

**涉及文件**：新建 `apps/datasets/unified_sample.py`，修改 `legacy_bridge.py`

#### F-3：编排层 — CrossDomainOrchestrationService

新建 `apps/datasets/orchestration.py`，提供：

| 方法 | 功能 |
|------|------|
| `get_datasets_for_material(material_id)` | Material → List[DatasetSummary] |
| `get_datasets_for_program(program_id, dataset_type?)` | Program → List[DatasetSummary] |
| `validate_assembly_consistency(dataset_ids)` | 检查 assembly 一致性 |
| `check_sample_alignment(variant_ds, pheno_ds)` | 样本配对覆盖率报告 |
| `assemble_gwas_input(variant_ds, pheno_ds, materials?)` | GWAS 分析矩阵组装 |
| `check_analysis_readiness(dataset_ids, analysis_type)` | 分析就绪度交通灯 |

#### F-4：Breeding 聚合 API

在 `BreedingDomainService` 中新增：

| 方法 | 端点 |
|------|------|
| `get_material_overview(material_id)` | `GET /breeding/material/{id}/overview` |
| `get_trial_overview(trial_id)` | `GET /breeding/trial/{id}/overview` |
| `link_dataset_to_program(program_id, dataset_id, link_type)` | `POST /breeding/program/{id}/link-dataset` |
| `get_program_datasets(program_id, type?)` | `GET /breeding/program/{id}/datasets` |

### 4.2 流程层修复（第二优先级）

#### F-5：Sample 提取 → Catalog 写入自动化

在 variant adapter 的 `samples_list()` 调用后，自动触发 `BreedingVariantSampleMap` 的 populate（或至少返回可导入的 diff）。同样适用于 expression adapter。

#### F-6：Index 新鲜度检测

在 `DatasetQueryAdapter.ensure_sidecar_index_files()` 中增加 timestamp 比对逻辑：索引文件的 mtime ≥ 源文件 mtime 才视为有效。

#### F-7：Withdraw 级联检查

在 `DatasetVersion.release_state` 变更（特别是 withdraw）时，检查：
```sql
SELECT COUNT(*) FROM breeding_dataset_subject_link WHERE version_id = ?
UNION ALL
SELECT COUNT(*) FROM breeding_dataset_assay_link WHERE version_id = ?
UNION ALL
SELECT COUNT(*) FROM breeding_variant_sample_map WHERE version_id = ?
```
若 sum > 0，返回警告并阻止 withdraw（或强制确认）。

### 4.3 能力增强（第三优先级）

#### F-8：Expression 多格式支持

扩展 `expression.py` adapter：
- TSV/CSV count matrix（`pandas.read_csv`）
- 10X mtx（scipy.io.mmread）
- HDF5（保持现有）

#### F-9：Phenome → Breeding Observation 桥接

`rebuild_phenome_index()` 完成后，自动在 `BreedingObservation` 中创建对应记录（如果 subject 可映射到 plot/material）。

#### F-10：Asset Type Registry 投入使用

删除 `services.py` 中的 `DATASET_TYPE_TO_ASSET_TYPE` 硬编码字典，改为查询 `AssetTypeRegistry` 表。

### 4.4 权限与 API 修复

#### F-11：跨 Domain 权限传递规则

定义默认规则：
- Breeding Program 成员通过 link table 访问关联的 dataset 时，使用 dataset 自身的 visibility 设置
- 不给 link table 附加权限传递（最小权限原则）
- 如需要预览（不暴露数据），提供 `dataset_summary` 级别（仅元数据）的受限视图

#### F-12：Admin API 差异化

在 `/admin/` 前缀下新增超管专属端点：
- `DELETE /admin/dataset/{id}` — 强制删除（含所有版本和文件）
- `POST /admin/dataset/{id}/rollback-state` — 状态回滚
- `GET /admin/dataset/audit-log` — 操作审计日志

---

## 5. 实施路线图

```
Phase 1（2-3 周）—— 架构补基
├── F-1: Dataset 主表重建
├── F-4: Breeding 聚合 API（material/trial overview + link-dataset）
├── F-3 部分: get_datasets_for_material、get_datasets_for_program
├── F-10: Asset Type Registry 投入使用
└── F-11: 跨 Domain 权限规则落地

Phase 2（2-3 周）—— 流程闭环
├── F-2: 统一 Sample/Experiment 抽象层
├── F-5: Sample 自动提取 → catalog 写入
├── F-3 部分: validate_assembly_consistency、check_sample_alignment
├── F-7: Withdraw 级联检查
└── S3-2: Expression Matrix → BioSample 映射

Phase 3（2-3 周）—— 分析编排
├── F-3 部分: assemble_gwas_input、check_analysis_readiness
├── S6-6: 跨 Dataset 联合查询（variant+annotation overlap, expression+functional）
├── F-6: Index 新鲜度检测
├── F-8: Expression 多格式支持
└── F-9: Phenome → Breeding Observation 桥接

Phase 4（1-2 周）—— 收尾
├── F-12: Admin API 差异化
├── X-5: 旧兼容层评估与清理
├── S1-6: Public Lineage 端点
└── X-6: Query 端点去重
```

### 依赖关系

```
Phase 1 ──────────────────────────────────────────────────────────────┐
  F-1 (Dataset 主表) ──── 被 F-3, F-4, F-7, F-12 依赖               │
  F-4 (Breeding 聚合) ─── 被 Phase 2 的流程闭环依赖                  │
  F-10 (Asset Registry) ─ 独立，可并行                                │
  F-11 (权限规则) ──────── 独立，可并行                                │
Phase 2 ──────────────────────────────────────────────────────────────┤
  F-2 (统一抽象层) ─────── 被 S3-2, Phase 3 的跨域查询依赖           │
  F-5 (Sample 自动提取) ─ 依赖 F-4 的 link-dataset API                │
  F-7 (Withdraw 检查) ─── 依赖 F-1                                    │
Phase 3 ──────────────────────────────────────────────────────────────┤
  F-3 剩余 ─────────────── 依赖 F-1, F-2, F-4                         │
  S6-6 (联合查询) ──────── 依赖 F-3                                    │
  F-8, F-9 ─────────────── 独立                                        │
Phase 4 ──────────────────────────────────────────────────────────────┤
  全部 ─────────────────── 依赖 Phase 1-3 的代码稳定                   │
```

---

## 6. 关键未决问题

以下问题需要在实施前由业务方确认：

1. **统一抽象层的 scope**：`BiologicalSample` 是新表还是 VIEW？如果新增表，旧 `abd_sample` 的数据如何迁移？如果使用 VIEW，需要确认 PostgreSQL 版本的 UNION ALL VIEW 性能。

2. **Breeding 状态机**：Trial/Program 需要哪些生命周期状态？建议最小集：`draft → active → completed → archived`。

3. **旧兼容层清理时间线**：当前 `abd_sample` 和 `abd_experiment` 中还有多少有效数据？旧前端是否还在依赖 `/api/v1/sample/*` 和 `/api/v1/experiment/*` 端点？

4. **Admin 端点的认证策略**：是否需要独立于 JWT 的 admin 认证机制，还是在 JWT 中增加 `is_admin` claim？

5. **Phenome ↔ Breeding Observation 的关系**：是 1:1 同步、引用视图、还是保留为两个独立体系？
