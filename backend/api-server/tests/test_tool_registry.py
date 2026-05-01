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


# ---------------------------------------------------------------------------
# New tests for domain tools
# ---------------------------------------------------------------------------


def test_all_dataset_tools_register():
    """All 16 domain tools register correctly and produce valid OpenAI tool schemas."""
    from apps.datasets.tools import DATASET_TOOLS

    registry = ToolRegistry()
    registry.register_many(DATASET_TOOLS)

    tool_names = {t.name for t in registry.get_all(admin=True)}
    expected = {
        "list_datasets", "get_dataset_info",
        "search_genes", "fetch_sequence",
        "get_gene_function", "search_annotation_terms", "list_genes_by_term",
        "list_expression_samples", "query_expression",
        "list_phenotype_traits", "query_phenotype",
        "list_variant_samples", "query_variants",
        "get_related_datasets",
        "list_projects",
        "search_germplasm",
    }
    assert tool_names == expected
    assert len(registry.get_all(admin=True)) == 16


def test_all_tools_have_valid_openai_schema():
    """Every tool produces a valid OpenAI function-calling schema."""
    from apps.datasets.tools import DATASET_TOOLS

    for tool in DATASET_TOOLS:
        schema = tool.to_openai_tool()
        assert schema["type"] == "function", f"{tool.name}: missing type"
        func = schema["function"]
        assert "name" in func, f"{tool.name}: missing name"
        assert func["name"] == tool.name
        assert "description" in func, f"{tool.name}: missing description"
        assert "parameters" in func, f"{tool.name}: missing parameters"
        params = func["parameters"]
        assert params["type"] == "object", f"{tool.name}: parameters.type != object"


def test_query_tools_accept_dataset_keyword():
    """All data-query tools accept dataset_keyword for keyword-based resolution."""
    from apps.datasets.tools import DATASET_TOOLS

    query_tool_names = {
        "search_genes", "fetch_sequence",
        "get_gene_function", "search_annotation_terms", "list_genes_by_term",
        "list_expression_samples", "query_expression",
        "list_phenotype_traits", "query_phenotype",
        "list_variant_samples", "query_variants",
    }

    for tool in DATASET_TOOLS:
        if tool.name not in query_tool_names:
            continue
        props = tool.parameters.get("properties", {})
        assert "dataset_keyword" in props, (
            f"{tool.name}: query tools must accept dataset_keyword"
        )


def test_discovery_tools_are_present():
    """list_datasets and get_dataset_info form the discovery layer."""
    from apps.datasets.tools import DATASET_TOOLS

    tool_map = {t.name: t for t in DATASET_TOOLS}
    assert "list_datasets" in tool_map
    assert "get_dataset_info" in tool_map
    assert tool_map["list_datasets"].require_admin is True
    assert tool_map["get_dataset_info"].require_admin is True
