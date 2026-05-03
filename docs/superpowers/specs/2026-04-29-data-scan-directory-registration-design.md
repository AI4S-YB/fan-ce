# 数据扫描目录浏览与批量注册设计

> 替换当前"当前暂存区"扁平文件列表为目录树浏览 + 多选批量注册模式。

**目标：** 让用户以服务器目录结构浏览扫描发现的文件，按文件夹自然分组，多选后批量注册为 Dataset。

**架构：** 页面拆为"扫描配置区"+"目录浏览区"。目录浏览复用并扩展 `browse_scan_root_path` API，注册走现有的 `candidate → register_candidate` 管线，补上校验步骤。

**设计文档关联：** 本文档是 `docs/数据扫描到Dataset中心注册设计草案.md` 的 UI/交互层实施方案，接受其 `scan_root → staging_file → candidate → dataset` 的总体架构。

---

## 1. 页面重组

### 1.1 拆分逻辑

| 区域 | 职责 | 变化 |
|------|------|------|
| 扫描配置区 | 扫描目录 CRUD、触发扫描、查看 job 记录 | 基本不动 |
| 目录浏览区 | 按目录树浏览文件、多选、批量注册 | **替代原"当前暂存区"扁平表格** |

### 1.2 目录浏览 — 顶层视图

```
┌──────────────────────────────────────────────────┐
│ 目录浏览                           [刷新] [上传]  │
├──────────────────────────────────────────────────┤
│ 📂 /data/genomes/                      ← 面包屑   │
│                                                  │
│ ┌──────────────────────────────────────────────┐ │
│ │ ☐ 📁 rice_genome_v3/      6 files  2025-03   │ │
│ │ ☐ 📁 wheat_cs/            4 files  2025-01   │ │
│ │ ☐ 📁 maize_b73/           5 files  2024-11   │ │
│ │ ☐ 📄 orphan_genome.fasta  2.3 GB   2025-04   │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ [打开选中目录]  [注册选中内容 →]                   │
└──────────────────────────────────────────────────┘
```

面包屑基于 scan root 路径显示。根目录下的散落文件不隐藏，作为 orphan file 列出。

### 1.3 目录浏览 — 文件视图（进入目录后）

```
┌──────────────────────────────────────────────────┐
│ 📂 /data/genomes/rice_genome_v3/                 │
│                                                  │
│ ┌──────────────────────────────────────────────┐ │
│ │ ☑ genome.fasta     2.3 GB  fasta  [可注册]   │ │
│ │ ☑ gene.gff          48 MB  gff    [可注册]   │ │
│ │ ☑ genome.db        1.8 GB  sqlite [已识别:预建]│ │
│ │ ☐ protein.fa        12 MB  fasta  [可注册]   │ │
│ │ ☐ mrna.fa           15 MB  fasta  [可注册]   │ │
│ │ ☐ notes/readme.md    2 KB  md     [忽略]     │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ 已选 3 个文件  推测类型: genome  [注册为 Dataset →]│
└──────────────────────────────────────────────────┘
```

底部 bar 实时响应选中变化，显示推断结果。

---

## 2. 选中 → 推断 → 确认流程

### 2.1 推断规则

**dataset_type：** 选中文件的 `file_format` 按 `FILE_FORMAT_TO_DATASET_TYPE` 多数投票决定。票数持平或无明确多数时 fallback 为 `generic`。用户可在确认对话框中修改。

**source_kind：** 沿用设计文档 9.1-9.3 逻辑（已在 `_infer_candidate_source_kind` 中实现）：
- 全是源文件 (fasta/gff/vcf/xlsx/csv/tsv) → `source_candidate`
- 含有预制结果 (db/sqlite/h5/hdf5/tbi) → 混入 prebuilt/mixed

**registration_mode 推荐：**

| source_kind | 推荐 mode |
|---|---|
| source_candidate | recipe_build |
| prebuilt_candidate | prebuilt |
| mixed_candidate | hybrid |

**candidate_name：** 同一目录的选中文件 → 取目录名；跨目录选中 → 取第一个文件名，用户可改。

### 2.2 确认对话框

点击底部 bar 的"注册 →"，弹出确认对话框（不跳页面）：

```
┌─ 注册确认 ──────────────────────────────────────┐
│                                                  │
│ Candidate 名称: [rice_genome_v3         ]        │
│ 数据类型:       [genome ▼]                       │
│ 注册模式:       (●) prebuilt  预建文件直接纳管    │
│                 ( ) hybrid    补齐缺失后纳管      │
│                 ( ) recipe_build  从源文件构建    │
│                                                  │
│ 目标版本:       [v1                 ] 可选        │
│ 物种:           [Oryza sativa       ] 可选        │
│ 组装:           [IRGSP-1.0          ] 可选        │
│                                                  │
│ 文件清单:                                        │
│   ✓ genome.fasta  →  reference_fasta (主文件)    │
│   ✓ gene.gff      →  gene_annotation             │
│   ✓ genome.db     →  functional_annotation       │
│                                                  │
│                              [取消]  [确认注册]    │
└──────────────────────────────────────────────────┘
```

关键交互原则：
- 推断结果自动填入，用户可改，不强制填写所有字段
- 模式选择为 radio，带简短说明
- 文件角色映射自动推断（基于 file_format 和 dataset_type），用户可查看但第一阶段不改
- "确认注册"调用 `register_candidate`，走完整管线

---

## 3. 注册执行流程

### 3.1 三种模式行为

