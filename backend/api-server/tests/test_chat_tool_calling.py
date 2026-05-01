import json

import httpx
import pytest
from unittest.mock import patch

from libs.tool_registry import ToolDefinition, tool_registry


async def _fake_execute(db, arguments, user):
    return {"items": [{"id": 1, "name": "test"}], "total": 1}


async def _fake_lineage_execute(db, arguments, user):
    """Simulate get_related_datasets returning a genome linked to a transcriptome."""
    return {
        "dataset_id": arguments.get("dataset_id"),
        "relations": [
            {
                "src_dataset_id": 10,
                "src_title": "月季转录组",
                "src_type": "transcriptome",
                "dst_dataset_id": 5,
                "dst_title": "月季参考基因组",
                "dst_type": "genome",
                "relation_type": "derived_from",
                "direction": "upstream",
            }
        ],
        "total": 1,
    }


async def _fake_gene_function_execute(db, arguments, user):
    """Simulate get_gene_function for a genome dataset."""
    return {
        "dataset_id": 5,
        "title": "月季参考基因组",
        "result": {
            "gene_id": arguments.get("gene_id", "unknown"),
            "go_terms": [{"id": "GO:0008150", "name": "biological_process"}],
            "kegg_pathways": [{"id": "ko00010", "name": "糖酵解"}],
            "interpro_domains": [],
            "description": "Hypothetical protein",
        },
    }


@pytest.fixture(autouse=True)
def setup_tools():
    tool_registry._tools.clear()
    tools = [
        ToolDefinition(
            name="list_datasets",
            description="搜索可用的数据集列表",
            parameters={
                "type": "object",
                "properties": {
                    "dataset_type": {"type": "string", "enum": ["genome", "transcriptome", "variome", "phenome", "generic"]},
                    "keyword": {"type": "string"},
                    "page": {"type": "integer", "default": 1},
                    "size": {"type": "integer", "default": 20},
                },
            },
            execute=_fake_execute,
            require_admin=True,
        ),
        ToolDefinition(
            name="get_related_datasets",
            description="获取数据集的关联数据集",
            parameters={
                "type": "object",
                "properties": {"dataset_id": {"type": "integer"}},
                "required": ["dataset_id"],
            },
            execute=_fake_lineage_execute,
            require_admin=True,
        ),
        ToolDefinition(
            name="get_gene_function",
            description="获取基因功能注释",
            parameters={
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "integer"},
                    "dataset_keyword": {"type": "string"},
                    "gene_id": {"type": "string"},
                    "gene_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
            execute=_fake_gene_function_execute,
            require_admin=True,
        ),
    ]
    tool_registry.register_many(tools)
    yield
    tool_registry._tools.clear()


class FakeStreamResponse:
    """A fake async-context-manager-compatible response for client.stream()."""

    def __init__(self, chunks: list[str], status_code: int = 200):
        self.status_code = status_code
        self._chunks = chunks

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def aiter_lines(self):
        for line in self._chunks:
            yield line

    async def aread(self):
        return b""


def make_chunk(content=None, tool_calls=None):
    delta = {}
    if content:
        delta["content"] = content
    if tool_calls:
        delta["tool_calls"] = tool_calls
    return {"choices": [{"delta": delta, "index": 0}]}


