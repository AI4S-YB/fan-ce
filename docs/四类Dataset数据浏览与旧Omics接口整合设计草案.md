# 四类 Dataset 数据浏览与旧 Omics 接口整合设计草案

本文档用于在正式改造前，把 `genome / transcriptome / variome / phenome` 四类数据的“数据浏览”目标、旧接口能力、现有 Dataset query adapter 能力、前端承接方式统一整理清楚。

这份文档不讨论数据注册、资产三层注册、版本发布等管理问题，只讨论一件事：

- 用户进入 Dataset 中心后，点击某个 dataset 的“数据浏览”，应该如何真正浏览数据文件内容。

---

## 1. 背景与问题

当前系统里其实同时存在两套查询语义：

- 旧 `omics:*` 业务接口
- 新 `apps/datasets` 的 `query adapter` 体系

两套并不是简单重复关系。

新 `query adapter` 已经把四类数据最小查询主线打通：

- `sequence`
- `expression`
- `variant`
- `phenome`

但如果直接把“数据浏览”完全收敛成当前 adapter 的最小能力，会丢掉旧系统里已经存在且仍然有价值的浏览逻辑，尤其是：

- `genome` 不只是序列查询
- `genome` 还包含 gene / transcript / feature / functional annotation 相关浏览
- 旧 portal 已经有一套相对成熟的 smart form + result view 设计

因此，本阶段不宜把四类数据浏览理解成一个统一的极简查询框，而应理解成：

- 用 Dataset 工作台承接统一容器
- 用旧 `omics:*` 能力定义各 dataset type 的真实浏览面
- 按需把旧能力逐步并入新的 Dataset query 层

---

## 2. 设计目标

本阶段目标是：

- 让四类 dataset 在 Dataset 中心都能有稳定可用的“数据浏览”入口
- 浏览动作直接面向真实文件内容，而不是只看元数据
- 复用旧接口里已经成熟的查询范式
- 尽量复用旧 portal 中已有的 smart form 和结果展示设计
- 不要求第一阶段就把所有旧接口全部重写成新的 adapter

非目标：

- 不在这一阶段重做一整套独立的组学浏览前端系统
- 不要求旧 `omics:*` 接口立即全部废弃
- 不要求所有浏览能力都先重构到底层 PostgreSQL

---

## 3. 参考实现来源

后端旧接口：

- [m_genome.py](/Users/kentnf/projects/fan-ce/backend/api-server/basis/api/m_genome.py)
- [g_sequences.py](/Users/kentnf/projects/fan-ce/backend/api-server/basis/api/g_sequences.py)
- [g_genes.py](/Users/kentnf/projects/fan-ce/backend/api-server/basis/api/g_genes.py)
- [g_features.py](/Users/kentnf/projects/fan-ce/backend/api-server/basis/api/g_features.py)
- [d_expression.py](/Users/kentnf/projects/fan-ce/backend/api-server/basis/api/d_expression.py)
- [d_variant.py](/Users/kentnf/projects/fan-ce/backend/api-server/basis/api/d_variant.py)
- [d_phenome.py](/Users/kentnf/projects/fan-ce/backend/api-server/basis/api/d_phenome.py)

新 Dataset adapter：

- [sequence.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/datasets/adapters/sequence.py)
- [expression.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/datasets/adapters/expression.py)
- [variant.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/datasets/adapters/variant.py)
- [phenome.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/datasets/adapters/phenome.py)
- [annotation.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/datasets/adapters/annotation.py)
- [functional_annotation.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/datasets/adapters/functional_annotation.py)

旧前端查询参考：

- [App.vue](/Users/kentnf/projects/fan-ce/frontend/portal-web/src/App.vue)
- [query.vue](/Users/kentnf/projects/fan-ce/frontend/admin-web/apps/web-antd/src/views/apps/phenome/query.vue)

当前 Dataset 工作台：

- [index.vue](/Users/kentnf/projects/fan-ce/frontend/admin-web/apps/web-antd/src/views/apps/dataset/index.vue)

---

## 4. 总体结论

### 4.1 四类数据浏览不是同一种浏览

四类 dataset 的浏览对象不同：

- `genome`：序列 + 基因实体 + 转录本实体 + 区域 feature + 功能注释
- `transcriptome`：表达矩阵切片
- `variome`：区间变异记录
- `phenome`：trait / subject / observation

因此，前端必须采用：

- 统一工作台容器
- dataset type 定制浏览分组

而不是强行做成一个所有类型完全对称的查询表单。

### 4.2 genome 是复合浏览器，不是单功能浏览器

`genome` 不能被简化成“只查 FASTA 序列”。

旧 `omics:genome` 实际上至少包含 4 条业务线：

- 序列
- gene / transcript
- 区域 feature
- functional annotation

所以 `genome` 的数据浏览页面应是一个多标签浏览器。

