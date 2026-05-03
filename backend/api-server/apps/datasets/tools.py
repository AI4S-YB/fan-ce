# apps/datasets/tools.py
"""Domain-specific tools for LLM function calling.

Each tool accepts dataset_id or dataset_keyword for flexible dataset resolution.
Query tools query ALL matching datasets when keyword matches multiple.
"""
import json
import re
from types import SimpleNamespace

from fastapi import HTTPException

from apps.datasets.adapters.registry import dataset_adapter_registry
from apps.datasets.models import DatasetRegistry
from apps.datasets.services import dataset_domain_service
from libs.tool_registry import ToolDefinition, tool_registry


# ---------------------------------------------------------------------------
# Dataset resolution helpers
# ---------------------------------------------------------------------------

def _resolve_datasets(db, arguments: dict, user, default_type: str = None) -> list[dict]:
    """Resolve datasets by dataset_id or dataset_keyword.

    Returns a list of dataset dicts (may be empty).
    Raises HTTPException if neither id nor keyword provided.
    """
    dataset_id = arguments.get("dataset_id")
    dataset_keyword = arguments.get("dataset_keyword")

    if dataset_id:
        ds = dataset_domain_service.get_dataset(db=db, dataset_id=dataset_id, user=user)
        return [ds]

    if dataset_keyword:
        kw = dataset_keyword.strip()

        # Try exact dataset_code match first (e.g., "ds-16", "DS-16")
        ds_match = db.query(DatasetRegistry).filter(
            DatasetRegistry.dataset_code == kw,
        ).first()
        if ds_match:
            return [dataset_domain_service.get_dataset(db=db, dataset_id=ds_match.id, user=user)]

        # Try extracting numeric ID from patterns like "ds-16", "数据集16", "#16"
        id_match = re.search(r"(?:ds[-_\s]*)?(\d+)", kw, re.IGNORECASE)
        if id_match:
            num_id = int(id_match.group(1))
            ds = db.query(DatasetRegistry).filter(
                DatasetRegistry.id == num_id,
            ).first()
            if ds:
                return [dataset_domain_service.get_dataset(db=db, dataset_id=ds.id, user=user)]

        # Fall back to name-based search
        result = dataset_domain_service.list_datasets(
            db=db,
            request_data=SimpleNamespace(
                project_id=0, team_id=0, page=1, size=20,
                dataset_id=None, name=kw,
                dataset_type=None, lifecycle_state=None, visibility=None,
            ),
            user=user,
        )
        return result.get("dataList", [])

    if default_type:
        result = dataset_domain_service.list_datasets(
            db=db,
            request_data=SimpleNamespace(
                project_id=0, team_id=0, page=1, size=50,
                dataset_id=None, name=None,
                dataset_type=default_type, lifecycle_state=None, visibility=None,
            ),
            user=user,
        )
        items = result.get("dataList", [])
        if not items:
            raise HTTPException(status_code=404, detail=f"未找到类型为 {default_type} 的数据集")
        return items

    raise HTTPException(status_code=400, detail="请提供 dataset_id 或 dataset_keyword 指定数据集")


def _build_adapter_payload(dataset: dict) -> dict:
    """Build a dataset payload suitable for dataset_adapter_registry.execute()."""
    return {
        "id": dataset["id"],
        "dataset_code": dataset.get("dataset_code", ""),
        "title": dataset.get("title", ""),
        "dataset_type": dataset.get("dataset_type", ""),
        "version": dataset.get("version", ""),
        "query_profile": dataset.get("query_profile", {}),
        "query_adapter": dataset.get("query_adapter", {}),
        "assets": dataset.get("assets") or [],
        "selected_version": dataset.get("selected_version"),
        "published_version": dataset.get("published_version"),
    }


def _query_all_datasets(db, arguments, user, operation: str, params: dict, default_type: str = None) -> dict:
    """Execute an adapter operation against all resolved datasets.

    Returns single result if 1 dataset, or aggregated results if multiple.
    """
    datasets = _resolve_datasets(db, arguments, user, default_type=default_type)

    if not datasets:
        raise HTTPException(status_code=404, detail="未找到匹配的数据集，请尝试使用 list_datasets 查看可用数据集")

    results = []
    for ds in datasets:
        payload = _build_adapter_payload(ds)
        try:
            result = dataset_adapter_registry.execute(
                dataset_payload=payload,
                operation=operation,
                params=params,
            )
            results.append({
                "dataset_id": ds["id"],
                "dataset_code": ds.get("dataset_code", ""),
                "title": ds.get("title", ""),
                "dataset_type": ds.get("dataset_type", ""),
                "result": result.get("data"),
            })
        except HTTPException as e:
            results.append({
                "dataset_id": ds["id"],
                "dataset_code": ds.get("dataset_code", ""),
                "title": ds.get("title", ""),
                "error": str(e.detail),
            })

    if len(results) == 1:
        return results[0]
    return {"searched_datasets": len(datasets), "results": results}


