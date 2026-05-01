import { ref, computed } from 'vue';
import type { GraphData, GraphNode } from './types';
import { transformToGraphData, filterGraphData, calculateGraphStats, findImportantNodes } from './utils';
import type { ParentChildDataItem } from './utils';

/**
 * 知识图谱通用Hook
 */
export function useKnowledgeGraph() {
  const loading = ref(false);
  const rawGraphData = ref<GraphData>({ nodes: [], edges: [] });
  const filteredGraphData = ref<GraphData>({ nodes: [], edges: [] });
  
  // 过滤条件
  const maxNodes = ref(100);
  const minDegree = ref(0);
  const keyword = ref('');

  // 计算属性
  const graphStats = computed(() => {
    if (!filteredGraphData.value.nodes.length) return null;
    return calculateGraphStats(filteredGraphData.value);
  });

  const importantNodes = computed(() => {
    if (!filteredGraphData.value.nodes.length) return [];
    return findImportantNodes(filteredGraphData.value, 10);
  });

  /**
   * 从数据列表构建图谱
   */
  const buildGraphFromData = (
    dataList: ParentChildDataItem[], 
    options?: {
      parentKey?: string;
      motherKey?: string;
      enableCrossingEdges?: boolean;
    }
  ) => {
    loading.value = true;
    try {
      const graphData = transformToGraphData(dataList, options);
      rawGraphData.value = graphData;
      applyFilters();
      return graphData;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 应用过滤条件
   */
  const applyFilters = () => {
    const filtered = filterGraphData(rawGraphData.value, {
      maxNodes: maxNodes.value,
      minDegree: minDegree.value,
      keyword: keyword.value.trim() || undefined,
    });
    filteredGraphData.value = filtered;
  };

  /**
   * 设置过滤条件
   */
  const setFilters = (filters: {
    maxNodes?: number;
    minDegree?: number;
    keyword?: string;
  }) => {
    if (filters.maxNodes !== undefined) maxNodes.value = filters.maxNodes;
    if (filters.minDegree !== undefined) minDegree.value = filters.minDegree;
    if (filters.keyword !== undefined) keyword.value = filters.keyword;
    applyFilters();
  };

  /**
   * 重置图谱数据
   */
  const resetGraph = () => {
    rawGraphData.value = { nodes: [], edges: [] };
    filteredGraphData.value = { nodes: [], edges: [] };
    maxNodes.value = 100;
    minDegree.value = 0;
    keyword.value = '';
  };

  /**
   * 高亮节点
   */
  const highlightNode = (nodeId: string) => {
    // 这个功能需要图谱组件配合实现
    return nodeId;
  };

  return {
    // 数据状态
    loading,
    rawGraphData,
    filteredGraphData,
    
    // 过滤条件
    maxNodes,
    minDegree,
    keyword,
    
    // 计算属性
    graphStats,
    importantNodes,
    
    // 方法
    buildGraphFromData,
    applyFilters,
    setFilters,
    resetGraph,
    highlightNode,
  };
}