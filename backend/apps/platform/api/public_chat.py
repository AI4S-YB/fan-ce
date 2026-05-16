"""Public AI chat endpoint — no auth, rate-limited, public-data-only tools."""

import json
import time
from collections import defaultdict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from db.database import get_db
from libs.responses.response import response_200
from libs.tool_registry import tool_registry
from .chat import _build_payload, _extract_text_from_chunk, _extract_tool_calls_from_chunk, _sse_event, _find_primary_model
from ..models import PlatformSiteSetting

public_chat_router = APIRouter(tags=["public:chat:公共AI对话"])

PUBLIC_SYSTEM_PROMPT = """你是一个生物信息学数据助手，帮助用户探索和分析公开的组学数据。你只能使用提供的工具来查询公开可用的数据集。

## 可用能力

1. **数据集发现** — 浏览和了解公开数据集
2. **基因组 (Genome)** — 搜索基因、获取序列
3. **功能注释** — GO、KEGG、InterPro 注释查询
4. **转录组 (Transcriptome)** — 样本列表、表达矩阵查询
5. **表型组 (Phenome)** — 性状列表、表型值查询
6. **变异组 (Variome)** — 变异样本、区域变异查询
7. **数据血缘** — 查找关联数据集

## 查询指南

- 用户通常不知道数据集 ID，用 list_datasets 搜索
- 查询前先了解可用的样本/性状名称
- 表达矩阵可能很大，先 list 再指定基因素材查询
- 跨数据域用 get_related_datasets 导航

用中文回答，数据结果清晰总结，优先用表格呈现。"""

# ── Simple in-memory rate limiter ──
RATE_LIMIT_WINDOW = 60       # seconds
RATE_LIMIT_MAX_REQUESTS = 10  # max requests per window per IP

_rate_buckets: dict[str, list[float]] = defaultdict(list)

def _check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    bucket = _rate_buckets[client_ip]
    # Remove expired entries
    bucket[:] = [t for t in bucket if now - t < RATE_LIMIT_WINDOW]
    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    bucket.append(now)
    return True

MAX_TOOL_ROUNDS = 3


@public_chat_router.get("/status", summary="公共AI对话状态")
def public_chat_status(db: Session = Depends(get_db)):
    """Return whether public AI chat is enabled."""
    site = db.query(PlatformSiteSetting).first()
    enabled = bool(site and site.public_ai_chat_enabled)
    return response_200(data={"enabled": enabled})


async def _public_stream_loop(model, messages: list[dict], db: Session):
    """Streaming tool-calling loop using only public-safe tools."""
    tools = tool_registry.to_openai_tools(admin=False)
    tool_map = {t.name: t for t in tool_registry.get_all(admin=False)}

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
                    yield _sse_event("error", {"message": f"Model error ({response.status_code})"})
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

        if accumulated_tool_calls:
            has_tool_call = True
            assistant_msg: dict = {"role": "assistant"}
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
                    result = await tool_registry.execute(tool_name, args, db=db, user=None)
                    yield _sse_event("tool_result", {"tool_name": tool_name, "data": result})
                except Exception as e:
                    yield _sse_event("tool_result", {"tool_name": tool_name, "error": str(e)})
                    result = {"error": str(e)}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_val["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                })

        if not has_tool_call:
            yield _sse_event("complete", {})
            return

    yield _sse_event("complete", {})


@public_chat_router.post("/completions", summary="公共AI流式对话")
async def public_chat_completions(
    request: Request,
    db: Session = Depends(get_db),
):
    # Check global switch
    site = db.query(PlatformSiteSetting).first()
    if not site or not site.public_ai_chat_enabled:
        raise HTTPException(status_code=403, detail="Public AI chat is disabled")

    # Rate limit by client IP
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded ({RATE_LIMIT_MAX_REQUESTS}/min). Please wait.")

    # Read JSON body manually (Pydantic model not required for public)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    messages_data = body.get("messages") or []
    if not messages_data:
        raise HTTPException(status_code=400, detail="messages is required")

    model = _find_primary_model(db)
    messages = [{"role": "system", "content": PUBLIC_SYSTEM_PROMPT}]
    messages += [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages_data]

    return StreamingResponse(
        _public_stream_loop(model, messages, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
