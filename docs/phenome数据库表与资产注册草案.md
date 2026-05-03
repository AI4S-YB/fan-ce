# phenome 数据库表与资产注册草案

## 1. 目标

本文是在 [phenome数据接入与结构化设计草案.md](/Users/kentnf/projects/fan-ce/docs/phenome数据接入与结构化设计草案.md) 基础上的下一层落地设计。

本草案解决两件事：

1. `phenome` 在 Dataset 平台中的正式注册方式
2. `phenome` 在 PostgreSQL 中的最小结构化表设计

这份设计的定位是：

- 能支撑第一阶段真实 rose phenome 数据接入
- 不阻塞后续与 breeding 域整合
- 不把 phenotype 文件一开始就强制改造成 breeding 业务对象

---

## 2. 命名与边界

### 2.1 顶层命名

建议：

- `dataset_type = phenome`

### 2.2 业务术语保留

继续保留以下术语：

- `phenotype`
  - 用于文件内容、表型记录、行映射
- `trait`
  - 用于性状定义
- `observation`
  - 用于 breeding 域中的正式业务观测对象

### 2.3 表前缀建议

建议新增的 phenome 平台索引表统一使用前缀：

- `phn_`

原因：

- 与 breeding 域 `brd_` 清晰区分
- 表示它属于 Dataset 平台的 phenome 结构化索引层
- 未来即使 breeding 域完全展开，`phn_` 仍然有独立存在价值

---

## 3. Dataset 注册表设计

### 3.1 dataset kind 建议

建议新增系统数据类型：

| 字段 | 建议值 |
| --- | --- |
| `code` | `phenome` |
| `base_code` | `phenotype_set` |
| `name` | `表型组` |
| `description` | 表型矩阵、性状观测表、性状统计表等表型相关数据集 |
| `is_system` | `1` |
| `is_active` | `1` |

说明：

- 这里 `base_code` 继续沿用此前正式设计中提过的 `phenotype_set`
- 但对外统一叫 `phenome`

### 3.2 asset type 建议

建议第一阶段新增两个正式 `asset_type`：

#### 3.2.1 `phenotype_table`

定位：

- 原始 phenotype 表文件

建议字段语义：

| 字段 | 建议值 |
| --- | --- |
| `code` | `phenotype_table` |
| `base_code` | `phenotype_table` |
| `name` | `表型原始表` |
| `allowed_dataset_types` | `["phenome"]` |
| `default_query_adapter` | `file` 或空 |
| `is_queryable` | 否 |

建议支持格式：

- `xlsx`
- `xls`
- `csv`
- `tsv`

#### 3.2.2 `phenotype_index`

定位：

- 为 phenotype 文件生成的查询资产

建议字段语义：

| 字段 | 建议值 |
| --- | --- |
| `code` | `phenotype_index` |
| `base_code` | `phenotype_index` |
| `name` | `表型查询索引` |
| `allowed_dataset_types` | `["phenome"]` |
| `default_query_adapter` | `phenome` |
| `is_queryable` | 是 |

建议支持格式：

- `sqlite`
- `db`
- 后续可扩展 `parquet`

### 3.3 可选扩展 asset type

后续可扩展：

- `trait_dictionary`
- `phenotype_summary_table`
- `sample_metadata`

但第一阶段不建议一次性启用过多类型。

---

## 4. Version 下的推荐资产组合

一个 `phenome dataset` 的某个 version，建议采用以下标准组合：

### 4.1 最小组合

1. `phenotype_table`
   - 原始交付文件
2. `phenotype_index`
   - 查询入口

### 4.2 推荐规则

- `phenotype_table` 保留原始交付文件，不做强变更
- `phenotype_index` 作为 `query_entry = true`
- 同一 version 内两者强绑定
- 查询层优先读 `phenotype_index`

### 4.3 真实案例映射

对于 rose 案例：

- `rose_phenotype_test.xlsx`
  - 注册为 `phenotype_table`
- `rose_phenotype_test.db`
  - 注册为 `phenotype_index`
  - 作为 `query_entry`

---

## 5. PostgreSQL 表设计原则

### 5.1 保留源文件可追溯性

所有标准化记录都必须能追溯回：

- `dataset_id`
- `version_id`
- `asset_id`
- 原始文件中的 `sheet / row / column`

