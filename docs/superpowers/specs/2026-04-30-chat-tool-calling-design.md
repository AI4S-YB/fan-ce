# Chat Tool Calling — 自然语言对话集成数据查询

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan.

**Goal:** 在探索工作台的对话流程中集成 tool calling，当用户意图是数据查询时，通过后端 dataset adapter 及其他模块 API 查询数据，并在对话气泡中展示结果。

**Architecture:** 后端 `/platform/chat/completions` 接管对话，加入 OpenAI function calling 循环——LLM 返回 `tool_calls` 时后端执行对应的 tool（dataset query、种质资源搜索、项目列表等），结果全量送回 LLM 做自然语言总结，通过 SSE 流将 `tool_call`、`tool_result`、`output_msg` 事件推送到前端。前端 OutputPanel 识别 `tool_result` 类型渲染数据卡片组件。

**Tech Stack:** FastAPI SSE streaming, OpenAI-compatible function calling, Vue3 + ant-design-x-vue BubbleList, Pinia

---

## Architecture

```
User Input → ChatInput.vue
    │ POST /api/v1/platform/chat/completions (SSE)
    ▼
FastAPI /platform/chat/completions
    ├─ Load model config from pf_model_api_setting
    ├─ Build messages + tools → LLM
    ├─ LLM returns text → SSE output_msg (streaming)
    ├─ LLM returns tool_calls →
    │   ├─ SSE tool_call event → frontend shows "正在查询..."
    │   ├─ ToolRegistry.execute(name, args)
    │   ├─ SSE tool_result event → frontend renders QueryCard
    │   ├─ Append tool_result to messages → LLM summary
    │   └─ SSE output_msg → summary text
    └─ SSE complete
```

## SSE Protocol Extension

New event types (in addition to existing `output_msg`, `execution_msg`, `interrupt`, `complete`):

### `tool_call`
```json
{
  "type": "tool_call",
  "tool_name": "query_dataset",
  "arguments": { "dataset_id": 21, "operation": "query", "regions": ["Chr1A:89017-90016"] }
}
```
Frontend shows a transient status bubble: "正在查询 ds-21..."

### `tool_result`
```json
{
  "type": "tool_result",
  "tool_name": "query_dataset",
  "data": { "count": 18, "preview": "...", "download_url": "..." },
  "message": "查询成功，共 18 条记录"
}
```
Frontend renders a QueryToolResultCard (data preview table + download link).

## Tool Registry

Pluggable: each app module registers its own tools. ToolRegistry collects them at startup.

```python
class ToolDefinition:
    name: str
    description: str
    parameters: dict       # JSON Schema for LLM function calling
    execute: Callable      # async function
    require_admin: bool    # True = admin API, False = public API
```

### Dataset Tools (`apps/datasets/tools.py`)
- `list_datasets` — 搜索数据集列表，按类型/关键词筛选，分页
- `get_dataset_info` — 获取单个数据集的详情（版本、字段、查询能力）
- `query_dataset` — 执行数据查询，委托给 `dataset_adapter_registry.execute()`

### Germplasm Tools (`apps/germplasm/tools.py`)
- `search_germplasm` — 搜索种质资源

### Project/System Tools
- `list_projects` — 列出项目
- (后续按需扩展)

### Permission Model
- 管理员工作台：所有 tools（`require_admin=True`），调 `/admin/` 接口
- 公开查询：仅 `require_admin=False` 的 tools，调 `/public/` 接口
- 两组 tool 列表在 `/platform/chat/completions` 中根据路由前缀区分

## Chat Endpoint Logic (`apps/platform/api/chat.py`)

```
handle_chat_completion(messages, user):
    tools = tool_registry.get_for_context(user, is_admin=True)
    system_prompt = build_system_prompt(...)
    messages = [system_prompt] + messages

    loop (max 3 tool-calling rounds):
        response = stream_to_llm(messages, tools)
        if response has tool_calls:
            for each tool_call:
                yield SSE(tool_call)
                result = tool_registry.execute(tool_call.name, tool_call.args)
                yield SSE(tool_result, data=result)
                messages.append({"role": "tool", "content": result, ...})
        else:
            yield SSE(output_msg, content=response.text)  # streaming
            break

    yield SSE(complete)
```

## Data Truncation Strategy

- Default: full data to LLM for summarization
- Future: if result exceeds LLM context window, add a statistical summary layer (count, column distributions, top-N rows)

## Frontend Changes

### Files to Modify
- `src/config/chat-endpoints.ts` — Remove `fileAnalysis` and `stageWorkflow` endpoints (10.33.105.56). Change `default.url` to `/api/v1/platform/chat/completions`.
- `src/api/agent/chat.ts` — Remove `chatApiURL` prefix logic. Chat endpoint is now an absolute API path (already starts with `/api/v1`), no separate base URL needed. Or keep the prefix but simplify.
- `src/views/agent/chat/types/chat.ts` — Add `tool_call`, `tool_result` to SSEMessage type union. Extend `ChatMessage` to carry optional tool result payload.
- `src/views/agent/chat/composables/useChatStream.ts` — Handle new message types in `processStream()`
- `src/views/agent/chat/components/OutputPanel.vue` — Render `tool_result` messages using QueryToolResultCard instead of text bubble
- `src/store/modules/agent-chat.ts` — Extend ChatMessage type to carry tool result data

### Files to Create
- `src/views/agent/chat/components/QueryToolResultCard.vue` — Data card component: shows tool name, arguments, data preview table (first 20 rows), record count, download link

### MVP Scope
- Implement ToolRegistry + dataset tools (`list_datasets`, `get_dataset_info`, `query_dataset`)
- Germplasm and project tools deferred to follow-up (the infrastructure supports adding them trivially)
- Only admin endpoint for now (管理员工作台); public route deferred

## Migration

- Remove old Dify/10.33.105.56 references
- Delete `fileAnalysis` and `stageWorkflow` endpoint configs
- Remove `VITE_GLOB_CHAT_API_URL` fallback ambiguity (make it explicit in `.env`)
