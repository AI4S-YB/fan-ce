# Chat Tool Calling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build pluggable tool-calling infrastructure in the platform chat endpoint so LLM can call dataset query APIs, with results rendered as data cards in the frontend chat UI.

**Architecture:** ToolRegistry collects ToolDefinitions from app modules. `/platform/chat/completions` sends tools to LLM, executes `tool_calls` via the registry, streams `tool_call`/`tool_result` SSE events, then asks LLM to summarize results. Frontend renders `tool_result` as QueryToolResultCard inside BubbleList.

**Tech Stack:** Python FastAPI + httpx SSE streaming, Vue3 + ant-design-x-vue + Pinia, OpenAI-compatible function calling

---

### File Map

| File | Responsibility |
|------|---------------|
| `libs/tool_registry.py` (new) | ToolDefinition, ToolRegistry: register + execute |
| `apps/datasets/tools.py` (new) | list_datasets, get_dataset_info, query_dataset tools |
| `apps/platform/api/chat.py` (modify) | Tool calling loop in SSE stream |
| `tests/test_tool_registry.py` (new) | Unit tests for registry |
| `tests/test_chat_tool_calling.py` (new) | Integration tests for chat tool calling |
| `src/config/chat-endpoints.ts` (modify) | Remove old endpoints, fix default URL |
| `.env.development` (modify) | Set VITE_GLOB_CHAT_API_URL |
| `src/views/agent/chat/types/chat.ts` (modify) | Add tool_call, tool_result types |
| `src/views/agent/chat/composables/useChatStream.ts` (modify) | Handle new SSE types |
| `src/views/agent/chat/components/QueryToolResultCard.vue` (new) | Data preview card |
| `src/views/agent/chat/components/OutputPanel.vue` (modify) | Render tool_result cards |
| `src/store/modules/agent-chat.ts` (modify) | Support tool result messages |

---

### Task 1: Tool Registry Infrastructure

**Files:**
- Create: `backend/api-server/libs/tool_registry.py`

- [ ] **Step 1: Create the tool registry module**

```python
# libs/tool_registry.py
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict  # JSON Schema
    execute: Callable  # async (db, arguments, user) -> dict
    require_admin: bool = True

    def to_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def register_many(self, tools: List[ToolDefinition]) -> None:
        for tool in tools:
            self.register(tool)

    def get_all(self, admin: bool = True) -> List[ToolDefinition]:
        return [t for t in self._tools.values() if not t.require_admin or admin]

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def to_openai_tools(self, admin: bool = True) -> List[dict]:
        return [t.to_openai_tool() for t in self.get_all(admin=admin)]

    async def execute(self, name: str, arguments: dict, db, user) -> dict:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        return await tool.execute(db=db, arguments=arguments, user=user)


# Global singleton
tool_registry = ToolRegistry()
```

- [ ] **Step 2: Verify the module imports cleanly**

Run: `cd backend/api-server && python -c "from libs.tool_registry import tool_registry, ToolDefinition; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/api-server/libs/tool_registry.py
git commit -m "feat: add pluggable tool registry for LLM function calling"
```

---

### Task 2: Dataset Tools

**Files:**
- Create: `backend/api-server/apps/datasets/tools.py`

- [ ] **Step 1: Create dataset tool definitions**

