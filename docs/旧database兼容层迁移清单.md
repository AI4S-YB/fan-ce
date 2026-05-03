# 旧 `database` 兼容层迁移清单

本文档用于记录当前代码库中仍直接依赖旧 `/database`、`/database-file` 体系的前后端入口，避免后续在没有迁移计划的情况下继续把新功能接入旧域。

目标不是立即删除旧能力，而是先把边界说清楚：

- 旧 `apps/databases/*` 当前视为兼容层
- 新增 dataset 生命周期、asset、asset_file、lineage、公开查询能力应进入 `apps/datasets/*`
- 旧页面在迁移前可以继续运行，但原则上不再扩展新业务语义

---

## 1. 后端兼容入口

当前仍挂载的旧后端路由：

- `/database/*`
- `/database/action/*`
- `/database/meta/*`
- `/database-file/*`

代码位置：

- [apps/routers.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/routers.py)
- [apps/databases/routers.py](/Users/kentnf/projects/fan-ce/backend/api-server/apps/databases/routers.py)

当前状态：

- 已保留路由挂载，保证旧前端页面与历史功能不被打断
- 已在 `datasets` 域内部新增 `legacy_bridge.py`，把 dataset 主线对旧表的兼容访问收口到内部桥接层
- `datasets/services.py` 已不再直接 import `apps.databases.crud`

---

## 2. 后台前端仍直接依赖旧 API 的页面

### 2.1 旧管理页

这些页面本身就是旧 `database` 域管理入口，短期内建议冻结为兼容态：

- `frontend/admin-web/apps/web-antd/src/views/apps/database/**`
- `frontend/admin-web/apps/web-antd/src/views/apps/database-files/**`
- `frontend/admin-web/apps/web-antd/src/views/apps/databaseWithMetadata/**`

对应 API 模块：

- [databases.ts](/Users/kentnf/projects/fan-ce/frontend/admin-web/apps/web-antd/src/api/apps/databases.ts)
- [database-files.ts](/Users/kentnf/projects/fan-ce/frontend/admin-web/apps/web-antd/src/api/apps/database-files.ts)

### 2.2 仍把旧 `/database/options` 当作数据选择器的数据页

这些页面未必是“管理页”，但还在直接消费旧 database 选项：

- `views/apps/genome/data.ts`
- `views/apps/rnaseq/data.ts`
- `views/apps/variant/data.ts`
- `views/apps/phenotype/data.ts`
- `views/apps/datashow/sequence/data.ts`
- `views/apps/germplasm/data.ts`
- `views/apps/grn/data.ts`
- `views/dashboard/workspace/index.vue`
- `views/apps/database/dataInfo/**`

这类页面的共同特点：

- 主要依赖 `getDatabaseOptionsApi(...)`
- 多数仍以旧 `database_id` + `file_path` 驱动查询或展示
- 还没有切换到 `dataset/version/asset` 语义

---

## 3. 建议的迁移分组

### A 组：先冻结，不新增功能

对象：

- 旧 `database` 管理页
- 旧 `database-file` 管理页

策略：

- 保持可用
- 只修 bug，不继续叠加 dataset 新语义
- 文档中明确标记为兼容入口
- 已在旧 `database` 首页、旧 `database-file` 首页、旧 `database` 详情页加入兼容提示条，并提供跳转到 `/apps/dataset` 的入口

### B 组：先替换“选项来源”，再替换业务语义

对象：

- `genome / rnaseq / variant / phenotype / germplasm / grn / datashow/sequence`

策略：

- 第一步先把下拉选项从 `/database/options` 切到 `/admin/dataset/options` 或专门的 dataset 选项适配接口
- 第二步再把页面内部的 `database_id / file_path` 语义替换为 `dataset_id / version_id / asset`

### C 组：最后处理聚合页和统计页

对象：

- dashboard workspace
- system/project 中 database 关联视图

策略：

- 等 A/B 组稳定后再决定是继续兼容旧聚合口径，还是改成 dataset 口径

---

## 4. 下一步建议

建议按以下 checkpoint 推进：

1. 保持旧 `database` 路由继续挂载，但明确视为兼容层
2. 新功能禁止继续接入 `apps/databases/*`
3. 选一类“只依赖 options 的页面”做最小迁移样板
4. 验证 `dataset options -> 页面查询` 的替换路径可行后，再逐页迁移

当前最适合作为样板的页面类型：

- 只需要数据下拉选择，不涉及复杂旧管理动作的页面
- 例如 `variant`、`rnaseq`、`phenotype` 这类以选择文件后执行查询为主的页面

---

## 5. 当前迁移进度

已完成的 B 组样板：

- `views/apps/variant/*`
  - 已从旧 `/database/options` 切到 `/admin/dataset/options`
  - 当前仍把解析后的 `file_path` 传给既有 omics 查询接口，业务语义暂未整体切到 `dataset/version/asset`
- `views/apps/rnaseq/*`
  - 已从旧 `/database/options` 切到 `/admin/dataset/options`
  - 已把选中项对应的 `file_path` 显式写入表单状态，避免继续依赖旧下拉返回对象中的隐式 `option.file_path`
- `views/apps/genome/*`
  - 已从旧 `/database/options` 切到 `/admin/dataset/options`
  - 已把基因组页的查询、跳转、基因集弹窗统一改成读取显式保存的 `database_file_path`
- `views/apps/datashow/sequence/*`
  - 已从旧 `/database/options` 切到 `/admin/dataset/options`
  - 已统一从显式保存的 `database_file_path` 生成 `genome_path`，不再依赖旧选择器对象结构
- `views/system/project/data.ts`
  - 已从旧 `/database/options` 切到 `/admin/dataset/options`
  - 当前仍只把数据项作为项目筛选/选择器使用，尚未把项目与 `dataset/version/asset` 的关系建模继续下钻

相关后端兼容收敛：

- `dataset options` 现在会返回当前版本解析后的 `file_path / file_format`
- 当旧 `dataset_version.file_path` 与新 `asset_file.primary` 不一致时，后端已固定优先返回 asset-first 解析结果
- 这意味着 B 组页面即使仍暂时把 `file_path` 传给旧查询接口，也会尽量读到当前 query entry asset 对应的主文件，而不是陈旧版本路径

下一批建议优先级：

- `views/apps/phenotype/*`
  - 先确认旧 `type: '8'` 与新 `dataset_type` 的映射是否已经存在；当前更像落在 `generic` 或待补专属类型，暂不建议直接硬迁
- `views/apps/germplasm/*`
  - 先确认旧 `type: '7'` 与新 `dataset_type` 的映射策略，再决定是否进入 B 组迁移
- `views/apps/grn/*`
  - 先确认旧 `type: '9'` 与新 `dataset_type` 的映射策略，再决定是否进入 B 组迁移
