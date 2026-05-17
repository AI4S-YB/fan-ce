import os
from fastapi import APIRouter, Query, Path, HTTPException
from omics.schemas.gene_model import *
from omics.core.gene_utils import extract_genomic_sequences
from omics.core.sqlite_utils import query_sqlite
from omics.core.path_utils import get_genome_db_path, get_genome_base_dir
from shared.responses import response_200

# 创建 APIRouter 实例
g_gene_router = APIRouter(
    prefix="/omics/gene",
    tags=["omics:genome"]
)

def build_gene_search_query(request: GeneSearchRequest):
    """构建动态基因搜索SQL查询条件"""
    conditions = []
    params = []
    
    # description字段模糊匹配 (keyword参数)
    if request.keyword and request.keyword.strip():
        conditions.append("description LIKE ?")
        params.append(f"%{request.keyword.strip()}%")
    
    # gene_id精确匹配
    if request.gene_id and request.gene_id.strip():
        conditions.append("gene_id = ?")
        params.append(request.gene_id.strip())
        
    # chrom精确匹配
    if request.chrom and request.chrom.strip():
        conditions.append("chrom = ?")
        params.append(request.chrom.strip())
        
    # 区间查询：找到完全位于指定区间内的基因
    if request.start is not None:
        conditions.append("start >= ?")
        params.append(request.start)
        
    if request.end is not None:
        conditions.append("stop <= ?")
        params.append(request.end)
    
    # strand精确匹配
    if request.strand and request.strand.strip():
        conditions.append("strand = ?")
        params.append(request.strand.strip())
        
    # family精确匹配
    if request.family and request.family.strip():
        conditions.append("family = ?")
        params.append(request.family.strip())
    
    # 构建WHERE子句
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    return where_clause, params

