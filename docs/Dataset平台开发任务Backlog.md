# Dataset 平台开发任务 Backlog

本文档在以下设计文档基础上整理为可执行开发队列：

- `docs/组学Dataset平台后端正式设计文档.md`
- `docs/dataset平台checkpoint实施方案.md`
- `docs/本地开发启动说明.md`
- `docs/旧database兼容层迁移清单.md`

目标不是再次讨论方向，而是把“下一步做什么”整理成可以连续推进的 backlog。

---

## 当前状态（2026-03-24）

- `P0-01`：已基本完成
  - `dataset_version.release_state`
  - `dataset_registry.default_public_version_id`
  - `is_default_public`
  - 已作为当前主判断语义使用
- `P0-02`：已完成
  - `release / withdraw / set-default-public` 已落地
  - `public dataset / public version / public capabilities` 已补基础回归测试
  - “默认公开版本执行 `withdraw` 后直接无公开版本” 已收口到实现，并补回归测试
- `P0-03`：已完成
  - service 查询能力与版本 payload 已切到 asset-first
  - adapter 已支持从 `query_entry_asset` 解析主文件
  - 对分目录存放的索引文件补了 sidecar link 兼容
  - 已继续收紧 `version.file_path` 在 query path 中的直接 fallback
  - 已修复 legacy bootstrap 不再用旧 `version.file_path` 覆盖已有 `asset_file.primary`
  - `version payload / public version payload / version list` 现在稳定优先暴露 query entry asset 的主文件路径
  - `dataset options` 已返回当前版本解析后的 `file_format`
  - adapter 基类已明确 `dataset.file` 仅为 legacy fallback
  - 已补“显式置空 `version.file_path` 时仍从 `asset_file` 解析主文件”的自动化回归
  - 已补“`version.file_path` 为旧值但 asset 主文件已迁移”时仍稳定走 asset-first 的自动化回归
  - 已补 `sequence / variant / expression` 在 `version.file_path = null` 条件下的 asset-first 查询回归
  - 已补类型专项回归：`annotation / signal / interaction` 在 `asset-first` 下的 capabilities 与 query execute 均可工作
  - 后端 `dataset/version/public version query capabilities & execute` 已支持显式传入 `asset_code`
  - admin 版本工作台已补按 `asset_code` 下钻：可围绕指定资产加载能力、执行查询，并同步聚焦资产/文件视图
  - 已补 `annotation / signal / interaction` 在“多资产 + 指定 asset_code”下的专项回归
  - 该阶段剩余扩展已转入各类型 `P1` 项，不再阻塞 `asset-first` 主线收口
- `P0-04`：已基本完成
  - 版本工作台已支持 `release / withdraw / set-default-public`
  - dataset 列表中的旧 `publish / unpublish` 主入口已移除
  - 版本工作台已补当前版本、默认公开版本、已发布版本、选中版本的语义摘要
  - 版本详情已补“公开访问效果 / 建议下一步”提示
  - Dataset 中心已补资产/文件可视化收口：可直接区分 `query entry asset`、主文件、索引文件、索引目标、格式与查询引擎
  - 版本工作台已补最小版本对比与发布动作时间线
  - 版本工作台已补最小结构化版本 diff：可对比发布状态、查询入口、资产数量与资产差异
  - 版本工作台已补文件级 diff，并支持“只看变化项 / 聚焦查询入口 / 聚焦主文件”的筛选视图
  - 版本工作台已补时间线摘要卡，可快速判断最近发布、最近设为默认公开、发布/撤回计数与当前公开状态
  - 剩余工作主要是更复杂类型下的对比摘要收敛
