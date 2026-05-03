# 种质资源 Phase 1 实施草案

## 1. 目标

本草案承接 [种质资源导入与浏览设计草案](/Users/kentnf/projects/fan-ce/docs/种质资源导入与浏览设计草案.md)，把第一阶段压成可实施范围：

- PostgreSQL 表结构草案
- 后端接口草案
- 前端页面与交互草案

本阶段只做：

- `rose_germplasm_v1` 模板
- taxonomy 锚点选择
- 上传前校验
- 导入落库
- 物种过滤 + 关键词搜索
- 详情页来源信息补齐

本阶段不做：

- 完整 NCBI taxonomy 全量同步
- 多模板 profile 管理后台
- breeding 项目内直接建材料
- 复杂谱系分析

---

## 2. 命名与落位建议

当前 breeding 域表采用 `brd_*` 前缀，且种质资源未来会直接为 `brd_material` 提供来源池，因此第一阶段建议统一落在 breeding 域内，便于后续关联。

推荐表命名：

- `brd_taxonomy_cache`
- `brd_germplasm_import_batch`
- `brd_germplasm`
- `brd_germplasm_lineage`

说明：

- 这样命名和现有 [models.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/breeding/models.py) 风格一致
- 后续若 taxonomy 要抽为平台级通用表，再独立迁移也不难

---

## 3. 数据库表草案

## 3.1 `brd_taxonomy_cache`

用途：

- 缓存 taxonomy 选择结果
- 为种质导入提供稳定锚点
- 给前端物种过滤提供本地数据源

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `tax_id` | bigint PK | NCBI taxonomy id |
| `scientific_name` | varchar(256) | 学名 |
| `common_name` | varchar(256) | 常用名 |
| `rank` | varchar(64) | species / genus 等 |
| `parent_tax_id` | bigint null | 父 tax id |
| `lineage` | text | 原始 lineage 字符串 |
| `lineage_names_json` | text | lineage 名称数组快照 |
| `source` | varchar(32) | `local_seed` / `ncbi_sync` / `manual` |
| `is_active` | integer | 1/0 |
| `last_sync_time` | datetime | 最近同步时间 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

建议索引：

- `pk(tax_id)`
- `idx scientific_name`
- `idx common_name`
- `idx rank`

---

## 3.2 `brd_germplasm_import_batch`

用途：

- 记录一次导入任务
- 保存校验报告
- 支持前端导入记录页

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | bigint PK | 主键 |
| `batch_code` | varchar(64) unique | 批次号 |
| `template_profile` | varchar(64) | 如 `rose_germplasm_v1` |
| `taxonomy_tax_id` | bigint FK | 绑定物种 |
| `taxonomy_name_snapshot` | varchar(256) | 导入时学名快照 |
| `source_filename` | varchar(512) | 上传文件名 |
| `source_file_path` | text | 服务器保存路径 |
| `status` | varchar(32) | `validated` / `imported` / `failed` |
| `total_rows` | integer | 总行数 |
| `valid_rows` | integer | 可导入行数 |
| `error_rows` | integer | 错误行数 |
| `warning_rows` | integer | 警告行数 |
| `validation_report_json` | text | 完整校验报告 |
| `created_by` | bigint null | 操作人 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

建议索引：

- `uk batch_code`
- `idx taxonomy_tax_id, created_at`
- `idx status, created_at`

---

## 3.3 `brd_germplasm`

用途：

- 存种质主数据
- 作为种质列表和详情页主表

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | bigint PK | 主键 |
| `batch_id` | bigint FK | 来源导入批次 |
| `taxonomy_tax_id` | bigint FK | 所属物种 |
| `accession_id` | varchar(128) | 种质编号 |
| `display_name` | varchar(256) | 列表主显示名，月季场景取 `chinese_name` |
| `scientific_name_snapshot` | varchar(256) | 学名快照 |
| `common_name_snapshot` | varchar(256) | 常用名快照 |
| `english_name` | varchar(256) null | 英文名 |
| `father_accession` | varchar(128) null | 父本 accession |
| `mother_accession` | varchar(128) null | 母本 accession |
| `father_name_snapshot` | varchar(256) null | 父本名称快照 |
| `mother_name_snapshot` | varchar(256) null | 母本名称快照 |
| `source_row_no` | integer | Excel 行号 |
| `status` | varchar(32) | `active` / `disabled` |
| `attributes_json` | text | 扩展属性，如育种历史、花朵性状等 |
| `search_text` | text | 预拼接检索字段 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

唯一约束建议：

- `unique (taxonomy_tax_id, accession_id)`

建议索引：

- `idx taxonomy_tax_id, display_name`
- `idx taxonomy_tax_id, accession_id`
- `idx batch_id`
- `idx father_accession`
- `idx mother_accession`

说明：

- 月季模板里的 `育种历史 / 花朵性状 / 植株特征 / 用途` 先存 `attributes_json`
- `search_text` 第一阶段可以简单拼接：
  - accession
  - 中文名
  - 英文名
  - 父母本编号
  - 关键属性文本

