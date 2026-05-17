# apps/platform/api/chat.py
import json

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from modules.common.depends import get_active_user
from shared.database import get_db
from shared.responses import response_200
from shared.tool_registry import tool_registry
from ..models import PlatformModelApiSetting
from ..schemas import PlatformChatCompletionRequest, PlatformChatTestRequest

chat_router = APIRouter(tags=["app:platform:LLM对话"])

SYSTEM_PROMPT = """你是一个生物信息学数据分析助手，运行在管理员工作台环境中。你可以使用提供的工具来查询以下六大领域的数据：

1. **数据集发现** — list_datasets / get_dataset_info：浏览和了解可用数据集
2. **基因组 (Genome)** — search_genes / fetch_sequence：搜索基因、获取序列
3. **功能注释** — get_gene_function / search_annotation_terms / list_genes_by_term：GO、KEGG、InterPro、BLAST 注释
4. **转录组 (Transcriptome)** — list_expression_samples / query_expression：样本列表、表达矩阵查询
5. **表型组 (Phenome)** — list_phenotype_traits / query_phenotype：性状列表、表型值查询
6. **变异组 (Variome)** — list_variant_samples / query_variants：变异样本、区域变异查询
7. **项目与种质** — list_projects / search_germplasm：项目管理、种质资源搜索
8. **数据血缘** — get_related_datasets：查找关联数据集（如转录组→参考基因组）

## 查询记忆文档

以下是你处理数据查询时应遵循的经验指南。不是硬性规则，而是帮助你更有效地完成任务的经验总结。

### 数据集解析策略

用户通常不知道数据集 ID，而是用自然语言描述需要的数据，如"月季的转录组数据"。此时应先用 list_datasets(keyword="月季", dataset_type="transcriptome") 搜索。大多数查询工具同时支持 dataset_id（精确）和 dataset_keyword（模糊匹配）。优先使用 dataset_keyword，让系统自动匹配；如果匹配到多个数据集，系统会自动查询全部并聚合结果。

### 分步探索模式

当用户意图模糊时，分步探索：
1. 用户说"看看有什么数据" → list_datasets 浏览
2. 用户指定某个数据集 → get_dataset_info 了解其能力（查询引擎、文件格式、字段）
3. 根据 query_profile 选择合适的查询工具

### 基因组→功能注释链路

用户常会追问"这个基因有什么功能"。典型链路：
1. search_genes 或 query_expression 找到基因 ID
2. get_gene_function(gene_ids=[...]) 获取 GO/KEGG/InterPro/BLAST 注释
3. 如果想了解有哪些基因共享某个功能 → list_genes_by_term

如果当前数据集是转录组但没有基因注释能力，先用 get_related_datasets 找到关联的基因组数据集，再对基因组调用 get_gene_function。

### 表型/变异查询

查询表型或变异数据前，先调用 list_phenotype_traits 或 list_variant_samples 了解可用的性状/样本名称，再用具体名称查询。避免凭空猜测性状名称。

### 表达数据查询

表达矩阵可能很大。先 list_expression_samples 了解样本，再用 query_expression 指定基因+样本切片查询，避免拉取全量矩阵。

### 跨数据集血缘导航

数据并非孤岛。转录组参考了基因组，变异数据基于参考基因组。当用户的问题跨越数据域时，用 get_related_datasets 发现上游/下游数据集。例如：用户在表达数据中发现差异基因，追问功能 → 先查血缘找到基因组 → 再查基因功能。

### 多数据集聚合

当 dataset_keyword 匹配到多个数据集时（如"月季"匹配到月季基因组、月季转录组），系统会自动查询全部。在总结时向用户说明查询了哪些数据集及其各自的结果，帮助用户理解数据来源。

用中文回答，数据结果要清晰总结。优先用表格呈现结构化数据。"""

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