### 4.3 新旧两套查询层要并轨，不是二选一

建议采用：

- 第一阶段：Dataset 工作台承接统一入口，旧 `omics:*` 和新 adapter 并存
- 第二阶段：把确实稳定、通用的旧能力逐步沉淀进 Dataset adapter
- 第三阶段：再视情况收缩旧 `basis/api/*`

---

## 5. 四类数据浏览能力矩阵

## 5.1 genome

### 浏览对象

- 参考基因组序列
- gene 列表与搜索
- transcript 列表与详情
- 区域 feature
- 基因功能注释

### 旧接口能力

#### 序列

- `/omics/genome/sequence/example`
- `/omics/genome/sequence/fetch`
- `/omics/genome/sequence/batchquery`

#### gene / transcript

- `/omics/gene/search`
- `/omics/gene/list`
- `/omics/gene/transcript/list`
- `/omics/gene/info`
- `/omics/gene/transcript/info`

#### feature

- `/omics/genome/feature/query`

### 新 Dataset 层已存在能力

- `sequence` adapter
  - `fetch`
  - `batch_fetch`
- `annotation` adapter
  - `table_stats`
  - `gene_lookup`
  - `region_features`
- `functional_annotation` adapter
  - `gene_detail`
  - `transcript_detail`
  - `gene_function_summary`
  - `term_lookup`
  - `term_gene_list`
  - `term_aggregation`

### 结论

`genome` 已经具备被收敛到 Dataset 工作台的基础条件。

但前端必须把它组织成多标签：

- `序列`
- `基因`
- `转录本`
- `Feature`
- `功能注释`

而不是只展示一个 `fetch` 操作。

### 默认浏览入口建议

- 默认标签：`基因`
- 默认操作：`gene_lookup` 或 `gene_detail`

原因：

- 用户进入 genome，往往不是只想看裸序列
- 更常见路径是“定位基因 -> 看结构和功能”

### genome 第一阶段前端结构建议

- `序列`
  - `fetch`
  - `batch_fetch`
- `基因`
  - `gene_lookup`
  - 兼容旧 `search`
- `区域 Feature`
  - `region_features`
- `功能注释`
  - `gene_detail`
  - `transcript_detail`
  - `gene_function_summary`

---

## 5.2 transcriptome

### 浏览对象

- HDF5 表达矩阵
- gene 名单
- sample 名单
- gene x sample 的矩阵切片

### 旧接口能力

- `/omics/rnaseq/genes/list`
- `/omics/rnaseq/samples/list`
- 旧逻辑的表达矩阵提取

### 新 Dataset 层已存在能力

- `expression` adapter
  - `genes_list`
  - `samples_list`
  - `matrix_slice`

### 结论

`transcriptome` 已经适合完全走 Dataset adapter。

旧接口主要提供了交互方式参考，不再需要作为独立主线保留。

### 默认浏览入口建议

- 默认操作：`matrix_slice`

原因：

- `genes_list / samples_list` 只是辅助索引
- 真正的数据浏览是表达矩阵切片

### transcriptome 第一阶段前端结构建议

- `矩阵切片`
  - `matrix_slice`
- `基因列表`
  - `genes_list`
- `样本列表`
  - `samples_list`

---

## 5.3 variome

### 浏览对象

- VCF / BCF 变异记录
- 样本名
- 区间内变异内容预览

### 旧接口能力

- `/omics/variants/region/example`
- `/omics/variants/samples/list`
- `/omics/variants/query`

### 新 Dataset 层已存在能力

- `variant` adapter
  - `region_example`
  - `samples_list`
  - `query`

### 结论

`variome` 已经可以完全走 Dataset adapter。

### 默认浏览入口建议

- 默认操作：`query`

原因：

- `region_example` 是辅助生成示例区间
- 真正的数据浏览是“按区间读取变异记录”

### variome 第一阶段前端结构建议

- `区间查询`
  - `query`
- `样本列表`
  - `samples_list`
- `示例区间`
  - `region_example`

---

## 5.4 phenome

### 浏览对象

- trait 定义
- subject 列表
- subject 详情
- 指定 trait 的观测值

### 旧接口能力

- `/omics/trait/names/list`
- `/omics/trait/samples/list`
- `/omics/trait/query`

### 新 Dataset 层已存在能力

- `phenome` adapter
  - `dataset_summary`
  - `trait_list`
  - `trait_search`
  - `subject_list`
  - `subject_detail`
  - `trait_values`

### 结论

`phenome` 新 adapter 已明显优于旧接口抽象。

旧接口仍可作为兼容桥，但新的浏览主线应直接走 Dataset adapter。

### 默认浏览入口建议

- 默认操作：`dataset_summary`
- 主浏览路径：`summary -> trait_list / trait_search -> trait_values`

