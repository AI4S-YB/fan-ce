# Workspace 对话工作台重构设计

> **目标:** 将当前基于纯 div + ref 数组的简陋对话区，重构为 Session 管理 + Markdown 渲染 + BubbleList 组件的完整对话工作台，为后续 R/Python 代码执行分析预留扩展点。

**架构:** 复用 agent/chat 的 `useMarkdownRender`（markdown-it + highlight.js）和 ant-design-x-vue BubbleList。新建轻量 `useWorkspaceStore` Pinia store 做前端持久化 Session 管理。不复用 agent-chat store 的全部复杂性（多阶段工作流、中断处理）。

**技术栈:** Vue 3 Composition API, Pinia + localStorage, ant-design-x-vue BubbleList, markdown-it + highlight.js (github theme), vue-i18n

---

## 1. 架构总览

```
index.vue                        ← 布局壳（WorkbenchHeader + 左sidebar + 右ChatPanel）
├── WorkbenchHeader              ← 保留不变
├── SessionSidebar.vue           ← 新建
│   ├── 新建 / 切换 / 重命名 / 删除 Session
│   └── 按 updatedAt 倒序
└── ChatPanel.vue                ← 新建（从 index.vue 迁移 + 增强）
    ├── BubbleList (ant-design-x-vue)
    ├── Input.TextArea + 发送/停止按钮
    └── 操作按钮行（平台设置、清空对话）
```

**依赖图：**

```
ChatPanel.vue ──→ useWorkspaceStore ──→ localStorage (pinia plugin)
     │
     └──→ useMarkdownRender ──→ markdown-it + highlight.js (已存在，不改)
```

---

## 2. Store 设计 (`useWorkspaceStore`)

### 数据模型

```typescript
interface WorkspaceMessage {
  id: string
  role: 'user' | 'assistant'
  type: 'text' | 'tool_call' | 'tool_result' | 'code_result'  // code_result 未来用
  content: string
  timestamp: number
}

interface WorkspaceMessageGroup {
  id: string
  messages: WorkspaceMessage[]
  startTime: number
  isComplete: boolean
}

interface WorkspaceSession {
  id: string
  title: string           // 首条消息截断前30字，或 "新对话"
  messageGroups: WorkspaceMessageGroup[]
  createdAt: number
  updatedAt: number
}

interface WorkspaceChatState {
  sessions: WorkspaceSession[]
  currentSessionId: string | null
  streaming: boolean
}
```

### Getters

- `currentSession` — 从 sessions 中匹配 currentSessionId
- `sortedSessions` — 按 updatedAt 倒序

### Actions

| Action | 行为 |
|--------|------|
| `createSession()` | 空 session，currentSessionId 切到它 |
| `ensureSession()` | 当前无 session 时自动创建（发送消息时调用） |
| `switchSession(id)` | 切换 currentSessionId |
| `renameSession(id, title)` | 更新 title |
| `deleteSession(id)` | 删除 session；若删除的是当前且还有其他，自动切到最近一个；若全部删除则新建空 session |
| `addMessage(group, msg)` | 追加消息到当前 session 的最后一个 group；若 group 已 closed 则 startNewGroup |
| `startNewGroup()` | 关闭当前 group，开新 group |
| `clearCurrentSession()` | 清空当前 session 的消息，不是删除 session |

### 持久化

Pinia localStorage plugin 自动序列化整个 state。不依赖后端 API。

---

## 3. ChatPanel — 消息渲染

### BubbleList 替代纯 div

```html
<BubbleList
  ref="listRef"
  :roles="rolesConfig"
  :items="bubbleItems"
  auto-scroll
/>
```

- 用户气泡：右对齐，蓝色渐变背景，纯文本
- AI 气泡：左对齐，白底，VNode 渲染（markdown → HTML）

### Markdown 渲染

直接复用 `#/views/agent/chat/composables/useMarkdownRender`：