```python
# apps/datasets/tools.py
from libs.tool_registry import ToolDefinition, tool_registry
from apps.datasets.services import dataset_domain_service


async def _execute_list_datasets(db, arguments: dict, user) -> dict:
    dataset_type = arguments.get("dataset_type")
    keyword = arguments.get("keyword")
    page = arguments.get("page", 1)
    size = arguments.get("size", 20)
    result = dataset_domain_service.list_datasets(
        db=db,
        dataset_type=dataset_type,
        keyword=keyword,
        page=page,
        size=size,
        user=user,
    )
    items = []
    for item in result.get("dataList", []):
        items.append({
            "id": item["id"],
            "dataset_code": item.get("dataset_code", ""),
            "title": item.get("title", ""),
            "dataset_type": item.get("dataset_type", ""),
            "lifecycle_state": item.get("lifecycle_state", ""),
            "version": item.get("version", ""),
            "file_format": item.get("query_profile", {}).get("file_format", ""),
        })
    return {"items": items, "total": result.get("total", 0), "page": page, "size": size}


async def _execute_get_dataset_info(db, arguments: dict, user) -> dict:
    dataset_id = arguments["dataset_id"]
    dataset = dataset_domain_service.get_dataset(db=db, dataset_id=dataset_id, user=user)
    return {
        "id": dataset["id"],
        "dataset_code": dataset.get("dataset_code", ""),
        "title": dataset.get("title", ""),
        "dataset_type": dataset.get("dataset_type", ""),
        "version": dataset.get("version", ""),
        "query_profile": dataset.get("query_profile", {}),
        "query_adapter": dataset.get("query_adapter", {}),
    }


async def _execute_query_dataset(db, arguments: dict, user) -> dict:
    dataset_id = arguments["dataset_id"]
    operation = arguments.get("operation", "query")
    params = arguments.get("params", {}) or {}
    asset_code = arguments.get("asset_code")
    result = dataset_domain_service.execute_query(
        db=db,
        dataset_id=dataset_id,
        operation=operation,
        asset_code=asset_code,
        params=params,
        user=user,
    )
    return {"data": result.get("data"), "adapter": result.get("adapter"), "operation": result.get("operation")}


DATASET_TOOLS = [
    ToolDefinition(
        name="list_datasets",
        description="搜索可用的数据集列表。可按数据集类型和名称关键词筛选，返回 id、名称、类型、版本等信息。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_type": {
                    "type": "string",
                    "enum": ["genome", "transcriptome", "variome", "phenome", "generic"],
                    "description": "数据集类型",
                },
                "keyword": {"type": "string", "description": "数据集名称关键词搜索"},
                "page": {"type": "integer", "default": 1},
                "size": {"type": "integer", "default": 20},
            },
        },
        execute=_execute_list_datasets,
        require_admin=True,
    ),
    ToolDefinition(
        name="get_dataset_info",
        description="获取指定数据集的详细信息，包括查询引擎、文件格式、支持的查询操作等。在查询数据前应先调用此工具了解数据集能力。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer", "description": "数据集 ID"},
            },
            "required": ["dataset_id"],
        },
        execute=_execute_get_dataset_info,
        require_admin=True,
    ),
    ToolDefinition(
        name="query_dataset",
        description="对指定数据集执行数据查询。先通过 get_dataset_info 了解可用的操作，再调用此工具。region_example 不需要参数，samples_list 不需要参数，query 需要 regions。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer", "description": "数据集 ID"},
                "operation": {
                    "type": "string",
                    "enum": ["query", "region_example", "samples_list"],
                    "description": "查询操作：region_example 获取示例区域，samples_list 列出样本，query 按区域查询数据",
                },
                "regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "基因组区域列表，格式如 ['Chr1:1000-2000']，仅 query 操作需要",
                },
                "asset_code": {
                    "type": "string",
                    "description": "指定查询资产代码，通常省略以使用默认查询入口",
                },
            },
            "required": ["dataset_id", "operation"],
        },
        execute=_execute_query_dataset,
        require_admin=True,
    ),
]


def register_dataset_tools():
    tool_registry.register_many(DATASET_TOOLS)
```

- [ ] **Step 2: Import and register at app startup**

Edit `apps/datasets/init.py`:

```python
# Add at the end of the existing init code:
from apps.datasets.tools import register_dataset_tools

register_dataset_tools()
```

- [ ] **Step 3: Verify registration**

Run: `cd backend/api-server && python -c "
from libs.tool_registry import tool_registry
from apps.datasets.tools import register_dataset_tools
register_dataset_tools()
print('Registered tools:', list(tool_registry._tools.keys()))
print('OpenAI format:', tool_registry.to_openai_tools()[:1])
"`
Expected: Shows 3 registered tools with OpenAI format output.

- [ ] **Step 4: Commit**

```bash
git add backend/api-server/apps/datasets/tools.py backend/api-server/apps/datasets/init.py
git commit -m "feat: add dataset tools for LLM function calling"
```

---

### Task 3: Refactor Chat Endpoint with Tool Calling Loop

**Files:**
- Modify: `backend/api-server/apps/platform/api/chat.py`

- [ ] **Step 1: Replace the chat endpoint with tool-calling loop**

