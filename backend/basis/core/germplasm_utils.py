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

class GermplasmGraph:
    """
    种质资源关系图管理类
    负责构建、存储和查询种质资源之间的关系图
    """
    
    def __init__(self, graph_file_path: str = None):
        """
        初始化种质资源图
        
        Args:
            graph_file_path: 图数据存储文件路径
        """
        self.graph = nx.Graph()
        self.graph_file_path = graph_file_path or "germplasm_graph.pkl"
        self.metadata = {
            "created_at": None,
            "updated_at": None,
            "source_file": None,
            "node_count": 0,
            "edge_count": 0
        }
        
    def load_xls_data(self, file_path: str) -> pd.DataFrame:
        """
        从 XLS 文件加载数据（处理第一个工作表）
        
        Args:
            file_path: XLS 文件路径
            
        Returns:
            pandas.DataFrame: 加载的数据
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
                
            # 读取 XLS 文件的第一个工作表
            df = pd.read_excel(file_path)
                
            logger.info(f"成功加载 XLS 文件: {file_path}, 数据行数: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"加载 XLS 文件失败: {str(e)}")
            raise

    def extract_node_attributes(self, df: pd.DataFrame, 
                              col1_index: int = 4, col2_index: int = 5) -> Dict[str, Dict]: 
        """
        从数据框中提取节点属性信息
        
        Args:
            df: 数据框
            col1_index: 第一列索引（默认为4，即第五列）
            col2_index: 第二列索引（默认为5，即第六列）
            
        Returns:
            Dict[str, Dict]: 节点属性字典，key为节点ID，value为属性字典
        """
        try:
            node_attributes = {}
            
            # 获取列名
            column_names = df.columns.tolist()
            
            # 确定属性列（排除第一列、col1_index列和col2_index列）
            attribute_columns = []
            for i, col_name in enumerate(column_names):
                if i not in [0]:
                    attribute_columns.append((i, col_name))
            
            # 提取每行的节点属性
            for i in range(len(df)):
                # 获取节点ID（第一列）
                node_id = str(df.iloc[i, 0]).strip()
                
                # 检查节点ID是否有效
                if node_id and node_id.lower() not in ['nan', 'none', '']:
                    # 提取属性信息
                    attributes = {}
                    for col_idx, col_name in attribute_columns:
                        if col_idx < df.shape[1]:  # 确保列索引有效
                            attr_value = df.iloc[i, col_idx]
                            # 处理空值
                            if pd.notna(attr_value) and str(attr_value).strip().lower() not in ['nan', 'none', '']:
                                attributes[col_name] = str(attr_value).strip()
                    
                    # 如果节点已存在，合并属性（保留最新的非空值）
                    if node_id in node_attributes:
                        for key, value in attributes.items():
                            if value:  # 只更新非空值
                                node_attributes[node_id][key] = value
                    else:
                        node_attributes[node_id] = attributes
            
            logger.info(f"提取到 {len(node_attributes)} 个节点的属性信息")
            return node_attributes
            
        except Exception as e:
            logger.error(f"提取节点属性失败: {str(e)}")
            raise

    def extract_relationship_data(self, df: pd.DataFrame, 
                                col1_index: int = 4, col2_index: int = 5) -> List[Tuple[str, str, str]]:
        """
        从数据框中提取关系数据
        
        Args:
            df: 数据框
            col1_index: 第一列索引（默认为4，即第五列）
            col2_index: 第二列索引（默认为5，即第六列）
            
        Returns:
            List[Tuple[str, str, str]]: 关系对列表，包含 (node1, node2, relationship_type)
        """
        try:
            if df.shape[1] <= max(col1_index, col2_index, 0):  # 确保至少有第一列
                raise ValueError(f"数据列数不足，需要至少 {max(col1_index, col2_index, 0) + 1} 列")
            
            # 获取第一列、第五列和第六列数据
            col0_data = df.iloc[:, 0].astype(str)  # 第一列
            col1_data = df.iloc[:, col1_index].astype(str)  # 第五列
            col2_data = df.iloc[:, col2_index].astype(str)  # 第六列
            
            # 过滤空值和无效数据
            relationships = []
            for i in range(len(df)):
                val0 = str(col0_data.iloc[i]).strip()  # 第一列值
                val1 = str(col1_data.iloc[i]).strip()  # 第五列值
                val2 = str(col2_data.iloc[i]).strip()  # 第六列值
                
                # 检查值是否有效
                def is_valid_value(val):
                    return (val and val.lower() not in ['nan', 'none', ''])
                
                # 添加 crossing 关系（第五列和第六列之间）
                if (is_valid_value(val1) and is_valid_value(val2) and val1 != val2):
                    relationships.append((val1, val2, 'crossing'))
                
                # 添加 parent-offspring 关系（第一列与第五列、第六列）
                if is_valid_value(val0):
                    if is_valid_value(val1) and val0 != val1:
                        relationships.append((val0, val1, 'parent-offspring'))
                    if is_valid_value(val2) and val0 != val2:
                        relationships.append((val0, val2, 'parent-offspring'))
            
            logger.info(f"提取到 {len(relationships)} 个有效关系对")
            return relationships
            
        except Exception as e:
            logger.error(f"提取关系数据失败: {str(e)}")
            raise

    def build_graph(self, relationships: List[Tuple[str, str, str]], 
                   node_attributes: Dict[str, Dict] = None,
                   add_attributes: bool = True) -> None:
        """
        根据关系数据和节点属性构建图
        
        Args:
            relationships: 关系对列表，包含 (node1, node2, relationship_type)
            node_attributes: 节点属性字典
            add_attributes: 是否添加节点和边的属性
        """
        try:
            # 清空现有图
            self.graph.clear()
            
            # 添加边（会自动添加节点）
            for node1, node2, rel_type in relationships:
                self.graph.add_edge(node1, node2)
                
                # 添加边属性
                if add_attributes:
                    self.graph[node1][node2]['relationship_type'] = rel_type
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
            
            logger.info(f"图构建完成: {self.metadata['node_count']} 个节点, {self.metadata['edge_count']} 条边")
            
        except Exception as e:
            logger.error(f"构建图失败: {str(e)}")
            raise

    def process_xls_file(self, file_path: str, col1_index: int = 4, col2_index: int = 5) -> None:
        """
        处理 XLS 文件并构建图
        
        Args:
            file_path: XLS 文件路径
            col1_index: 第一列索引
            col2_index: 第二列索引
        """
        try:
            # 加载数据（处理第一个工作表）
            df = self.load_xls_data(file_path)
            
            # 提取节点属性信息
            node_attributes = self.extract_node_attributes(df, col1_index, col2_index)
            
            # 提取关系数据
            relationships = self.extract_relationship_data(df, col1_index, col2_index)
            
            # 构建图（包含节点属性）
            self.build_graph(relationships, node_attributes)
            
            # 更新元数据
            self.metadata["source_file"] = file_path
            self.metadata["created_at"] = datetime.now().isoformat()
            
            logger.info(f"XLS 文件处理完成: {file_path}")
            
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

    def get_relationship(self, node1: str, node2: str) -> Optional[Dict]:
        """
        获取两个节点之间的关系信息
        
        Args:
            node1: 节点1
            node2: 节点2
            
        Returns:
            Optional[Dict]: 关系信息
        """
        try:
            if self.graph.has_edge(node1, node2):
                edge_data = self.graph[node1][node2]
                return {
                    "node1": node1,
                    "node2": node2,
                    "relationship_type": edge_data.get('relationship_type', 'unknown'),
                    "weight": edge_data.get('weight', 1),
                    "created_at": edge_data.get('created_at', None),
                    "exists": True
                }
            else:
                return {
                    "node1": node1,
                    "node2": node2,
                    "exists": False
                }
                
        except Exception as e:
            logger.error(f"获取关系信息失败: {str(e)}")
            return None

    def get_batch_relationships(self, selected_nodes: List[str], 
                              include_internal: bool = True,
                              include_external: bool = False,
                              max_connections_per_node: int = 50) -> Optional[Dict]:
        """
        获取勾选节点的批量关系信息，用于构建知识图谱
        
        Args:
            selected_nodes: 勾选的种质资源节点ID列表
            include_internal: 是否包含勾选节点之间的内部关系
            include_external: 是否包含与外部节点的关系
            max_connections_per_node: 每个节点的最大连接数限制
            
        Returns:
            Optional[Dict]: 包含节点和边信息的知识图谱数据
        """
        try:
            # 验证节点是否存在
            valid_nodes = []
            for node_id in selected_nodes:
                if node_id in self.graph.nodes:
                    valid_nodes.append(node_id)
                else:
                    logger.warning(f"节点 {node_id} 在图中不存在，将被跳过")
            
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
            
            # 添加勾选的节点
            for node_id in valid_nodes:
                node_data = self.graph.nodes[node_id]
                result_nodes[node_id] = {
                    "id": node_id,
                    "label": node_id,
                    "degree": self.graph.degree(node_id),
                    "attributes": dict(node_data),
                    "selected": True  # 标记为勾选节点
                }
            
            # 收集边信息
            added_edges = set()  # 避免重复边
            
            for node_id in valid_nodes:
                neighbors = list(self.graph.neighbors(node_id))
                connection_count = 0
                
                for neighbor in neighbors:
                    if connection_count >= max_connections_per_node:
                        break
                    
                    # 检查是否应该包含这条边
                    should_include = False
                    
                    if include_internal and neighbor in valid_nodes:
                        # 内部关系：勾选节点之间的关系
                        should_include = True
                    elif include_external and neighbor not in valid_nodes:
                        # 外部关系：与非勾选节点的关系
                        should_include = True
                    
                    if should_include:
                        # 确保边的方向一致，避免重复
                        edge_key = tuple(sorted([node_id, neighbor]))
                        if edge_key not in added_edges:
                            # 添加邻居节点（如果还没添加）
                            if neighbor not in result_nodes:
                                neighbor_data = self.graph.nodes[neighbor]
                                result_nodes[neighbor] = {
                                    "id": neighbor,
                                    "label": neighbor,
                                    "degree": self.graph.degree(neighbor),
                                    "attributes": dict(neighbor_data),
                                    "selected": False  # 标记为非勾选节点
                                }
                            
                            # 添加边信息
                            edge_data = self.graph[node_id][neighbor]
                            result_edges.append({
                                "id": f"{node_id}_{neighbor}",
                                "source": node_id,
                                "target": neighbor,
                                "relationship_type": edge_data.get('relationship_type', 'unknown'),
                                "weight": edge_data.get('weight', 1),
                                "created_at": edge_data.get('created_at', None)
                            })
                            
                            added_edges.add(edge_key)
                            connection_count += 1
            
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
                "max_connections_per_node": max_connections_per_node
            }
            
            return {
                "nodes": nodes_list,
                "edges": result_edges,
                "statistics": statistics
            }
                
        except Exception as e:
            logger.error(f"获取批量关系信息失败: {str(e)}")
            return None

    def get_nodes_with_search(self, keyword: str = None, exact_match: bool = False, page: int = 1, page_size: int = 20) -> Dict[str, any]:
        """
        获取节点列表，支持可选的关键词搜索和分页功能
        
        Args:
            keyword: 搜索关键词，如果为None则返回所有节点
            exact_match: 是否精确匹配（仅在提供keyword时有效）
            page: 页码（从1开始）
            page_size: 每页节点数量
            
        Returns:
            Dict containing:
                - nodes: List of node information for current page
                - total: Total number of nodes (filtered or all)
                - total_pages: Total number of pages
                - current_page: Current page number
                - page_size: Number of nodes per page
                - search_params: Search parameters used (if any)
        """
        try:
            # 如果提供了关键词，则进行搜索
            if keyword:
                matched_nodes = set()
                keyword_lower = keyword.lower()
                
                for node in self.graph.nodes():
                    # 检查节点ID
                    if exact_match:
                        if node == keyword:
                            matched_nodes.add(node)
                    else:
                        if keyword_lower in node.lower():
                            matched_nodes.add(node)
                    
                    # 检查所有节点属性
                    node_attrs = self.graph.nodes[node]
                    for attr_value in node_attrs.values():
                        if attr_value is not None:
                            attr_str = str(attr_value).lower()
                            if exact_match:
                                if attr_str == keyword_lower:
                                    matched_nodes.add(node)
                                    break
                            else:
                                if keyword_lower in attr_str:
                                    matched_nodes.add(node)
                                    break
                
                all_nodes = sorted(list(matched_nodes))
            else:
                # 如果没有关键词，返回所有节点
                all_nodes = sorted(list(self.graph.nodes()))
            
            total_nodes = len(all_nodes)
            
            # 计算分页信息
            total_pages = (total_nodes + page_size - 1) // page_size if total_nodes > 0 else 1
            page = max(1, min(page, total_pages))  # 确保页码在有效范围内
            
            # 获取当前页的节点
            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, total_nodes)
            current_page_nodes = all_nodes[start_idx:end_idx]
            
            # 获取每个节点的详细信息
            nodes_info = []
            for node in current_page_nodes:
                node_data = self.graph.nodes[node]
                neighbors = list(self.graph.neighbors(node))
                nodes_info.append({
                    "id": node,
                    "degree": self.graph.degree(node),
                    "neighbor_count": len(neighbors),
                    "attributes": dict(node_data)
                })
            
            result = {
                "nodes": nodes_info,
                "total": total_nodes,
                "total_pages": total_pages,
                "current_page": page,
                "page_size": page_size
            }
            
            # 如果进行了搜索，添加搜索参数信息
            if keyword:
                result["search_params"] = {
                    "keyword": keyword,
                    "exact_match": exact_match
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get nodes with search: {str(e)}")
            return {
                "nodes": [],
                "total": 0,
                "total_pages": 0,
                "current_page": page,
                "page_size": page_size,
                "search_params": {"keyword": keyword, "exact_match": exact_match} if keyword else None
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
    

    
    # 注意：search_nodes 函数已被合并到 get_nodes_with_search 函数中
    # 使用 get_nodes_with_search(keyword="your_keyword") 来搜索节点
     
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
        打印图的详细信息
        
        Args:
            detailed: 是否显示详细信息
            max_nodes_display: 最大显示节点数
            max_edges_display: 最大显示边数
        """
        try:
            print("\n" + "="*60)
            print("种质资源关系图信息")
            print("="*60)
            
            # 基本统计信息
            stats = self.get_graph_statistics()
            print(f"\n📊 基本统计:")
            print(f"   节点数量: {stats.get('node_count', 0)}")
            print(f"   边数量: {stats.get('edge_count', 0)}")
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
                # 显示部分节点信息
                print(f"\n🌟 节点信息 (显示前 {max_nodes_display} 个):")
                nodes_to_show = list(self.graph.nodes())[:max_nodes_display]
                for i, node in enumerate(nodes_to_show, 1):
                    degree = self.graph.degree(node)
                    neighbors = list(self.graph.neighbors(node))
                    print(f"   {i:2d}. {node} (度数: {degree}, 邻居: {len(neighbors)})")
                    if len(neighbors) <= 5:
                        print(f"       邻居: {', '.join(neighbors)}")
                    else:
                        print(f"       邻居: {', '.join(neighbors[:5])}...")
                
                if len(self.graph.nodes()) > max_nodes_display:
                    print(f"   ... 还有 {len(self.graph.nodes()) - max_nodes_display} 个节点")
                
                # 显示部分边信息
                print(f"\n🔗 边信息 (显示前 {max_edges_display} 条):")
                edges_to_show = list(self.graph.edges(data=True))[:max_edges_display]
                for i, (node1, node2, data) in enumerate(edges_to_show, 1):
                    rel_type = data.get('relationship_type', 'unknown')
                    weight = data.get('weight', 1)
                    print(f"   {i:2d}. {node1} -- {node2} ({rel_type}, 权重: {weight})")
                
                if len(self.graph.edges()) > max_edges_display:
                    print(f"   ... 还有 {len(self.graph.edges()) - max_edges_display} 条边")
            
            # 度数分布
            if self.graph.number_of_nodes() > 0:
                degrees = [self.graph.degree(node) for node in self.graph.nodes()]
                degree_dist = {}
                for degree in degrees:
                    degree_dist[degree] = degree_dist.get(degree, 0) + 1
                
                print(f"\n📈 度数分布:")
                sorted_degrees = sorted(degree_dist.items())
                for degree, count in sorted_degrees[:10]:  # 显示前10个度数
                    print(f"   度数 {degree}: {count} 个节点")
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