# ---------------------------------------------------------------------------
# httpx.AsyncClient.stream is a *synchronous* method that returns an
# async context manager (StreamContextManager).  The actual chat code does:
#
#     async with client.stream("POST", url, json=payload, headers=headers) as response:
#
# so our mock must be a regular (non-async) function that returns an object
# supporting __aenter__ / __aexit__ — i.e. a FakeStreamResponse.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_text_only():
    """Pure text conversation -- no tool calls."""
    from apps.platform.api.chat import _stream_tool_calling_loop
    from apps.platform.models import PlatformModelApiSetting

    model = PlatformModelApiSetting(
        model_name="test-model",
        api_base_url="http://fake",
        api_key="k",
        is_primary=True,
        is_active=True,
    )

    def fake_stream(self, method, url, json_data=None, headers=None, **kwargs):
        lines = []
        for t in ["Hello", " world!"]:
            chunk = make_chunk(content=t)
            lines.append(f"data: {json.dumps(chunk)}")
        lines.append("data: [DONE]")
        return FakeStreamResponse(lines)

    with patch.object(httpx.AsyncClient, "stream", new=fake_stream):
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
    """LLM returns a tool call in round 1, then a summary in round 2."""
    from apps.platform.api.chat import _stream_tool_calling_loop
    from apps.platform.models import PlatformModelApiSetting

    model = PlatformModelApiSetting(
        model_name="test-model",
        api_base_url="http://fake",
        api_key="k",
        is_primary=True,
        is_active=True,
    )

    call_count = [0]

    def two_phase_stream(self, method, url, json_data=None, headers=None, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # Round 1: LLM responds with a tool_call (no text)
            args = json.dumps({"dataset_type": "variome"})
            chunk = make_chunk(tool_calls=[{
                "index": 0, "id": "call_1",
                "function": {"name": "list_datasets", "arguments": args},
            }])
            lines = [
                f"data: {json.dumps(chunk)}",
                "data: [DONE]",
            ]
        else:
            # Round 2: LLM summarises the tool result in Chinese
            lines = []
            for w in ["找到", "1", "个", "数据集"]:
                lines.append(f"data: {json.dumps(make_chunk(content=w))}")
            lines.append("data: [DONE]")
        return FakeStreamResponse(lines)

    with patch.object(httpx.AsyncClient, "stream", new=two_phase_stream):
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


# ---------------------------------------------------------------------------
# New tests for multi-round orchestration & keyword-based resolution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_data_lineage_orchestration():
    """Multi-round orchestration: browse datasets → get lineage → query gene function.

    Simulates a user asking "月季转录组里差异表达的基因有什么功能？"
    The LLM should orchestrate across 3 rounds:
      1. list_datasets(keyword="月季", dataset_type="transcriptome")
      2. get_related_datasets(dataset_id=10) → finds genome dataset 5
      3. get_gene_function(dataset_id=5, gene_id="RhNAC1")
    """
    from apps.platform.api.chat import _stream_tool_calling_loop
    from apps.platform.models import PlatformModelApiSetting

    model = PlatformModelApiSetting(
        model_name="test-model",
        api_base_url="http://fake",
        api_key="k",
        is_primary=True,
        is_active=True,
    )

    call_count = [0]

    def multi_round_stream(self, method, url, json_data=None, headers=None, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # Round 1: LLM calls list_datasets to find transcriptome datasets
            args = json.dumps({"keyword": "月季", "dataset_type": "transcriptome"})
            chunk = make_chunk(tool_calls=[{
                "index": 0, "id": "call_discover",
                "function": {"name": "list_datasets", "arguments": args},
            }])
            return FakeStreamResponse([
                f"data: {json.dumps(chunk)}",
                "data: [DONE]",
            ])
        elif call_count[0] == 2:
            # Round 2: LLM calls get_related_datasets to find upstream genome
            args = json.dumps({"dataset_id": 10})
            chunk = make_chunk(tool_calls=[{
                "index": 0, "id": "call_lineage",
                "function": {"name": "get_related_datasets", "arguments": args},
            }])
            return FakeStreamResponse([
                f"data: {json.dumps(chunk)}",
                "data: [DONE]",
            ])
        else:
            # Round 3: LLM calls get_gene_function on the genome dataset
            args = json.dumps({"dataset_id": 5, "gene_id": "RhNAC1"})
            chunk = make_chunk(tool_calls=[{
                "index": 0, "id": "call_func",
                "function": {"name": "get_gene_function", "arguments": args},
            }])
            return FakeStreamResponse([
                f"data: {json.dumps(chunk)}",
                "data: [DONE]",
            ])

    with patch.object(httpx.AsyncClient, "stream", new=multi_round_stream):
        events = []
        async for event_str in _stream_tool_calling_loop(model, [
            {"role": "user", "content": "月季转录组里差异表达的RhNAC1基因有什么功能？"},
        ], db=None, user=None):
            data_str = event_str.replace("data: ", "").strip()
            if data_str:
                events.append(json.loads(data_str))

    # Verify all three rounds happened
    tool_call_names = [e["tool_name"] for e in events if e["type"] == "tool_call"]
    assert tool_call_names == ["list_datasets", "get_related_datasets", "get_gene_function"]

    # Verify the lineage result connects transcriptome → genome
    lineage_results = [e for e in events if e["type"] == "tool_result" and e["tool_name"] == "get_related_datasets"]
    assert len(lineage_results) == 1
    rel = lineage_results[0]["data"]["relations"][0]
    assert rel["src_type"] == "transcriptome"
    assert rel["dst_type"] == "genome"

    # Verify gene function result has annotations
    func_results = [e for e in events if e["type"] == "tool_result" and e["tool_name"] == "get_gene_function"]
    assert len(func_results) == 1
    assert "go_terms" in func_results[0]["data"]["result"]

    assert any(e["type"] == "complete" for e in events)


@pytest.mark.asyncio
async def test_chat_max_tool_rounds_enforced():
    """After MAX_TOOL_ROUNDS (3), the loop stops even if LLM keeps requesting tools."""
    from apps.platform.api.chat import _stream_tool_calling_loop, MAX_TOOL_ROUNDS
    from apps.platform.models import PlatformModelApiSetting

    model = PlatformModelApiSetting(
        model_name="test-model",
        api_base_url="http://fake",
        api_key="k",
        is_primary=True,
        is_active=True,
    )

    def always_tool_stream(self, method, url, json_data=None, headers=None, **kwargs):
        args = json.dumps({"keyword": "test"})
        chunk = make_chunk(tool_calls=[{
            "index": 0, "id": "call_loop",
            "function": {"name": "list_datasets", "arguments": args},
        }])
        return FakeStreamResponse([
            f"data: {json.dumps(chunk)}",
            "data: [DONE]",
        ])

    with patch.object(httpx.AsyncClient, "stream", new=always_tool_stream):
        events = []
        async for event_str in _stream_tool_calling_loop(model, [
            {"role": "user", "content": "无限循环测试"},
        ], db=None, user=None):
            data_str = event_str.replace("data: ", "").strip()
            if data_str:
                events.append(json.loads(data_str))

    tool_call_count = sum(1 for e in events if e["type"] == "tool_call")
    assert tool_call_count == MAX_TOOL_ROUNDS
    assert any(e["type"] == "complete" for e in events)


@pytest.mark.asyncio
async def test_chat_tool_call_error_handling():
    """When a tool raises an exception, the error is sent as tool_result with error field."""
    from apps.platform.api.chat import _stream_tool_calling_loop, MAX_TOOL_ROUNDS
    from apps.platform.models import PlatformModelApiSetting

    tool_registry._tools.clear()

    async def _failing_execute(db, arguments, user):
        raise ValueError("模拟执行失败")

    tool_registry.register(ToolDefinition(
        name="list_datasets",
        description="List datasets",
        parameters={"type": "object", "properties": {}},
        execute=_failing_execute,
        require_admin=True,
    ))

    model = PlatformModelApiSetting(
        model_name="test-model",
        api_base_url="http://fake",
        api_key="k",
        is_primary=True,
        is_active=True,
    )

    def error_stream(self, method, url, json_data=None, headers=None, **kwargs):
        args = json.dumps({})
        chunk = make_chunk(tool_calls=[{
            "index": 0, "id": "call_err",
            "function": {"name": "list_datasets", "arguments": args},
        }])
        return FakeStreamResponse([
            f"data: {json.dumps(chunk)}",
            "data: [DONE]",
        ])

    with patch.object(httpx.AsyncClient, "stream", new=error_stream):
        events = []
        async for event_str in _stream_tool_calling_loop(model, [
            {"role": "user", "content": "查一下数据集"},
        ], db=None, user=None):
            data_str = event_str.replace("data: ", "").strip()
            if data_str:
                events.append(json.loads(data_str))

    tool_results = [e for e in events if e["type"] == "tool_result"]
    # MAX_TOOL_ROUNDS rounds all fail → 3 error results
    assert len(tool_results) == MAX_TOOL_ROUNDS
    for tr in tool_results:
        assert "error" in tr
        assert "模拟执行失败" in tr["error"]