- `P1-01`：已进入最小实现
  - 后端已新增 `annotation` adapter
  - 已支持 sqlite 注释库 `table_stats / gene_lookup / region_features`
  - 已支持 GFF/GTF 路径的 `gene_lookup / region_features`
  - ingest 已支持 annotation 基础校验与索引
  - portal 已补 annotation smart query 表单
  - 已提供 `demo_annotation` provisioning
  - 已提供 `demo_annotation_gff` provisioning
  - admin 版本工作台已补版本级查询测试器，可直接加载 capabilities 并执行查询
  - admin 版本工作台已补 annotation 结构化结果展示：`table_stats / gene_lookup / region_features`
  - 已补 GTF 专项回归：私有/公开查询闭环、多资产 `asset_code` 切换、transcript id 解析
  - 已补 annotation ingest 自动化回归：`gtf` 校验、`bgzip/tabix` 建索引、sqlite ready 分支
  - 剩余工作仍包括：更多类型主线扩展、结果体验继续细化
- `P1-04`：已进入最小实现
  - public API 已新增公开版本列表与按版本 detail/capabilities/query
  - portal 已支持在 released versions 间切换
  - 默认仍落在 `default_public_version`
  - portal 已补公开资产视图收口：可区分 `query entry`、公开版本状态、主文件与索引文件关系
  - portal 已补公开版本状态摘要：可直接查看默认公开命中语义、release state、入口资产与查询引擎就绪情况
  - 已补后端自动化回归：默认公开版本命中、released 非默认版本按 version 显式访问、unreleased 版本公开访问拒绝
  - public version list 已支持过滤：`keyword / is_default_public / is_current / release_state`
  - portal 已补公开版本筛选条与过滤后计数
- `P1-02`：已进入最小实现
  - 后端已新增 `signal` adapter
  - 已支持 `bed / bed.gz` 信号轨道的 `region_features`
  - ingest 已支持 signal 基础校验与 tabix 建索引
  - portal 已补 signal smart query 表单
  - 已提供 `demo_signal` provisioning
  - 已支持 BigWig `region_signal / describe_signal`
  - 已补 BigWig 私有/公开查询与多资产 `asset_code` 切换回归
  - portal 已补 BigWig 区域信号结果与头信息展示
  - 剩余工作仍包括：结果聚合继续增强
- `P1-03`：已进入最小实现
  - 后端已新增 `interaction` adapter
  - 已支持 `bedpe / bedpe.gz` 互作文件的 `region_contacts`
  - ingest 已支持 interaction 基础校验与 tabix 建索引
  - portal 已补 interaction smart query 表单
  - 已提供 `demo_interaction` provisioning
  - 已支持 `cool / mcool` 的 `matrix_meta / matrix_slice / resolutions_list`
  - ingest 已支持 `cool / mcool` 合法性校验、分辨率探测与 ready 直通
  - portal 已补 interaction matrix 查询表单与结构化矩阵结果展示
  - 已补 interaction matrix 专项回归：私有/公开查询闭环、`asset_code` 切换、ingest 校验
  - 剩余工作仍包括：更强的结果聚合、版本对比增强、admin 侧矩阵体验继续细化
- `P2-01`：已进入最小实现
  - 保留原同步 `validate / index / pipeline` 接口
  - 已新增异步 ingest task 提交、详情查询、失败重试
  - `dataset_workflow_task` 已开始承载运行态明细
  - admin-web dataset 页面已切到“提交任务”模式，并支持失败任务重试
  - 已完成烟雾验证：成功任务、失败任务、失败后重试
- `P2-02`：已进入第一阶段实现
  - 后端已补 dataset 级行权限守卫
  - version / asset / asset_file / lineage / ingest task 已继承 dataset 权限边界
  - 当前一期规则为：超级管理员可全量访问；普通后台用户按 dataset owner、team、project 归属获得访问权
  - admin-web `Dataset 中心` 已开始区分“数据不存在/加载失败”和“数据权限拒绝”两类状态
  - admin-web `Dataset 中心` 的主要写操作已补显式 403 提示，不再仅弹后端原始错误
  - registry 管理区已收口为“仅超级管理员可见、仅超级管理员可维护”
  - 公开 API 仍仅按 released/default-public 语义开放，不走后台私有鉴权
  - 已补跨团队/跨项目拒绝访问回归
  - 已补 registry 管理权限回归：非超管不可维护 `dataset kind / asset type`
  - 已补组合边界回归：多 team / 多 project 访问、`project_id` 过滤与行权限叠加、ingest task retry 的 dataset/global 边界
  - 剩余工作仍包括：asset 级覆盖权限是否启用、其它页面入口是否需要沿用同样的权限拒绝 UX
