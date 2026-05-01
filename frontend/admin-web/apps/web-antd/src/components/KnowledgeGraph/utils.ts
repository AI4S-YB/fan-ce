import type { GraphData, GraphNode, GraphEdge } from './types';

// 通用数据项接口
export interface BaseDataItem {
  id: string;
  degree: number;
  attributes?: Record<string, any>;
}

// 支持父子关系的数据项接口
export interface ParentChildDataItem extends BaseDataItem {
  attributes: {
    P?: string; // 父本ID
    M?: string; // 母本ID
    [key: string]: any;
  };
}

/**
 * 通用的数据转换函数：将具有父子关系的数据转换为图谱数据
 * @param dataList 数据列表
 * @param options 转换选项
 * @returns 图谱数据
 */
export function transformToGraphData(
  dataList: ParentChildDataItem[], 
  options: {
    parentKey?: string;
    motherKey?: string;
    enableCrossingEdges?: boolean;
  } = {}
): GraphData {
  const { 
    parentKey = 'P', 
    motherKey = 'M', 
    enableCrossingEdges = true 
  } = options;
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  const edgeSet = new Set<string>(); // 用于去重

  // 转换节点数据
  dataList.forEach(item => {
    nodes.push({
      id: item.id,
      label: item.id,
      degree: item.degree,
      size: calculateNodeSize(item.degree),
      attributes: item.attributes,
    });
  });

  // 构建边数据 - 基于父母本关系
  dataList.forEach(item => {
    // 添加与父本的连接
    const parentId = item.attributes?.[parentKey];
    if (parentId) {
      const parentExists = dataList.some(n => n.id === parentId);
      
      if (parentExists) {
        const edgeId1 = `${item.id}-${parentId}`;
        const edgeId2 = `${parentId}-${item.id}`;
        
        if (!edgeSet.has(edgeId1) && !edgeSet.has(edgeId2)) {
          edges.push({
            id: edgeId1,
            source: item.id,
            target: parentId,
            relationshipType: 'parent-offspring',
          });
          edgeSet.add(edgeId1);
        }
      }
    }
    
    // 添加与母本的连接
    const motherId = item.attributes?.[motherKey];
    if (motherId) {
      const motherExists = dataList.some(n => n.id === motherId);
      
      if (motherExists) {
        const edgeId1 = `${item.id}-${motherId}`;
        const edgeId2 = `${motherId}-${item.id}`;
        
        if (!edgeSet.has(edgeId1) && !edgeSet.has(edgeId2)) {
          edges.push({
            id: edgeId1,
            source: item.id,
            target: motherId,
            relationshipType: 'parent-offspring',
          });
          edgeSet.add(edgeId1);
        }
      }
    }
    
    // 添加父母本之间的杂交连接
    if (enableCrossingEdges && parentId && motherId) {
      const parentExists = dataList.some(n => n.id === parentId);
      const motherExists = dataList.some(n => n.id === motherId);
      
      if (parentExists && motherExists && parentId !== motherId) {
        const edgeId1 = `${parentId}-${motherId}`;
        const edgeId2 = `${motherId}-${parentId}`;
        
        if (!edgeSet.has(edgeId1) && !edgeSet.has(edgeId2)) {
          edges.push({
            id: edgeId1,
            source: parentId,
            target: motherId,
            relationshipType: 'crossing',
          });
          edgeSet.add(edgeId1);
        }
      }
    }
  });

  return {
    nodes,
    edges,
  };
}

/**
 * 种质资源数据转换函数（兼容性函数）
 * @param germplasmList 种质资源列表
 * @returns 图谱数据
 */
export function transformGermplasmToGraphData(germplasmList: any[]): GraphData {
  return transformToGraphData(germplasmList, {
    parentKey: 'P',
    motherKey: 'M',
    enableCrossingEdges: true,
  });
}

/**
 * 根据度数计算节点大小
 * @param degree 节点度数
 * @returns 节点大小
 */
function calculateNodeSize(degree: number): number {
  const minSize = 6;
  const maxSize = 20;
  const scale = 2;
  
  const normalizedDegree = Math.max(degree, 1);
  const size = minSize + (normalizedDegree * scale);
  
  return Math.min(size, maxSize);
}

/**
 * 过滤图谱数据
 * @param graphData 原始图谱数据
 * @param options 过滤选项
 * @returns 过滤后的图谱数据
 */