**prebuilt（预建文件纳管）：**

```
选中文件 → 校验 → 直接映射 asset/asset_file → Dataset 中心
           ├─ 文件可读性
           ├─ 格式与声明一致
           └─ sqlite/h5 schema 检查（可做则做）
耗时：秒级
```

**recipe_build（从源文件构建）：**

```
选中文件 → 校验 → 创建构建任务 → 等待完成 → Dataset 中心
           │      ├─ genome: fasta索引 + gff解析 + 派生序列
           │      ├─ phenome: xlsx → sqlite
           │      └─ variome: vcf → 索引生成
           └─ 最小输入是否齐全
耗时：分钟级（异步）
```

**hybrid（混合补全）：**

```
选中文件 → 识别已有 → 计算缺失项 → 补构建 → 合并 → Dataset 中心
                      └─ 例如：有 fasta+gff 缺 genome.db → 只构建 genome.db
```

### 3.2 candidate 状态机

```
draft → validated → ready → building → registered
  │        │          │         │           │
  └────────┴──────────┴─────────┴── failed ←┘
```

- prebuilt：draft → validated → ready → registered（无 building）
- recipe_build / hybrid：多一个 building 阶段，build_status 跟踪

### 3.3 第一阶段范围

- 完成 prebuilt 模式的完整通路（校验 + 映射 + 注册）
- recipe_build 和 hybrid 的构建调度后续实现
- 注册成功后的反馈：底部 bar/通知显示 "已创建 candidate，状态：registered"

---

## 4. 后端 API 调整

### 4.1 `browse_scan_root_path` — 补充文件返回

现有实现只返回目录。增加 `files` 字段：

```json
{
  "browse_root": "/data/genomes/",
  "current_path": "/data/genomes/rice_genome_v3/",
  "parent_path": "/data/genomes/",
  "entries": [
    { "name": "notes/", "path": "...", "is_dir": true, "modified_time": 1728000000 }
  ],
  "files": [
    { "name": "genome.fasta", "path": "...", "size": 2460000000, "format": "fasta", "modified_time": 1728000000 },
    { "name": "gene.gff", "path": "...", "size": 50331648, "format": "gff", "modified_time": 1728000000 },
    { "name": "genome.db", "path": "...", "size": 1932735283, "format": "sqlite", "modified_time": 1728000000 }
  ]
}
```

`files` 过滤掉隐藏文件和系统文件（`.DS_Store`, `Thumbs.db`）。与 `entries` 共享权限检查逻辑。

### 4.2 `list_staging_files` — 目录视图模式

新增参数 `view_mode`：
- `flat`（默认）：保持现有行为
- `directory`：按 scan_root 子目录聚合

```json
{
  "directories": [
    { "path": "/data/genomes/rice_genome_v3/", "name": "rice_genome_v3", "file_count": 5, "dataset_type_hint": "genome" }
  ],
  "orphan_files": [
    { "id": 42, "file_name": "orphan_genome.fasta", "local_path": "/data/genomes/orphan_genome.fasta", ... }
  ]
}
```

`orphan_files` 存放不在任何 scan root 子目录下的散落文件（直接位于 scan root 根目录的文件）。

### 4.3 `register_candidate` — 补校验步骤

在现有映射逻辑之前插入 `validate_candidate()`：

```
register_candidate():
  1. validate_candidate()    ← 新增
     ├─ 文件路径存在
     ├─ 文件可读
     ├─ 未被其他 Dataset 注册占用
     ├─ file_format 与 candidate 声明一致
     └─ 预制文件 schema 检查（sqlite/h5，尽力而为）
  2. 现有映射逻辑（_ensure_candidate_asset 等）
  3. 写入 Dataset 中心表
```

校验失败返回明确错误列表，前端在注册对话框中展示。

---

## 5. 不与设计文档冲突的简化

- candidate 中间层表结构沿用现有 `dataset_registration_candidate` 和 `dataset_registration_candidate_file`
- `source_kind` / `registration_mode` 推断逻辑延续 `_infer_candidate_source_kind`
- 注册向导第二阶段再做独立页面，第一阶段通过对话框完成
- 构建调度 (recipe_build/hybrid) 第二阶段补

---

## 6. 前端组件拆分

| 组件 | 职责 |
|------|------|
| `ScanConfigPanel` | 扫描目录管理（现有逻辑提取） |
| `DirectoryBrowser` | 目录树导航 + 文件列表 + 多选 |
| `RegisterConfirmModal` | 注册确认对话框（推断 + 用户确认） |
| `StagingPage` | 组装上述组件，管理选中状态和底部 bar |

`DirectoryBrowser` 内部状态：
- `currentPath`：当前浏览路径
- `selectedFilePaths`：选中的文件路径集合
- `browseStack`：面包屑导航栈

---

## 7. 与当前实现的差异对照

| 当前 | 改为 |
|------|------|
| 扁平表格列出所有 staging file | 目录树浏览，按文件夹分组 |
| 每行一个"注册"按钮 | 多选后底部 bar 批量操作 |
| 注册直接走 `register_dataset_from_staging` | 走 candidate 管线：选中 → 推断 → 确认 → `register_candidate` |
| "生成注册候选"单独按钮并跳页 | 融入注册确认对话框，不跳页 |
| staging file 的状态列展示 stage_status | 保留，但移动到目录视图下的文件列表中 |
| candidate 列表独立页面 | 保留独立页面作为补充入口，目录浏览为主入口 |
