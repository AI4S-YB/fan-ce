import pandas as pd
import networkx as nx
import pickle
import os
from typing import Dict, List, Tuple, Optional, Set
from pathlib import Path
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeneRegulatoryNetworkGraph:
    """
    基因调控网络图管理类
    负责构建、存储和查询基因调控网络中基因之间的关系图
    """
    
    def __init__(self, graph_file_path: str = None):
        """
        初始化基因调控网络图
        
        Args:
            graph_file_path: 图数据存储文件路径
        """
        self.graph = nx.Graph()
        self.graph_file_path = graph_file_path or "grn_graph.pkl"
        self.metadata = {
            "created_at": None,
            "updated_at": None,
            "source_file": None,
            "node_count": 0,
            "edge_count": 0
        }
        
    def load_xls_data(self, file_path: str, header: int = 0) -> pd.DataFrame:
        """
        从 XLS 文件加载数据（处理第一个工作表）
        
        Args:
            file_path: XLS 文件路径
            header: 指定哪一行作为列名，默认为0（第一行）
            
        Returns:
            pandas.DataFrame: 加载的数据
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
                
            # 读取 XLS 文件的第一个工作表，支持header参数
            df = pd.read_excel(file_path, header=header)
                
            logger.info(f"成功加载 XLS 文件: {file_path}, 数据行数: {len(df)}, header行: {header}")
            return df
            
        except Exception as e:
            logger.error(f"加载 XLS 文件失败: {str(e)}")
            raise

    # extract_node_attributes函数已被移除，因为新的process_xls_file函数直接处理行数据

    # extract_relationship_data函数已被移除，因为新的process_xls_file函数直接处理行数据

    def build_graph(self, relationships: List[Tuple[str, str, Dict]], 
                   node_attributes: Dict[str, Dict] = None,
                   add_attributes: bool = True) -> None:
        """
        根据基因调控关系数据和基因节点属性构建基因调控网络图
        注意：此函数已被新的process_xls_file函数替代，保留用于兼容性
        
        Args:
            relationships: 基因调控关系对列表，包含 (node1, node2, edge_attributes)
            node_attributes: 基因节点属性字典
            add_attributes: 是否添加基因节点和边的属性
        """
        try:
            # 清空现有图
            self.graph.clear()
            
            # 添加边（会自动添加节点）
            for node1, node2, edge_attrs in relationships:
                self.graph.add_edge(node1, node2)
                
                # 添加边属性
                if add_attributes:
                    # 添加从数据中提取的边属性
                    for attr_name, attr_value in edge_attrs.items():
                        self.graph[node1][node2][attr_name] = attr_value
                    
                    # 添加默认属性
                    self.graph[node1][node2]['weight'] = 1
                    self.graph[node1][node2]['created_at'] = datetime.now().isoformat()
            
            # 添加节点属性
            if add_attributes:
                for node in self.graph.nodes():
                    # 添加基本属性
                    self.graph.nodes[node]['degree'] = self.graph.degree(node)
                    self.graph.nodes[node]['created_at'] = datetime.now().isoformat()
                    
                    # 添加从XLS文件中提取的属性
                    if node_attributes and node in node_attributes:
                        for attr_name, attr_value in node_attributes[node].items():
                            self.graph.nodes[node][attr_name] = attr_value
            
            # 更新元数据
            self.metadata.update({
                "updated_at": datetime.now().isoformat(),
                "node_count": self.graph.number_of_nodes(),
                "edge_count": self.graph.number_of_edges()
            })
            
            logger.info(f"基因调控网络图构建完成: {self.metadata['node_count']} 个基因节点, {self.metadata['edge_count']} 条调控关系")
            
        except Exception as e:
            logger.error(f"构建图失败: {str(e)}")
            raise

    def process_xls_file(self, file_path: str, 
                        node1_config: Dict = None,
                        node2_config: Dict = None,
                        edge_attr_cols: List[int] = None,
                        header: int = 0) -> None:
        """
        处理基因调控网络 XLS 文件并构建基因调控网络图
        每行数据包含两个节点和一条边的完整信息，直接处理行数据构建图
        
        Args:
            file_path: 基因调控网络 XLS 文件路径
            node1_config: 第一个节点配置，格式: {"name_col": 0, "attr_cols": [1,2]}
            node2_config: 第二个节点配置，格式: {"name_col": 1, "attr_cols": [6,7]}
            edge_attr_cols: 边属性列索引列表，如 [3,5]
            header: 指定哪一行作为列名，默认为0（第一行）
        """
        try:
            # 设置默认配置
            if node1_config is None:
                node1_config = {"name_col": 0, "attr_cols": []}
            if node2_config is None:
                node2_config = {"name_col": 1, "attr_cols": []}
            if edge_attr_cols is None:
                edge_attr_cols = []
                
            # 加载数据（处理第一个工作表）
            df = self.load_xls_data(file_path, header=header)
                        
            # 清空现有图
            self.graph.clear()
            
            # 直接处理每行数据，构建节点和边
            node_attributes = {}
            
            for index, row in df.iterrows():
                # 获取节点名称
                node1_name = str(row.iloc[node1_config["name_col"]])
                node2_name = str(row.iloc[node2_config["name_col"]])
                
                # 跳过空值
                if pd.isna(node1_name) or pd.isna(node2_name) or node1_name == 'nan' or node2_name == 'nan':
                    continue
                    
                # 收集节点属性
                if node1_name not in node_attributes:
                    node1_attrs = {}
                    for attr_col in node1_config.get("attr_cols", []):
                        if attr_col < len(row):
                            attr_value = row.iloc[attr_col]
                            if not pd.isna(attr_value):
                                # 使用列名作为属性名，如果没有列名则使用列索引
                                attr_name = df.columns[attr_col] if attr_col < len(df.columns) else f"attr_{attr_col}"
                                node1_attrs[attr_name] = str(attr_value)
                    node_attributes[node1_name] = node1_attrs
                    
                if node2_name not in node_attributes:
                    node2_attrs = {}
                    for attr_col in node2_config.get("attr_cols", []):
                        if attr_col < len(row):
                            attr_value = row.iloc[attr_col]
                            if not pd.isna(attr_value):
                                # 使用列名作为属性名，如果没有列名则使用列索引
                                attr_name = df.columns[attr_col] if attr_col < len(df.columns) else f"attr_{attr_col}"
                                node2_attrs[attr_name] = str(attr_value)
                    node_attributes[node2_name] = node2_attrs
                
                # 收集边属性
                edge_attrs = {}
                for edge_col in edge_attr_cols:
                    if edge_col < len(row):
                        edge_value = row.iloc[edge_col]
                        if not pd.isna(edge_value):
                            # 使用列名作为属性名，如果没有列名则使用列索引
                            edge_attr_name = df.columns[edge_col] if edge_col < len(df.columns) else f"edge_attr_{edge_col}"
                            edge_attrs[edge_attr_name] = str(edge_value)
                
                # 添加默认边属性
                edge_attrs.update({
                    "weight": 1.0,
                    "created_at": datetime.now().isoformat()
                })
                
                # 添加边到图中
                self.graph.add_edge(node1_name, node2_name, **edge_attrs)
            
            # 添加节点属性
            for node, attrs in node_attributes.items():
                if self.graph.has_node(node):
                    self.graph.nodes[node].update(attrs)
            
            # 更新元数据
            self.metadata["source_file"] = file_path
            self.metadata["created_at"] = datetime.now().isoformat()
            self.metadata["node1_config"] = node1_config
            self.metadata["node2_config"] = node2_config
            self.metadata["edge_attr_cols"] = edge_attr_cols
            self.metadata["header"] = header
            self.metadata["nodes_count"] = self.graph.number_of_nodes()
            self.metadata["edges_count"] = self.graph.number_of_edges()
            
            logger.info(f"基因调控网络 XLS 文件处理完成: {file_path}, 节点数: {self.graph.number_of_nodes()}, 边数: {self.graph.number_of_edges()}")
            
        except Exception as e:
            logger.error(f"处理 XLS 文件失败: {str(e)}")
            raise

    def save_graph(self, graph_file_path: str) -> bool:
        """
        保存图数据到文件
        
        Returns:
            bool: 是否保存成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.graph_file_path), exist_ok=True)
            
            # 保存图数据和元数据
            graph_data = {
                'graph': self.graph,
                'metadata': self.metadata
            }
            
            with open(self.graph_file_path, 'wb') as f:
                pickle.dump(graph_data, f)
            
            logger.info(f"图数据已保存到: {self.graph_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存图数据失败: {str(e)}")
            return False
    
    def load_graph(self) -> bool:
        """
        从文件加载图数据
        
        Returns:
            bool: 是否加载成功
        """
        try:
            if not os.path.exists(self.graph_file_path):
                logger.info(f"图数据文件不存在: {self.graph_file_path}，将创建新图")
                return False
            
            with open(self.graph_file_path, 'rb') as f:
                graph_data = pickle.load(f)
            
            self.graph = graph_data.get('graph', nx.Graph())
            self.metadata = graph_data.get('metadata', {
                "created_at": None,
                "updated_at": None,
                "source_file": None,
                "node_count": 0,
                "edge_count": 0
            })
            
            logger.info(f"图数据已从 {self.graph_file_path} 加载完成")
            logger.info(f"加载的图包含 {self.graph.number_of_nodes()} 个节点，{self.graph.number_of_edges()} 条边")
            return True
            
        except Exception as e:
            logger.error(f"加载图数据失败: {str(e)}")
            return False

    def get_relationship(self, node1: str, node2: str, max_paths: int = 10, max_path_length: int = 5) -> Optional[Dict]:
        """
        获取两个节点之间的所有路径信息
        
        Args:
            node1: 起始节点
            node2: 目标节点
            max_paths: 最大路径数量限制
            max_path_length: 最大路径长度限制
            
        Returns:
            Optional[Dict]: 包含所有路径信息的字典
        """
        try:
            # 检查节点是否存在
            if node1 not in self.graph.nodes or node2 not in self.graph.nodes:
                return {
                    "node1": node1,
                    "node2": node2,
                    "exists": False,
                    "error": "One or both nodes do not exist in the graph",
                    "paths": []
                }
            
            # 如果是同一个节点
            if node1 == node2:
                node_attrs = dict(self.graph.nodes[node1])
                return {
                    "node1": node1,
                    "node2": node2,
                    "exists": True,
                    "is_same_node": True,
                    "node_attributes": node_attrs,
                    "paths": [{
                        "path_length": 0,
                        "nodes": [{
                            "name": node1,
                            "attributes": node_attrs
                        }],
                        "edges": []
                    }]
                }
            
            # 查找所有简单路径
            all_paths = []
            try:
                # 使用NetworkX查找所有简单路径
                simple_paths = nx.all_simple_paths(
                    self.graph, 
                    source=node1, 
                    target=node2, 
                    cutoff=max_path_length
                )
                
                path_count = 0
                for path in simple_paths:
                    if path_count >= max_paths:
                        break
                    
                    # 构建路径信息
                    path_info = {
                        "path_length": len(path) - 1,  # 边的数量
                        "nodes": [],
                        "edges": []
                    }
                    
                    # 添加节点信息
                    for node in path:
                        node_attrs = dict(self.graph.nodes[node])
                        path_info["nodes"].append({
                            "name": node,
                            "attributes": node_attrs
                        })
                    
                    # 添加边信息
                    for i in range(len(path) - 1):
                        source_node = path[i]
                        target_node = path[i + 1]
                        
                        if self.graph.has_edge(source_node, target_node):
                            edge_attrs = dict(self.graph[source_node][target_node])
                            path_info["edges"].append({
                                "source": source_node,
                                "target": target_node,
                                "attributes": edge_attrs
                            })
                    
                    all_paths.append(path_info)
                    path_count += 1
                    
            except nx.NetworkXNoPath:
                # 没有路径连接两个节点
                pass
            
            # 检查是否有直接连接
            has_direct_connection = self.graph.has_edge(node1, node2)
            direct_edge_info = None
            if has_direct_connection:
                direct_edge_info = dict(self.graph[node1][node2])
            
            return {
                "node1": node1,
                "node2": node2,
                "exists": len(all_paths) > 0,
                "has_direct_connection": has_direct_connection,
                "direct_edge_attributes": direct_edge_info,
                "total_paths_found": len(all_paths),
                "max_paths_limit": max_paths,
                "max_path_length_limit": max_path_length,
                "paths": all_paths
            }
                
        except Exception as e:
            logger.error(f"获取路径信息失败: {str(e)}")
            return {
                "node1": node1,
                "node2": node2,
                "exists": False,
                "error": str(e),
                "paths": []
            }

    def get_batch_relationships(self, selected_nodes: List[str], 
                              include_internal: bool = True,
                              include_external: bool = False,
                              max_connections_per_node: int = 50,
                              max_path_length: int = 3) -> Optional[Dict]:
        """
        获取勾选基因节点的批量调控关系信息，用于构建基因调控网络知识图谱
        
        Args:
            selected_nodes: 勾选的基因节点ID列表
            include_internal: 是否包含勾选基因之间的内部调控关系
            include_external: 是否包含与外部基因的调控关系
            max_connections_per_node: 每个基因的最大连接数限制
            max_path_length: 基因调控关系的最大路径长度
            
        Returns:
            Optional[Dict]: 包含基因节点和调控关系的知识图谱数据
        """
        try:
            # 验证节点是否存在
            valid_nodes = []
            for node_id in selected_nodes:
                if node_id in self.graph.nodes:
                    valid_nodes.append(node_id)
                else:
                    logger.warning(f"基因节点 {node_id} 在调控网络中不存在，将被跳过")
            
            if not valid_nodes:
                return {
                    "nodes": [],
                    "edges": [],
                    "statistics": {
                        "total_nodes": 0,
                        "total_edges": 0,
                        "selected_nodes_count": len(selected_nodes),
                        "valid_nodes_count": 0
                    }
                }
            
            # 收集节点信息
            result_nodes = {}
            result_edges = []
            
            # 添加勾选的基因节点
            for node_id in valid_nodes:
                node_data = self.graph.nodes[node_id]
                result_nodes[node_id] = {
                    "id": node_id,
                    "label": node_id,
                    "degree": self.graph.degree(node_id),
                    "attributes": dict(node_data),
                    "selected": True,  # 标记为勾选节点
                    "node_type": "selected_gene"
                }
            
            # 收集调控关系信息
            added_edges = set()  # 避免重复边
            
            for node_id in valid_nodes:
                neighbors = list(self.graph.neighbors(node_id))
                connection_count = 0
                
                for neighbor in neighbors:
                    if connection_count >= max_connections_per_node:
                        break
                    
                    # 检查是否应该包含这条调控关系
                    should_include = False
                    
                    if include_internal and neighbor in valid_nodes:
                        # 内部关系：勾选基因之间的调控关系
                        should_include = True
                    elif include_external and neighbor not in valid_nodes:
                        # 外部关系：与非勾选基因的调控关系
                        should_include = True
                    
                    if should_include:
                        # 确保边的方向一致，避免重复
                        edge_key = tuple(sorted([node_id, neighbor]))
                        if edge_key not in added_edges:
                            # 添加邻居基因节点（如果还没添加）
                            if neighbor not in result_nodes:
                                neighbor_data = self.graph.nodes[neighbor]
                                result_nodes[neighbor] = {
                                    "id": neighbor,
                                    "label": neighbor,
                                    "degree": self.graph.degree(neighbor),
                                    "attributes": dict(neighbor_data),
                                    "selected": False,  # 标记为非勾选节点
                                    "node_type": "connected_gene"
                                }
                            
                            # 添加调控关系信息
                            edge_data = self.graph[node_id][neighbor]
                            result_edges.append({
                                "id": f"{node_id}_{neighbor}",
                                "source": node_id,
                                "target": neighbor,
                                "relationship_type": edge_data.get('relationship_type', 'regulation'),
                                "weight": edge_data.get('weight', 1),
                                "created_at": edge_data.get('created_at', None),
                                # 复制其他边属性
                                "attributes": {k: v for k, v in edge_data.items() 
                                             if k not in ['weight', 'created_at']}
                            })
                            
                            added_edges.add(edge_key)
                            connection_count += 1
            
            # 如果需要更复杂的路径分析，可以在这里添加
            # 基于max_path_length参数进行多层调控关系的发现
            if max_path_length > 1 and include_external:
                # 可以实现多层调控网络的发现逻辑
                # 这里暂时保持简单的直接邻居关系
                pass
            
            # 转换节点字典为列表
            nodes_list = list(result_nodes.values())
            
            # 统计信息
            statistics = {
                "total_nodes": len(nodes_list),
                "total_edges": len(result_edges),
                "selected_nodes_count": len(selected_nodes),
                "valid_nodes_count": len(valid_nodes),
                "internal_edges": sum(1 for edge in result_edges 
                                    if edge["source"] in valid_nodes and edge["target"] in valid_nodes),
                "external_edges": sum(1 for edge in result_edges 
                                    if not (edge["source"] in valid_nodes and edge["target"] in valid_nodes)),
                "include_internal": include_internal,
                "include_external": include_external,
                "max_connections_per_node": max_connections_per_node,
                "max_path_length": max_path_length,
                "gene_types": {
                    "selected_genes": len([n for n in nodes_list if n["selected"]]),
                    "connected_genes": len([n for n in nodes_list if not n["selected"]])
                }
            }
            
            return {
                "nodes": nodes_list,
                "edges": result_edges,
                "statistics": statistics
            }
                
        except Exception as e:
            logger.error(f"获取批量基因调控关系信息失败: {str(e)}")
            return None

    def get_nodes_with_relationships(self, page: int = 1, page_size: int = 20, keyword: str = None, exact_match: bool = False) -> Dict[str, any]:
        """
        获取节点列表及其关系信息，支持搜索功能
        
        Args:
            page: 页码（从1开始）
            page_size: 每页节点数量
            keyword: 搜索关键词，如果提供则进行搜索
            exact_match: 是否精确匹配
            
        Returns:
            Dict containing:
                - relationships: 关系列表，包含节点和边的详细信息
                - total: 总关系数
                - total_pages: 总页数
                - current_page: 当前页码
                - page_size: 每页大小
                - search_keyword: 搜索关键词（如果有）
        """
        try:
            # 获取所有边的信息
            all_relationships = []
            
            for edge in self.graph.edges(data=True):
                node1, node2, edge_attrs = edge
                
                # 如果提供了关键词，进行搜索过滤
                if keyword:
                    keyword_lower = keyword.lower()
                    match_found = False
                    
                    # 检查节点名称
                    if exact_match:
                        if node1 == keyword or node2 == keyword:
                            match_found = True
                    else:
                        if keyword_lower in node1.lower() or keyword_lower in node2.lower():
                            match_found = True
                    
                    # 检查节点属性
                    if not match_found:
                        for node in [node1, node2]:
                            node_attrs = self.graph.nodes[node]
                            for attr_value in node_attrs.values():
                                if attr_value is not None:
                                    attr_str = str(attr_value).lower()
                                    if exact_match:
                                        if attr_str == keyword_lower:
                                            match_found = True
                                            break
                                    else:
                                        if keyword_lower in attr_str:
                                            match_found = True
                                            break
                            if match_found:
                                break
                    
                    # 检查边属性
                    if not match_found:
                        for attr_value in edge_attrs.values():
                            if attr_value is not None:
                                attr_str = str(attr_value).lower()
                                if exact_match:
                                    if attr_str == keyword_lower:
                                        match_found = True
                                        break
                                else:
                                    if keyword_lower in attr_str:
                                        match_found = True
                                        break
                    
                    # 如果没有匹配，跳过这条关系
                    if not match_found:
                        continue
                
                # 构建关系信息
                relationship_info = {
                    "node1": {
                        "name": node1,
                        "attributes": dict(self.graph.nodes[node1])
                    },
                    "node2": {
                        "name": node2,
                        "attributes": dict(self.graph.nodes[node2])
                    },
                    "edge_attributes": dict(edge_attrs)
                }
                
                all_relationships.append(relationship_info)
            
            # 按节点名称排序
            all_relationships.sort(key=lambda x: (x["node1"]["name"], x["node2"]["name"]))
            
            total_relationships = len(all_relationships)
            
            # 计算分页信息
            total_pages = (total_relationships + page_size - 1) // page_size if total_relationships > 0 else 1
            page = max(1, min(page, total_pages))  # 确保页码在有效范围内
            
            # 获取当前页的关系
            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, total_relationships)
            current_page_relationships = all_relationships[start_idx:end_idx]
            
            return {
                "relationships": current_page_relationships,
                "total": total_relationships,
                "total_pages": total_pages,
                "current_page": page,
                "page_size": page_size,
                "search_keyword": keyword
            }
            
        except Exception as e:
            logger.error(f"获取节点关系信息失败: {str(e)}")
            return {
                "relationships": [],
                "total": 0,
                "total_pages": 0,
                "current_page": page,
                "page_size": page_size,
                "search_keyword": keyword
            }
    
    def get_neighbors(self, node: str) -> List[str]:
        """
        获取节点的邻居列表
        
        Args:
            node: 节点名称
            
        Returns:
            List[str]: 邻居节点列表
        """
        try:
            if node in self.graph:
                return list(self.graph.neighbors(node))
            else:
                return []
                
        except Exception as e:
            logger.error(f"获取邻居节点失败: {str(e)}")
            return []

    def get_node_info(self, node: str) -> Optional[Dict]:
        """
        获取节点信息（包含属性）
        
        Args:
            node: 节点名称
            
        Returns:
            Optional[Dict]: 节点信息
        """
        try:
            if node in self.graph:
                node_data = self.graph.nodes[node]
                neighbors = list(self.graph.neighbors(node))
                
                return {
                    "node": node,
                    "degree": self.graph.degree(node),
                    "neighbors": neighbors,
                    "neighbor_count": len(neighbors),
                    "attributes": dict(node_data)
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"获取节点信息失败: {str(e)}")
            return None
    
    # search_nodes函数已被合并到get_nodes_with_relationships函数中
    # 使用get_nodes_with_relationships(keyword=keyword, exact_match=exact_match)来替代
    
    def get_graph_statistics(self) -> Dict:
        """
        获取图的统计信息
        
        Returns:
            Dict: 图的统计信息
        """
        try:
            stats = {
                "node_count": self.graph.number_of_nodes(),
                "edge_count": self.graph.number_of_edges(),
                "is_connected": nx.is_connected(self.graph),
                "connected_components": nx.number_connected_components(self.graph),
                "metadata": self.metadata
            }
            
            if self.graph.number_of_nodes() > 0:
                degrees = [self.graph.degree(node) for node in self.graph.nodes()]
                stats.update({
                    "average_degree": sum(degrees) / len(degrees),
                    "max_degree": max(degrees),
                    "min_degree": min(degrees)
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"获取图统计信息失败: {str(e)}")
            return {}


    def print_graph_info(self, detailed: bool = False, max_nodes_display: int = 20, 
                        max_edges_display: int = 30) -> None:
        """
        打印基因调控网络图的详细信息
        
        Args:
            detailed: 是否显示详细信息
            max_nodes_display: 最大显示基因节点数
            max_edges_display: 最大显示调控关系数
        """
        try:
            print("\n" + "="*60)
            print("基因调控网络图信息")
            print("="*60)
            
            # 基本统计信息
            stats = self.get_graph_statistics()
            print(f"\n📊 基本统计:")
            print(f"   基因节点数量: {stats.get('node_count', 0)}")
            print(f"   调控关系数量: {stats.get('edge_count', 0)}")
            print(f"   是否连通: {'是' if stats.get('is_connected', False) else '否'}")
            print(f"   连通分量数: {stats.get('connected_components', 0)}")
            
            if stats.get('node_count', 0) > 0:
                print(f"   平均度数: {stats.get('average_degree', 0):.2f}")
                print(f"   最大度数: {stats.get('max_degree', 0)}")
                print(f"   最小度数: {stats.get('min_degree', 0)}")
            
            # 元数据信息
            metadata = self.metadata
            print(f"\n📋 元数据信息:")
            print(f"   创建时间: {metadata.get('created_at', 'N/A')}")
            print(f"   更新时间: {metadata.get('updated_at', 'N/A')}")
            print(f"   源文件: {metadata.get('source_file', 'N/A')}")
            
            # 关系类型统计
            relationship_types = {}
            for edge in self.graph.edges(data=True):
                rel_type = edge[2].get('relationship_type', 'unknown')
                relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
            
            if relationship_types:
                print(f"\n🔗 关系类型统计:")
                for rel_type, count in relationship_types.items():
                    print(f"   {rel_type}: {count} 条")
            
            if detailed and self.graph.number_of_nodes() > 0:
                # 显示部分基因节点信息
                print(f"\n🌟 基因节点信息 (显示前 {max_nodes_display} 个):")
                nodes_to_show = list(self.graph.nodes())[:max_nodes_display]
                for i, node in enumerate(nodes_to_show, 1):
                    degree = self.graph.degree(node)
                    neighbors = list(self.graph.neighbors(node))
                    print(f"   {i:2d}. {node} (度数: {degree}, 相关基因: {len(neighbors)})")
                    if len(neighbors) <= 5:
                        print(f"       相关基因: {', '.join(neighbors)}")
                    else:
                        print(f"       相关基因: {', '.join(neighbors[:5])}...")
                
                if len(self.graph.nodes()) > max_nodes_display:
                    print(f"   ... 还有 {len(self.graph.nodes()) - max_nodes_display} 个基因节点")
                
                # 显示部分调控关系信息
                print(f"\n🔗 调控关系信息 (显示前 {max_edges_display} 条):")
                edges_to_show = list(self.graph.edges(data=True))[:max_edges_display]
                for i, (node1, node2, data) in enumerate(edges_to_show, 1):
                    rel_type = data.get('relationship_type', 'unknown')
                    weight = data.get('weight', 1)
                    print(f"   {i:2d}. {node1} -> {node2} ({rel_type}, 权重: {weight})")
                
                if len(self.graph.edges()) > max_edges_display:
                    print(f"   ... 还有 {len(self.graph.edges()) - max_edges_display} 条调控关系")
            
            # 基因节点度数分布
            if self.graph.number_of_nodes() > 0:
                degrees = [self.graph.degree(node) for node in self.graph.nodes()]
                degree_dist = {}
                for degree in degrees:
                    degree_dist[degree] = degree_dist.get(degree, 0) + 1
                
                print(f"\n📈 基因节点度数分布:")
                sorted_degrees = sorted(degree_dist.items())
                for degree, count in sorted_degrees[:10]:  # 显示前10个度数
                    print(f"   度数 {degree}: {count} 个基因节点")
                if len(sorted_degrees) > 10:
                    print(f"   ... 还有 {len(sorted_degrees) - 10} 种度数")
            
            print("\n" + "="*60)
            
        except Exception as e:
            logger.error(f"打印图信息失败: {str(e)}")
            print(f"❌ 打印图信息时发生错误: {str(e)}")
    
    def export_graph_to_text(self, file_path: str = None, detailed: bool = True) -> str:
        """
        将图信息导出到文本文件或返回文本字符串
        
        Args:
            file_path: 导出文件路径，如果为 None 则返回字符串
            detailed: 是否包含详细信息
            
        Returns:
            str: 图信息文本（当 file_path 为 None 时）
        """
        try:
            import io
            from contextlib import redirect_stdout
            
            # 捕获 print_graph_info 的输出
            f = io.StringIO()
            with redirect_stdout(f):
                self.print_graph_info(detailed=detailed, max_nodes_display=50, max_edges_display=100)
            
            output_text = f.getvalue()
            
            if file_path:
                # 导出到文件
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(output_text)
                logger.info(f"图信息已导出到: {file_path}")
                return f"图信息已成功导出到: {file_path}"
            else:
                # 返回字符串
                return output_text
                
        except Exception as e:
            logger.error(f"导出图信息失败: {str(e)}")
            return f"导出失败: {str(e)}"
    
    def validate_graph_data(self) -> Dict[str, any]:
        """
        验证图数据的完整性
        
        Returns:
            Dict: 验证结果
        """
        try:
            validation_result = {
                "is_valid": True,
                "issues": [],
                "warnings": [],
                "statistics": {}
            }
            
            # 检查孤立节点
            isolated_nodes = list(nx.isolates(self.graph))
            if isolated_nodes:
                validation_result["warnings"].append(f"发现 {len(isolated_nodes)} 个孤立节点")
                validation_result["statistics"]["isolated_nodes"] = len(isolated_nodes)
            
            # 检查自环
            self_loops = list(nx.selfloop_edges(self.graph))
            if self_loops:
                validation_result["issues"].append(f"发现 {len(self_loops)} 个自环")
                validation_result["statistics"]["self_loops"] = len(self_loops)
                validation_result["is_valid"] = False
            
            # 检查边的关系类型
            edges_without_type = []
            for edge in self.graph.edges(data=True):
                if 'relationship_type' not in edge[2]:
                    edges_without_type.append((edge[0], edge[1]))
            
            if edges_without_type:
                validation_result["warnings"].append(f"发现 {len(edges_without_type)} 条边缺少关系类型")
                validation_result["statistics"]["edges_without_type"] = len(edges_without_type)
            
            # 检查连通性
            if not nx.is_connected(self.graph) and self.graph.number_of_nodes() > 1:
                validation_result["warnings"].append("图不是连通的")
                validation_result["statistics"]["connected_components"] = nx.number_connected_components(self.graph)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"验证图数据失败: {str(e)}")
            return {
                "is_valid": False,
                "issues": [f"验证过程出错: {str(e)}"],
                "warnings": [],
                "statistics": {}
            }