---

## 3.4 `brd_germplasm_lineage`

用途：

- 把谱系关系从主表字段中拆出来
- 便于图谱和关系查询

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | bigint PK | 主键 |
| `taxonomy_tax_id` | bigint FK | 所属物种 |
| `child_accession` | varchar(128) | 子代 accession |
| `parent_accession` | varchar(128) | 亲本 accession |
| `parent_role` | varchar(16) | `father` / `mother` |
| `batch_id` | bigint FK | 来源批次 |
| `source_row_no` | integer | 来源 Excel 行号 |
| `created_at` | datetime | 创建时间 |

唯一约束建议：

- `unique (taxonomy_tax_id, child_accession, parent_accession, parent_role)`

建议索引：

- `idx taxonomy_tax_id, child_accession`
- `idx taxonomy_tax_id, parent_accession`

---

## 3.5 与现有 `brd_material` 的关系

第一阶段不改 `brd_material` 主结构，只做逻辑约束收紧：

- `brd_material.germplasm_accession` 应优先引用 `brd_germplasm.accession_id`
- 如果项目物种已知，应与 `brd_germplasm.taxonomy_tax_id` 保持一致

后续阶段可以再补正式 FK 或逻辑关联表。

---

## 4. 导入校验接口草案

## 4.1 `POST /breeding/germplasm/import/validate`

用途：

- 上传文件
- 选择模板
- 选择 taxonomy
- 返回校验结果
- 不正式写入主表

请求：

```json
{
  "template_profile": "rose_germplasm_v1",
  "taxonomy_tax_id": 74636,
  "upload_token": "temp-file-token"
}
```

返回重点：

```json
{
  "summary": {
    "passed": false,
    "template_profile": "rose_germplasm_v1",
    "total_rows": 120,
    "valid_rows": 113,
    "error_rows": 5,
    "warning_rows": 2
  },
  "errors": [
    {
      "row_no": 18,
      "column_name": "ID",
      "error_code": "duplicate_accession",
      "message": "accession 已重复"
    }
  ],
  "warnings": [],
  "preview_rows": []
}
```

---

## 4.2 `POST /breeding/germplasm/import/commit`

用途：

- 对通过校验的临时导入结果正式落库

请求：

```json
{
  "validation_token": "validated-import-token"
}
```

返回重点：

```json
{
  "batch_id": 12,
  "batch_code": "GIP-20260405-001",
  "imported_count": 113
}
```

导入动作包括：

1. 写 `brd_germplasm_import_batch`
2. 批量写 `brd_germplasm`
3. 衍生写 `brd_germplasm_lineage`
4. 生成或刷新图谱缓存

---

## 4.3 `POST /breeding/germplasm/import/batches`

用途：

- 导入记录列表

查询参数：

- `taxonomy_tax_id`
- `status`
- `page`
- `size`

---

## 4.4 `POST /breeding/germplasm/import/batch-info`

用途：

- 查看单批次详情和校验报告

返回重点：

- 批次信息
- 物种信息
- 原始文件信息
- 校验报告
- 导入结果统计

---

## 5. 浏览接口草案

## 5.1 `POST /breeding/germplasm/list`

替代当前“必须传 `file_path`”的模式。

查询参数建议：

- `taxonomy_tax_id` 必填或在前端默认选中一个
- `keyword`
- `batch_id`
- `status`
- `page`
- `size`

查询逻辑：

1. 先按 `taxonomy_tax_id` 过滤
2. 再按 `keyword` 搜索 `search_text`
3. 补充 breeding 引用摘要

返回字段建议：

- `accession_id`
- `display_name`
- `scientific_name_snapshot`
- `english_name`
- `father_accession`
- `mother_accession`
- `taxonomy_tax_id`
- `batch_code`
- `breeding_summary`

---

## 5.2 `POST /breeding/germplasm/info`

用途：

- 种质详情页主接口

查询参数：

- `taxonomy_tax_id`

返回结构建议：

- `basic_info`
- `taxonomy`
- `attributes`
- `lineage_summary`
- `breeding_usage`
- `audit_info`

---

## 5.3 `POST /breeding/germplasm/relationship`

用途：

- 返回父母本和邻近谱系节点

第一阶段不做复杂层级展开，只做：

- 父本
- 母本
- 直接子代
- 邻近边

---

## 5.4 `POST /breeding/germplasm/taxonomy/options`

用途：

- 给前端物种下拉使用

返回结构：

- `tax_id`
- `scientific_name`
- `common_name`
- `rank`
- `germplasm_count`

这样前端列表页能显示：

- 月季 Rosa chinensis-like 之类的学名
- 对应已有多少条种质

---

## 5.5 `POST /breeding/germplasm/taxonomy/search`

用途：

- 导入页中搜索 taxonomy 锚点

第一阶段建议：

- 先查本地缓存表
- 没命中时可返回“未收录，请后台同步或补录”