### 5.2 不把宽表列名直接当最终业务模型

例如：

- `2021年花瓣数量`

在原始文件中可以作为列名存在；
但在结构化层中建议拆为：

- `trait_code = petal_count`
- `trait_name = 花瓣数量`
- `timepoint = 2021`

### 5.3 与 breeding 解耦

`phn_*` 表不强制外键到：

- `brd_program`
- `brd_trial`
- `brd_plot`
- `brd_material`

这些映射应通过后续桥接层完成。

---

## 6. PostgreSQL 最小表集合

第一阶段建议先建 5 张表。

### 6.1 `phn_import_run`

定位：

- 记录一次 phenome 文件导入与索引构建过程

建议字段：

- `id`
- `dataset_id`
- `version_id`
- `asset_id`
- `source_file_path`
- `source_checksum`
- `parser_name`
- `parser_version`
- `sheet_count`
- `row_count`
- `trait_count`
- `observation_count`
- `status`
- `summary_json`
- `created_at`
- `updated_at`
- `created_by`
- `updated_by`

用途：

- 可重建
- 可审计
- 可比较两次导入差异

### 6.2 `phn_subject`

定位：

- 记录原始 phenotype 表中的观测主体

建议字段：

- `id`
- `dataset_id`
- `version_id`
- `asset_id`
- `import_run_id`
- `subject_id`
- `subject_name`
- `subject_name_cn`
- `subject_name_en`
- `subject_type`
- `source_sheet`
- `source_row_key`
- `meta_json`
- `created_at`
- `updated_at`

说明：

- 第一阶段 `subject_id` 可直接对应用例中的 `ID`
- `subject_type` 第一阶段建议默认：
  - `material_candidate`

### 6.3 `phn_trait`

定位：

- 记录 trait 定义

建议字段：

- `id`
- `dataset_id`
- `version_id`
- `asset_id`
- `import_run_id`
- `trait_code`
- `trait_name`
- `trait_name_cn`
- `trait_name_en`
- `value_type`
- `unit`
- `time_axis_type`
- `category_group`
- `display_order`
- `meta_json`
- `created_at`
- `updated_at`

说明：

- `value_type` 推荐值：
  - `numeric`
  - `categorical`
  - `text`
- `time_axis_type` 推荐值：
  - `none`
  - `year`
  - `date`
  - `season`

### 6.4 `phn_source_column`

定位：

- 记录原始列到结构化 trait 的映射

建议字段：

- `id`
- `dataset_id`
- `version_id`
- `asset_id`
- `import_run_id`
- `source_sheet`
- `source_column_name`
- `source_column_index`
- `trait_id`
- `trait_code`
- `timepoint`
- `parse_rule`
- `meta_json`
- `created_at`

说明：

- 这张表非常重要
- 它保证宽表结构的可解释性
- 例如：
  - `source_column_name = 2021年花瓣数量`
  - `trait_code = petal_count`
  - `timepoint = 2021`

### 6.5 `phn_observation`

定位：

- 平台级表型观测索引主表

建议字段：

- `id`
- `dataset_id`
- `version_id`
- `asset_id`
- `import_run_id`
- `subject_id`
- `trait_id`
- `trait_code`
- `timepoint`
- `obs_date`
- `value_numeric`
- `value_text`
- `value_category`
- `raw_value`
- `is_missing`
- `source_sheet`
- `source_row_key`
- `source_column_name`
- `qc_status`
- `meta_json`
- `created_at`

说明：

- 一条 observation 对应原始宽表中的一个有效单元格
- `raw_value` 用于保留原始值
- 标准化值拆到三个字段：
  - `value_numeric`
  - `value_text`
  - `value_category`

---

## 7. 主键、唯一键、索引建议

### 7.1 `phn_import_run`

建议索引：

- `(dataset_id, version_id, asset_id, created_at desc)`

### 7.2 `phn_subject`

建议唯一键：

- `(asset_id, subject_id, source_row_key)`

建议索引：

- `(dataset_id, version_id, subject_id)`

### 7.3 `phn_trait`

建议唯一键：

- `(asset_id, trait_code)`

建议索引：

- `(dataset_id, version_id, trait_name)`

### 7.4 `phn_source_column`

建议唯一键：

