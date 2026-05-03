# 数据扫描到 Dataset 中心注册设计草案

## 1. 文档目标

这份文档解决的是 Dataset 平台下一阶段最核心的问题：

- 数据扫描页发现的服务器文件，如何稳定进入 Dataset 中心
- 不同组学数据，如何以“最少用户输入 + 受控自动化”的方式注册
- 已经积累好的预制数据，如何不重跑长流程而直接纳管
- 新数据到来时，如何继续保留 recipe 分析和自动派生能力

这份文档是“可审核版总设计”，把当前讨论过的关键点统一落下：

- `registration_mode` 设计
- `candidate` 数据表草案
- 四类 `dataset type` 的 registration recipe 草案
- 扫描结果如何识别 `source candidate` 和 `prebuilt candidate`
- genome 三种注册模式的页面与后端流程
- 前端注册向导页面草图
- 与现有 `dataset -> version -> asset -> asset file` 主线的连接方式

---

## 2. 当前问题的本质

现在平台已经有两条线：

1. `Dataset 中心`
   - 负责正式数据的管理、版本、资产、文件、查询、发布
2. `数据扫描`
   - 负责发现服务器目录中的文件并写入 staging

真正缺失的不是“继续扫描更多文件”，而是中间缺了一层“注册候选与注册流程”：

- 扫描出的文件还只是文件级记录
- Dataset 中心需要的是：
  - 一个明确的数据类型
  - 一个版本
  - 一组资产
  - 一组资产文件

因此，下一阶段不能把“扫描出的文件”直接当成 Dataset。

需要增加一个中间层：

- 扫描文件
- 注册候选
- 注册模式
- 按数据类型套用 recipe
- 再正式落到 Dataset 中心

---

## 3. 设计结论

### 3.1 核心结论

平台不应该只支持一种接入方式，而应同时支持两条主线：

1. `预制数据注册`
2. `recipe 分析构建`

并补一个中间态：

3. `混合补全注册`

也就是说，下一阶段不是“只允许最小输入自动构建”，也不是“完全自由上传已有结果”，而是：

- 按 `dataset type` 提供受控的多模式注册
- 不同模式最终都落到同一套 Dataset 中心实例结构
- 差别只在于：
  - 哪些文件是用户直接提供的
  - 哪些文件是系统自动生成的

### 3.2 统一落点

无论哪种模式，最终都必须收口到当前主线：

- `dataset`
- `version`
- `asset`
- `asset file`

其中类型注册层继续沿用三层：

- `dataset type`
- `asset type`
- `asset file type`

---

## 4. 设计原则

### 4.1 源文件优先

数据扫描默认发现和关注的是“用户原始提供或用户可维护的文件”，不是系统内部派生缓存。

### 4.2 按数据类型走固定 recipe

平台不做一个完全通用、完全自由的“文件拼装器”。

更合理的方式是：

- genome 走 genome recipe
- transcriptome 走 transcriptome recipe
- variome 走 variome recipe
- phenome 走 phenome recipe

### 4.3 用户尽量少填

对绝大部分真实场景，应优先支持：

- 一个或少量输入文件
- 系统自动补索引、sqlite、hdf5、派生序列等

### 4.4 预制数据必须允许

尤其是 genome，必须支持直接纳管已有长期积累成果：

- `genome.fasta`
- `gene.gff`
- `genome.db`
- 索引
- mRNA / protein / 其他预制文件

### 4.5 动态字段不中心化硬编码

phenome 和 germplasm 这类数据要保留：

- 固定骨架字段
- 批次字段快照
- 行级动态字段值

不能强行把所有 trait 列全写死到中心库结构中。

### 4.6 扫描结果与 Dataset 正式数据要可重复对账

今天扫一次、明天再扫一次，系统应能知道：

- 新增了什么
- 变化了什么
- 哪些文件已注册，应跳过
- 哪些文件已消失，应标缺失

---

## 5. 术语

### 5.1 扫描层术语

- `scan root`
  - 一个服务器目录配置
- `scan job`
  - 一次实际扫描执行
- `staging file`
  - 扫描发现的文件记录

### 5.2 注册层术语

- `candidate`
  - 一个待注册的数据候选
- `candidate source file`
  - 构成候选的数据输入文件