```python
# apps/platform/api/chat.py
import json

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from apps.common.depends import get_active_user
from apps.datasets.tools import register_dataset_tools
from db.database import get_db
from libs.responses.response import response_200
from libs.tool_registry import tool_registry
from ..models import PlatformModelApiSetting
from ..schemas import PlatformChatCompletionRequest, PlatformChatTestRequest

chat_router = APIRouter(tags=["app:platform:LLM对话"])

SYSTEM_PROMPT = """你是一个生物信息学数据分析助手，运行在管理员工作台环境中。
你可以使用提供的工具来查询数据集、搜索种质资源和管理项目数据。
当用户询问关于数据内容的问题时，应先调用 list_datasets 了解有哪些数据集，
然后调用 get_dataset_info 查看具体数据集的能力，最后调用 query_dataset 执行查询。
用中文回答，数据结果要清晰总结。"""

MAX_TOOL_ROUNDS = 3


def _find_primary_model(db: Session) -> PlatformModelApiSetting:
    model = (
        db.query(PlatformModelApiSetting)
        .filter(PlatformModelApiSetting.is_primary == True, PlatformModelApiSetting.is_active == True)  # noqa: E712
        .order_by(PlatformModelApiSetting.sort_order.asc(), PlatformModelApiSetting.id.asc())
        .first()
    )
    if not model:
        model = (
            db.query(PlatformModelApiSetting)
            .filter(PlatformModelApiSetting.is_active == True)  # noqa: E712
            .order_by(PlatformModelApiSetting.sort_order.asc(), PlatformModelApiSetting.id.asc())
            .first()
        )
    if not model:
        raise HTTPException(status_code=400, detail="没有可用的模型 API 配置，请先在平台设置中配置")
    return model


def _build_payload(model: PlatformModelApiSetting, messages: list[dict], tools: list[dict], stream: bool = True):
    payload = {
        "model": model.model_name,
        "messages": messages,
        "stream": stream,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    return payload


def _sse_event(event_type: str, data: dict) -> str:
    return f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False)}\n\n"


def _extract_text_from_chunk(chunk: dict) -> str:
    choices = chunk.get("choices") or []
    if not choices:
        return ""
    delta = choices[0].get("delta") or {}
    return delta.get("content") or ""


def _extract_tool_calls_from_chunk(chunk: dict) -> list[dict]:
    choices = chunk.get("choices") or []
    if not choices:
        return []
    delta = choices[0].get("delta") or {}
    return delta.get("tool_calls") or []


async def _stream_tool_calling_loop(model: PlatformModelApiSetting, messages: list[dict], db: Session, user):
    tools = tool_registry.to_openai_tools(admin=True)
    tool_map = {t.name: t for t in tool_registry.get_all(admin=True)}

    for _round in range(MAX_TOOL_ROUNDS):
        has_tool_call = False
        accumulated_content = ""
        accumulated_tool_calls: dict[int, dict] = {}

        payload = _build_payload(model, messages, tools)
        headers = {
            "Authorization": f"Bearer {model.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            async with client.stream("POST", f"{model.api_base_url.rstrip('/')}/chat/completions",
                                     json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    error_text = error_body.decode("utf-8", errors="replace")[:500]
                    yield _sse_event("error", {"message": f"模型服务返回错误 ({response.status_code}): {error_text}"})
                    yield _sse_event("complete", {})
                    return

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]

                    if data_str.strip() == "[DONE]":
                        continue

                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    text = _extract_text_from_chunk(chunk)
                    if text:
                        accumulated_content += text
                        yield _sse_event("output_msg", {"content": text})

                    for tc in _extract_tool_calls_from_chunk(chunk):
                        idx = tc.get("index", 0)
                        if idx not in accumulated_tool_calls:
                            accumulated_tool_calls[idx] = {"id": tc.get("id", ""), "name": "", "arguments": ""}
                        if tc.get("function", {}).get("name"):
                            accumulated_tool_calls[idx]["name"] += tc["function"]["name"]
                        if tc.get("function", {}).get("arguments"):
                            accumulated_tool_calls[idx]["arguments"] += tc["function"]["arguments"]

        # Process tool calls after stream completes
        if accumulated_tool_calls:
            has_tool_call = True
            assistant_msg = {"role": "assistant"}
            if accumulated_content:
                assistant_msg["content"] = accumulated_content
            tool_calls_msg = []
            for tc in accumulated_tool_calls.values():
                tool_calls_msg.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                })
            if tool_calls_msg:
                assistant_msg["tool_calls"] = tool_calls_msg
            messages.append(assistant_msg)

            for tc_val in accumulated_tool_calls.values():
                tool_name = tc_val["name"]
                try:
                    args = json.loads(tc_val["arguments"])
                except json.JSONDecodeError:
                    args = {}

                yield _sse_event("tool_call", {"tool_name": tool_name, "arguments": args})

                try:
                    result = await tool_registry.execute(tool_name, args, db=db, user=user)
                    yield _sse_event("tool_result", {
                        "tool_name": tool_name,
                        "data": result,
                        "message": f"工具 {tool_name} 执行成功",
                    })
                except Exception as e:
                    yield _sse_event("tool_result", {
                        "tool_name": tool_name,
                        "error": str(e),
                        "message": f"工具 {tool_name} 执行失败: {str(e)}",
                    })
                    result = {"error": str(e)}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_val["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                })

        if not has_tool_call:
            yield _sse_event("complete", {})
            return

    # Exceeded max rounds
    yield _sse_event("complete", {})


@chat_router.post("/chat/completions", summary="LLM 流式对话（支持 Tool Calling）")
async def chat_completions(
    request_data: PlatformChatCompletionRequest,
    db: Session = Depends(get_db),
    _user=Depends(get_active_user),
):
    model = _find_primary_model(db)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in request_data.messages]
    return StreamingResponse(
        _stream_tool_calling_loop(model, messages, db, _user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@chat_router.post("/chat/test", summary="测试模型连接")
async def chat_test(
    request_data: PlatformChatTestRequest,
    db: Session = Depends(get_db),
    _user=Depends(get_active_user),
):
    base_url = request_data.api_base_url.strip().rstrip("/")
    if not base_url:
        raise HTTPException(status_code=400, detail="API 地址不能为空")
    url = f"{base_url}/chat/completions"

    payload = {
        "model": request_data.model_name,
        "messages": [{"role": "user", "content": "你好，请回复：测试成功"}],
        "stream": False,
        "max_tokens": 20,
    }

    headers = {
        "Authorization": f"Bearer {request_data.api_key.strip()}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code == 200:
        body = resp.json()
        reply = ""
        choices = body.get("choices") or []
        if choices:
            reply = choices[0].get("message", {}).get("content", "") or ""
        return response_200(data={
            "ok": True,
            "status_code": resp.status_code,
            "model": body.get("model", request_data.model_name),
            "reply_preview": reply.strip(),
        })

    error_text = resp.text[:500]
    return response_200(data={
        "ok": False,
        "status_code": resp.status_code,
        "error": error_text,
    })
```

