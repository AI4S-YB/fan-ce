# phenome 数据接入与结构化设计草案

## 1. 背景

当前平台已经逐步形成按组学大类管理数据资产的主线：

- `genome`
- `transcriptome`
- `variome`
- `signal`
- `interaction`

下一步需要把表型数据接入同一条主线。

本设计基于真实案例目录：

- `/Users/kentnf/projects/data/test_data/phenotype`

当前目录中有两类文件：

- `rose_phenotype_test.xlsx`
- `rose_phenotype_test.db`

其中：

- `xlsx` 更像原始交付文件
- `sqlite` 更像为查询准备的轻量索引库

这和前面 `genome + functional_annotation` 的落地方式很相似，因此适合延续“文件资产 + 派生查询资产 + 平台结构化索引”的分层思路。

---

## 2. 命名决策

### 2.1 dataset_type 建议采用 `phenome`

结论：

- 对外的 dataset 类型，建议使用 `phenome`

原因：

1. 和当前主线命名更一致
   - `genome / transcriptome / variome / phenome`
   - 都是平台级数据大类名称

2. `phenotype` 更适合描述具体观测值，而不是整类数据集
   - 一个 dataset 里往往包含多个 trait
   - 每个 trait 下又有多个 observation
   - 因此 `phenotype` 更像内容对象，不像顶层容器

3. 后续与 breeding 域并存时，语义更清楚
   - Dataset 域用 `phenome`
   - Breeding/业务域继续用 `trait / phenotype / observation`

### 2.2 术语分工建议

- `phenome`
  - 用于 Dataset 平台中的 `dataset_type`
  - 表示一类表型/性状相关数据资产

- `phenotype`
  - 用于描述具体表型记录、表型文件、表型行映射
  - 例如 `phenotype_subject_map`

- `trait`
  - 用于描述单个性状定义
  - 例如花瓣长、瓶插寿命、连续开花性

- `observation`
  - 用于描述结构化观测值
  - 是 breeding 域中的正式业务对象

一句话收束：

- Dataset 类型叫 `phenome`
- 业务内容继续叫 `phenotype / trait / observation`

---

## 3. 真实案例判断

基于 `rose_phenotype_test.xlsx` 和 `rose_phenotype_test.db`，当前这批数据具备以下特征：

1. 主体键明确
   - 有 `ID`
   - 可作为材料编号或观测主体编号

2. 同时带展示字段
   - `chinese_name`
   - `english_name`

3. 性状类型混合
   - 连续型：花瓣长、花瓣宽、瓶插寿命
   - 分类型/等级型：连续开花性、乙烯敏感脱落

4. 存在时间维度
   - `2021年花瓣数量`
   - `2022年花瓣数量`
   - `2023年花瓣数量`

5. 当前 `sqlite` 是宽表单表结构
   - 适合点查
   - 不适合长期承担平台级筛选、聚合、跨试验整合

因此这类数据的合理定位是：

- 原始交付层：`xlsx/csv/tsv`
- 轻量查询层：`sqlite`
- 平台检索层：`postgresql`
- 业务整合层：`breeding observation`

---

## 4. 设计目标

本设计要解决四个问题：

1. 让表型文件在没有 breeding 元数据时也能先注册
2. 让用户能快速查看某个材料的全部表型
3. 让平台能按 trait 检索和筛选
4. 让后续可以平滑挂接到 `Trial / Plot / Material / Observation`

本设计明确不做的事情：

- 不要求用户一开始就提供完整 Program/Trial/Plot
- 不把 phenotype 文件强制转换为 breeding 结构后才能落库
- 不要求第一阶段就实现复杂统计分析

---

## 5. 总体架构

建议沿用三层模型：

### 5.1 文件资产层

保留用户交付的原始文件：

- `xlsx`
- `csv`
- `tsv`

职责：

- 归档
- 下载
- 追溯
- 法务/协议交付

### 5.2 查询资产层

从原始表生成轻量查询资产：

- `sqlite`
- 后续可选 `parquet`

职责：

- 材料详情点查
- trait 列表
- 简单筛选
- 前端表格查询

### 5.3 平台结构化层

在 PostgreSQL 中保存标准化索引：

- material 维度
- trait 维度
- observation 维度