# ---------------------------------------------------------------------------
# Tool execute functions
# ---------------------------------------------------------------------------

async def _execute_list_datasets(db, arguments: dict, user) -> dict:
    dataset_type = arguments.get("dataset_type")
    keyword = arguments.get("keyword")
    page = arguments.get("page", 1)
    size = arguments.get("size", 20)

    result = dataset_domain_service.list_datasets(
        db=db,
        request_data=SimpleNamespace(
            project_id=0, team_id=0, page=page, size=size,
            dataset_id=None, name=keyword, dataset_type=dataset_type,
            lifecycle_state=None, visibility=None,
        ),
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
            "description_md": item.get("description_md", ""),
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
        "description_md": dataset.get("description_md", ""),
        "query_profile": dataset.get("query_profile", {}),
        "query_adapter": dataset.get("query_adapter", {}),
    }


async def _execute_search_genes(db, arguments: dict, user) -> dict:
    params = {}
    for key in ("keyword", "gene_keyword", "chrom", "start", "end", "strand", "family", "page", "size"):
        if key in arguments and arguments[key] is not None:
            params[key] = arguments[key]
    return _query_all_datasets(db, arguments, user, "search_genes", params, default_type="genome")


async def _execute_fetch_sequence(db, arguments: dict, user) -> dict:
    params = {}
    region = arguments.get("region", "")
    if region:
        # Parse "Chr1:1000-2000" format
        parts = region.replace(":", " ").replace("-", " ").split()
        if len(parts) >= 1:
            params["seq_id"] = parts[0]
        if len(parts) >= 2:
            params["start"] = int(parts[1])
        if len(parts) >= 3:
            params["end"] = int(parts[2])
    seq_id = arguments.get("seq_id")
    if seq_id:
        params["seq_id"] = seq_id
    params["start"] = arguments.get("start", params.get("start"))
    params["end"] = arguments.get("end", params.get("end"))
    return _query_all_datasets(db, arguments, user, "fetch", params, default_type="genome")


async def _execute_get_gene_function(db, arguments: dict, user) -> dict:
    gene_ids = arguments.get("gene_ids", [])
    if not gene_ids:
        # Try single gene_id
        gene_id = arguments.get("gene_id")
        if gene_id:
            gene_ids = [gene_id]
        else:
            raise HTTPException(status_code=400, detail="请提供 gene_ids 或 gene_id")
    # Query first gene_id for summary
    params = {"gene_id": str(gene_ids[0])}
    return _query_all_datasets(db, arguments, user, "gene_function_summary", params)


async def _execute_search_annotation_terms(db, arguments: dict, user) -> dict:
    params = {}
    for key in ("term_source", "keyword", "term_id", "limit"):
        if key in arguments and arguments[key] is not None:
            params[key] = arguments[key]
    return _query_all_datasets(db, arguments, user, "term_lookup", params)


async def _execute_list_genes_by_term(db, arguments: dict, user) -> dict:
    params = {
        "term_source": arguments["term_source"],
        "term_id": arguments["term_id"],
    }
    if "page" in arguments:
        params["page"] = arguments["page"]
    if "size" in arguments:
        params["size"] = arguments["size"]
    return _query_all_datasets(db, arguments, user, "term_gene_list", params)


async def _execute_list_expression_samples(db, arguments: dict, user) -> dict:
    return _query_all_datasets(db, arguments, user, "samples_list", {}, default_type="transcriptome")


async def _execute_query_expression(db, arguments: dict, user) -> dict:
    params = {}
    for key in ("genes", "samples", "data_type"):
        if key in arguments and arguments[key] is not None:
            params[key] = arguments[key]
    return _query_all_datasets(db, arguments, user, "matrix_slice", params, default_type="transcriptome")


async def _execute_list_phenotype_traits(db, arguments: dict, user) -> dict:
    return _query_all_datasets(db, arguments, user, "trait_list", {}, default_type="phenome")