- [ ] **Step 2: Restart backend and verify no import errors**

Run: `cd backend/api-server && python -c "from apps.platform.api.chat import chat_router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/api-server/apps/platform/api/chat.py
git commit -m "feat: add tool calling loop to platform chat endpoint"
```

---

### Task 4: Chat API Endpoint Uses Token Auth

**Files:**
- Modify: `backend/api-server/apps/platform/api/chat.py` — the `chat_completions` endpoint already uses `get_active_user` dependency for JWT auth

No additional changes needed for this task. The endpoint is already protected with `_user=Depends(get_active_user)`.

- [ ] **Step 1: Verify auth is correct**

Run: `curl -s http://127.0.0.1:8001/api/v1/platform/chat/completions -X POST -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"test"}]}'`
Expected: `{"code": 4001, "msg": "Not authenticated", ...}`

- [ ] **Step 2: Commit**

(No changes to commit for this task.)

---

### Task 5: Unit Tests for Tool Registry

**Files:**
- Create: `backend/api-server/tests/test_tool_registry.py`

- [ ] **Step 1: Write the tests**

```python
import pytest
from libs.tool_registry import ToolDefinition, ToolRegistry


async def _fake_execute(db, arguments, user):
    return {"result": "ok", "args": arguments}


def test_register_tool():
    registry = ToolRegistry()
    tool = ToolDefinition(
        name="test_tool",
        description="A test tool",
        parameters={"type": "object", "properties": {}},
        execute=_fake_execute,
    )
    registry.register(tool)
    assert "test_tool" in registry._tools
    assert registry.get("test_tool") is tool


def test_register_duplicate_raises():
    registry = ToolRegistry()
    tool = ToolDefinition(name="dup", description="x", parameters={}, execute=_fake_execute)
    registry.register(tool)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool)


def test_to_openai_tools_format():
    registry = ToolRegistry()
    tool = ToolDefinition(
        name="my_func",
        description="Does something",
        parameters={"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]},
        execute=_fake_execute,
    )
    registry.register(tool)
    openai_tools = registry.to_openai_tools()
    assert len(openai_tools) == 1
    assert openai_tools[0]["type"] == "function"
    assert openai_tools[0]["function"]["name"] == "my_func"
    assert openai_tools[0]["function"]["parameters"]["required"] == ["x"]


def test_get_all_filters_by_admin():
    registry = ToolRegistry()
    admin_tool = ToolDefinition(name="admin_only", description="x", parameters={}, execute=_fake_execute, require_admin=True)
    public_tool = ToolDefinition(name="public", description="x", parameters={}, execute=_fake_execute, require_admin=False)
    registry.register_many([admin_tool, public_tool])

    assert len(registry.get_all(admin=True)) == 2
    assert len(registry.get_all(admin=False)) == 1
    assert registry.get_all(admin=False)[0].name == "public"


@pytest.mark.asyncio
async def test_execute():
    registry = ToolRegistry()
    tool = ToolDefinition(
        name="echo",
        description="echo",
        parameters={},
        execute=_fake_execute,
    )
    registry.register(tool)
    result = await registry.execute("echo", {"x": 1}, db=None, user=None)
    assert result["result"] == "ok"
    assert result["args"] == {"x": 1}


@pytest.mark.asyncio
async def test_execute_unknown_tool():
    registry = ToolRegistry()
    with pytest.raises(ValueError, match="Unknown tool"):
        await registry.execute("nonexistent", {}, db=None, user=None)
```