职责：

- trait 检索
- 聚合统计
- 结构化接口
- 与 breeding 域对接

---

## 6. Dataset 资产设计

### 6.1 dataset_type

建议新增：

- `dataset_type = phenome`

### 6.2 asset_type

建议至少新增两个正式资产类型：

- `phenotype_table`
- `phenotype_index`

可选后续扩展：

- `trait_dictionary`
- `sample_metadata`
- `phenotype_summary_table`

### 6.3 推荐资产组合

一个 `phenome dataset` 的某个 version 下，推荐有：

1. `phenotype_table`
   - 原始 `xlsx/csv/tsv`
   - 作为交付主文件

2. `phenotype_index`
   - 派生 `sqlite`
   - 作为查询入口资产

3. 可选 `trait_dictionary`
   - 若用户提供 trait 描述表，可单独挂载

### 6.4 真实案例映射

对于 rose 案例，建议直接映射为：

- `dataset_type = phenome`
- `asset_code = phenotype_table`
  - file: `rose_phenotype_test.xlsx`
- `asset_code = phenotype_index`
  - file: `rose_phenotype_test.db`
  - query_entry = true

---

## 7. SQLite 在 phenome 中的定位

### 7.1 结论

SQLite 是合理的，但不能是唯一长期查询层。

### 7.2 合理之处

- 单文件易分发
- 可伴随原始 phenotype 文件发布
- 很适合“按 ID 查整行详情”
- 对当前小中型 phenotype 宽表非常友好

### 7.3 局限

- trait 被摊平成列，不利于统一索引
- 年份列被编码到字段名中，不利于标准化时间维度
- 反向检索和聚合不自然
- 不适合承担跨 trial / 跨 dataset 的统一搜索

### 7.4 定位建议

- SQLite 作为版本内查询资产保留
- PostgreSQL 作为平台级结构化索引

一句话概括：

- SQLite 解决“这个材料有什么表型”
- PostgreSQL 解决“这个性状有哪些材料、如何过滤聚合”

---

## 8. PostgreSQL 标准化索引设计

第一阶段不建议直接建很重的业务模型，而是先建最小索引层。

### 8.1 `phenome_subject`

建议字段：

- `id`
- `dataset_id`
- `version_id`
- `asset_id`
- `subject_id`
- `subject_name_cn`
- `subject_name_en`
- `subject_type`
- `meta_json`
- `create_time`
- `update_time`

说明：

- `subject_id` 第一阶段可直接对应原始表中的 `ID`
- `subject_type` 可先默认 `material_candidate`
- 后续可映射到 breeding 的 `material / plot / trial`

### 8.2 `phenome_trait`

建议字段：

- `id`
- `dataset_id`
- `version_id`
- `asset_id`
- `trait_code`
- `trait_name`
- `trait_name_cn`
- `trait_name_en`
- `value_type`
- `unit`
- `time_axis_type`
- `category_group`
- `meta_json`
- `create_time`
- `update_time`

说明：

- 例如 `2021年花瓣数量` 不应长期直接等于 trait
- 应拆成：
  - `trait_name = 花瓣数量`
  - `timepoint = 2021`

### 8.3 `phenome_observation`

建议字段：

- `id`
- `dataset_id`
- `version_id`
- `asset_id`
- `subject_id`
- `trait_code`
- `timepoint`
- `obs_date`
- `value_numeric`
- `value_text`
- `value_category`
- `raw_value`
- `source_sheet`
- `source_row_key`
- `source_column_name`
- `qc_status`
- `meta_json`
- `create_time`

说明：

- 这是平台级最核心的索引表
- 每个宽表单元格最终都应转成一条 observation

### 8.4 `phenome_import_run`

建议字段：

- `id`
- `dataset_id`
- `version_id`
- `asset_id`
- `source_file_path`
- `source_checksum`
- `parser_version`
- `row_count`
- `trait_count`
- `observation_count`
- `status`
- `summary_json`
- `create_time`

说明：

- 用于保证可重建
- 用于审计和回放

---

## 9. 查询接口分层

建议明确分两类查询。

### 9.1 详情型查询

优先走 `sqlite` 查询资产。

建议接口：

- `subject_detail`
- `subject_trait_matrix`
- `dataset_trait_summary`