- `registration recipe`
  - 一类数据的标准接入方案
- `registration mode`
  - 某个候选采用何种注册方式

### 5.3 正式层术语

- `dataset`
- `version`
- `asset`
- `asset file`

---

## 6. 总体架构

建议下一阶段的完整链路为：

1. 用户配置扫描目录
2. 系统执行数据扫描，生成 `dataset_staging_file`
3. 系统或用户基于扫描结果生成 `candidate`
4. 用户选择 `registration_mode`
5. 系统套用对应 `registration_recipe`
6. 完成：
   - 校验
   - 自动补全
   - 派生构建
   - 资产映射
7. 注册为 Dataset 中心正式数据

简化后的逻辑关系是：

- `scan root`
  -> `staging file`
  -> `candidate`
  -> `dataset/version/asset/file`

---

## 7. registration_mode 设计

建议引入统一字段：

- `registration_mode`

取值建议：

### 7.1 `prebuilt`

含义：

- 用户已经准备好了平台可直接使用的大部分或全部结果文件
- 系统以校验、识别、挂载、补元数据为主

适用：

- genome 最重要
- 也可用于 variome、transcriptome、phenome 的高级用户场景

典型场景：

- genome 已有 `genome.db`
- variome 已有 `vcf.gz + tbi`
- transcriptome 已有标准化 `hdf5`
- phenome 已有符合平台 schema 的 sqlite

### 7.2 `recipe_build`

含义：

- 用户只提供最小源文件
- 系统按 recipe 自动完成标准化和派生构建

适用：

- transcriptome
- variome
- phenome
- 新 genome 的标准化接入

### 7.3 `hybrid`

含义：

- 用户提供部分结果
- 缺失部分由系统补生成

适用：

- genome 最实用
- 也适用于 variome 缺索引、phenome 缺 sqlite、transcriptome 缺 hdf5 等情形

### 7.4 推荐策略

按数据类型建议默认值如下：

- `genome`
  - 默认推荐：`prebuilt` 或 `hybrid`
- `transcriptome`
  - 默认推荐：`recipe_build`
- `variome`
  - 默认推荐：`recipe_build`
- `phenome`
  - 默认推荐：`recipe_build`

---

## 8. candidate 中间层设计

## 8.1 为什么需要 candidate

扫描结果只是文件级记录，但注册过程需要表达：

- 这是一份什么数据
- 它准备按哪种模式注册
- 它当前处于什么注册状态
- 它引用了哪些扫描文件
- 它绑定了哪个参考基因组
- 它是否已经完成校验

因此需要引入 `candidate` 中间层。

## 8.2 推荐表结构

### 8.2.1 `dataset_registration_candidate`

建议字段：

- `id`
- `candidate_code`
- `scan_root_id`
- `dataset_type`
- `recipe_code`
- `registration_mode`
- `candidate_name`
- `version_name`
- `organism`
- `assembly`
- `reference_dataset_id`
- `reference_version_id`
- `status`
- `validation_status`
- `build_status`
- `registration_status`
- `source_kind`
- `meta_json`
- `create_user_id`
- `create_time`
- `update_time`

字段语义建议：

- `status`
  - `draft`
  - `validated`
  - `ready`
  - `building`
  - `registered`
  - `failed`
  - `ignored`
- `validation_status`
  - `pending`
  - `passed`
  - `failed`
- `build_status`
  - `not_required`
  - `pending`
  - `running`
  - `success`
  - `failed`
- `registration_status`
  - `pending`
  - `success`
  - `failed`
- `source_kind`
  - `source_candidate`
  - `prebuilt_candidate`
  - `mixed_candidate`

### 8.2.2 `dataset_registration_candidate_file`

建议字段：

- `id`
- `candidate_id`
- `staging_file_id`
- `source_role`
- `asset_type`
- `asset_file_type_code`
- `file_role`
- `is_primary`
- `is_required`
- `validation_status`
- `confidence`
- `origin_type`
- `meta_json`
- `create_time`

字段语义建议：

- `source_role`
  - `genome_fasta`
  - `gene_gff`
  - `functional_db`
  - `rawcount_matrix`
  - `normalized_matrix`
  - `variant_file`
  - `variant_index`
  - `phenotype_xlsx`
  - `phenotype_sqlite`