```typescript
import { useMarkdownRender } from '#/views/agent/chat/composables/useMarkdownRender'
const { messageRender } = useMarkdownRender()
```

- 支持 **粗体**、`行内代码`、``` 代码块 ```（highlight.js github 主题）、表格、列表
- HTML sanitization（DOMPurify 去 script/iframe/on* 属性）

### 流式光标

AI 消息内容为空时（等待第一个 token），BubbleList 底部显示闪烁光标动画。

---

## 4. ChatInput — 输入框清空

### 修复方案

```typescript
async function handleSendMessage() {
  const content = chatInput.value.trim()
  if (!content || store.streaming) return

  const messageText = content

  // 先清空输入框 + 强制 DOM 更新
  chatInput.value = ''
  await nextTick()

  // 再追加用户消息、调用 API
  store.ensureSession()
  store.addMessage(currentGroup, { role: 'user', type: 'text', content: messageText })
  // ... streaming
}
```

关键：清空 + `nextTick()` 在消息推送之前，消除异步竞态。

### 输入框 HTML

```html
<Input.TextArea
  v-model:value="chatInput"
  :auto-size="{ minRows: 3, maxRows: 6 }"
  :disabled="streaming"
  :placeholder="$t('workspace.chat.placeholder')"
  @press-enter.prevent="handleSendMessage"
/>
```

- 流式中禁用输入
- Enter 发送（无 Shift），Shift+Enter 换行
- 操作栏：停止按钮（流式中）/ 发送按钮

---

## 5. SessionSidebar — 对话列表

### 布局（desktop）

侧栏宽度 260px，右侧 ChatPanel 用 flex:1。

### 功能

| 操作 | 行为 |
|------|------|
| 新建 | `+` 按钮，`createSession()` |
| 切换 | 点击项，`switchSession(id)` |
| 重命名 | 双击标题，inline input，Enter 确认 |
| 删除 | hover 删除图标，Popconfirm "确定删除此对话？" |

### 排序

按 `updatedAt` 倒序，最近对话在顶部。

### 空状态

- 初始无 session → 左侧空列表，右侧欢迎消息
- 首条消息 → `ensureSession()` 自动创建
- 删光 session → 自动新建空 session

### 移动端

`@media (max-width: 768px)` 侧栏折叠为抽屉/汉堡菜单（deferred，先做 desktop）。

---

## 6. 文件变更清单

### 新建

| 文件 | 职责 |
|------|------|
| `src/store/modules/workspace.ts` | Pinia store（WorkspaceChatState + actions + localStorage 持久化） |
| `src/views/dashboard/workspace/SessionSidebar.vue` | 对话列表侧栏 |
| `src/views/dashboard/workspace/ChatPanel.vue` | 气泡列表 + 输入框 + markdown 渲染 |

### 修改

| 文件 | 改动 |
|------|------|
| `src/views/dashboard/workspace/index.vue` | 重构为布局壳（sidebar + ChatPanel），迁移现有 API 调用到 ChatPanel |
| `src/locales/langs/zh-CN/workspace.json` | 添加 `session.*` keys |
| `src/locales/langs/en-US/workspace.json` | 添加英文对应 |

---

## 7. 不做的事

- 不引入后端 Session API — 先 localStorage 持久化
- 不实现代码执行（code_result 消息类型只是预留）
- 不迁移到 agent-chat store — 保持独立轻量
- 不修改后端 `/platform/chat/completions` 接口
- 不改 `useMarkdownRender` 源码 — 直接 import 复用

---

## 8. i18n Keys（新增）

```json
{
  "session": {
    "newSession": "新对话",
    "newSessionBtn": "+ 新对话",
    "renamePlaceholder": "输入对话名称",
    "deleteConfirm": "确定要删除这个对话吗？",
    "emptyList": "暂无对话记录",
    "defaultTitle": "新对话"
  }
}
```