- `(asset_id, source_sheet, source_column_name)`

建议索引：

- `(asset_id, trait_code, timepoint)`

### 7.5 `phn_observation`

建议索引：

- `(dataset_id, version_id, subject_id)`
- `(dataset_id, version_id, trait_code)`
- `(dataset_id, version_id, trait_code, timepoint)`
- `(asset_id, source_sheet, source_row_key)`
- `(dataset_id, version_id, qc_status)`

---

## 8. 与 breeding 的挂接方式

### 8.1 不直接在 `phn_*` 中写 breeding 外键

理由：

- 会抬高文件接入门槛
- 会把 platform index 层和 breeding 主数据耦合死

### 8.2 推荐桥接方式

后续通过以下路径挂接：

1. `phn_subject`
   - 与 `brd_material / brd_plot / brd_trial` 建立映射
2. `phn_observation`
   - 在确认后转化为 `brd_observation`
3. `phenotype_subject_map`
   - 作为过渡桥

### 8.3 兼容真实业务的原因

因为很多 phenotype 文件初始只有：

- 材料编号
- 中文名
- 一组 trait 列

而没有：

- 正式 trial 编码
- plot 编号
- 观测协议

平台必须允许先落库。

---

## 9. 导入流程建议

### 9.1 第一阶段导入链

1. 注册 `phenotype_table`
2. 生成或挂接 `phenotype_index`
3. 解析原始表头
4. 生成 `phn_import_run`
5. 生成 `phn_subject`
6. 生成 `phn_trait`
7. 生成 `phn_source_column`
8. 生成 `phn_observation`

### 9.2 重建语义

建议导入采用“按 asset/version 重建”策略：

- 同一 `asset_id` 重建时
- 删除上一轮对应的 `phn_subject / phn_trait / phn_source_column / phn_observation`
- 再写入新一轮数据

这样可以避免增量同步复杂化。

---

## 10. 第一阶段接口建议

在 `phenotype_index` adapter 或 `phenome` adapter 中，第一阶段建议只支持以下接口：

- `dataset_summary`
- `subject_list`
- `subject_detail`
- `trait_list`
- `trait_values`

其中：

### 10.1 `dataset_summary`

返回：

- subject 数量
- trait 数量
- timepoint 覆盖
- 缺失率摘要

### 10.2 `subject_detail`

输入：

- `subject_id`

返回：

- 主体展示信息
- 全部 trait 及其按年份展开的值

### 10.3 `trait_values`

输入：

- `trait_code`
- 可选 `timepoint`

返回：

- 所有主体在该 trait 下的值

---

## 11. rose 案例的直接映射

以当前案例为例：

- `ID`
  - 对应 `phn_subject.subject_id`
- `chinese_name`
  - 对应 `subject_name_cn`
- `english_name`
  - 对应 `subject_name_en`
- `花瓣长`
  - trait: `petal_length`
- `瓶插寿命`
  - trait: `vase_life`
- `2021年花瓣数量`
  - trait: `petal_count`
  - timepoint: `2021`

这意味着当前这批数据已经非常适合作为 `phenome` 最小真实接入案例。

---

## 12. 实施顺序建议

### 12.1 先做

1. 注册 `phenome` dataset type
2. 注册 `phenotype_table / phenotype_index` asset type
3. 新增 `phn_*` PostgreSQL 表
4. 做最小 `phenome` adapter

### 12.2 再做

1. rose 真实案例接入
2. `xlsx + sqlite` 双资产注册
3. `subject_detail / trait_list / trait_values`

### 12.3 最后再做

1. 与 `phenotype_subject_map` 打通
2. 向 `brd_observation` 结构化沉淀
3. trial / plot / material 级联视图

---

## 13. 最终结论

本草案建议：

1. `phenome` 作为平台正式数据类型
2. 第一阶段只启用：
   - `phenotype_table`
   - `phenotype_index`
3. 平台索引层新增：
   - `phn_import_run`
   - `phn_subject`
   - `phn_trait`
   - `phn_source_column`
   - `phn_observation`
4. 与 breeding 域继续解耦，通过桥接层逐步整合

一句话概括：

先把 phenotype 文件稳定变成 `phenome dataset`，
再把宽表逐步沉淀成可检索、可映射、可进入 breeding 主线的结构化 observation 索引。