- `origin_type`
  - `user_supplied`
  - `system_generated`
  - `user_supplied_prebuilt`

### 8.2.3 可选扩展表：`dataset_registration_build_artifact`

如果后续要把构建链路做得更清晰，可增加：

- `id`
- `candidate_id`
- `artifact_role`
- `asset_type`
- `asset_file_type_code`
- `local_path`
- `file_format`
- `status`
- `meta_json`

这个表用于记录 recipe 过程中系统生成的文件，但第一阶段可以先不落地，先写到 candidate 的 `meta_json` 中也可。

---

## 9. source candidate 与 prebuilt candidate 识别

扫描结果不应全部进入同一类候选。

建议系统在扫描后先做一层识别：

### 9.1 `source candidate`

含义：

- 这些文件更适合作为 recipe 的输入源

典型识别对象：

- `genome.fasta`
- `gene.gff`
- `rawcount.tsv`
- `fpkm.tsv`
- `vcf`
- `vcf.gz`
- `bcf`
- `phenotype.xlsx`

### 9.2 `prebuilt candidate`

含义：

- 这些文件本身已经是平台查询或资产结构可直接消费的结果文件

典型识别对象：

- `genome.db`
- `vcf.gz.tbi`
- `vcf.gz.csi`
- 标准化 `expression.h5`
- `phenome.sqlite`

### 9.3 `mixed candidate`

含义：

- 一个候选同时含有源文件和预制结果

典型场景：

- genome 目录中同时存在：
  - `genome.fasta`
  - `gene.gff`
  - `genome.db`
  - `protein.fa`

### 9.4 识别原则

建议按以下顺序识别：

1. 文件路径模式
2. 文件后缀与压缩形式
3. 目录上下文
4. 已知命名规则
5. 简单 schema 校验

需要强调：

- 扫描阶段不读大文件内容
- 识别阶段只做轻量判断
- 真正的结构校验放在 candidate 校验或 recipe 校验阶段

---

## 10. 四类 dataset type 的 registration recipe 草案

## 10.1 genome

### 10.1.1 背景判断

genome 是最特殊的一类：

- 分析流程长
- 派生文件多
- 用户已有积累数据价值高
- 不适合只支持最小输入强制重建

因此 genome 必须支持三种模式：

- `prebuilt`
- `recipe_build`
- `hybrid`

### 10.1.2 最小源输入

- `genome.fasta`
- `gene.gff`

### 10.1.3 可识别的预制结果

- `genome.db`
- `gene annotation sqlite/db`
- `protein.fa`
- `mrna.fa`
- fasta 索引文件
- 其他系统已定义的标准派生文件

### 10.1.4 recipe 产出目标

按现有三层注册设计，最终产出应对齐：

- `reference_fasta`
- `gene_annotation`
- `functional_annotation`

并在各资产下挂接标准 `asset file type`

### 10.1.5 推荐行为

- `prebuilt`
  - 优先识别已有资产文件
  - 通过校验后直接注册
- `recipe_build`
  - 从 `genome.fasta + gene.gff` 开始全流程构建
- `hybrid`
  - 优先复用已有预制结果
  - 缺失部分再补生成

## 10.2 transcriptome

### 10.2.1 设计判断

transcriptome 不应要求用户先准备 `hdf5`。

平台应允许用户只提供一个表达矩阵主文件。

### 10.2.2 最小源输入

- `rawcount` 文件

可选：

- `fpkm/tpm` 文件
- sample metadata

### 10.2.3 可识别预制结果

- 符合平台 schema 的 `h5/hdf5`

### 10.2.4 recipe 产出目标

- 原始矩阵资产
- 查询用 `hdf5` 资产
- 基础摘要或样本元数据资产

### 10.2.5 关键约束

- transcriptome 必须可绑定参考 genome dataset/version

### 10.2.6 推荐行为

- 默认推荐：`recipe_build`
- 高级用户可走：`prebuilt`
- 缺部分派生时走：`hybrid`

## 10.3 variome

### 10.3.1 设计判断

variome 也不应要求用户先准备索引。

用户给一个变异文件即可。

### 10.3.2 最小源输入

- `vcf`
- 或 `vcf.gz`
- 或 `bcf`

### 10.3.3 可识别预制结果