export function filterGraphData(
  graphData: GraphData,
  options: {
    minDegree?: number;
    maxDegree?: number;
    maxNodes?: number;
    keyword?: string;
  }
): GraphData {
  let filteredNodes = [...graphData.nodes];

  // 根据度数过滤
  if (options.minDegree !== undefined) {
    filteredNodes = filteredNodes.filter(node => node.degree >= options.minDegree!);
  }
  if (options.maxDegree !== undefined) {
    filteredNodes = filteredNodes.filter(node => node.degree <= options.maxDegree!);
  }

  // 关键词搜索
  if (options.keyword) {
    const keyword = options.keyword.toLowerCase();
    filteredNodes = filteredNodes.filter(node =>
      node.id.toLowerCase().includes(keyword) ||
      node.label.toLowerCase().includes(keyword) ||
      (node.attributes && Object.values(node.attributes).some(value =>
        String(value).toLowerCase().includes(keyword)
      ))
    );
  }

  // 限制节点数量（按度数排序，保留度数最高的节点）
  if (options.maxNodes && filteredNodes.length > options.maxNodes) {
    filteredNodes.sort((a, b) => b.degree - a.degree);
    filteredNodes = filteredNodes.slice(0, options.maxNodes);
  }

  // 过滤相关的边
  const nodeIds = new Set(filteredNodes.map(node => node.id));
  const filteredEdges = graphData.edges.filter(edge => {
    const sourceId = typeof edge.source === 'string' ? edge.source : edge.source.id;
    const targetId = typeof edge.target === 'string' ? edge.target : edge.target.id;
    return nodeIds.has(sourceId) && nodeIds.has(targetId);
  });

  return {
    nodes: filteredNodes,
    edges: filteredEdges,
  };
}

/**
 * 计算图谱统计信息
 * @param graphData 图谱数据
 * @returns 统计信息
 */
export function calculateGraphStats(graphData: GraphData) {
  const { nodes, edges } = graphData;

  if (nodes.length === 0) {
    return {
      nodeCount: 0,
      edgeCount: 0,
      avgDegree: 0,
      maxDegree: 0,
      minDegree: 0,
      density: 0,
    };
  }

  const degrees = nodes.map(n => n.degree);
  const maxDegree = Math.max(...degrees);
  const minDegree = Math.min(...degrees);
  const avgDegree = degrees.reduce((sum, degree) => sum + degree, 0) / degrees.length;
  
  // 图密度 = 实际边数 / 最大可能边数
  const maxPossibleEdges = (nodes.length * (nodes.length - 1)) / 2;
  const density = maxPossibleEdges > 0 ? edges.length / maxPossibleEdges : 0;

  return {
    nodeCount: nodes.length,
    edgeCount: edges.length,
    avgDegree: Number(avgDegree.toFixed(2)),
    maxDegree,
    minDegree,
    density: Number(density.toFixed(4)),
  };
}

/**
 * 根据中心性算法找出重要节点
 * @param graphData 图谱数据
 * @param topN 返回前N个重要节点
 * @returns 重要节点列表
 */
export function findImportantNodes(graphData: GraphData, topN: number = 10): GraphNode[] {
  // 简单的基于度数的中心性计算
  const sortedNodes = [...graphData.nodes].sort((a, b) => b.degree - a.degree);
  return sortedNodes.slice(0, topN);
}

/**
 * 查找两个节点之间的最短路径
 * @param graphData 图谱数据
 * @param sourceId 源节点ID
 * @param targetId 目标节点ID
 * @returns 路径上的节点ID数组，如果没有路径则返回空数组
 */
export function findShortestPath(graphData: GraphData, sourceId: string, targetId: string): string[] {
  if (sourceId === targetId) return [sourceId];

  // 构建邻接表
  const adjacencyMap = new Map<string, string[]>();
  graphData.nodes.forEach(node => {
    adjacencyMap.set(node.id, []);
  });

  graphData.edges.forEach(edge => {
    const source = typeof edge.source === 'string' ? edge.source : edge.source.id;
    const target = typeof edge.target === 'string' ? edge.target : edge.target.id;
    
    adjacencyMap.get(source)?.push(target);
    adjacencyMap.get(target)?.push(source);
  });

  // BFS寻找最短路径
  const queue: string[] = [sourceId];
  const visited = new Set<string>([sourceId]);
  const parent = new Map<string, string>();

  while (queue.length > 0) {
    const current = queue.shift()!;
    
    if (current === targetId) {
      // 构建路径
      const path: string[] = [];
      let node = targetId;
      while (node !== undefined) {
        path.unshift(node);
        node = parent.get(node)!;
      }
      return path;
    }

    const neighbors = adjacencyMap.get(current) || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        parent.set(neighbor, current);
        queue.push(neighbor);
      }
    }
  }

  return []; // 没有找到路径
}