# 全局图实例
_global_graph = None

def get_graph_path(xls_path: str) -> str:
    """
    Convert Excel file path to pickle file path
    Args:
        xls_path: Path to Excel file
    Returns:
        Pickle file path
    Raises:
        ValueError: If file path is not absolute or file not accessible
        FileNotFoundError: If file does not exist
    """
    # Check if path is absolute
    if not os.path.isabs(xls_path):
        raise ValueError(f"File path must be absolute: {xls_path}")

    # Check if file exists
    if not os.path.exists(xls_path):
        raise FileNotFoundError(f"Excel file not found: {xls_path}")

    # Check if file is accessible
    if not os.access(xls_path, os.R_OK):
        raise ValueError(f"Excel file is not readable: {xls_path}")

    # Check if file has valid Excel extension
    if not xls_path.endswith(('.xlsx', '.xls')):
        raise ValueError(f"File must be an Excel file (.xlsx or .xls): {xls_path}")

    # Get base path without extension
    base_path = os.path.splitext(xls_path)[0]

    # check if parent directory is writeable instead of the file itself
    parent_dir = os.path.dirname(base_path)
    if parent_dir and not os.access(parent_dir, os.W_OK):
        raise ValueError(f"Parent directory is not writeable: {parent_dir}")
 
    # Return path with .pkl extension
    return f"{base_path}.pkl"


