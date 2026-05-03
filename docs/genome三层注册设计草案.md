# Genome 三层注册设计草案

## 1. 目标

围绕基因组类数据，明确采用三层注册模型：

- `dataset type`
- `asset type`
- `asset file type`

同时保留实例层：

- `dataset`
- `version`
- `asset`
- `asset file`

这两层不是互相替代，而是：

- 注册层回答“允许有哪些类型”
- 实例层回答“这个版本里实际有哪些对象和文件”

## 2. 命名约定

为了减少概念混淆，后续产品和设计文档优先使用：

- `dataset type`
- `asset type`
- `asset file type`

但考虑当前后端已经稳定使用 `dataset_kind_registry` 表名，因此第一阶段兼容策略是：

- 概念层把 `dataset kind` 视为 `dataset type`
- 数据库表名暂不强改
- API 与服务层先在现有结构上扩展第三层

也就是说：

- 产品语义：`dataset type`
- 兼容实现：`dataset_kind_registry`

## 3. 三层注册模型

### 3.1 第一层：dataset type

回答：

- 这是什么大类数据

对 genome 场景，第一阶段采用：

- `genome`

其职责：

- 前端分类入口
- 限定允许挂载的 `asset type`
- 决定默认展示结构

### 3.2 第二层：asset type

回答：

- 这个 dataset version 里包含哪些业务部件

对 genome 场景，第一阶段采用：

- `reference_fasta`
- `gene_annotation`
- `functional_annotation`
- `metadata_table`

其职责：

- 组织版本中的业务部件
- 绑定默认查询入口语义
- 绑定允许出现的 `asset file type`

### 3.3 第三层：asset file type

回答：

- 某类业务部件下面允许出现哪些“文件内容类型”

这里强调一个设计原则：

- 第三层不是按扩展名逐条注册
- 第三层描述的是语义内容类型
- 扩展名、压缩方式、用户提交习惯，退回成第三层记录的一个属性：`supported_file_formats`
- `supported_file_formats` 必须支持多个值，不能把格式写死

对 genome 场景，第一阶段采用：

- `reference_fasta` 下：
  - `genome_sequence`
  - `genome_sequence_index`
- `gene_annotation` 下：
  - `gene_models`
  - `gene_models_index`
  - `transcript_sequence`
  - `protein_sequence`
- `functional_annotation` 下：
  - `functional_annotation_db`
  - `functional_annotation_table`

其职责：

- 约束某个 `asset type` 允许登记哪些内容类型
- 为每个内容类型声明支持的 `file_format` 集合
- 标记文件角色，例如主文件、索引文件、派生文件
- 为后续前端三层树形展示提供注册依据

## 4. 实例层模型

实例层继续保持：

- `dataset`
- `version`
- `asset`
- `asset file`

解释如下：

- `dataset` 是具体数据集，例如 `arabidopsis_dataset01`
- `version` 是具体版本，例如 `TAIR10`
- `asset` 是该版本中的业务部件实例，例如 `Reference FASTA`
- `asset file` 是该业务部件挂载的具体物理文件，例如：
  - `genome.fa.gz`
  - `genome.fa.gz.fai`
  - `genome.fa.gz.gzi`

注册层和实例层的对应关系：

- `dataset.type` 属于某个 `dataset type`
- `asset.asset_type` 属于某个 `asset type`
- `asset_file.file_format` 需要落在某个 `asset file type.supported_file_formats` 集合中

## 5. Genome 第一阶段建议清单

### 5.1 dataset type

- `genome`

### 5.2 asset type

- `reference_fasta`
- `gene_annotation`
- `functional_annotation`
- `metadata_table`

### 5.3 asset file type

#### `reference_fasta`

- `genome_sequence`
  - `supported_file_formats`
  - `fa`
  - `fasta`
  - `fna`
  - `fa.gz`
  - `fasta.gz`
  - `fna.gz`
- `genome_sequence_index`
  - `supported_file_formats`
  - `fai`
  - `gzi`

建议角色：

- 主文件：
  - `genome_sequence`
- 索引文件：
  - `genome_sequence_index`

#### `gene_annotation`

- `gene_models`
  - `supported_file_formats`
  - `gff`
  - `gff.gz`
  - `gff3`
  - `gff3.gz`
  - `gtf`
  - `gtf.gz`
  - `db`
  - `sqlite`
- `gene_models_index`
  - `supported_file_formats`
  - `tbi`
- `transcript_sequence`
  - `supported_file_formats`
  - `fa`
  - `fasta`
  - `fna`
  - `fa.gz`
  - `fasta.gz`
  - `fna.gz`
- `protein_sequence`
  - `supported_file_formats`
  - `faa`
  - `fa`
  - `fasta`
  - `faa.gz`
  - `fa.gz`
  - `fasta.gz`

建议角色：

- 主文件：
  - `gene_models`
  - `transcript_sequence`
  - `protein_sequence`
- 索引文件：
  - `gene_models_index`

#### `functional_annotation`

- `functional_annotation_db`
  - `supported_file_formats`
  - `db`
  - `sqlite`
- `functional_annotation_table`
  - `supported_file_formats`
  - `tsv`
  - `csv`
  - `xlsx`
  - `xls`
  - `h5`
  - `hdf5`

建议角色：

- 主文件：
  - `functional_annotation_db`
  - `functional_annotation_table`

## 6. 数据库建议

第一阶段新增一张第三层注册表：

- `asset_file_type_registry`

建议字段：

- `id`
- `code`
- `base_code`
- `name`
- `description`
- `supported_file_formats`
- `file_role`
- `allowed_asset_types`
- `is_system`
- `is_active`
- `sort_order`
- `meta_json`
- `create_time`
- `update_time`

字段语义：

- `supported_file_formats`
  - 一个 JSON 数组
  - 表示该内容类型允许的多个文件格式
  - 例如 `["fa","fasta","fna","fa.gz","fasta.gz","fna.gz"]`
- `file_role`
  - 默认文件角色
  - 例如 `primary` / `index` / `derived` / `metadata`
- `allowed_asset_types`
  - JSON 数组
  - 例如 `["reference_fasta"]`

## 7. 第一阶段实现范围

本轮只做 genome 主线：

1. 新增 `asset_file_type_registry`
2. seed 基因组三层默认注册项
3. 第三层按“内容类型”建模，而不是按扩展名建模
4. 每条第三层记录携带 `supported_file_formats`
5. 提供后端 registry 查询接口
6. 先不改前端三层展示
7. 先不做全量 file type 校验拦截，只先把注册表和查询链补齐

## 8. 后续演进

在 genome 主线稳定后，再扩展：

- `variome`
- `transcriptome`
- `phenome`
- `interaction`

以及后续前端把类型注册页改成三层树：

- `dataset type`
  - `asset type`
    - `asset file type`