@g_gene_router.post("/search", summary="Search and Query Genes")
async def search_genes(request: GeneSearchRequest):    
    # Extract parameters from request
    genome_id = getattr(request, 'genome_id', None)
    genome_path = getattr(request, 'genome_path', None)
    page = getattr(request, 'page', 1)
    page_size = getattr(request, 'page_size', 20)

    # Validate required parameters
    if genome_id is None and genome_path is None:
        raise HTTPException(status_code=400, detail="Either genome_id or genome_path must be provided")
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be greater than or equal to 1")
    if not 1 <= page_size <= 100:
        raise HTTPException(status_code=400, detail="page_size must be between 1 and 100")
    
    # 检查是否有任何查询条件 (向后兼容性检查)
    has_query_conditions = any([
        request.keyword, request.gene_id, request.chrom, 
        request.start is not None, request.end is not None,
        request.strand, request.family
    ])
    
    # 向后兼容：如果没有任何查询条件，返回友好提示
    if not has_query_conditions:
        raise HTTPException(
            status_code=400, 
            detail="At least one search condition is required (keyword, gene_id, chrom, position range, strand, or family)"
        )

    # Get database path
    if genome_path:
        db_path = os.path.join(genome_path, "genome.db")
    else:
        base_dir = get_genome_base_dir(genome_id)
        db_path = os.path.join(base_dir, "genome.db")

    if not db_path:
        raise HTTPException(status_code=404, detail=f"Genome database for {genome_id} not found, please process the genome data")

    try:
        # Calculate offset for pagination
        offset = (page - 1) * page_size

        # Build dynamic query conditions
        where_clause, search_params = build_gene_search_query(request)

        # Get total count of matching genes
        count_query = f"SELECT COUNT(*) as total FROM hse_genes WHERE {where_clause}"
        count_result = query_sqlite(db_path, count_query, search_params)
        total_genes = count_result[0]['total']

        # Get paginated search results
        query = f"""
            SELECT * 
            FROM hse_genes 
            WHERE {where_clause}
            ORDER BY chrom, start
            LIMIT ? OFFSET ?
        """
        params = search_params + [page_size, offset]
        results = query_sqlite(db_path, query, params)

        # 动态消息生成
        if request.keyword and len([c for c in [request.gene_id, request.chrom, request.start, request.end, request.strand, request.family] if c is not None]) == 0:
            # 仅keyword搜索 (向后兼容)
            msg = "Search results found" if results else "No genes found matching the search criteria"
        else:
            # 多字段查询
            msg = f"Found {total_genes} genes matching query criteria" if results else "No genes found matching the specified criteria"

        return response_200(
            code=2000,
            msg=msg,
            data={
                "total": total_genes,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_genes + page_size - 1) // page_size,
                "genes": [dict(gene) for gene in results] if results else [],
                "query_info": {
                    "has_keyword": bool(request.keyword),
                    "has_position_filter": any([request.start is not None, request.end is not None]),
                    "has_exact_match": any([request.gene_id, request.chrom, request.strand, request.family])
                }
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gene query error: {str(e)}")


@g_gene_router.post("/list", summary="Get Gene List")
async def get_gene_list(request: GeneListRequest):
    # Extract parameters from request
    genome_id = getattr(request, 'genome_id', None)
    genome_path = getattr(request, 'genome_path', None)
    page = getattr(request, 'page', 1)
    page_size = getattr(request, 'page_size', 20)

    if genome_id is None and genome_path is None:
        raise HTTPException(status_code=400, detail="Either genome_id or genome_path must be provided")
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be greater than or equal to 1")
    if not 1 <= page_size <= 100:
        raise HTTPException(status_code=400, detail="page_size must be between 1 and 100")

    # Get database path
    if genome_path:
        db_path = os.path.join(genome_path, "genome.db")
    else:
        base_dir = get_genome_base_dir(genome_id)
        db_path = os.path.join(base_dir, "genome.db")

    if not db_path:
        raise HTTPException(status_code=404, detail=f"Genome database for {genome_id} not found, please process the genome data")

    try:
        # Calculate offset for pagination
        offset = (page - 1) * page_size

        # Get total count of genes
        count_query = "SELECT COUNT(*) as total FROM hse_genes"
        count_result = query_sqlite(db_path, count_query)
        total_genes = count_result[0]['total']

        # Get paginated gene list
        query = f"""
            SELECT * 
            FROM hse_genes 
            LIMIT ? OFFSET ?
        """
        params = (page_size, offset)
        results = query_sqlite(db_path, query, params)

        return response_200(
            code=2000,
            msg="Data found" if results else "No genes found",
            data={
                "total": total_genes,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_genes + page_size - 1) // page_size,
                "genes": [dict(gene) for gene in results] if results else []
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get gene list error: {str(e)}")


@g_gene_router.post("/transcript/list", summary="Get Transcript List")
async def get_transcript_list(request: GeneListRequest):
    # Extract parameters from request
    genome_id = getattr(request, 'genome_id', None)
    genome_path = getattr(request, 'genome_path', None)
    page = getattr(request, 'page', 1)
    page_size = getattr(request, 'page_size', 20)

    if genome_id is None and genome_path is None:
        raise HTTPException(status_code=400, detail="Either genome_id or genome_path must be provided")
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be greater than or equal to 1")
    if not 1 <= page_size <= 100:
        raise HTTPException(status_code=400, detail="page_size must be between 1 and 100")

    # Get database path
    if genome_path:
        db_path = os.path.join(genome_path, "genome.db")
    else:
        base_dir = get_genome_base_dir(genome_id)
        db_path = os.path.join(base_dir, "genome.db")

    if not db_path:
        raise HTTPException(status_code=404, detail=f"Genome database for {genome_id} not found, please process the genome data")

    try:
        # Calculate offset for pagination
        offset = (page - 1) * page_size

        # Get total count of transcripts
        count_query = "SELECT COUNT(*) as total FROM hse_transcripts"
        count_result = query_sqlite(db_path, count_query)
        total_transcripts = count_result[0]['total']

        # Get paginated transcript list
        query = """
            SELECT * 
            FROM hse_transcripts 
            LIMIT ? OFFSET ?
        """
        params = (page_size, offset)
        results = query_sqlite(db_path, query, params)

        return response_200(
            code=2000,
            msg="Data found" if results else "No transcripts found",
            data={
                "total": total_transcripts,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_transcripts + page_size - 1) // page_size,
                "transcripts": [dict(transcript) for transcript in results] if results else []
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get transcript list error: {str(e)}")


@g_gene_router.post("/info", summary="Get Gene Info")
async def get_gene(request: GeneInfoRequest):
    # Extract parameters from request
    genome_id = getattr(request, 'genome_id', None)
    genome_path = getattr(request, 'genome_path', None)
    gene_id = getattr(request, 'gene_id', None)

    # Validate required parameters
    if not gene_id:
        raise HTTPException(status_code=400, detail="gene_id is required")
    if genome_id is None and genome_path is None:
        raise HTTPException(status_code=400, detail="Either genome_id or genome_path must be provided")

    # Get database path
    if genome_path is None:
        genome_path = get_genome_base_dir(genome_id)

    db_path = os.path.join(genome_path, "genome.db")

    if not db_path:
        raise HTTPException(status_code=404, detail=f"Genome database not found")

    try:
        query = f"SELECT * FROM hse_genes WHERE gene_id=?"
        params = (gene_id,)
        results = query_sqlite(db_path, query, params)

        if not results:
            raise HTTPException(status_code=404, detail=f"Gene ID {gene_id} not found")
        gene_data = results[0]

        if 'canonical_transcript' not in gene_data:
            raise HTTPException(status_code=404, detail="Canonical transcript not found for this gene")
        transcript_id = gene_data['canonical_transcript']

        query = f"SELECT * FROM hse_transcripts WHERE transcript_id=?"
        params = (transcript_id,)
        results = query_sqlite(db_path, query, params)
        if not results:
            raise HTTPException(status_code=404, detail=f"Transcript ID {transcript_id} not found")
        trans_data = results[0]

        # Extract sequences
        sequences = extract_genomic_sequences(genome_path, transcript_id, gene_data['chrom'], gene_data['start'], gene_data['stop'])

        # Prepare response
        return response_200(
            code=2000,
            msg="Data found",
            data={
                "gene_info": dict(gene_data),
                "transcript_info": dict(trans_data),
                "sequences": sequences
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get gene data error: {str(e)}")


# 获取单个transcript 信息 API
@g_gene_router.post("/transcript/info", summary="Get Transcript Info")
async def get_transcript(request: TranscriptInfoRequest):
    # Extract parameters from request
    genome_id = getattr(request, 'genome_id', None)
    genome_path = getattr(request, 'genome_path', None)
    transcript_id = getattr(request, 'transcript_id', None)

    # Validate required parameters
    if not transcript_id:
        raise HTTPException(status_code=400, detail="transcript_id is required")
    if genome_id is None and genome_path is None:
        raise HTTPException(status_code=400, detail="Either genome_id or genome_path must be provided")

    # Get database path
    if genome_path is None:
        genome_path = get_genome_base_dir(genome_id)

    db_path = os.path.join(genome_path, "genome.db")

    if not db_path:
        raise HTTPException(status_code=404, detail=f"Genome database not found")

    try:
        query = "SELECT * FROM hse_transcripts WHERE transcript_id=?"
        params = (transcript_id,)
        results = query_sqlite(db_path, query, params)

        if not results:
            raise HTTPException(status_code=404, detail=f"Transcript ID {transcript_id} not found")
        trans_data = results[0]

        # Extract sequences
        sequences = extract_genomic_sequences(genome_path, transcript_id)

        # Prepare response
        return response_200(
            code=2000,
            msg="Data found",
            data={
                "transcript_info": dict(trans_data),
                "sequences": sequences
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get transcript data error: {str(e)}")
