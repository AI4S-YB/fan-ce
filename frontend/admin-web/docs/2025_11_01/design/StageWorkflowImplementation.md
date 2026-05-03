# 多阶段工作流功能设计文档

## 文档信息

- **创建日期**: 2025-11-01
- **功能名称**: 多阶段工作流 (Stage Workflow)
- **标记前缀**: `🔧 [STAGE_WORKFLOW]`
- **实施状态**: 待实施
- **预计移除**: 本功能为演示性质，后续可能删除

## 业务需求

### 核心需求

实现一个支持多阶段自动流转的聊天工作流系统，满足以下要求：

1. **阶段自动流转**: 当某个阶段完成时（收到带`next`字段的complete消息），自动调用下一阶段接口
2. **无缝用户体验**: 视觉和交互上等同于default模式的单次连续对话
3. **灵活阶段命名**: 支持后端返回任意阶段名称（如stage1, stage2, stage3等）
4. **简化功能**: 不需要进度显示、重试机制、阶段跳过等高级功能
5. **中断处理**: 与default模式一致，拒绝后解锁输入框，不做额外操作

### 技术示例

#### 后端接口示例

```bash
# 第一阶段
curl -X 'POST' \
  'http://10.33.105.56:8000/api/chat/stage1' \
  -H 'accept: application/json' \
  -d ''
```

#### SSE响应示例

```
data: {"type": "start", "message": "Workflow started"}

data: {"type": "output_msg", "content": "正在分析用户意图..."}

data: {"type": "output_msg", "content": "用户意图分析已完成。"}

data: {"type": "break"}

data: {"type": "interrupt", "content": "是否接受目前的执行结果：\n\n1. 接受  2. 不接受"}

data: {"type": "complete", "message": "Workflow completed", "next": "stage2"}
```

#### 工作流程

```
用户发起请求
    ↓
调用 stage1 (http://10.33.105.56:8000/api/chat/stage1)
    ↓
接收SSE流数据
    ├─ type: start
    ├─ type: output_msg
    ├─ type: break
    ├─ type: interrupt (等待用户点击"接受")
    └─ type: complete (next: "stage2")
           ↓
    自动调用 stage2 (http://10.33.105.56:8000/api/chat/stage2)
           ↓
    继续接收SSE流
           ↓
    type: complete (next: "stage3")
           ↓
    自动调用 stage3
           ↓
    type: complete (无next字段)
           ↓
    工作流结束
```

## 技术设计

### 设计原则

1. **最小侵入**: 优先新增代码，避免修改现有逻辑
2. **可回滚性**: 所有修改点使用`🔧 [STAGE_WORKFLOW]`标记
3. **功能隔离**: 通过配置开关控制，不影响现有端点（default、fileAnalysis）
4. **向后兼容**: 保持现有API和类型签名不变

### 实现方案

**采用方案**: 最小侵入式改造

**核心思路**:
- 在`handleComplete`函数中检测`next`字段，返回标志位而非直接结束流
- 在`processStream`函数中检测阶段流转需求，返回下一阶段信息
- 在`sendMessage`函数中使用while循环处理多阶段流转
- 新增`proceedToNextStage`函数封装阶段切换逻辑

