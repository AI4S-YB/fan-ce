# 全站多语言 (i18n) 支持设计

> **目标:** 在现有 vue-i18n 基础设施上，启用语言切换器，为全站约 1100+ 处硬编码中文创建 locale key 并替换为 $t() 调用，支持 zh-CN / en-US 即时切换。

**架构:** 项目已有完整的 i18n 框架（`@vben/locales` + `vue-i18n`，`LanguageToggle` widget），本次不引入新依赖，只做三件事——打开开关、补 locale 文件、逐页替换硬编码文本。

**技术栈:** vue-i18n (Composition API mode), `@vben/locales`, ant-design-vue ConfigProvider

---

## 设计概览

### 1. 启用语言切换器

`LanguageToggle` 组件已存在并在 header 中集成完毕（index 80，位于 theme-toggle 和 fullscreen 之间），由 `preferences.widget.languageToggle` 控制显隐。

**改动:** `packages/@core/preferences/src/config.ts` 中将 `widget.languageToggle` 默认值从 `false` 改为 `true`。

切换时自动调用 `loadLocaleMessages(lang)` 加载语言包、更新 `antdLocale`、写入 localStorage，全站即时生效。

### 2. Locale 文件组织

新增/扩展以下 namespace（位于 `apps/web-antd/src/locales/langs/zh-CN/` 和 `en-US/`）：

| 文件 | Namespace | 覆盖页面 |
|------|-----------|---------|
| `workspace.json` | `workspace` | dashboard/workspace（工作台对话） |
| `platform.json` | `platform` | platform/setting, setup-taxonomy, api, news |
| `dataset.json` | `dataset` | dataset list/detail/query, dataset-staging, dataset-registry, dataset-candidate |
| `germplasm.json` | `germplasm` | 种质资源管理 |
| `breeding.json` | `breeding` | 育种项目管理 |
| `grn.json` | `grn` | 基因调控网络 |
| `geneset.json` | `geneset` | 基因集 |
| `phenome.json` | `phenome` | 表型组查询 |
| `system.json` | `system` | user/role/team/menu/project/permission/dict/profile |
| `agent.json` | `agent` | agent/chat（智能助手对话） |
| `component.json` | `component`（扩展） | GraphModal, KnowledgeGraph, AiChat, Upload, Form, DataTable 等 |
| `page.json` | `page`（扩展） | 路由 meta title、面包屑、page-level titles |

每个文件独立 namespace，key 使用嵌套对象分组（如 `workspace.chat.placeholder`），参数化用 `{name}` 占位符。

### 3. 代码模式

#### 模式 A — Vue 模板

```html
<span>{{ $t('workspace.greeting.morning', { name: userStore.userInfo?.realName }) }}</span>
```

#### 模式 B — Vue script（computed / message）

```typescript
import { $t } from '@vben/locales';

const desc = computed(() => $t('workspace.currentTeam', { name: teamName }));
message.success($t('platform.saved'));
```

#### 模式 C — data.ts 列定义 / 表单 schema

```typescript
import { $t } from '@vben/locales';

export const columns = [
  { title: $t('system.user.username'), dataIndex: 'username' },
];
```

`$t` 返回的是响应式值，语言切换后自动更新。现有 `adapter/vxe-table.ts` 已验证此模式可行。

#### 模式 D — 枚举/选项映射

```typescript
export const statusMap = {
  active: $t('common.enabled'),
  disabled: $t('common.disabled'),
};
```

#### 模式 E — 路由 meta titles

```typescript
// 改动前
meta: { title: '平台管理' }
// 改动后
meta: { title: 'page.platform' }
```

路由 title 在 `bootstrap.ts` 中已通过 `$t(routeTitle)` 调用，只需替换为 key。

### 4. 不做的事

- Dashboard analytics 页面中的 mock/toy 数据（使用量、访问来源等）保留中文原样，不纳入 i18n
- Demo 页面保留中文，不纳入
- `components/data-table/example/` 示例文件不纳入
- 控制台日志、代码注释保留中文

---

## 实施顺序

按页面可见度从高到低分 Tier：

**Tier 1（最高可见，最先做）：**
- 启用 LanguageToggle
- workspace.json + workspace/index.vue（工作台）
- page.json 扩展 + 全部路由文件
- component.json 扩展 + 全部公共组件

**Tier 2：**
- platform.json + platform/* 全部页面
- system.json + system/* 全部 data.ts + 页面

**Tier 3：**
- dataset.json + dataset/* 全部页面

**Tier 4：**
- germplasm.json + germplasm/*
- breeding.json + breeding/*
- grn.json + grn/*
- geneset.json + geneset/*
- phenome.json + phenome/*
- agent.json + agent/*

**Tier 5：**
- 布局文件（basic.vue, project.vue）
- 剩余零散页面