### phenome 第一阶段前端结构建议

- `总览`
  - `dataset_summary`
- `性状`
  - `trait_list`
  - `trait_search`
  - `trait_values`
- `材料/样本`
  - `subject_list`
  - `subject_detail`

---

## 6. 前端统一容器设计

数据浏览仍放在 Dataset 工作台中，但不再只显示“操作下拉框 + 参数 JSON”。

统一容器分成三层：

### 6.1 顶部摘要层

- 当前 dataset / version
- 当前 query entry asset
- 当前 adapter
- 文件可访问状态

### 6.2 dataset type 导航层

不同 dataset type 显示不同浏览标签：

- `genome`
  - 序列
  - 基因
  - Feature
  - 功能注释
- `transcriptome`
  - 矩阵切片
  - 基因列表
  - 样本列表
- `variome`
  - 区间查询
  - 样本列表
  - 示例区间
- `phenome`
  - 总览
  - 性状
  - 材料/样本

### 6.3 查询与结果层

每个标签内再显示：

- smart form
- JSON 参数
- 结果区

其中结果区应优先复用旧 portal 里已经成熟的渲染样式。

---

## 7. 新旧接口并轨策略

## 7.1 第一阶段

目标：

- 先让 Dataset 工作台成为统一入口
- 不强求底层立刻只剩一套 API

策略：

- `transcriptome / variome / phenome`
  - 直接优先走新的 Dataset adapter
- `genome`
  - 优先走新的 `sequence + annotation + functional_annotation` adapter
  - 缺失的 gene search / transcript list 能力，先桥接旧 `omics/gene/*`

## 7.2 第二阶段

把 genome 缺失能力逐步沉淀到新的 Dataset adapter：

- `gene_search`
- `gene_list`
- `transcript_list`
- `gene_info`
- `transcript_info`

此时旧 `omics/gene/*` 可逐步转为兼容层。

## 7.3 第三阶段

当 Dataset 工作台里的 genome 浏览器稳定后：

- 将旧 portal 中与四类数据浏览直接相关的重复入口收缩
- 让 Dataset 工作台成为 admin 端统一浏览面

---

## 8. 实施建议

建议按下面顺序推进。

### Step 1

先补一份前端浏览能力映射表：

- 哪个 dataset type 显示哪些标签
- 每个标签默认调用哪个 operation
- 每个 operation 用哪套结果组件

### Step 2

先在 Dataset 工作台中补齐四类结果视图：

- `sequence`
- `expression`
- `variant`
- `phenome`

这一步优先复用：

- [App.vue](/Users/kentnf/projects/fan-ce/frontend/portal-web/src/App.vue)

### Step 3

把 `phenome` 从旧独立页完全并回 Dataset 工作台。

### Step 4

为 `genome` 增加二级浏览标签，并决定哪些先桥接旧接口、哪些直接走新 adapter。

### Step 5

再考虑是否把旧 `omics:*` 接口逐步适配成新的 Dataset adapter 能力。

---

## 9. 前端标签与 Operation 映射表

这一节用于直接指导 Dataset 工作台里的“数据浏览”实施。

## 9.1 总体规则

- 一级仍使用 Dataset 工作台的统一 `查询` Tab 容器
- 在 `查询` Tab 内，根据 dataset type 再显示二级浏览标签
- 每个二级标签绑定一个默认 operation
- 每个 operation 绑定一个结果组件
- 第一阶段尽量复用现有 portal 结果视图，不重新发明展示方式

---

## 9.2 genome

| 二级标签 | 默认 operation | 后端来源 | 结果视图 |
| --- | --- | --- | --- |
| 序列 | `fetch` | Dataset `sequence` adapter | 序列文本卡片 |
| 基因 | `gene_lookup` 或桥接 `gene_search` | Dataset `annotation` adapter + 旧 `omics/gene/search` | gene 列表 / gene 详情卡片 |
| 转录本 | `transcript_detail` 或桥接 `transcript_list` | Dataset `functional_annotation` adapter + 旧 `omics/gene/transcript/list` | transcript 列表 / transcript 详情 |
| Feature | `region_features` | Dataset `annotation` adapter | feature 表格 |
| 功能注释 | `gene_detail` | Dataset `functional_annotation` adapter | functional gene / transcript 结果视图 |

### genome 第一阶段说明

- `序列 / Feature / 功能注释` 可以先直接走 Dataset adapter
- `基因 / 转录本` 这两块如果 Dataset adapter 现阶段不够顺手，允许先桥接旧 `omics/gene/*`
- genome 页面里必须允许用户围绕 `gene_id` 连续浏览：
  - gene 结构
  - transcript
  - functional annotation

### genome 默认落点

- 默认标签：`基因`
- 默认行为：
  - 若当前 adapter 已支持 `gene_lookup`，直接进入 `gene_lookup`
  - 若要先保留旧逻辑，则进入旧 `gene_search`