**URL构建方式**: 直接拼接
```
baseUrl + '/' + next值
例: http://10.33.105.56:8000/api/chat/stage2
```

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         用户界面                              │
│                    (views/agent/chat)                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   useChatStream Hook                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  sendMessage()                                       │   │
│  │    ↓                                                 │   │
│  │  while (hasNextStage) {                              │   │
│  │    processStream() ──→ 检测 complete + next          │   │
│  │      ↓                                               │   │
│  │    proceedToNextStage() ──→ 发起下一阶段请求         │   │
│  │  }                                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  ChatEndpointConfig                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  isStageWorkflow: true                               │   │
│  │  stageBaseUrl: 'http://10.33.105.56:8000/api/chat'   │   │
│  │  url: 'http://10.33.105.56:8000/api/chat/stage1'     │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      后端SSE流                               │
│  stage1 → complete(next: stage2) → stage2 → complete(...)   │
└─────────────────────────────────────────────────────────────┘
```

## 详细实施步骤

### 步骤1: 扩展类型定义

**文件**: `src/views/agent/chat/types/chat.ts`

**位置**: 第15-22行（SSEMessage接口）

**改动**:
```typescript
export interface SSEMessage {
  type: StreamMessageType
  message?: string
  content?: string
  node_name?: string
  conversation_id?: string
  checkpoint_id?: string
  next?: string  // 🔧 [STAGE_WORKFLOW] 新增：下一阶段标识
}
```

---

### 步骤2: 扩展端点配置

**文件**: `src/config/chat-endpoints.ts`

#### 2.1 扩展接口

**位置**: 第1-9行（ChatEndpointConfig接口）

**改动**:
```typescript
export interface ChatEndpointConfig {
  url: string;
  inputType: 'file' | 'text';
  supportsFileUpload: boolean;
  fileFieldName?: string;
  maxFileSize?: number;
  acceptedFileTypes?: string[];
  timeoutMs?: number;
  // 🔧 [STAGE_WORKFLOW] 新增
  isStageWorkflow?: boolean;
  stageBaseUrl?: string;
}
```

#### 2.2 新增端点配置

**位置**: CHAT_ENDPOINTS对象内

**改动**:
```typescript
export const CHAT_ENDPOINTS: Record<string, ChatEndpointConfig> = {
  default: { /* 保持不变 */ },
  fileAnalysis: { /* 保持不变 */ },
  // 🔧 [STAGE_WORKFLOW] 新增
  stageWorkflow: {
    url: 'http://10.33.105.56:8000/api/chat/stage1',
    inputType: 'text',
    supportsFileUpload: false,
    timeoutMs: undefined,
    isStageWorkflow: true,
    stageBaseUrl: 'http://10.33.105.56:8000/api/chat',
  },
};
```

#### 2.3 扩展路由匹配

**位置**: getChatEndpointConfig函数

**改动**:
```typescript
export function getChatEndpointConfig(path: string): ChatEndpointConfig {
  // 🔧 [STAGE_WORKFLOW] 新增
  if (path.includes('/stage-workflow-chat')) {
    return CHAT_ENDPOINTS.stageWorkflow;
  }

  if (path.includes('/file-chat')) {
    return CHAT_ENDPOINTS.fileAnalysis;
  }
  return CHAT_ENDPOINTS.default;
}
```

---

### 步骤3: 扩展Store状态

**文件**: `src/store/modules/agent-chat.ts`

#### 3.1 扩展状态接口

**位置**: 第30-40行（AgentChatState接口）

**改动**:
```typescript
interface AgentChatState {
  currentSession: ConversationSession | null
  messageGroups: MessageGroup[]
  streamState: StreamState
  currentInterrupt: InterruptRequest | null
  needsUserCommand: boolean
  pendingContinuation: {
    conversationId: string
    checkpointId: string
  } | null
  // 🔧 [STAGE_WORKFLOW] 新增
  currentStage: string | null
}
```

#### 3.2 初始化状态

**位置**: 第61-68行（state函数）

**改动**:
```typescript
state: (): AgentChatState => ({
  currentSession: null,
  messageGroups: [],
  streamState: { ...INITIAL_STREAM_STATE },
  currentInterrupt: null,
  needsUserCommand: false,
  pendingContinuation: null,
  currentStage: null,  // 🔧 [STAGE_WORKFLOW] 新增
}),
```

#### 3.3 新增Actions

**位置**: actions对象内（第244行之前）

**改动**:
```typescript
// 🔧 [STAGE_WORKFLOW] 新增
setCurrentStage(stage: string | null) {
  this.currentStage = stage
},
```

#### 3.4 修改resetState

**位置**: resetState函数内

**改动**:
```typescript
resetState() {
  this.currentSession = null
  this.messageGroups = []
  this.streamState = { ...INITIAL_STREAM_STATE }
  this.currentInterrupt = null
  this.needsUserCommand = false
  this.pendingContinuation = null
  this.currentStage = null  // 🔧 [STAGE_WORKFLOW] 新增
},
```

---

### 步骤4: 核心流处理逻辑

**文件**: `src/views/agent/chat/composables/useChatStream.ts`

#### 4.1 添加Import

**位置**: 文件顶部

**改动**:
```typescript
// 🔧 [STAGE_WORKFLOW] 新增
import { useAccessStore } from '@vben/stores'
import { preferences } from '@vben/preferences'
import { useProjectStoreWithOut } from '#/store/modules/project'
```

#### 4.2 修改handleComplete

**位置**: 第113-121行

**改动**:
```typescript
function handleComplete(message: SSEMessage) {
  // 🔧 [STAGE_WORKFLOW] 新增：检测阶段流转
  if (message.next) {
    return { shouldContinue: true, nextStage: message.next }
  }

  // 原有逻辑保持不变
  store.updateStreamState({
    isStreaming: false,
    connectionStatus: ConnectionStatus.DISCONNECTED,
    lastUpdateTime: Date.now(),
  })
  clearStreamTimeout()
  isStreaming.value = false

  return { shouldContinue: false }  // 🔧 [STAGE_WORKFLOW] 新增返回值
}
```

#### 4.3 修改processStream

**位置**: 第130-175行

**改动**:
```typescript
async function processStream(
  readable: ReadableStream<Uint8Array>,
  config: ChatEndpointConfig
) {
  const stream = XStream({ readableStream: readable })

  for await (const chunk of stream) {
    scheduleTimeout(config)

    const raw = chunk?.data
    if (!raw || typeof raw !== 'string') {
      continue
    }

    let payload: unknown
    try {
      payload = JSON.parse(raw)
    } catch (parseError) {
      handleStreamError(
        createStreamError('Failed to parse stream message', 'STREAM_PARSE_ERROR'),
      )
      continue
    }

    if (!isSSEMessage(payload)) {
      continue
    }

    switch (payload.type) {
      case 'start':
        handleStart(payload)
        break
      case 'output_msg':
        handleOutput(payload)
        break
      case 'execution_msg':
        handleExecution(payload)
        break
      case 'interrupt':
        handleInterrupt(payload)
        break
      case 'complete': {
        // 🔧 [STAGE_WORKFLOW] 修改：支持阶段流转
        const result = handleComplete(payload)
        if (result.shouldContinue && result.nextStage) {
          return { nextStage: result.nextStage, lastMessage: payload }
        }
        break
      }
      default:
        break
    }
  }

  // 🔧 [STAGE_WORKFLOW] 新增：正常结束返回null
  return null
}
```

#### 4.4 新增proceedToNextStage函数

**位置**: processStream函数之后

**改动**:
```typescript
// 🔧 [STAGE_WORKFLOW] 新增：阶段流转函数
async function proceedToNextStage(
  nextStage: string,
  config: ChatEndpointConfig,
  previousMessage: SSEMessage,
  signal?: AbortSignal
): Promise<{ nextStage: string; lastMessage: SSEMessage } | null> {
  try {
    // 更新当前阶段状态
    store.setCurrentStage(nextStage)

    // 构建下一阶段URL
    const nextUrl = `${config.stageBaseUrl}/${nextStage}`

    // 构建请求（空消息，继承上下文）
    const formData = new FormData()
    formData.append('message', '')
    formData.append('stream', 'true')

    if (previousMessage.conversation_id) {
      formData.append('conversation_id', previousMessage.conversation_id)
    }
    if (previousMessage.checkpoint_id) {
      formData.append('checkpoint_id', previousMessage.checkpoint_id)
    }

    // 添加项目和团队ID
    const projectStore = useProjectStoreWithOut()
    const teamId = projectStore.teamInfo?.team_id ?? 0
    const projectId = projectStore.projectInfo?.id ?? 0
    formData.append('team_id', String(teamId))
    formData.append('project_id', String(projectId))

    // 发起请求
    const accessStore = useAccessStore()
    const headers = new Headers({
      Accept: 'text/event-stream',
      'Accept-Language': preferences.app.locale,
      'Cache-Control': 'no-cache',
    })

    if (accessStore.accessToken) {
      headers.append('Authorization', `Bearer ${accessStore.accessToken}`)
    }

    const response = await fetch(nextUrl, {
      method: 'POST',
      body: formData,
      headers,
      signal,
    })

    if (!response.ok) {
      throw createStreamError(
        `Stage ${nextStage} request failed (${response.status})`,
        'HTTP_ERROR'
      )
    }

    if (!response.body) {
      throw createStreamError(
        `Stage ${nextStage} response missing body`,
        'NO_STREAM_BODY'
      )
    }

    // 处理新阶段的流
    scheduleTimeout(config)
    return await processStream(response.body, config)

  } catch (err) {
    const streamError = err instanceof Error
      ? createStreamError(`Stage transition failed: ${err.message}`)
      : createStreamError('Unknown stage transition error')
    handleStreamError(streamError)
    throw err
  }
}
```

#### 4.5 修改sendMessage函数

**位置**: 第177-232行

**改动**:
```typescript
async function sendMessage(request: ChatRequest, config: ChatEndpointConfig) {
  if (isStreaming.value) {
    controller?.abort()
  }

  controller = new AbortController()
  error.value = null
  isStreaming.value = true

  // 🔧 [STAGE_WORKFLOW] 新增：初始化阶段状态
  if (config.isStageWorkflow) {
    store.setCurrentStage('stage1')
  }

  // Check if this is continuing an existing session (interrupt response)
  if (request.conversation_id && request.checkpoint_id) {
    store.continueSession(request.conversation_id, request.checkpoint_id)
  } else {
    store.startNewSession({
      userInput: request.message,
    })
  }

  store.updateStreamState({
    isStreaming: true,
    connectionStatus: ConnectionStatus.CONNECTING,
    lastUpdateTime: Date.now(),
    retryCount: 0,
  })

  try {
    const response = await sendChatMessage(request, config, { signal: controller.signal })

    if (!response.ok) {
      throw createStreamError(`Stream request failed (${response.status})`, 'HTTP_ERROR')
    }

    if (!response.body) {
      throw createStreamError('Stream response missing body', 'NO_STREAM_BODY')
    }

    store.updateStreamState({
      connectionStatus: ConnectionStatus.CONNECTED,
      lastUpdateTime: Date.now(),
    })

    scheduleTimeout(config)

    // 🔧 [STAGE_WORKFLOW] 修改：支持多阶段循环
    let stageResult = await processStream(response.body, config)

    // 如果是阶段工作流且有下一阶段，继续处理
    while (config.isStageWorkflow && stageResult?.nextStage) {
      stageResult = await proceedToNextStage(
        stageResult.nextStage,
        config,
        stageResult.lastMessage,
        controller.signal
      )
    }

  } catch (err) {
    const streamError =
      err instanceof Error
        ? createStreamError(err.message)
        : createStreamError('Unknown stream error')
    handleStreamError(streamError)
    throw err
  } finally {
    clearStreamTimeout()
    isStreaming.value = false
    controller = null

    // 🔧 [STAGE_WORKFLOW] 新增：清理阶段状态
    if (config.isStageWorkflow) {
      store.setCurrentStage(null)
    }
  }
}
```

## 实施清单

- [ ] 1. 修改`src/views/agent/chat/types/chat.ts`，添加next字段到SSEMessage接口
- [ ] 2. 修改`src/config/chat-endpoints.ts`，扩展ChatEndpointConfig接口
- [ ] 3. 修改`src/config/chat-endpoints.ts`，新增stageWorkflow配置
- [ ] 4. 修改`src/config/chat-endpoints.ts`，扩展getChatEndpointConfig函数
- [ ] 5. 修改`src/store/modules/agent-chat.ts`，扩展AgentChatState接口
- [ ] 6. 修改`src/store/modules/agent-chat.ts`，初始化currentStage状态
- [ ] 7. 修改`src/store/modules/agent-chat.ts`，新增setCurrentStage action
- [ ] 8. 修改`src/store/modules/agent-chat.ts`，修改resetState清理逻辑
- [ ] 9. 修改`src/views/agent/chat/composables/useChatStream.ts`，添加必要的import
- [ ] 10. 修改`src/views/agent/chat/composables/useChatStream.ts`，修改handleComplete函数
- [ ] 11. 修改`src/views/agent/chat/composables/useChatStream.ts`，修改processStream函数
- [ ] 12. 修改`src/views/agent/chat/composables/useChatStream.ts`，新增proceedToNextStage函数
- [ ] 13. 修改`src/views/agent/chat/composables/useChatStream.ts`，修改sendMessage函数

## 回滚方案

### 快速回滚步骤

1. **搜索标记**
   ```bash
   # 在项目根目录执行
   grep -r "🔧 \[STAGE_WORKFLOW\]" --include="*.ts" --include="*.vue" apps/web-antd/src/
   ```

2. **删除新增代码**
   - 删除所有带`🔧 [STAGE_WORKFLOW]`标记的新增代码行
   - 删除新增的函数：`proceedToNextStage`
   - 删除新增的配置：`CHAT_ENDPOINTS.stageWorkflow`

3. **恢复原始逻辑**

   **文件**: `src/views/agent/chat/composables/useChatStream.ts`

   恢复`handleComplete`:
   ```typescript
   function handleComplete() {
     store.updateStreamState({
       isStreaming: false,
       connectionStatus: ConnectionStatus.DISCONNECTED,
       lastUpdateTime: Date.now(),
     })
     clearStreamTimeout()
     isStreaming.value = false
   }
   ```

   恢复`processStream`:
   ```typescript
   case 'complete':
     handleComplete()
     break
   ```

   恢复`sendMessage` (移除while循环):
   ```typescript
   scheduleTimeout(config)
   await processStream(response.body, config)
   ```

4. **移除import**

   如果原代码中没有使用，移除以下import:
   ```typescript
   import { useAccessStore } from '@vben/stores'
   import { preferences } from '@vben/preferences'
   import { useProjectStoreWithOut } from '#/store/modules/project'
   ```

5. **移除类型字段**

   从接口中移除：
   - `SSEMessage.next`
   - `ChatEndpointConfig.isStageWorkflow`
   - `ChatEndpointConfig.stageBaseUrl`
   - `AgentChatState.currentStage`

6. **移除路由配置**

   从`getChatEndpointConfig`中移除stage-workflow-chat分支

### 回滚验证

- [ ] 删除所有标记代码后，执行`pnpm check:type`确保无类型错误
- [ ] 测试default端点功能正常
- [ ] 测试fileAnalysis端点功能正常
- [ ] 确认没有引入任何运行时错误

## 测试验证

### 基础功能测试

- [ ] **Default端点**: 正常发送消息，接收流式响应
- [ ] **File端点**: 上传文件并接收分析结果
- [ ] **中断处理**: 接受/拒绝选项功能正常

### 阶段工作流测试

#### 测试场景1: 单阶段工作流
- [ ] 访问`/stage-workflow-chat`路由
- [ ] 发送消息触发stage1
- [ ] 接收到complete消息无next字段
- [ ] 流正常结束

#### 测试场景2: 多阶段工作流
- [ ] 发送消息触发stage1
- [ ] 接收到complete消息带`next: "stage2"`
- [ ] 自动请求stage2接口
- [ ] 接收到complete消息带`next: "stage3"`
- [ ] 自动请求stage3接口
- [ ] 接收到complete消息无next字段
- [ ] 流正常结束

#### 测试场景3: 中断处理
- [ ] 在某个阶段接收到interrupt消息
- [ ] 点击"接受"选项
- [ ] 继续流程，进入下一阶段
- [ ] 流程正常完成

#### 测试场景4: 拒绝中断
- [ ] 接收到interrupt消息
- [ ] 点击"拒绝"选项
- [ ] 输入框解锁
- [ ] 可以输入新指令
- [ ] 发送新指令后流程继续

#### 测试场景5: 错误处理
- [ ] 某个阶段请求失败（如网络错误）
- [ ] 显示错误信息
- [ ] 流程停止
- [ ] 可以点击重试

#### 测试场景6: 取消流
- [ ] 在多阶段流程进行中
- [ ] 点击取消按钮
- [ ] 所有阶段请求被中止
- [ ] 流程停止

### 性能测试

- [ ] 验证10个阶段的工作流性能
- [ ] 检查内存占用是否异常
- [ ] 确认无内存泄漏

## 附录

### 相关文件清单

```
apps/web-antd/src/
├── api/
│   └── agent/
│       └── chat.ts                           # API请求函数
├── config/
│   └── chat-endpoints.ts                     # 端点配置 [修改]
├── store/
│   └── modules/
│       └── agent-chat.ts                     # 状态管理 [修改]
└── views/
    └── agent/
        └── chat/
            ├── index.vue                      # 主页面 [不修改]
            ├── types/
            │   └── chat.ts                    # 类型定义 [修改]
            └── composables/
                └── useChatStream.ts           # 流处理逻辑 [修改]
