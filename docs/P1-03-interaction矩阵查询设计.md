# P1-03 Interaction 矩阵查询设计

本文档用于承接 Dataset 平台当前主线中的 `P1-03 interaction`，目标是把现有 `BEDPE region_contacts` 最小实现继续推进到 `cool/mcool` 真正矩阵查询。

它不是重新讨论“是否要做 interaction”，而是把下一阶段如何做收敛成可以直接实现的设计。

> 实施进展（2026-04-01）：
> 当前仓库已经完成本文档定义的最小闭环：后端 `interaction` adapter 已支持 `cool/mcool` 的 `matrix_meta / matrix_slice / resolutions_list`，ingest 已支持校验与分辨率探测，portal 已补矩阵查询表单与结构化结果展示。本文档后续主要用于承接更强聚合、版本对比和 admin 体验增强。

---

## 1. 当前问题

当前 interaction 主线已经完成的部分是：

- `dataset_type = interaction`
- adapter 已接入 `interaction`
- `bedpe / bedpe.gz / pairs / pairs.gz` 已支持 `region_contacts`
- ingest 已支持基础校验和 `tabix` 建索引
- portal 已有 interaction smart query 骨架

但真正缺的核心能力仍然是：

- `cool / mcool` 的矩阵切片查询
- 矩阵查询结果的结构化返回
- 版本级 capability 正确暴露 `matrix_slice`
- portal/admin 对矩阵结果的稳定展示

当前 portal 端其实已经预留了 `matrix_slice` 的交互骨架，但后端 interaction adapter 还没有对应实现，这会导致前端设计已经向前走、后端能力还停留在 BEDPE 文本记录层。

---

## 2. 设计目标

这一阶段只做最小可用但真实的 `cool/mcool` 查询闭环，不追求一开始就覆盖所有 Hi-C 分析场景。

本阶段目标：

1. 能对 `cool` 文件执行单分辨率矩阵切片查询
2. 能对 `mcool` 文件按分辨率选择具体矩阵并切片
3. 能返回 portal/admin 可直接消费的结构化矩阵结果
4. 不破坏现有 `BEDPE region_contacts` 主线
5. 继续沿用 `asset-first + version-aware + public query` 现有架构

本阶段暂不做：

- balance/normalization 策略的复杂组合
- 跨版本矩阵 compare
- 热图渲染层的大幅增强
- 复杂聚合统计和 TAD/loop 高阶分析

---

## 3. 文件与资产语义

### 3.1 Dataset / Asset 层

`interaction` 仍作为 dataset 类型。

建议 `asset_type` 继续使用：

- `interaction_matrix`

`file_format` 应扩展为：

- `cool`
- `mcool`
- 保留现有：
  - `bedpe`
  - `bedpe.gz`
  - `pairs`
  - `pairs.gz`

### 3.2 query_engine

建议 interaction adapter 内继续统一使用：

- `query_engine = interaction`

而不要把 `cool` 和 `bedpe` 再拆成两个 adapter。原因是：

- 它们属于同一业务域
- 能力差异主要体现在 `file_format`
- 前端仍然把它们视为 interaction 数据

---

## 4. 查询能力模型

### 4.1 capability 暴露

interaction adapter 的 `describe()` 应按文件格式返回不同操作集：

- `bedpe / bedpe.gz / pairs / pairs.gz`
  - `region_contacts`
- `cool`
  - `matrix_slice`
  - `matrix_meta`
- `mcool`
  - `matrix_slice`
  - `matrix_meta`
  - `resolutions_list`

### 4.2 operation 定义

#### `matrix_meta`

用于返回矩阵文件的基础信息。

返回内容至少包括：

- `source`
- `format`
- `bin_size`
- `chroms`
- `shape`
- `available_resolutions`（仅 `mcool`）
- `balanced_supported`

#### `resolutions_list`

只对 `mcool` 开放。

返回内容：

- `resolutions`
- `default_resolution`

#### `matrix_slice`

这是本阶段核心操作。

请求参数建议：

- `chrom`
- `start`
- `end`
- `target_chrom`
- `target_start`
- `target_end`
- `resolution`
- `balanced`
- `limit_bins`

说明：

- 当未指定 `target_*` 时，默认取同一区间自交矩阵
- `cool` 可忽略 `resolution`
- `mcool` 必须允许显式指定 `resolution`
- `balanced` 默认 `false`

---

## 5. 响应结构