- `P2` 其它项：未开始主线实现
  - 公开前台暂不展示 lineage
  - “撤回后直接无公开版本” 的小调整已记录，后续可继续收口产品语义
- `P2-03`：已进入第一阶段收口
  - 已新增 `backend/api-server/apps/datasets/legacy_bridge.py`
  - `datasets/services.py` 已不再直接 import 旧 `apps.databases.crud`
  - `datasets` 主线对旧 `database/file/meta/project_link` 的兼容访问已统一走 bridge
  - `datasets/crud.py` 中未使用的 `legacy_database_db` 已移除
  - 已新增 `docs/旧database兼容层迁移清单.md`，列出旧 `/database` 前后端依赖面与建议迁移分组
  - 后台前端 B 组样板页已完成 `variant`、`rnaseq`、`genome`、`datashow/sequence` 四页的 options 源切换，均改为读取 `dataset options`
  - `system/project` 页面已完成 options 源切换，项目筛选中的“数据”下拉已改为读取 `dataset options`
  - 工作台中的“数据管理”项目入口与快捷入口已切到 `/apps/dataset`，不再跳旧 `/database/list`
  - 已补静态边界测试，锁定 dashboard 入口不得回退到旧 `database/list`
  - 已为旧 `database` 首页、旧 `database-file` 首页、旧 `database` 详情页增加兼容提示条，并提供跳转到 Dataset 中心的入口
  - 剩余工作仍包括：继续减少其它旧页面/旧接口对 `apps/databases/*` 的直接耦合，并评估哪些旧接口可冻结为兼容态

---

## 1. 使用方式

建议按以下节奏使用本清单：

1. 先完成 `P0`
2. `P0` 收口后进入 `P1`
3. `P2` 作为平台化收敛
4. `P3` 作为体验增强

每个任务包含：

- `任务编号`
- `优先级`
- `任务目标`
- `当前差距`
- `影响范围`
- `风险等级`
- `完成标准`
- `验收用例`

---

## 2. P0 核心主线

### P0-01 统一版本状态模型

- 优先级：最高
- 任务目标：把版本状态正式收敛为稳定的三轴语义，避免继续混用旧的 `lifecycle/public/current` 兼容逻辑
- 当前差距：
  - 代码中已部分引入 `release_state`
  - 但还没有把设计中的状态语义完全统一
  - `dataset` 和 `dataset_version` 仍存在旧语义残留
- 影响范围：
  - `backend/api-server/apps/datasets/models.py`
  - `backend/api-server/apps/datasets/services.py`
  - `backend/api-server/apps/datasets/schemas.py`
  - `backend/api-server/apps/datasets/api/version.py`
- 风险等级：中
- 完成标准：
  - 版本状态能够稳定表达“工作流状态、可见范围、发布状态”
  - 新逻辑优先读正式状态字段
  - 旧兼容字段不再作为核心判断依据
- 验收用例：
  - 创建新版本后默认处于草稿工作流状态
  - `ready` 版本可以执行 `release`
  - 已 `released` 版本可以设置为 `default public`
  - 非默认公开版本不会被 public API 默认读取

### P0-02 收口版本发布规则

- 优先级：最高
- 任务目标：彻底统一 `release / withdraw / set-default-public` 语义
- 当前差距：
  - 新接口已存在
  - 旧 `publish / unpublish` 仍在承担主要表达
  - `withdraw` 逻辑当前仍会自动补位其它 released 版本