典型输入：

- `dataset_id / version_id`
- `subject_id`

典型输出：

- 某个材料的全部 trait
- 多年份并列展示
- 缺失值保留

### 9.2 检索型查询

优先走 PostgreSQL 标准化索引。

建议接口：

- `trait_list`
- `trait_values`
- `trait_subjects`
- `phenome_search`

典型输入：

- `trait_code`
- `keyword`
- `value range`
- `timepoint`
- `dataset/version/public filters`

典型输出：

- 某 trait 对应的材料列表
- trait 分布
- 统计计数

---

## 10. 与 breeding 域的关系

### 10.1 解耦原则

`phenome dataset` 必须允许独立注册，不依赖以下对象预先存在：

- `Program`
- `Material`
- `Trial`
- `Plot`
- `Observation`

### 10.2 挂接原则

后续进入 breeding 域时，应通过关联层逐步挂接，而不是在 dataset 注册时强绑定。

推荐路径：

1. `phenome dataset` 先落库
2. 解析出 `subject_id / trait / row_key`
3. 通过 `phenotype_subject_map` 逐步映射到：
   - `plot`
   - `material`
   - `trial`
4. 确认后再沉淀为正式 `Observation`

### 10.3 为什么这样设计

因为表型文件往往存在这些情况：

- 只有材料编号，没有 trial 结构
- 只有 plot 编号，但没有材料主数据
- 只有 Excel 宽表，没有标准 trait 词典
- 一个文件中混合多年份和多批次观测

如果强制先建 breeding 域对象，接入门槛会过高。

---

## 11. 前端页面建议

第一阶段不需要复杂页面，建议先做三类入口。

### 11.1 Dataset 概览页

展示：

- 数据集标题
- 版本
- 主体数量
- trait 数量
- 年份覆盖
- 文件资产列表

### 11.2 Subject 详情页

展示：

- `ID`
- 中文名 / 英文名
- 该主体的全部 trait
- 多年份值并排展示

### 11.3 Trait 检索页

展示：

- trait 列表
- 某 trait 对应材料值
- 排序 / 过滤 / 缺失值筛选

---

## 12. 当前 rose 案例的直接接入建议

基于当前真实数据，建议按最小方案推进：

### 12.1 第一阶段

- 新增 `phenome` dataset type
- 新增 `phenotype_table` asset type
- 新增 `phenotype_index` asset type
- 支持把：
  - `rose_phenotype_test.xlsx`
  - `rose_phenotype_test.db`
  注册为同一个 version 下的两个资产

### 12.2 查询入口

优先使用 `phenotype_index` 作为查询资产，先支持：

- `subject_detail`
- `trait_list`
- `dataset_summary`

### 12.3 结构化索引

第二阶段把 SQLite 宽表解析到 PostgreSQL：

- `phenome_subject`
- `phenome_trait`
- `phenome_observation`

### 12.4 breeding 关联

第三阶段再补：

- `phenotype_subject_map`
- 与 `Material / Plot / Trial / Observation` 的挂接

---

## 13. 分阶段实施建议

### 13.1 P1 最小接入

- 完成 `phenome` dataset type
- 完成 `phenotype_table / phenotype_index` asset type
- 完成 SQLite 查询 adapter
- 完成 rose 真实案例注册

### 13.2 P2 平台检索

- 建 PostgreSQL phenome 索引表
- 支持 trait 反查、过滤、聚合
- 前端补 trait 检索页

### 13.3 P3 breeding 整合

- 引入 phenotype 行映射
- 与 Material / Plot / Trial 建立关联
- 逐步沉淀 Observation

---

## 14. 最终结论

本设计建议：

1. 顶层 dataset 类型命名采用 `phenome`
2. `phenotype` 保留为具体表型记录与映射层术语
3. 平台采用“三层模型”：
   - 原始表文件
   - SQLite 查询资产
   - PostgreSQL 标准化索引
4. 与 breeding 域采用“先落文件、后做映射、再沉淀 observation”的解耦路线

一句话概括：

`phenome` 负责把表型数据先稳定纳入 Dataset 平台，
`phenotype / trait / observation` 负责把这些数据逐步接入 breeding 业务主线。