- `vcf.gz + tbi`
- `vcf.gz + csi`
- `bcf + csi`

### 10.3.4 recipe 产出目标

- 标准化变异查询主资产
- 索引资产文件
- 基础摘要

### 10.3.5 关键约束

- variome 应允许绑定参考 genome dataset/version

### 10.3.6 推荐行为

- 默认推荐：`recipe_build`
- 已有索引时支持：`prebuilt`
- 缺索引时支持：`hybrid`

## 10.4 phenome

### 10.4.1 设计判断

phenome 的问题不在文件个数，而在：

- `xlsx` 模板结构必须稳定
- trait 列不固定
- 需要把宽表转换为平台可查询结构

### 10.4.2 最小源输入

- 一个符合模板的 `xls/xlsx`

### 10.4.3 可识别预制结果

- 符合系统 schema 的 `sqlite`

### 10.4.4 recipe 产出目标

- 原始表型表资产
- 派生 sqlite 查询资产
- trait/subject/observation 结构化索引
- 本次导入字段快照

### 10.4.5 动态字段设计

phenome 应采用与 germplasm 一致的思路：

1. 固定字段骨架
2. 批次字段快照
3. 行级动态字段值

### 10.4.6 推荐行为

- 默认推荐：`recipe_build`
- 已有符合 schema 的 sqlite 时支持：`prebuilt`
- 有原始 xlsx 但缺 sqlite 时可走：`hybrid`

---

## 11. candidate 校验规则

candidate 在进入正式注册前，应至少完成以下校验：

### 11.1 通用校验

- 文件路径存在
- 文件可读
- 未被 Dataset 中心正式注册重复占用
- 所属 `dataset type` 合法
- `registration_mode` 合法

### 11.2 genome 校验

- `genome.fasta` 是否存在
- `gene.gff` 是否存在
- 预制 `genome.db` 若存在，schema 是否符合要求
- 预制序列和注释文件是否命名或角色可识别

### 11.3 transcriptome 校验

- 原始表达矩阵格式是否可读
- 是否能识别 gene/sample 维度
- 预制 `hdf5` 是否符合平台 schema
- 是否已绑定参考基因组

### 11.4 variome 校验

- 主变异文件是否合法
- 若已有索引，索引是否匹配
- 若未有索引，是否允许自动补生成
- 是否已绑定参考基因组

### 11.5 phenome 校验

- `xlsx` 模板结构是否符合系统要求
- 保留字段是否齐全
- 动态列是否可提取为批次字段快照
- 若已有 sqlite，schema 是否匹配查询适配器要求

---

## 12. 与现有 Dataset 中心实例层的映射

candidate 注册成功后，统一落到：

- `dataset`
- `dataset_version`
- `dataset_asset`
- `asset_file`

### 12.1 映射原则

- `candidate.dataset_type` -> `dataset.dataset_type`
- `candidate.version_name` -> `dataset_version.version`
- `candidate_file.asset_type` -> `dataset_asset.asset_type`
- `candidate_file.asset_file_type_code` -> `asset_file.asset_file_type_code`

### 12.2 文件来源语义建议

建议在 `asset_file.meta_json` 或扩展字段中记录：

- `file_origin`
  - `user_supplied`
  - `system_generated`
  - `system_regenerated`
- `build_stage`
  - `source`
  - `derived`
  - `index`
  - `cache`
- `validation_status`
  - `pending`
  - `passed`
  - `failed`

这能帮助系统区分：

- 哪些文件是用户原始提交的
- 哪些文件是系统构建出来的

---

## 13. 重复注册与版本策略

注册时必须区分以下情况：

### 13.1 完全未注册

- 允许新建 dataset

### 13.2 已有同名 dataset，但这是新版本

- 允许注册成新 `dataset version`

### 13.3 文件完全重复

- 默认阻止重复注册
- 或提示用户：
  - 关联到已有 dataset
  - 或作为新版本处理

### 13.4 genome 特殊情况

genome 的预制数据可能包含大量已有派生文件，因此去重策略应优先看：

- 主源文件路径
- 主源文件 checksum
- 已绑定的 assembly / organism
- 已有版本名

---

## 14. 前端注册向导页面草图

## 14.1 页面组织建议