- 影响范围：
  - `backend/api-server/apps/datasets/services.py`
  - `backend/api-server/apps/datasets/api/version.py`
  - `frontend/admin-web/apps/web-antd/src/api/apps/dataset.ts`
- 风险等级：中
- 完成标准：
  - `release` 只负责把版本变成 released
  - `set-default-public` 只负责切换默认公开版本
  - `withdraw` 默认公开版本后，系统直接进入“无公开版本”
  - dataset 级 `publish / unpublish` 只保留兼容包装
- 验收用例：
  - dataset 有两个 released 版本，切换默认公开版本时旧版本不自动撤回
  - 默认公开版本执行 `withdraw` 后，`public/dataset/info` 返回不可访问
  - 非默认公开版本执行 `withdraw` 不影响当前默认公开版本

### P0-03 清理查询层对 `dataset_version.file_path` 的残留依赖

- 优先级：最高
- 任务目标：让查询正式以 `asset + asset_file` 为主，而不是继续回退到单文件模型
- 当前状态：
  - 主链路已能从 asset 查询
  - `version payload / query capabilities / public query` 已继续收紧为优先从 asset 解析主文件
  - `dataset_version.file_path` 仍保留，但主要用于迁移期自动补出 `dataset_asset / asset_file`
  - adapter 基类已将 `dataset.file` 标记为 legacy fallback
- 剩余差距：
  - 个别老数据修复脚本仍可继续补齐
- 影响范围：
  - `backend/api-server/apps/datasets/services.py`
  - `backend/api-server/apps/datasets/adapters/base.py`
  - `backend/api-server/apps/datasets/adapters/sequence.py`
  - `backend/api-server/apps/datasets/adapters/variant.py`
  - `backend/api-server/apps/datasets/adapters/expression.py`
- 风险等级：中
- 当前完成情况：
  - adapter 查询、索引、能力探测优先从 query entry asset 取主文件：已基本完成
  - index 文件从 `asset_file` 解析：已完成
  - `dataset_version.file_path` 仅作为迁移兼容信息：已进入收尾
  - `version.file_path = null` 时，query capabilities 仍可从 `query_entry_asset -> asset_file` 返回主文件：已补回归
  - 已修复迁移期 bootstrap 覆盖问题：已有 `asset_file.primary` 时，不再被旧 `dataset_version.file_path` 反向覆盖
  - `get_dataset_version / list_dataset_versions / public version payload` 已补 asset-first 回归
  - `sequence / variant / expression` 三类主线查询已补 asset-first execute 回归
- 验收用例：
  - 删除 `dataset_version.file_path` 的情况下，`sequence / variant / expression` 查询仍可工作
  - query capabilities 返回的主入口文件来自 query entry asset
  - pipeline 更新后不会把 asset 级路径覆盖回旧字段

### P0-04 后台前端版本工作台切换到新语义

- 优先级：高
- 任务目标：让后台使用者看到的是 `release / withdraw / set-default-public`，不是旧 `publish / unpublish`
- 当前状态：
  - 页面操作已切到 `release / withdraw / set-default-public`
  - 版本列表已显示 `is_current / release_state / is_default_public`
  - 版本详情已能区分当前版本、默认公开版本、已发布版本
  - 已补充顶部摘要区和选中版本的语义说明
- 剩余差距：
  - 还没有版本间 diff / compare 视图
  - 对“当前版本不等于默认公开版本”的历史变化还没有单独时间线
- 影响范围：
  - `frontend/admin-web/apps/web-antd/src/api/apps/dataset.ts`
  - `frontend/admin-web/apps/web-antd/src/views/apps/dataset/index.vue`
- 风险等级：低
- 当前完成情况：
  - 版本列表显示 `is_current / release_state / is_default_public`：已完成
  - 操作按钮变为新语义：已完成
  - 版本详情能区分当前版本、默认公开版本、已发布版本：已完成
- 验收用例：
  - 页面可直接执行 release：已实现
  - 页面可直接执行 withdraw：已实现
  - 页面可直接执行 set default public：已实现
  - 页面状态展示与接口返回一致：已验证