- [ ] **Step 2: Run the tests**

Run: `cd backend/api-server && python -m pytest tests/test_tool_registry.py -v`
Expected: 6 tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/api-server/tests/test_tool_registry.py
git commit -m "test: add unit tests for tool registry"
```

---

### Task 6: Integration Test for Chat Tool Calling

**Files:**
- Create: `backend/api-server/tests/test_chat_tool_calling.py`

- [ ] **Step 1: Write the integration test**

```python
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from libs.tool_registry import ToolDefinition, tool_registry


async def _fake_execute(db, arguments, user):
    return {"items": [{"id": 1, "name": "test"}], "total": 1}


@pytest.fixture(autouse=True)
def setup_tools():
    tool_registry._tools.clear()
    tool = ToolDefinition(
        name="list_datasets",
        description="List datasets",
        parameters={"type": "object", "properties": {}},
        execute=_fake_execute,
        require_admin=True,
    )
    tool_registry.register(tool)
    yield
    tool_registry._tools.clear()


def make_chunk(content=None, tool_calls=None):
    delta = {}
    if content:
        delta["content"] = content
    if tool_calls:
        delta["tool_calls"] = tool_calls
    return {"choices": [{"delta": delta, "index": 0}]}


def make_llm_text_stream(*texts):
    """Simulate a simple text stream (no tool calls)."""
    async def stream(url, json, headers, **kwargs):
        class FakeResponse:
            status_code = 200
            async def aiter_lines(self):
                for t in texts:
                    chunk = make_chunk(content=t)
                    yield f"data: {json.dumps(chunk)}"
                yield "data: [DONE]"
            async def aread(self):
                return b""
        return FakeResponse()
    return stream


def make_llm_tool_stream(tool_name, args_dict):
    """Simulate a stream that returns a single tool_call."""
    args_str = json.dumps(args_dict)
    async def stream(url, json, headers, **kwargs):
        class FakeResponse:
            status_code = 200
            async def aiter_lines(self):
                yield f"data: {json.dumps(make_chunk(tool_calls=[{
                    'index': 0, 'id': 'call_1',
                    'function': {'name': tool_name, 'arguments': args_str},
                }]))}"
                yield "data: [DONE]"
            async def aread(self):
                return b""
        return FakeResponse()
    return stream


def make_llm_summary_stream(summary_text):
    """Simulate a follow-up summary stream."""
    async def stream(url, json, headers, **kwargs):
        class FakeResponse:
            status_code = 200
            async def aiter_lines(self):
                for word in summary_text.split():
                    yield f"data: {json.dumps(make_chunk(content=word + ' '))}"
                yield "data: [DONE]"
            async def aread(self):
                return b""
        return FakeResponse()
    return stream


@pytest.mark.asyncio
async def test_chat_text_only():
    """Pure text conversation — no tool calls."""
    from apps.platform.api.chat import _stream_tool_calling_loop
    from apps.platform.models import PlatformModelApiSetting

    model = PlatformModelApiSetting(
        model_name="test-model",
        api_base_url="http://fake",
        api_key="k",
        is_primary=True,
        is_active=True,
    )

    # LLM just returns text
    with patch("httpx.AsyncClient.stream", new=make_llm_text_stream("Hello", " world!")):
        events = []
        async for event_str in _stream_tool_calling_loop(model, [
            {"role": "user", "content": "hi"},
        ], db=None, user=None):
            data_str = event_str.replace("data: ", "").strip()
            if data_str:
                events.append(json.loads(data_str))

    output_contents = [e["content"] for e in events if e["type"] == "output_msg"]
    assert "".join(output_contents).strip() == "Hello world!"
    assert any(e["type"] == "complete" for e in events)