不要在页面搜索时直接打远端 NCBI。

---

## 6. 前端页面草案

## 6.1 页面一：种质列表

路径建议：

- `/germplasm/list`
  - 前端页面路径保留不变，后端数据源改为 `/breeding/germplasm/list`

页面结构：

### 顶部筛选条

- `物种`
  - 必选
  - 支持搜索
  - 放在第一个控件
- `关键词`
  - 次级过滤
  - placeholder:
    - `搜索 accession、中文名、英文名、亲本编号`
- `导入批次`
  - 可选
- `状态`
  - 可选

### 操作区

- `导入种质资源`
- `查看导入记录`
- `导出当前筛选`
- `查看图谱`

### 列表字段

- `种质编号`
- `显示名称`
- `英文名`
- `父本`
- `母本`
- `物种`
- `来源批次`
- `breeding 引用`
- `更新时间`
- `操作`

### 行操作

- `详情`
- `谱系`
- `图谱定位`

交互规则：

- 首次进入页面时，如果只有一个物种，自动选中
- 如果有多个物种，先要求选择物种再加载列表
- 关键词只在选中的物种范围内搜索

---

## 6.2 页面二：导入种质资源

路径建议：

- `/germplasm/import`

推荐使用四步向导：

### Step 1 基础配置

- 选择模板
  - 第一阶段仅 `rose_germplasm_v1`
- 搜索并选择 taxonomy
- 显示 taxonomy 卡片：
  - scientific name
  - common name
  - rank
  - lineage

### Step 2 上传文件

- 上传 `xls/xlsx`
- 显示文件名、大小
- 支持重新上传

### Step 3 校验预览

- 汇总卡片：
  - 总行数
  - 可导入
  - 错误
  - 警告
- 错误表
- 警告表
- 前 20 行预览

### Step 4 导入确认

- 显示导入摘要
- 点击确认后正式导入
- 成功后跳转到：
- `/germplasm/list?taxonomy_tax_id=...&batch_id=...`
  - 页面跳转参数保留，实际列表接口走 `/breeding/germplasm/list`

---

## 6.3 页面三：导入记录

路径建议：

- `/germplasm/import-batches`

列表字段：

- `批次号`
- `模板`
- `物种`
- `文件名`
- `总行数`
- `成功数`
- `错误数`
- `导入时间`
- `状态`
- `操作`

操作：

- `查看报告`
- `查看该批次记录`

---

## 6.4 页面四：种质详情

现有详情页可以保留路径：

- `/germplasm/info`

但页面内容建议改成四块：

### 基本信息

- accession
- 显示名称
- 学名
- taxonomy
- 英文名

### 谱系关系

- 父本
- 母本
- 邻居数量
- 简单关系图

### breeding 引用

- 哪些项目用了它
- 哪些 material 引用了它

### 来源审计

- 导入批次
- 原始文件名
- 原始行号
- 校验警告

---

## 7. 后端实现顺序建议

不要一口气把所有页面都改完，建议按下面顺序推进：

### Step 1

- 建表：
  - `brd_taxonomy_cache`
  - `brd_germplasm_import_batch`
  - `brd_germplasm`
  - `brd_germplasm_lineage`

### Step 2

- 做 `rose_germplasm_v1` 校验器
- 支持：
  - 必填列校验
  - 重复 accession 校验
  - 父母本基本关系校验

### Step 3

- 做导入接口：
  - `validate`
  - `commit`

### Step 4

- 把现有列表页切到 PostgreSQL 主表
- 实现：
  - 物种过滤
  - 关键词查询

### Step 5

- 详情页切到主表 + 谱系表
- 保留 breeding 引用摘要

### Step 6

- 图谱页从 PG 衍生数据，不再依赖固定文件路径

---

## 8. 当前代码改造边界

现有代码里需要逐步替换的点：

- breeding 主接口见 [core.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/breeding/api/core.py)
  - 现阶段围绕 `file_path` 和 `graph.pkl`
- [api.ts](/Users/kentnf/projects/fan-ce/frontend/admin-web/apps/web-antd/src/views/apps/germplasm/api.ts)
  - 现阶段默认绑定固定月季文件
- [index.vue](/Users/kentnf/projects/fan-ce/frontend/admin-web/apps/web-antd/src/views/apps/germplasm/index.vue)
  - 现阶段是图谱浏览优先，不是导入与列表优先

第一阶段建议：

- 不直接删除旧图谱能力
- 先把数据源从文件路径切到 PostgreSQL
- 图谱作为列表页上的一个衍生视图保留

---

## 9. 最终建议

下一步最合适的不是继续讨论概念，而是直接开始 Phase 1 的第一刀：

1. 先把 PostgreSQL 四张表建出来
2. 再做 `rose_germplasm_v1` 校验器
3. 然后把种质列表页从固定文件模式切到 PG 模式

一句话收束：

种质资源下一阶段要先从“文件浏览模块”变成“可导入、可校验、可筛选的主数据模块”，图谱能力放在这个主线之后。