---

## 3. P1 核心业务扩展

### P1-01 落地 annotation 数据类型主线

- 优先级：高
- 任务目标：支持基因注释、功能注释的资产建模、索引、查询与发布闭环
- 当前差距：
  - 设计已明确
  - annotation 最小主线已落地
  - GFF/GTF 查询闭环已补齐到回归层
  - 但更深结果体验与后续类型扩展仍待增强
- 影响范围：
  - `backend/api-server/apps/datasets/adapters/`
  - `backend/api-server/apps/datasets/services.py`
  - admin-web dataset 页面
  - portal-web 查询页面
- 风险等级：中
- 完成标准：
  - 至少支持 `gene_annotation`
  - 至少支持一类注释查询能力
  - 能完成上传、校验、索引、发布、公开查询
  - 后台版本工作台可直接进行 annotation 版本查询调试
- 当前完成情况：
  - sqlite / GFF / GTF 注释查询已可走同一 dataset/version/public 主链路
  - 后台版本工作台已支持 annotation 结构化结果查看与复制
  - 已补 GTF `gene_lookup / region_features` 与多资产 `asset_code` 切换回归
  - 已补 annotation ingest 自动化回归，锁定 `validate/index` 关键分支
- 验收用例：
  - 注释类 dataset 能创建 asset 和 file
  - 后台能查看 annotation capabilities
  - 后台能对指定版本执行 annotation 查询
  - 前台能执行一个 annotation 查询
  - GFF/GTF 注释文件经过 pipeline 后可压缩、建 tabix 索引并公开查询

### P1-02 落地 signal 数据类型主线

- 优先级：高
- 任务目标：支持 BED/BigWig 等区域或信号轨道数据
- 当前差距：
  - BED 主线已落地
  - BigWig 查询能力已进入主线
  - 后续主要是更复杂的信号聚合与展示增强
- 影响范围：
  - datasets adapters
  - datasets services
  - admin-web
  - portal-web
- 风险等级：中
- 完成标准：
  - 支持 signal asset 类型
  - 支持至少一个区域查询或信号切片操作
  - portal 可直接执行 signal smart query
- 当前完成情况：
  - BED `region_features` 与 BigWig `region_signal / describe_signal` 已可走 dataset/version/public 主链路
  - portal 已支持 BigWig 区域查询参数输入、分箱结果展示、头信息展示
  - 已补 BigWig 多资产 `asset_code` 切换回归
- 验收用例：
  - BigWig 或 BED demo 数据能被注册并发布
  - 前台可查询指定区间

### P1-03 落地 interaction 数据类型主线

- 优先级：中高
- 任务目标：支持互作类数据的资产建模与最小查询闭环
- 当前差距：
  - BEDPE 主线已落地
  - `cool/mcool` 查询能力仍未进入主线
- 影响范围：
  - datasets adapters
  - datasets services
  - admin-web
  - portal-web
- 风险等级：中高
- 完成标准：
  - 至少支持一个 interaction 资产类型
  - 至少支持一个 interaction demo dataset
  - portal 可直接执行 interaction smart query
- 验收用例：
  - interaction 数据可被导入、发布、查询

### P1-04 公开接口补版本感知能力

- 优先级：高
- 任务目标：让 public API 不只返回默认公开版本，还能表达公开版本集合
- 当前差距：
  - 最小 released versions 访问模型已落地
  - portal 的版本筛选主线已补齐
  - 后续若继续增强，主要是展示层体验，不再阻塞版本感知主线
- 影响范围：
  - `backend/api-server/apps/datasets/api/public.py`
  - `backend/api-server/apps/datasets/services.py`
  - `frontend/portal-web/src/App.vue`
- 风险等级：中
- 完成标准：
  - 提供公开版本列表接口
  - 提供指定 version 的 detail/capabilities/query 能力
  - portal 可切换查看版本
  - 默认仍进入 `default public version`