建议不要把注册向导塞进 Dataset 中心列表页本身。

更合理的是：

1. `数据扫描`
2. `注册候选`
3. `注册向导`

### 14.1.1 数据扫描页

职责：

- 管理扫描目录
- 执行扫描
- 查看扫描任务
- 查看 staging 文件

### 14.1.2 候选列表页

职责：

- 展示扫描结果经识别后的 `candidate`
- 区分：
  - `source candidate`
  - `prebuilt candidate`
  - `mixed candidate`
- 提供：
  - 校验
  - 忽略
  - 进入注册向导

### 14.1.3 注册向导页

职责：

- 选择或确认注册模式
- 查看 recipe 预期输入与产出
- 确认参考基因组
- 确认版本和资产映射
- 执行注册

## 14.2 genome 注册向导

建议 genome 向导第一页就是模式选择：

- `最小输入构建`
- `预制数据注册`
- `混合补全注册`

后续步骤建议：

1. 选择模式
2. 选择/确认输入文件
3. 查看自动识别到的资产结构
4. 查看缺失项与可补生成项
5. 确认 dataset 名称 / version
6. 注册

## 14.3 transcriptome 注册向导

步骤建议：

1. 选择 `rawcount`
2. 可选选择 `fpkm/tpm`
3. 选择参考基因组
4. 选择模式：
   - 仅源文件构建
   - 使用已有 hdf5
5. 确认资产
6. 注册

## 14.4 variome 注册向导

步骤建议：

1. 选择主变异文件
2. 自动识别索引
3. 选择参考基因组
4. 确认是否自动补索引
5. 注册

## 14.5 phenome 注册向导

步骤建议：

1. 选择 `xlsx` 或预制 `sqlite`
2. 模板校验
3. 展示固定字段与动态字段快照
4. 确认查询资产生成策略
5. 注册

---

## 15. 后端流程草图

建议后端拆成以下几个服务步骤：

### 15.1 扫描发现

- `scan_root`
- `scan_job`
- `dataset_staging_file`

### 15.2 候选生成

- 从 staging 文件生成 `candidate`
- 自动识别：
  - `dataset_type`
  - `source_kind`
  - `recipe_code`
  - `source_role`

### 15.3 校验

- candidate 级校验
- 预制文件 schema 校验
- recipe 输入校验

### 15.4 构建

- 仅对 `recipe_build` / `hybrid` 需要
- 构建索引、sqlite、hdf5、派生序列等

### 15.5 正式注册

- 写入 Dataset 中心表
- 写入 asset 和 asset file
- 建立与参考 genome 的 lineage

### 15.6 genome 三种模式的后端流程

#### 15.6.1 genome `prebuilt`

目标：

- 最大限度复用用户已有成果
- 不强制重新跑长时间构建流程

建议流程：

1. 从 candidate 中识别已有文件
   - `genome.fasta`
   - `gene.gff`
   - `genome.db`
   - `protein.fa`
   - `mrna.fa`
   - 索引文件
2. 执行预制文件校验
   - 路径存在
   - schema/格式可识别
   - 资产角色可推断
3. 生成目标资产映射
   - `reference_fasta`
   - `gene_annotation`
   - `functional_annotation`
4. 将用户文件直接登记到 `asset_file`
5. 若缺失关键但可容忍文件，只做 warning，不立即失败
6. 注册为 Dataset 中心正式版本

#### 15.6.2 genome `recipe_build`

目标：

- 用系统固定流程，从最小输入稳定构建标准 genome 数据资产

建议流程：

1. 检查最小输入是否齐全
   - `genome.fasta`
   - `gene.gff`
2. 创建构建任务
3. 按系统既有 genome 分析流程生成：
   - fasta 索引
   - gene annotation 相关派生
   - mRNA / protein sequence
   - functional annotation 查询资产
4. 将生成结果映射到标准资产结构
5. 注册到 Dataset 中心

#### 15.6.3 genome `hybrid`

目标：

- 先复用已有成果
- 对缺失部分按 recipe 自动补齐

建议流程：

1. 先按 `prebuilt` 识别已有文件
2. 计算缺失的目标资产项
3. 对缺失项触发定向构建
   - 例如补索引
   - 补派生序列
   - 补 `functional_annotation`