### 5.1 `matrix_slice` 响应

建议统一返回：

```json
{
  "adapter": "interaction",
  "operation": "matrix_slice",
  "dataset_id": 123,
  "data": {
    "source": "cool",
    "format": "mcool",
    "resolution": 10000,
    "region": "chr1:1-1000000",
    "target_region": "chr1:1-1000000",
    "bin_size": 10000,
    "x_labels": ["chr1:1-10000", "..."],
    "y_labels": ["chr1:1-10000", "..."],
    "matrix": [[0, 12, 5], [12, 0, 8], [5, 8, 0]],
    "shape": [3, 3],
    "balanced": false
  }
}
```

设计原则：

- 保持和 expression 的 `matrix_slice` 足够接近
- 但 interaction 仍需要额外暴露：
  - `region`
  - `target_region`
  - `resolution`
  - `bin_size`

这样 portal 端已经存在的矩阵表格 UI 可以最小复用。

---

## 6. 后端实现建议

### 6.1 adapter 扩展

当前文件：

- `backend/api-server/apps/datasets/adapters/interaction.py`

建议扩展为：

1. 保留现有 `_query_region_contacts()`
2. 新增 `_query_matrix_meta()`
3. 新增 `_query_matrix_slice()`
4. 在 `describe()` 里按 `file_format` 动态返回 capability
5. 在 `execute()` 里分发：
   - `region_contacts`
   - `matrix_meta`
   - `resolutions_list`
   - `matrix_slice`

### 6.2 依赖选择

实现 `cool/mcool` 查询时，优先建议：

- 首选 Python 库方式读取
- 尽量不要再引入新的 shell 级外部二进制作为主依赖

原因：

- 现有 interaction `BEDPE` 已依赖 `tabix`
- `cool/mcool` 如果继续依赖额外 CLI，会让部署链更脆弱
- Python 侧读取更容易和 adapter 架构融合

### 6.3 ingest / validate

当前 `datasets/services.py` 里 interaction validate/index 仍偏向文本文件。

下一步应补：

- `cool` 文件合法性校验
- `mcool` 文件合法性校验
- `mcool` 可用分辨率探测
- 将上述信息写入 `validation_summary` 或 `meta_json`

本阶段可以不做“二次建索引”，因为 `cool/mcool` 本身已经是适合查询的数据格式。

---

## 7. 前端收口建议

### 7.1 portal

当前 portal 已有 `matrix_slice` UI 骨架，因此主要是把后端真正接上。

需要收口的点：

- 当 adapter = `interaction` 且 capability 包含 `matrix_slice` 时，展示矩阵查询模式
- 如果是 `mcool`，展示 resolution 选择
- 在结果区复用现有 matrix table 视图
- 在结果头信息展示：
  - region
  - target_region
  - resolution
  - bin_size

### 7.2 admin 版本工作台

建议与 portal 保持同一套 operation 语义：

- `matrix_meta`
- `matrix_slice`

后台的价值不在更炫的展示，而在：

- 验证某个版本下某个 asset 是否真的可查
- 明确 matrix file 的 resolution / bin size / shape

---

## 8. 回归测试建议

本阶段至少补四类回归：

### 8.1 adapter 级

- `cool` 的 `matrix_meta`
- `cool` 的 `matrix_slice`
- `mcool` 的 `resolutions_list`
- `mcool` 指定 `resolution` 的 `matrix_slice`

### 8.2 dataset service 级

- `asset-first` 下从 `query_entry_asset -> asset_file.primary` 正确解析 `cool/mcool`
- `public query` 与 `version query` 都能工作

### 8.3 portal 级

- interaction smart query 在 `matrix_slice` 模式下能提交
- `mcool` resolution 切换后请求参数正确

### 8.4 权限边界

- private 版本后台可查
- unreleased 版本 public query 拒绝
- released 非默认版本可按 public version 显式查询

---

## 9. 完成标准

满足以下条件时，可认为 `P1-03` 从“最小实现”进入“稳定主线”：

1. `interaction` adapter 支持真实 `cool/mcool` 查询
2. capability 能正确区分 `BEDPE` 和 `cool/mcool`
3. portal 可查看矩阵切片结果
4. admin 工作台可做版本级矩阵验证
5. 已补自动化回归

一旦这一步完成，Dataset 平台在核心组学类型上的主线就只剩结果增强，而不再存在明显的“核心类型能力断层”。