async def _execute_query_phenotype(db, arguments: dict, user) -> dict:
    traits = arguments.get("traits", [])
    if not traits:
        trait = arguments.get("trait")
        traits = [trait] if trait else []
    samples = arguments.get("samples", [])

    # Try multi_trait_query for multiple traits
    if len(traits) >= 1:
        params = {"trait_codes": traits}
        if samples:
            params["plot_ids"] = samples
        return _query_all_datasets(db, arguments, user, "multi_trait_query", params, default_type="phenome")

    # Single trait
    if traits:
        return _query_all_datasets(db, arguments, user, "trait_values", {"trait": traits[0]}, default_type="phenome")

    raise HTTPException(status_code=400, detail="请提供 traits 列表")


async def _execute_list_variant_samples(db, arguments: dict, user) -> dict:
    return _query_all_datasets(db, arguments, user, "samples_list", {}, default_type="variome")


async def _execute_query_variants(db, arguments: dict, user) -> dict:
    regions = arguments.get("regions", [])
    if not regions:
        raise HTTPException(status_code=400, detail="请提供 regions 参数，如 ['Chr1:1000-2000']")
    return _query_all_datasets(db, arguments, user, "query", {"regions": regions}, default_type="variome")


async def _execute_get_related_datasets(db, arguments: dict, user) -> dict:
    dataset_id = arguments["dataset_id"]
    result = dataset_domain_service.list_dataset_lineage(db=db, dataset_id=dataset_id, user=user)
    items = []
    for item in result.get("items", []):
        items.append({
            "src_dataset_id": item.get("src_dataset_id"),
            "src_title": item.get("src_dataset_title"),
            "src_type": item.get("src_dataset_type"),
            "dst_dataset_id": item.get("dst_dataset_id"),
            "dst_title": item.get("dst_dataset_title"),
            "dst_type": item.get("dst_dataset_type"),
            "relation_type": item.get("relation_type"),
            "direction": item.get("direction"),
        })
    return {"dataset_id": dataset_id, "relations": items, "total": len(items)}


async def _execute_list_projects(db, arguments: dict, user) -> dict:
    # Community Edition: system_project removed. Use brd_program via breeding module.
    return {"items": [], "total": 0, "page": arguments.get("page", 1), "size": arguments.get("size", 20)}


async def _execute_search_germplasm(db, arguments: dict, user) -> dict:
    keyword = arguments.get("keyword")
    taxonomy_tax_id = arguments.get("taxonomy_tax_id")
    page = arguments.get("page", 1)
    size = arguments.get("size", 20)

    from apps.breeding.schemas import BreedingGermplasmListRequest
    from apps.breeding.services import breeding_domain_service

    request_data = BreedingGermplasmListRequest(
        page=page,
        size=size,
        keyword=keyword,
        taxonomy_tax_id=taxonomy_tax_id,
    )
    result = breeding_domain_service.list_germplasms(db=db, request_data=request_data)

    items = []
    for item in result.get("items", []):
        tax = item.get("taxonomy") or {}
        items.append({
            "accession_id": item.get("accession_id"),
            "display_name": item.get("display_name"),
            "status": item.get("status"),
            "scientific_name": tax.get("scientific_name"),
            "common_name": tax.get("common_name"),
            "father_accession": item.get("father_accession"),
            "mother_accession": item.get("mother_accession"),
        })
    return {"items": items, "total": result.get("total", 0), "page": page, "size": size}


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