def get_global_graph(graph_file_path: str) -> GermplasmGraph:
    """
    获取全局图实例（单例模式）
    
    Args:
        graph_file_path: 图数据文件路径
        
    Returns:
        GermplasmGraph: 全局图实例
    """
    global _global_graph
    if _global_graph is None:
        _global_graph = GermplasmGraph(graph_file_path)
        # 尝试加载已存在的图数据
        _global_graph.load_graph()
    return _global_graph


def load_graph_from_xls(file_path: str, col1_index: int = 4, col2_index: int = 5) -> GermplasmGraph:
    """
    从 XLS 文件初始化图（项目启动时调用）
    
    Args:
        file_path: XLS 文件路径
        col1_index: 第一列索引
        col2_index: 第二列索引        
    Returns:
        GermplasmGraph: 图实例
    """
    try:
        graph_file_path = get_graph_path(file_path)
        graph = GermplasmGraph(graph_file_path)
        graph.process_xls_file(file_path, col1_index, col2_index)
        print(graph_file_path)
        graph.save_graph(graph_file_path)
        
        # 打印图信息
        # graph.print_graph_info(detailed=True)
        
        logger.info("种质资源图初始化完成")
        return graph
        
    except Exception as e:
        logger.error(f"初始化图失败: {str(e)}")
        raise

# 导出的主要接口
__all__ = [
    "GermplasmGraph",
    "get_global_graph",
    "load_graph_from_xls",
]
