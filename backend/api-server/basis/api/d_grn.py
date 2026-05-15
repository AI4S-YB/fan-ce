import os
from typing import List
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse
from basis.core.grn_utils import GeneRegulatoryNetworkGraph, get_graph_path
from datetime import datetime
from libs.responses.response import response_2000
from db.database import get_db


# 创建 APIRouter 实例
grn_router = APIRouter(
    prefix="/grn",
    tags=["omics:grn:GeneRegulatoryNetwork"]
)


@grn_router.post("/file/process", response_model=dict, summary="Process gene regulatory network Excel file")
async def process_grn_file(file_path: str = Query(default="", description="Path to the Excel file")):
    """
    Process gene regulatory network Excel file and return graph statistics
    
    Args:
        file_path: Path to the Excel file containing gene regulatory network data
        
    Returns:
        Graph statistics including node and edge counts
    """
    
    try:
        # get the graph file path 
        graph_file_path = get_graph_path(file_path)

        # init graph and process xls file 
        graph = GeneRegulatoryNetworkGraph(graph_file_path)
        graph.process_xls_file(
            file_path, 
            node1_config={"name_col": 0, "attr_cols": [1,2]},  # First node name and attribute columns
            node2_config={"name_col": 4, "attr_cols": [6,7]},  # Second node name and attribute columns 
            edge_attr_cols=[3,5],  # Edge attribute columns
            header=0  # 第一行作为header
        ) 

        # save graph to pkl file 
        graph.save_graph(graph_file_path)

        # print(graph_file_path)
        # graph.print_graph_info(detailed=True)
        
        return response_2000(
            code=2000,
            msg="Gene regulatory network file processed successfully",
            data={
                "graph_file": graph_file_path,
                "original_filename": os.path.basename(file_path)
            }
        )
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process gene regulatory network file: {str(e)}")