---

## 9.3 transcriptome

| 二级标签 | 默认 operation | 后端来源 | 结果视图 |
| --- | --- | --- | --- |
| 矩阵切片 | `matrix_slice` | Dataset `expression` adapter | matrix table |
| 基因列表 | `genes_list` | Dataset `expression` adapter | chip / list |
| 样本列表 | `samples_list` | Dataset `expression` adapter | chip / list |

### transcriptome 第一阶段说明

- 直接走 Dataset adapter
- 结果区复用 portal 中已有的 `matrix_slice / genes_list / samples_list` 展示逻辑

### transcriptome 默认落点

- 默认标签：`矩阵切片`
- 默认 operation：`matrix_slice`

---

## 9.4 variome

| 二级标签 | 默认 operation | 后端来源 | 结果视图 |
| --- | --- | --- | --- |
| 区间查询 | `query` | Dataset `variant` adapter | VCF preview + download |
| 样本列表 | `samples_list` | Dataset `variant` adapter | chip / list |
| 示例区间 | `region_example` | Dataset `variant` adapter | region chips |

### variome 第一阶段说明

- 直接走 Dataset adapter
- `region_example` 是辅助，不是主入口
- 区间查询结果优先显示：
  - preview
  - count
  - size
  - download_url

### variome 默认落点

- 默认标签：`区间查询`
- 默认 operation：`query`

---

## 9.5 phenome

| 二级标签 | 默认 operation | 后端来源 | 结果视图 |
| --- | --- | --- | --- |
| 总览 | `dataset_summary` | Dataset `phenome` adapter | summary cards |
| 性状 | `trait_list` | Dataset `phenome` adapter | trait table |
| 性状搜索 | `trait_search` | Dataset `phenome` adapter | trait search table |
| 性状观测 | `trait_values` | Dataset `phenome` adapter | values table |
| 材料/样本 | `subject_list` | Dataset `phenome` adapter | subject list |
| 样本详情 | `subject_detail` | Dataset `phenome` adapter | subject detail table |

### phenome 第一阶段说明

- 新 adapter 已经比旧 `/omics/trait/*` 更适合当前平台
- `phenome/query.vue` 最终应被 Dataset 工作台吸收
- 旧接口只保留兼容，不再作为主浏览入口

### phenome 默认落点

- 默认标签：`总览`
- 主浏览路径：
  - `dataset_summary`
  - `trait_list / trait_search`
  - `trait_values`

---

## 9.6 第一阶段结果组件复用映射

优先从 [App.vue](/Users/kentnf/projects/fan-ce/frontend/portal-web/src/App.vue) 复用以下结果视图：

- `sequence.fetch`
- `sequence.batch_fetch`
- `variant.samples_list`
- `variant.region_example`
- `variant.query`
- `expression.genes_list`
- `expression.samples_list`
- `expression.matrix_slice`
- `annotation.gene_lookup`
- `annotation.region_features`
- `functional_annotation.gene_detail`
- `functional_annotation.transcript_detail`
- `functional_annotation.gene_function_summary`
- `functional_annotation.term_lookup`
- `functional_annotation.term_gene_list`
- `functional_annotation.term_aggregation`
- `phenome.dataset_summary`
- `phenome.trait_list`
- `phenome.trait_search`
- `phenome.subject_list`
- `phenome.subject_detail`
- `phenome.trait_values`

---

## 9.7 第一阶段不做的内容

这一轮先不做：

- 把四类浏览完全拆成独立路由页
- 重做一套新的 portal 级查询前端
- 把 genome 的所有旧接口都先重写成 Dataset adapter
- 跨 dataset 联合浏览
- 与育种项目详情页的深度联动

---

## 10. 当前最关键的设计决定

本次讨论后，建议先固定下面 4 条。

- `genome` 是复合浏览器，不是单一序列浏览器。
- `transcriptome` 的默认浏览应是 `matrix_slice`。
- `variome` 的默认浏览应是区间 `query`，不是 `region_example`。
- `phenome` 的默认浏览应是 `dataset_summary`，主线是 `trait_values`，不是旧 xls 查询页。

---

## 11. 最终结论

Dataset 工作台里的“数据浏览”不应只是一个抽象查询框，而应是：

- 统一入口
- 分类型浏览
- 底层允许新旧接口并轨

一句话概括：

- `genome` 看序列、基因、feature 和功能
- `transcriptome` 看表达矩阵
- `variome` 看区间变异
- `phenome` 看性状与样本观测

下一步可以直接按本设计开始实施前端：

- 先补 `transcriptome / variome / phenome` 三类结果视图
- 再把 `phenome` 旧独立页并回 Dataset 工作台
- 最后单独做 `genome` 复合浏览器