@pytest.mark.asyncio
async def test_chat_with_tool_call():
    """LLM returns a tool call → tool executes → summary."""
    from apps.platform.api.chat import _stream_tool_calling_loop
    from apps.platform.models import PlatformModelApiSetting

    model = PlatformModelApiSetting(
        model_name="test-model",
        api_base_url="http://fake",
        api_key="k",
        is_primary=True,
        is_active=True,
    )

    # First request returns tool_call, second (summary) returns text
    call_count = [0]

    async def two_phase_stream(url, json, headers, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # Tool call phase
            async def lines():
                args = json.dumps({"dataset_type": "variome"})
                chunk = make_chunk(tool_calls=[{
                    "index": 0, "id": "call_1",
                    "function": {"name": "list_datasets", "arguments": args},
                }])
                yield f"data: {json.dumps(chunk)}"
                yield "data: [DONE]"
            class Resp:
                status_code = 200
                @staticmethod
                async def aiter_lines():
                    async for l in lines(): yield l
                @staticmethod
                async def aread(): return b""
            return Resp()
        else:
            # Summary phase
            async def lines():
                for w in ["找到", "1", "个", "数据集"]:
                    yield f"data: {json.dumps(make_chunk(content=w))}"
                yield "data: [DONE]"
            class Resp:
                status_code = 200
                @staticmethod
                async def aiter_lines():
                    async for l in lines(): yield l
                @staticmethod
                async def aread(): return b""
            return Resp()

    with patch("httpx.AsyncClient.stream", new=two_phase_stream):
        events = []
        async for event_str in _stream_tool_calling_loop(model, [
            {"role": "user", "content": "有哪些变异组数据集？"},
        ], db=None, user=None):
            data_str = event_str.replace("data: ", "").strip()
            if data_str:
                events.append(json.loads(data_str))

    event_types = [e["type"] for e in events]
    assert "tool_call" in event_types
    assert "tool_result" in event_types
    assert "output_msg" in event_types
    assert "complete" in event_types

    tool_call_event = next(e for e in events if e["type"] == "tool_call")
    assert tool_call_event["tool_name"] == "list_datasets"
    assert tool_call_event["arguments"] == {"dataset_type": "variome"}

    tool_result_event = next(e for e in events if e["type"] == "tool_result")
    assert tool_result_event["data"]["total"] == 1
```

- [ ] **Step 2: Run the integration tests**

Run: `cd backend/api-server && python -m pytest tests/test_chat_tool_calling.py -v`
Expected: 2 tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/api-server/tests/test_chat_tool_calling.py
git commit -m "test: add integration tests for chat tool calling"
```

---

### Task 7: Frontend — Clean Up Old Endpoints & Fix Chat URL

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/config/chat-endpoints.ts`
- Modify: `frontend/admin-web/apps/web-antd/.env.development`

- [ ] **Step 1: Rewrite chat-endpoints.ts**

```typescript
// src/config/chat-endpoints.ts
export interface ChatEndpointConfig {
  url: string;
  inputType: 'file' | 'text';
  supportsFileUpload: boolean;
  fileFieldName?: string;
  maxFileSize?: number;
  acceptedFileTypes?: string[];
  timeoutMs?: number;
}

export const CHAT_ENDPOINTS: Record<string, ChatEndpointConfig> = {
  default: {
    url: '/api/v1/platform/chat/completions',
    inputType: 'text',
    supportsFileUpload: false,
    timeoutMs: 10800000, // 3-hour timeout
  },
};

export function getChatEndpointConfig(_path: string): ChatEndpointConfig {
  return CHAT_ENDPOINTS.default;
}
```

- [ ] **Step 2: Set chatApiURL to empty in .env.development**

Add to `.env.development`:
```
VITE_GLOB_CHAT_API_URL=
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend/admin-web && pnpm run check:type 2>&1 | tail -5`
Expected: No new errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/config/chat-endpoints.ts frontend/admin-web/apps/web-antd/.env.development
git commit -m "refactor: remove old Dify endpoints, point chat to /platform/chat/completions"
```

---

### Task 8: Frontend — Extend SSE Types for Tool Events

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/views/agent/chat/types/chat.ts`

- [ ] **Step 1: Add tool_call and tool_result to types**

Edit `chat.ts`:

```typescript
// In StreamMessageType (line 5):
export type StreamMessageType =
  | 'start'
  | 'output_msg'
  | 'execution_msg'
  | 'break'
  | 'interrupt'
  | 'tool_call'     // NEW
  | 'tool_result'   // NEW
  | 'complete'

// In ChatMessage type (line 29):
export interface ChatMessage {
  id: string
  type: 'output' | 'execution' | 'user' | 'tool_call' | 'tool_result'  // extended
  content: string
  nodeName?: string
  timestamp: number
  conversationId?: string
  toolPayload?: ToolResultPayload  // NEW — carries tool result data
}

// Add new interface (after ChatMessage):
export interface ToolResultPayload {
  tool_name: string
  data?: Record<string, any>
  error?: string
  message?: string
}

// In ChatMessageValidation (line 39):
type: { required: true, enum: ['output', 'execution', 'user', 'tool_call', 'tool_result'] as const },

// In isSSEMessage (line 198):
return (
  ['start', 'output_msg', 'execution_msg', 'break', 'interrupt', 'tool_call', 'tool_result', 'complete'] as const
).includes(candidate.type as StreamMessageType)

// In isChatMessage (line 210):
(candidate.type === 'output' || candidate.type === 'execution' || candidate.type === 'user'
  || candidate.type === 'tool_call' || candidate.type === 'tool_result') &&
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend/admin-web && pnpm run check:type 2>&1 | tail -5`
Expected: No new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/views/agent/chat/types/chat.ts
git commit -m "feat: extend chat types with tool_call and tool_result events"
```

---

### Task 9: Frontend — Handle Tool Events in Stream

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/views/agent/chat/composables/useChatStream.ts`

- [ ] **Step 1: Add tool_call and tool_result handlers**

In `useChatStream.ts`, add after `handleExecution`:

```typescript
function handleToolCall(message: SSEMessage) {
  const chatMessage = toChatMessage(message, 'tool_call');
  (chatMessage as any).toolPayload = {
    tool_name: (message as any).tool_name,
    arguments: (message as any).arguments,
  };
  store.addMessageToCurrentGroup(chatMessage);
}

function handleToolResult(message: SSEMessage) {
  const chatMessage = toChatMessage(message, 'tool_result');
  (chatMessage as any).toolPayload = {
    tool_name: (message as any).tool_name,
    data: (message as any).data,
    error: (message as any).error,
    message: (message as any).message,
  };
  store.addMessageToCurrentGroup(chatMessage);
}
```

In `processStream` switch, add:
```typescript
case 'tool_call': {
  handleToolCall(payload);
  break;
}
case 'tool_result': {
  handleToolResult(payload);
  break;
}
```

- [ ] **Step 2: Also remove old stage workflow references**

Remove imports of `useAccessStore` if only used for stage workflow. Keep if used elsewhere.
Remove `proceedToNextStage` and `triggerNextStage` functions if no longer needed.

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend/admin-web && pnpm run check:type 2>&1 | tail -5`
Expected: No new errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/views/agent/chat/composables/useChatStream.ts
git commit -m "feat: handle tool_call and tool_result events in SSE stream"
```

---

### Task 10: Frontend — Create QueryToolResultCard Component

**Files:**
- Create: `frontend/admin-web/apps/web-antd/src/views/agent/chat/components/QueryToolResultCard.vue`

- [ ] **Step 1: Create the component**

```vue
<script setup lang="ts">
import { computed } from 'vue';
import { Descriptions, Table, Tag } from 'ant-design-vue';
import type { ToolResultPayload } from '#/views/agent/chat/types/chat';

defineOptions({ name: 'QueryToolResultCard' });

const props = defineProps<{
  payload: ToolResultPayload;
}>();

const hasError = computed(() => !!props.payload.error);
const hasData = computed(() => !!props.payload.data && !props.payload.error);

const previewRows = computed(() => {
  const data = props.payload.data;
  if (!data) return [];
  // If data has items array, show as table
  if (data.items && Array.isArray(data.items)) {
    return data.items.slice(0, 20);
  }
  // If data has preview (VCF text), show as single row
  if (data.preview && typeof data.preview === 'string') {
    return [{ preview: data.preview.slice(0, 2000) }];
  }
  // If data has count, show summary
  if (typeof data.count === 'number') {
    return [{ count: data.count, preview: data.preview?.slice(0, 1000) || `共 ${data.count} 条记录` }];
  }
  return [data];
});

const columns = computed(() => {
  if (previewRows.value.length === 0) return [];
  return Object.keys(previewRows.value[0]).map((key) => ({
    title: key,
    dataIndex: key,
    key,
    ellipsis: true,
  }));
});
</script>

<template>
  <div class="tool-result-card">
    <div class="tool-result-header">
      <Tag :color="hasError ? 'red' : 'blue'">{{ payload.tool_name }}</Tag>
      <span v-if="payload.message" class="tool-result-msg">{{ payload.message }}</span>
    </div>

    <div v-if="hasError" class="tool-result-error">
      {{ payload.error }}
    </div>

    <div v-else-if="hasData && previewRows.length > 0" class="tool-result-body">
      <Table
        :columns="columns"
        :data-source="previewRows"
        :pagination="false"
        size="small"
        bordered
      />
      <div v-if="payload.data?.total && payload.data.total > 20" class="tool-result-truncated">
        仅显示前 20 条，共 {{ payload.data.total }} 条
      </div>
    </div>
  </div>
</template>

<style scoped>
.tool-result-card {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: 8px;
  padding: 12px;
  margin: 4px 0;
}

.tool-result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.tool-result-msg {
  font-size: 13px;
  color: #666;
}

.tool-result-error {
  color: #ff4d4f;
  background: #fff2f0;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 13px;
}

.tool-result-body {
  overflow: auto;
}

.tool-result-truncated {
  text-align: center;
  color: #999;
  font-size: 12px;
  margin-top: 4px;
  padding: 4px 0;
}
</style>
```

- [ ] **Step 2: Verify component imports**

Run: `cd frontend/admin-web && pnpm run check:type 2>&1 | tail -5`
Expected: No new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/views/agent/chat/components/QueryToolResultCard.vue
git commit -m "feat: add QueryToolResultCard for displaying tool results in chat"
```

---

### Task 11: Frontend — Integrate QueryToolResultCard in OutputPanel

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/views/agent/chat/components/OutputPanel.vue`

- [ ] **Step 1: Import and then render tool_result messages as cards rather than text.**

In `OutputPanel.vue`:

Import the component:
```typescript
import QueryToolResultCard from './QueryToolResultCard.vue';
```

In the template, for each message in a group, check if it's a `tool_result` or `tool_call` type and render accordingly. The key change is inside the BubbleList slot that renders individual messages — add a conditional:

```vue
<template v-for="msg in group.messages" :key="msg.id">
  <QueryToolResultCard
    v-if="msg.type === 'tool_result' && msg.toolPayload"
    :payload="msg.toolPayload"
  />
  <div v-else-if="msg.type === 'tool_call'" class="tool-call-status">
    正在调用 {{ (msg as any).toolPayload?.tool_name }} ...
  </div>
  <!-- existing text rendering for output/execution/user types -->
</template>
```

Also add the `tool-call-status` CSS:
```css
.tool-call-status {
  color: #1677ff;
  font-style: italic;
  padding: 4px 8px;
  font-size: 13px;
}
```

If `OutputPanel.vue` uses `BubbleList` without per-message slot control, simply append `QueryToolResultCard` components after the BubbleList by iterating `tool_result` messages from `group.messages`.

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend/admin-web && pnpm run check:type 2>&1 | tail -5`
Expected: No new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/views/agent/chat/components/OutputPanel.vue
git commit -m "feat: render tool_result and tool_call messages in chat output panel"
```

---

### Task 12: Frontend — Update Store for Tool Messages

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/store/modules/agent-chat.ts`

- [ ] **Step 1: Update store to accept tool_call and tool_result types**

In `agent-chat.ts`, update the `addMessageToCurrentGroup` method's group type logic to handle `tool_call` and `tool_result` message types without breaking the group categorization. The existing logic that sets `group.type = message.type` already works — the new types will be stored correctly.

No significant structural changes needed to the store — `ChatMessage` already carries `toolPayload`, and `addMessageToCurrentGroup` just pushes messages into groups.

The only change: update any `SessionStatus` transitions that should account for tool messages (tool messages are intermediate, not final).

No changes needed — current store handles this generically.

- [ ] **Step 1: Verify no changes needed, run type check**

Run: `cd frontend/admin-web && pnpm run check:type 2>&1 | tail -5`
Expected: No new errors.

---

### Task 13: End-to-End Manual Verification

- [ ] **Step 1: Restart backend**

```bash
cd backend/api-server
# Kill existing uvicorn and restart
lsof -i :8001 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null
source .venv/bin/activate 2>/dev/null || true
nohup uvicorn main:app --host 0.0.0.0 --port 8001 --reload --workers 5 > /tmp/uvicorn-8001.log 2>&1 &
```

- [ ] **Step 2: Restart frontend**

```bash
cd frontend/admin-web
pnpm dev:antd
```

- [ ] **Step 3: Test with curl — text only query**

Get token:
```bash
TOKEN=$(curl -s http://127.0.0.1:8001/api/v1/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123456"}' | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['access_token'])")
```

Test chat:
```bash
curl -s http://127.0.0.1:8001/api/v1/platform/chat/completions -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"messages":[{"role":"user","content":"你好，你能做什么？"}]}' --max-time 30
```
Expected: SSE stream with `output_msg` + `complete` events.

- [ ] **Step 4: Test with prompt that triggers tool_call**

```bash
curl -s http://127.0.0.1:8001/api/v1/platform/chat/completions -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"messages":[{"role":"user","content":"有哪些可用的数据集？请用 list_datasets 查询"}]}' --max-time 60
```
Expected: SSE stream with `tool_call` + `tool_result` + `output_msg`(summary) + `complete`.

- [ ] **Step 5: Open frontend chat page**

Navigate to `http://127.0.0.1:5666/agent/chat` and verify:
- Chat input works
- Tool call status appears when LLM triggers a tool
- Data card renders when tool result comes back
- LLM summary follows the data card