```

### 代码统计

- **修改文件数**: 4个
- **新增函数**: 1个 (proceedToNextStage)
- **新增类型字段**: 4个
- **新增配置项**: 1个 (stageWorkflow)
- **估计代码行数**: ~150行

### 风险评估

| 风险项 | 等级 | 缓解措施 |
|--------|------|----------|
| 调用栈深度 | 低 | 使用while循环而非递归 |
| 内存泄漏 | 低 | 及时清理状态，使用单一AbortController |
| 类型安全 | 低 | 使用TypeScript类型守卫 |
| 现有功能影响 | 极低 | 通过配置隔离，最小改动原则 |
| 回滚难度 | 低 | 明确标记，详细文档 |

### 技术债务

本功能为演示性质，存在以下技术债务：

1. **代码重复**: `proceedToNextStage`中复制了部分API请求逻辑
2. **硬编码**: stage1作为初始阶段硬编码在代码中
3. **缺少日志**: 阶段切换过程缺少详细日志记录
4. **缺少监控**: 无阶段性能监控和统计

如功能需要长期保留，建议进行重构优化。

---

**文档版本**: 1.0
**最后更新**: 2025-11-01
**维护者**: Claude Code
**审核状态**: 待审核
## 修改记录 - 2025-11-01 16:04:02

### 重大修改：阶段流转触发方式变更

**原设计（错误）**：
- complete消息带next时，自动在while循环中调用下一阶段
- 无需用户确认即触发

**修改后（正确）**：
- complete消息带next时，保存到store.pendingNextStage，不触发调用
- 用户在interrupt中点击'接受'时，检查pendingNextStage
- 如果存在pendingNextStage，调用triggerNextStage执行下一阶段
- 用户点击'拒绝'时，清除pendingNextStage，不执行下一阶段

**修改的文件**：
1. `store/modules/agent-chat.ts`
   - 添加pendingNextStage状态
   - 添加setPendingNextStage、clearPendingNextStage actions

2. `views/agent/chat/composables/useChatStream.ts`
   - 修改handleComplete：保存next到store而非返回继续标志
   - 修改processStream：移除返回值处理
   - 修改sendMessage：移除while循环自动流转逻辑
   - 新增triggerNextStage：手动触发下一阶段的包装函数

3. `views/agent/chat/index.vue`
   - 解构triggerNextStage函数
   - 修改handleInterruptSelect：在接受后检查并触发pendingNextStage

**正确的工作流程**：
```
用户发起请求 → stage1
  ↓
收到interrupt → 等待用户操作
  ↓
收到complete(next: stage2) → 保存到pendingNextStage
  ↓
用户点击接受 → sendMessage发送确认
  ↓
检查pendingNextStage → 调用triggerNextStage
  ↓
执行stage2 → 收到interrupt和complete(next: stage3)
  ↓
用户点击接受 → 执行stage3
  ↓
收到complete(无next) → 工作流结束
```