DATASET_TOOLS = [
    # --- Discovery ---
    ToolDefinition(
        name="list_datasets",
        description="搜索可用的数据集列表。按数据集类型和名称关键词筛选。用户提到某个数据集特征（如'月季转录组'）时使用 keyword 参数。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_type": {
                    "type": "string",
                    "enum": ["genome", "transcriptome", "variome", "phenome", "generic"],
                    "description": "数据集类型",
                },
                "keyword": {"type": "string", "description": "数据集名称或特征关键词，如'月季'、'激素'、'转录组'"},
                "page": {"type": "integer", "default": 1},
                "size": {"type": "integer", "default": 20},
            },
        },
        execute=_execute_list_datasets,
        require_admin=True,
    ),
    ToolDefinition(
        name="get_dataset_info",
        description="获取指定数据集的详细信息，包括查询引擎、文件格式、关联数据集等。",
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

    # --- Genome / Genes ---
    ToolDefinition(
        name="search_genes",
        description="在基因组数据集中搜索基因。支持按基因ID关键词、染色体位置、区域范围筛选。dataset_keyword 可用于指定如'月季基因组'。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer", "description": "数据集 ID（与 dataset_keyword 二选一）"},
                "dataset_keyword": {"type": "string", "description": "数据集关键词（与 dataset_id 二选一）"},
                "gene_keyword": {"type": "string", "description": "基因 ID 或描述关键词，如 'BRCA1'"},
                "keyword": {"type": "string", "description": "基因 ID 或描述关键词（与 gene_keyword 同义）"},
                "chrom": {"type": "string", "description": "染色体，如 'Chr1'"},
                "start": {"type": "integer", "description": "区域起始位置"},
                "end": {"type": "integer", "description": "区域结束位置"},
                "strand": {"type": "string", "enum": ["+", "-"]},
                "page": {"type": "integer", "default": 1},
                "size": {"type": "integer", "default": 20},
            },
        },
        execute=_execute_search_genes,
        require_admin=True,
    ),
    ToolDefinition(
        name="fetch_sequence",
        description="获取基因组指定区域的 DNA 序列。region 格式如 'Chr1:1000-2000'。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer", "description": "数据集 ID（与 dataset_keyword 二选一）"},
                "dataset_keyword": {"type": "string", "description": "数据集关键词（与 dataset_id 二选一）"},
                "region": {"type": "string", "description": "基因组区域，格式如 'Chr1:1000-2000'"},
                "seq_id": {"type": "string", "description": "序列 ID/染色体名"},
                "start": {"type": "integer", "description": "起始位置"},
                "end": {"type": "integer", "description": "结束位置"},
            },
        },
        execute=_execute_fetch_sequence,
        require_admin=True,
    ),

    # --- Functional Annotation ---
    ToolDefinition(
        name="get_gene_function",
        description="获取基因的功能注释信息，包括 GO、KEGG、InterPro、BLAST、基因家族和功能描述。当用户在表达数据中看到感兴趣的基因后追问功能时调用。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer", "description": "数据集 ID（与 dataset_keyword 二选一）"},
                "dataset_keyword": {"type": "string", "description": "数据集关键词（与 dataset_id 二选一）"},
                "gene_ids": {
                    "type": "array", "items": {"type": "string"},
                    "description": "基因 ID 列表，如 ['AT1G01010', 'AT1G01020']",
                },
                "gene_id": {"type": "string", "description": "单个基因 ID（与 gene_ids 二选一）"},
            },
        },
        execute=_execute_get_gene_function,
        require_admin=True,
    ),
    ToolDefinition(
        name="search_annotation_terms",
        description="搜索功能注释术语（GO/KEGG/InterPro）。可按 term_source 筛选，按关键词搜索术语名或描述。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer", "description": "数据集 ID（与 dataset_keyword 二选一）"},
                "dataset_keyword": {"type": "string", "description": "数据集关键词（与 dataset_id 二选一）"},
                "term_source": {
                    "type": "string",
                    "enum": ["go", "kegg", "interpro"],
                    "description": "术语来源：go(Gene Ontology)、kegg(KEGG通路)、interpro(蛋白结构域)",
                },
                "keyword": {"type": "string", "description": "搜索术语 ID、名称或描述的关键词"},
                "limit": {"type": "integer", "default": 20},
            },
        },
        execute=_execute_search_annotation_terms,
        require_admin=True,
    ),
    ToolDefinition(
        name="list_genes_by_term",
        description="反查某个功能注释术语关联了哪些基因。如找出所有与 'GO:0006355' 相关的基因。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer", "description": "数据集 ID（与 dataset_keyword 二选一）"},
                "dataset_keyword": {"type": "string", "description": "数据集关键词（与 dataset_id 二选一）"},
                "term_source": {
                    "type": "string",
                    "enum": ["go", "kegg", "interpro"],
                    "description": "术语来源",
                },
                "term_id": {"type": "string", "description": "术语 ID，如 'GO:0006355'"},
                "page": {"type": "integer", "default": 1},
                "size": {"type": "integer", "default": 20},
            },
            "required": ["term_source", "term_id"],
        },
        execute=_execute_list_genes_by_term,
        require_admin=True,
    ),

    # --- Transcriptome / Expression ---
    ToolDefinition(
        name="list_expression_samples",
        description="列出转录组/表达数据集中可用的样本名称。先了解有哪些样本再查询表达量。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer", "description": "数据集 ID（与 dataset_keyword 二选一）"},
                "dataset_keyword": {"type": "string", "description": "数据集关键词（与 dataset_id 二选一）"},
            },
        },
        execute=_execute_list_expression_samples,
        require_admin=True,
    ),
    ToolDefinition(
        name="query_expression",
        description="查询转录组表达矩阵。指定基因和/或样本获取表达量数据。先通过 list_expression_samples 了解可用样本。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer", "description": "数据集 ID（与 dataset_keyword 二选一）"},
                "dataset_keyword": {"type": "string", "description": "数据集关键词（与 dataset_id 二选一）"},
                "genes": {
                    "type": "array", "items": {"type": "string"},
                    "description": "要查询的基因 ID 列表",
                },
                "samples": {
                    "type": "array", "items": {"type": "string"},
                    "description": "要查询的样本名称列表",
                },
                "data_type": {
                    "type": "string",
                    "enum": ["count", "fpkm", "tpm"],
                    "description": "表达数据类型，默认 count",
                },
            },
        },
        execute=_execute_query_expression,
        require_admin=True,
    ),

    # --- Phenome ---
    ToolDefinition(
        name="list_phenotype_traits",
        description="列出表型数据集中可用的性状/指标名称。先了解有哪些性状再查询具体数据。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer", "description": "数据集 ID（与 dataset_keyword 二选一）"},
                "dataset_keyword": {"type": "string", "description": "数据集关键词（与 dataset_id 二选一）"},
            },
        },
        execute=_execute_list_phenotype_traits,
        require_admin=True,
    ),
    ToolDefinition(
        name="query_phenotype",
        description="查询表型数据。指定性状名称和/或样本获取表型值。先通过 list_phenotype_traits 了解可用性状。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer", "description": "数据集 ID（与 dataset_keyword 二选一）"},
                "dataset_keyword": {"type": "string", "description": "数据集关键词（与 dataset_id 二选一）"},
                "traits": {
                    "type": "array", "items": {"type": "string"},
                    "description": "要查询的性状名称列表",
                },
                "samples": {
                    "type": "array", "items": {"type": "string"},
                    "description": "要查询的样本/材料ID列表",
                },
            },
        },
        execute=_execute_query_phenotype,
        require_admin=True,
    ),

    # --- Variome / Variant ---
    ToolDefinition(
        name="list_variant_samples",
        description="列出变异数据集中可用的样本名称。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer", "description": "数据集 ID（与 dataset_keyword 二选一）"},
                "dataset_keyword": {"type": "string", "description": "数据集关键词（与 dataset_id 二选一）"},
            },
        },
        execute=_execute_list_variant_samples,
        require_admin=True,
    ),
    ToolDefinition(
        name="query_variants",
        description="按基因组区域查询变异数据。返回指定区域的变异位点信息。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer", "description": "数据集 ID（与 dataset_keyword 二选一）"},
                "dataset_keyword": {"type": "string", "description": "数据集关键词（与 dataset_id 二选一）"},
                "regions": {
                    "type": "array", "items": {"type": "string"},
                    "description": "基因组区域列表，格式如 ['Chr1:1000-2000', 'Chr2:5000-6000']",
                },
            },
            "required": ["regions"],
        },
        execute=_execute_query_variants,
        require_admin=True,
    ),

    # --- Lineage ---
    ToolDefinition(
        name="get_related_datasets",
        description="获取一个数据集的关联数据集（血缘关系）。例如转录组数据集可能关联到参考基因组数据集。查完表达数据后，如果用户追问基因功能，先用此工具找到关联的基因组。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer", "description": "当前数据集 ID"},
            },
            "required": ["dataset_id"],
        },
        execute=_execute_get_related_datasets,
        require_admin=True,
    ),

    # --- Projects ---
    ToolDefinition(
        name="list_projects",
        description="搜索项目列表，支持按名称或代码关键词筛选。",
        parameters={
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "项目名称或代码关键词"},
                "page": {"type": "integer", "default": 1},
                "size": {"type": "integer", "default": 20},
            },
        },
        execute=_execute_list_projects,
        require_admin=True,
    ),

    # --- Germplasm ---
    ToolDefinition(
        name="search_germplasm",
        description="搜索种质资源。支持按名称关键词、分类学 ID 筛选。",
        parameters={
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "种质名称关键词"},
                "taxonomy_tax_id": {"type": "integer", "description": "分类学 ID，用于筛选特定物种"},
                "page": {"type": "integer", "default": 1},
                "size": {"type": "integer", "default": 20},
            },
        },
        execute=_execute_search_germplasm,
        require_admin=True,
    ),
]


def register_dataset_tools():
    tool_registry.register_many(DATASET_TOOLS)