- 当前完成情况：
  - public version list 已支持 `keyword / is_default_public / is_current / release_state` 过滤
  - portal 已支持公开版本筛选与过滤后计数展示
  - 默认公开版本与非默认 released 版本的切换访问均已有后端回归
- 验收用例：
  - 某 dataset 有两个 released 版本时可列出版本
  - 默认进入 default public version
  - 指定公开版本仍可查询

---

## 4. P2 平台化收敛

### P2-01 标准 ingest 工作流任务化

- 优先级：中
- 任务目标：把当前同步式流程升级为更正式的平台任务流
- 当前状态：
  - 已保留同步接口，兼容现有脚本和调用方
  - 已新增异步接口：
    - `POST /api/v1/admin/dataset/ingest/task/submit`
    - `POST /api/v1/admin/dataset/ingest/task/info`
    - `POST /api/v1/admin/dataset/ingest/task/retry`
  - `dataset_workflow_task.detail` 已承载 request/result/error/attempt/retry_of_task_id
  - admin-web 已支持任务提交、状态展示、失败重试
- 剩余差距：
  - 仍是单进程内后台执行，尚未引入独立 worker/队列
  - 还没有“中断 / 取消 / 恢复到指定 step”能力
  - 还没有任务清理策略与更细粒度的步骤级可视化
- 影响范围：
  - `dataset_workflow_task`
  - `backend/api-server/apps/datasets/services.py`
  - admin-web dataset 页面
- 风险等级：中
- 当前完成情况：
  - 长任务可追踪：已完成
  - 失败任务可重跑：已完成
  - 任务详情可回看：已完成
- 验收用例：
  - 模拟一个失败 ingest 任务：已验证
  - 页面能看到失败状态：已实现
  - 可再次触发重跑：已验证

### P2-02 权限模型细化

- 优先级：中
- 任务目标：明确 dataset、version、asset 三层权限边界
- 当前状态：
  - dataset 级行权限已落到 `datasets service`
  - version / asset / asset_file / lineage / ingest task 已按 dataset 归属继承读写权限
  - 当前一期仍不启用 asset 级独立覆盖权限
  - 已新增后端自动化回归 `tests/test_dataset_permissions.py`
  - 已补 owner / team / project 授权与跨团队 / 跨项目拒绝访问场景
  - `dataset kind / asset type` 注册表已补“仅平台管理员”限制，前后端均已收口
- 当前差距：
  - 前端仅在 `Dataset 中心` 开始承接“有菜单权限但无数据权限”的错误态，其它页面仍未统一
  - asset 级覆盖权限仍停留在设计预留
  - 多团队多项目叠加授权、管理员覆盖等组合回归还需要继续补
- 影响范围：
  - datasets API
  - 权限依赖与校验
  - 设计文档
- 风险等级：中
- 完成标准：
  - 定义 dataset 主权限：已进入最小实现
  - 定义 version 是否可覆盖：当前结论为 version 不单独覆盖，沿用 dataset 权限
  - 明确 asset 级权限是否进入一期实现：当前结论为不进入一期强制实现，仅保留扩展位
- 验收用例：
  - 私有 dataset 不可被 public API 查询
  - 已发布版本可被 public API 查询
  - 非授权用户不可修改私有 dataset
  - 非授权用户不可读取私有 dataset/version/asset/file/lineage
  - 已有自动化覆盖 owner / team / project / version / asset / file / lineage / task 访问边界

### P2-03 收缩旧 `apps/databases` 兼容层

- 优先级：中
- 任务目标：逐步减少新功能对旧 database 域的依赖
- 当前差距：
  - 目前是双域共存
  - 仍有兼容读取和老模型反向影响
  - `datasets` 域虽然仍依赖旧表作为事实源之一，但主服务层已开始通过内部 bridge 间接访问，而不是直接耦合旧 CRUD
- 影响范围：
  - `backend/api-server/apps/databases/*`
  - `backend/api-server/apps/datasets/*`
  - admin-web 历史页面入口