4. 将用户文件与系统生成文件一起登记
5. 注册为正式版本

### 15.7 transcriptome / variome / phenome 的后端模式建议

为了避免第一阶段复杂度过高，建议：

- `transcriptome`
  - 先支持 `recipe_build`
  - 第二阶段补 `prebuilt/hybrid`
- `variome`
  - 先支持 `recipe_build + hybrid`
  - `prebuilt` 也较容易支持
- `phenome`
  - 先支持 `recipe_build`
  - `prebuilt` 仅对符合 schema 的 sqlite 开放

### 15.8 candidate 生成机制建议

candidate 的产生建议支持两种方式：

1. 自动候选生成
   - 扫描完成后，按规则自动生成候选
2. 手动生成候选
   - 用户从 staging 文件中手动选择并创建候选

第一阶段可优先支持：

- genome
  - 目录级自动候选
- variome
  - 单主文件自动候选
- transcriptome
  - 手动确认式候选
- phenome
  - 单文件自动候选

---

## 16. 数据扫描与持续扫描语义

当前数据扫描已经开始具备：

- 重复扫描
- 已注册文件跳过
- 变更识别
- 缺失识别

后续持续扫描应建立在这套语义之上。

### 16.1 当前建议

数据扫描的目标不是自动把一切都变成 Dataset，而是：

- 持续发现可能的新数据输入源
- 持续发现已存在数据的变化
- 为候选生成提供来源

### 16.2 后续建议

持续扫描真正上线时，应建立：

- 调度配置
- 任务记录
- 去重
- 失败重试
- 手动重扫

但这部分属于任务管理层，不在本文详细展开。

---

## 17. 审核重点

这份设计在正式进入实现前，建议优先审核下面几个问题：

### 17.1 registration_mode 是否合理

重点判断：

- `genome` 是否必须三模式并存
- `transcriptome / variome / phenome` 是否默认 `recipe_build`
- `hybrid` 是否覆盖了现实中的主要“半成品”接入场景

### 17.2 candidate 中间层是否足够但不过度

重点判断：

- 是否需要先落 `candidate` 两张表
- 是否暂时不需要更复杂的 build artifact 表

### 17.3 genome recipe 是否符合你的既有分析流程

重点判断：

- 从 `genome.fasta + gene.gff` 出发的自动构建，是否和你已有流程一致
- 哪些产出必须作为正式资产
- 哪些产出只应作为内部派生文件

### 17.4 phenome 动态字段设计是否继续沿用 germplasm 思路

重点判断：

- 固定字段骨架是否足够
- trait 动态列是否必须按“批次字段快照”处理

### 17.5 扫描与正式注册的边界是否清晰

重点判断：

- 数据扫描是否只负责发现与变化识别
- 注册是否必须通过 candidate 和 recipe
- 是否避免让扫描页直接变成自由资产装配器

---

## 18. 分阶段实施建议

### 18.1 第一阶段

- 增加 `candidate` 中间层
- 先做 `registration_mode`
- 先做 genome / variome / phenome / transcriptome 的候选识别
- 先完成前端候选列表页

### 18.2 第二阶段

- 实现 genome 三种模式注册向导
- 实现 variome 与 transcriptome 基础向导
- 实现 phenome 模板校验向导

### 18.3 第三阶段

- 把 recipe 构建任务正式接入任务管理层
- 让持续扫描与候选生成自动打通
- 增加跨版本去重与版本建议

---

## 19. 最终结论

下一阶段的正确主线不是：

- “继续扫描更多文件”

而是：

- “把扫描发现的文件，稳定转化为可注册的候选”
- “按 `dataset type` 的固定 recipe 和注册模式，进入 Dataset 中心”

一句话收束：

数据扫描负责发现文件，
candidate 负责组织注册意图，
registration mode 决定走预制、构建还是混合补全，
registration recipe 决定不同组学数据怎样变成正式的 Dataset 资产。

其中：

- genome 必须支持 `prebuilt / recipe_build / hybrid`
- transcriptome / variome / phenome 默认推荐 `recipe_build`
- 但也允许受控的 `prebuilt`
- phenome 与 germplasm 继续采用“固定骨架 + 批次字段快照 + 动态值”模式

这套设计既能接住你已有积累的数据，也能支持后续新数据标准化接入。