@grn_router.post("/list", response_model=dict, summary="Get paginated list of gene relationships with optional search")
async def list_gene_relationships(
    page: int = Query(default=1, description="Page number", gt=0),
    page_size: int = Query(default=10, description="Items per page", gt=0),
    keyword: str = Query(default=None, description="Search keyword (optional)"),
    exact_match: bool = Query(default=False, description="Whether to perform exact match search"),
    file_path: str = Query(default="", description="Path to the Excel file")
):
    """
    获取基因调控关系列表，支持可选的搜索功能
    
    Args:
        page: 页码（从1开始）
        page_size: 每页项目数
        keyword: 搜索关键词（可选）
        exact_match: 是否精确匹配
        file_path: Excel文件路径
        
    Returns:
        包含节点和边详细信息的关系列表
    """
    try:
        # Get the graph file path
        graph_file_path = get_graph_path(file_path)
        
        # Create graph instance and load data
        graph = GeneRegulatoryNetworkGraph(graph_file_path)
        success = graph.load_graph()
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to load gene regulatory network")
            
        # Get relationships with optional search
        result = graph.get_nodes_with_relationships(page, page_size, keyword, exact_match)
                
        return response_2000(
            code=2000,
            msg="Successfully retrieved gene relationships" + (f" for keyword '{keyword}'" if keyword else ""),
            data={
                "items": result["relationships"],
                "total": result["total"],
                "page": result["current_page"],
                "page_size": result["page_size"],
                "total_pages": result["total_pages"],
                "search_keyword": result["search_keyword"]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve gene relationships: {str(e)}")


@grn_router.post("/info", response_model=dict, summary="Get gene details")
async def get_gene_detail(gene_id: str="AT1G01030.1", file_path: str = Query(default="", description="Path to the Excel file")):
    """
    Get detailed information of a gene by ID from the gene regulatory network
    """
    try:
        graph_file_path = get_graph_path(file_path)

        # Initialize and load graph
        graph = GeneRegulatoryNetworkGraph(graph_file_path)
        success = graph.load_graph()
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to load graph from {graph_file_path}")
            
        # Query the specific gene node
        node_info = graph.get_node_info(gene_id)
        
        if not node_info:
            raise HTTPException(status_code=404, detail="Gene not found")
            
        # Add id to node_info and return all key-value pairs directly
        node_info["id"] = gene_id
        
        return response_2000(
            code=2000,
            msg="Successfully retrieved gene details",
            data=node_info
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get gene details: {str(e)}")


# search_genes函数已被合并到list_gene_relationships函数中
# 使用list_gene_relationships接口并传递keyword参数来实现搜索功能


@grn_router.post("/relationship", response_model=dict, summary="Get all paths between two genes")
async def get_gene_relationship(
    regulator: str = Query(default="AT1G01030.1", description="ID of regulator gene"),
    target: str = Query(default="AT2G22430", description="ID of target gene"),
    max_paths: int = Query(default=10, description="Maximum number of paths to find", ge=1, le=50),
    max_path_length: int = Query(default=5, description="Maximum path length (number of edges)", ge=1, le=10),
    file_path: str = Query(default="", description="Path to the Excel file")
):
    """
    获取两个基因之间的所有调控路径信息
    
    Args:
        regulator: 调控基因ID
        target: 目标基因ID
        max_paths: 最大路径数量
        max_path_length: 最大路径长度（边的数量）
        file_path: Excel文件路径
        
    Returns:
        包含所有路径信息的详细数据，包括每条路径的节点和边属性
    """
    try:
        # Get graph file path and load graph
        graph_file_path = get_graph_path(file_path)
        graph = GeneRegulatoryNetworkGraph(graph_file_path)
        success = graph.load_graph()
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to load gene regulatory network")
            
        # Get all paths between the two genes
        relationship = graph.get_relationship(regulator, target, max_paths, max_path_length)
        
        if relationship is None:
            raise HTTPException(status_code=500, detail="Failed to get regulatory relationship information")
            
        return response_2000(
            code=2000,
            msg=f"Successfully found {relationship.get('total_paths_found', 0)} paths between genes",
            data=relationship
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get regulatory relationship information: {str(e)}")


@grn_router.post("/relationships/batch", response_model=dict, summary="Get relationships for selected genes")
async def get_gene_relationships_batch(request: dict):
    """
    获取勾选基因节点的批量调控关系信息，用于构建基因调控网络知识图谱
    
    Args:
        selected_nodes: 勾选的基因ID列表
        include_internal: 是否包含勾选基因之间的内部调控关系
        include_external: 是否包含与外部基因的调控关系
        max_connections_per_node: 每个基因的最大连接数限制
        max_path_length: 基因调控关系的最大路径长度
        file_path: Excel文件路径
        
    Returns:
        包含基因节点和调控关系的知识图谱数据
    """
    try:
        # 从请求体中提取参数
        selected_nodes = request.get("selected_nodes", [])
        include_internal = request.get("include_internal", True)
        include_external = request.get("include_external", False)
        max_connections_per_node = request.get("max_connections_per_node", 50)
        max_path_length = request.get("max_path_length", 3)
        file_path = request.get("file_path", "")
        
        # 验证输入参数
        if not selected_nodes or len(selected_nodes) == 0:
            raise HTTPException(status_code=400, detail="Selected nodes list cannot be empty")
            
        # 获取图文件路径并加载图
        graph_file_path = get_graph_path(file_path)
        graph = GeneRegulatoryNetworkGraph(graph_file_path)
        success = graph.load_graph()
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to load gene regulatory network")
            
        # 获取批量调控关系信息
        result = graph.get_batch_relationships(
            selected_nodes=selected_nodes,
            include_internal=include_internal,
            include_external=include_external,
            max_connections_per_node=max_connections_per_node,
            max_path_length=max_path_length
        )
        
        if result is None:
            raise HTTPException(status_code=500, detail="Failed to get batch gene regulatory relationships")
            
        return response_2000(
            code=2000,
            msg=f"Successfully retrieved regulatory relationships for {len(selected_nodes)} selected genes",
            data=result
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get batch gene relationships: {str(e)}")


@grn_router.post("/statistics", response_model=dict, summary="Get statistics of gene regulatory network")
async def get_grn_statistics(
    file_path: str = Query(default="", description="Path to the Excel file")
):
    """
    Get statistics of gene regulatory network including gene count, regulation count, connectivity info etc.
    
    Args:
        file_path: Path to the Excel file containing gene regulatory network data
        
    Returns:
        Statistics information of the gene regulatory network
    """
    try:
        # Get graph file path and load graph
        graph_file_path = get_graph_path(file_path)
        graph = GeneRegulatoryNetworkGraph(graph_file_path)
        success = graph.load_graph()
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to load gene regulatory network")
            
        # Get network statistics
        statistics = graph.get_graph_statistics()
        
        if not statistics:
            raise HTTPException(status_code=500, detail="Failed to get network statistics")
            
        return response_2000(
            code=2000,
            msg="Successfully retrieved gene regulatory network statistics",
            data=statistics
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get network statistics: {str(e)}")