- 风险等级：中高
- 完成标准：
  - 新功能只进 `datasets` 域
  - `datasets/services.py` 不再直接依赖旧 `apps.databases.crud`：已完成
  - `databases` 域仅保留兼容能力
- 当前完成情况：
  - 后端 bridge 收口：已完成第一阶段
  - 前端 B 组最小迁移样板：`variant`、`rnaseq`、`genome`、`datashow/sequence` 已完成
  - `rnaseq` 页面已显式保存 `database_file_path`，不再依赖旧选择器对象隐式结构
  - `genome` 页面已显式保存 `database_file_path`，并同步修正详情跳转与基因集弹窗的文件路径来源
  - `datashow/sequence` 页面已显式保存 `database_file_path`，并统一用其生成 `genome_path`
  - 已补静态兼容边界回归：已迁移样板页不得重新 import `getDatabaseOptionsApi`
- 验收用例：
  - 新增功能不再需要改动 `apps/databases`
  - dataset 主线可以独立维护

---

## 5. P3 前端与体验增强

### P3-01 后台前端补版本状态展示

- 优先级：中低
- 任务目标：让版本工作台更直观
- 当前差距：
  - 版本列表已可用
  - 但对状态理解成本仍高
- 影响范围：
  - admin-web dataset 页面
- 风险等级：低
- 完成标准：
  - 版本状态标签清晰
  - 发布记录可读性提升
- 验收用例：
  - 非研发用户能看懂当前版本、已发布版本、默认公开版本

### P3-02 公开前台扩展 smart query 表单

- 优先级：中低
- 任务目标：为 annotation、signal、interaction 增加结构化查询表单
- 当前差距：
  - 当前 smart query 主要覆盖 sequence/variant/expression
- 影响范围：
  - `frontend/portal-web/src/App.vue`
  - `frontend/portal-web/src/style.css`
- 风险等级：低
- 完成标准：
  - 新增数据类型不必退回 JSON 模式
- 验收用例：
  - annotation、signal 至少各有一个 smart query 表单

### P3-03 公开前台版本浏览

- 优先级：中低
- 任务目标：支持公开版本列表、版本说明、默认公开标识
- 当前差距：
  - 当前主要展示单版本
- 影响范围：
  - public API
  - portal-web
- 风险等级：低
- 完成标准：
  - portal 能查看公开版本列表
- 验收用例：
  - dataset 有多个 released versions 时，用户可切换查看

### P3-04 公开 lineage 展示

- 优先级：最低
- 任务目标：后续开放 lineage 展示能力
- 当前差距：
  - 当前明确不展示
- 影响范围：
  - public API
  - portal-web
  - 权限与暴露边界
- 风险等级：中
- 完成标准：
  - 暂不纳入当前阶段
- 验收用例：
  - 暂不编排

---

## 6. 推荐实施顺序

建议按以下顺序连续推进：

1. `P0-01` 统一版本状态模型
2. `P0-02` 收口版本发布规则
3. `P0-03` 清理查询层旧路径依赖
4. `P0-04` 后台前端切换新语义
5. `P1-01` annotation
6. `P1-02` signal
7. `P1-03` interaction
8. `P1-04` public 版本感知
9. `P2-01` ingest 任务化
10. `P2-02` 权限细化
11. `P2-03` 收缩旧兼容层
12. `P3-*` 体验增强

---

## 7. 当前建议的直接下一步

如果继续按 backlog 开工，建议直接进入：

### 下一步 A

- 任务：`P0-02` 收口版本发布规则
- 原因：范围小、影响核心、能快速把发布语义彻底稳定
- 具体先做：
  - 默认公开版本 `withdraw` 后直接无公开版本
  - dataset 级 `publish/unpublish` 仅保留兼容包装
  - 补对应接口验证

### 下一步 B

- 任务：`P0-04` 后台前端切换新语义
- 原因：后端语义一旦稳定，前端应立即同步，否则使用者会继续按旧模型操作