def load_graph_from_xls(file_path: str, 
                       node1_config: Dict = None,
                       node2_config: Dict = None,
                       edge_attr_cols: List[int] = None,
                       header: int = 0) -> GeneRegulatoryNetworkGraph:
    """
    从基因调控网络 XLS 文件初始化基因调控网络图（项目启动时调用）
    
    Args:
        file_path: 基因调控网络 XLS 文件路径
        node1_config: 第一个节点配置，格式: {"name_col": 0, "attr_cols": [1,2]}
        node2_config: 第二个节点配置，格式: {"name_col": 1, "attr_cols": [6,7]}
        edge_attr_cols: 边属性列索引列表，如 [3,5]
        header: 指定哪一行作为列名，默认为0（第一行）
    Returns:
        GeneRegulatoryNetworkGraph: 基因调控网络图实例
    """
    try:
        # 设置默认配置
        if node1_config is None:
            node1_config = {"name_col": 0, "attr_cols": []}
        if node2_config is None:
            node2_config = {"name_col": 1, "attr_cols": []}
        if edge_attr_cols is None:
            edge_attr_cols = []
            
        graph_file_path = get_graph_path(file_path)
        graph = GeneRegulatoryNetworkGraph(graph_file_path)
        graph.process_xls_file(file_path, node1_config, node2_config, edge_attr_cols, header)
        print(graph_file_path)
        graph.save_graph(graph_file_path)
        
        # 打印基因调控网络图信息
        # graph.print_graph_info(detailed=True)
        
        logger.info("基因调控网络图初始化完成")
        return graph
        
    except Exception as e:
        logger.error(f"初始化基因调控网络图失败: {str(e)}")
        raise


# 导出的主要接口
__all__ = [
    "GeneRegulatoryNetworkGraph",
    "load_graph_from_xls",
]
