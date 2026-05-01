<script setup lang="ts">
import type { GraphData, GraphEdge, GraphNode } from './types';

import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import { Button, Input, message, Spin } from 'ant-design-vue';
import { $t } from '@vben/locales';
import * as d3 from 'd3';

const props = withDefaults(defineProps<Props>(), {
  width: 800,
  height: 600,
  layoutMode: 'force',
  loading: false,
});
const emit = defineEmits<Emits>();
// 组件
const AInputSearch = Input.Search;
const AButton = Button;
const ASpin = Spin;

// Props和Emits
interface Props {
  data: GraphData;
  width?: number;
  height?: number;
  layoutMode?: 'force' | 'generation';
  loading?: boolean;
}

interface Emits {
  (e: 'nodeClick', node: GraphNode): void;
  (e: 'nodeHover', node: GraphNode | null): void;
}

// 响应式数据
const graphContainer = ref<HTMLElement>();
const tooltip = ref<HTMLElement>();
const searchKeyword = ref('');
const tooltipVisible = ref(false);
const tooltipPosition = ref({ x: 0, y: 0 });
const hoveredNode = ref<GraphNode | null>(null);
const graphData = ref<GraphData>({ nodes: [], edges: [] });

// D3相关变量
let svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;
let simulation: d3.Simulation<GraphNode, GraphEdge>;
let nodeSelection: d3.Selection<
  SVGCircleElement,
  GraphNode,
  SVGGElement,
  unknown
>;
let linkSelection: d3.Selection<
  SVGLineElement,
  GraphEdge,
  SVGGElement,
  unknown
>;
let labelSelection: d3.Selection<
  SVGTextElement,
  GraphNode,
  SVGGElement,
  unknown
>;

// 配置常量
const CONFIG = {
  nodeRadius: {
    min: 6,
    max: 20,
    scale: 3,
  },
  colors: {
    node: '#3b82f6',
    nodeHighlight: '#f59e0b',
    nodeSearch: '#10b981',
    edge: '#94a3b8',
    edgeHighlight: '#3b82f6',
    nodeFocus: '#f59e0b',
    nodePlaceholder: '#cbd5e1',
    edgeFather: '#2563eb',
    edgeMother: '#db2777',
    edgeCrossing: '#8b5cf6',
  },
  simulation: {
    linkDistance: 100,
    linkStrength: 0.1,
    chargeStrength: -300,
    centerStrength: 0.1,
  },
};

const getNodeBaseColor = (node: GraphNode) => {
  if (node.color) {
    return node.color;
  }
  if (node.selected) {
    return CONFIG.colors.nodeFocus;
  }
  if (node.attributes?.is_placeholder) {
    return CONFIG.colors.nodePlaceholder;
  }
  return CONFIG.colors.node;
};

const getEdgeBaseColor = (edge: GraphEdge) => {
  if (edge.relationshipType === 'father') {
    return CONFIG.colors.edgeFather;
  }
  if (edge.relationshipType === 'mother') {
    return CONFIG.colors.edgeMother;
  }
  if (edge.relationshipType === 'crossing') {
    return CONFIG.colors.edgeCrossing;
  }
  return CONFIG.colors.edge;
};

// 计算节点大小
const calculateNodeSize = (degree: number, maxDegree: number): number => {
  const normalizedDegree = Math.max(degree, 1);
  const scale =
    (normalizedDegree / Math.max(maxDegree, 1)) * CONFIG.nodeRadius.scale;
  return Math.max(
    CONFIG.nodeRadius.min,
    Math.min(CONFIG.nodeRadius.max, CONFIG.nodeRadius.min + scale),
  );
};

const getNodeId = (node: GraphNode | string) =>
  typeof node === 'string' ? node : node.id;

const buildGenerationLayout = (data: GraphData) => {
  const parentToChildren = new Map<string, string[]>();
  const indegree = new Map<string, number>();
  const levels = new Map<string, number>();

  data.nodes.forEach((node) => {
    indegree.set(node.id, 0);
    parentToChildren.set(node.id, []);
  });

  data.edges.forEach((edge) => {
    const sourceId = getNodeId(edge.source);
    const targetId = getNodeId(edge.target);
    parentToChildren.get(sourceId)?.push(targetId);
    indegree.set(targetId, (indegree.get(targetId) || 0) + 1);
  });

  const queue = data.nodes
    .filter((node) => (indegree.get(node.id) || 0) === 0)
    .map((node) => node.id);

  queue.forEach((nodeId) => {
    levels.set(nodeId, 0);
  });

  while (queue.length > 0) {
    const currentId = queue.shift()!;
    const currentLevel = levels.get(currentId) || 0;
    const children = parentToChildren.get(currentId) || [];

    children.forEach((childId) => {
      levels.set(childId, Math.max(levels.get(childId) || 0, currentLevel + 1));
      indegree.set(childId, (indegree.get(childId) || 0) - 1);
      if ((indegree.get(childId) || 0) <= 0) {
        queue.push(childId);
      }
    });
  }

  let fallbackLevel = Math.max(...levels.values(), 0);
  data.nodes.forEach((node) => {
    if (!levels.has(node.id)) {
      fallbackLevel += 1;
      levels.set(node.id, fallbackLevel);
    }
  });

  const grouped = new Map<number, GraphNode[]>();
  data.nodes.forEach((node) => {
    const level = levels.get(node.id) || 0;
    if (!grouped.has(level)) {
      grouped.set(level, []);
    }
    grouped.get(level)!.push(node);
  });

  const maxLevel = Math.max(...grouped.keys(), 0);
  const verticalSpacing = Math.max(
    110,
    (props.height - 140) / Math.max(maxLevel, 1),
  );
  const layout = new Map<string, { level: number; x: number; y: number }>();

  [...grouped.entries()]
    .sort((left, right) => left[0] - right[0])
    .forEach(([level, nodes]) => {
      const sortedNodes = [...nodes].sort((left, right) =>
        left.label.localeCompare(right.label),
      );
      const horizontalSpacing = props.width / (sortedNodes.length + 1);
      sortedNodes.forEach((node, index) => {
        layout.set(node.id, {
          level,
          x: horizontalSpacing * (index + 1),
          y: 90 + level * verticalSpacing,
        });
      });
    });

  return layout;
};

// 初始化图谱
const initGraph = () => {
  if (!graphContainer.value) return;

  // 清理之前的SVG
  d3.select(graphContainer.value).selectAll('*').remove();

  // 创建SVG
  svg = d3
    .select(graphContainer.value)
    .append('svg')
    .attr('width', '100%')
    .attr('height', '100%')
    .attr('viewBox', `0 0 ${props.width} ${props.height}`)
    .call(
      d3
        .zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
          svg.select('.graph-content').attr('transform', event.transform);
        }),
    );

  // 创建图形内容组
  const graphContent = svg.append('g').attr('class', 'graph-content');

  // 创建连线组
  graphContent.append('g').attr('class', 'links');

  // 创建节点组
  graphContent.append('g').attr('class', 'nodes');

  // 创建标签组
  graphContent.append('g').attr('class', 'labels');

  // 初始化力导向模拟
  simulation = d3
    .forceSimulation<GraphNode>()
    .force(
      'link',
      d3
        .forceLink<GraphNode, GraphEdge>()
        .id((d) => d.id)
        .distance(CONFIG.simulation.linkDistance)
        .strength(CONFIG.simulation.linkStrength),
    )
    .force(
      'charge',
      d3.forceManyBody().strength(CONFIG.simulation.chargeStrength),
    )
    .force(
      'center',
      d3
        .forceCenter(props.width / 2, props.height / 2)
        .strength(CONFIG.simulation.centerStrength),
    )
    .force(
      'collision',
      d3.forceCollide().radius((d) => calculateNodeSize(d.degree, 10) + 2),
    );
};

// 更新图谱数据
const updateGraph = () => {
  if (!svg || !simulation) return;

  svg.attr('viewBox', `0 0 ${props.width} ${props.height}`);

  const data = props.data;
  graphData.value = {
    nodes: [...data.nodes],
    edges: [...data.edges],
  };

  const maxDegree = Math.max(...data.nodes.map((n) => n.degree), 1);

  // 处理节点
  nodeSelection = svg
    .select('.nodes')
    .selectAll<SVGCircleElement, GraphNode>('circle')
    .data(data.nodes, (d) => d.id);

  nodeSelection.exit().remove();

  const nodeEnter = nodeSelection
    .enter()
    .append('circle')
    .attr('stroke', '#ffffff')
    .attr('stroke-width', 2)
    .style('cursor', 'pointer')
    .call(
      d3
        .drag<SVGCircleElement, GraphNode>()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }),
    );

  nodeSelection = nodeEnter.merge(nodeSelection);
  nodeSelection
    .attr('r', (d) => calculateNodeSize(d.degree, maxDegree))
    .attr('fill', (d) => getNodeBaseColor(d))
    .attr('stroke', '#ffffff')
    .attr('stroke-width', 2);

  // 添加节点交互
  nodeSelection
    .on('mouseover', handleNodeMouseOver)
    .on('mouseout', handleNodeMouseOut)
    .on('click', handleNodeClick);

  // 处理连线
  linkSelection = svg
    .select('.links')
    .selectAll<SVGLineElement, GraphEdge>('line')
    .data(data.edges, (d) => d.id);

  linkSelection.exit().remove();

  const linkEnter = linkSelection
    .enter()
    .append('line')
    .attr('stroke', (d) => getEdgeBaseColor(d))
    .attr('stroke-width', (d) =>
      d.relationshipType === 'father' || d.relationshipType === 'mother'
        ? 2
        : 1.2,
    )
    .attr('stroke-opacity', 0.6);

  linkSelection = linkEnter.merge(linkSelection);

  // 处理标签
  labelSelection = svg
    .select('.labels')
    .selectAll<SVGTextElement, GraphNode>('text')
    .data(data.nodes, (d) => d.id);

  labelSelection.exit().remove();

  const labelEnter = labelSelection
    .enter()
    .append('text')
    .text((d) => d.label || d.id)
    .attr('font-size', '12px')
    .attr('font-family', 'Arial, sans-serif')
    .attr('fill', '#374151')
    .attr('text-anchor', 'middle')
    .attr('pointer-events', 'none');

  labelSelection = labelEnter.merge(labelSelection);

  // 更新力导向模拟
  const linkForce =
    simulation.force<d3.ForceLink<GraphNode, GraphEdge>>('link')!;
  const collisionForce = d3
    .forceCollide<GraphNode>()
    .radius((d) => calculateNodeSize(d.degree, maxDegree) + 6);

  if (props.layoutMode === 'generation') {
    const generationLayout = buildGenerationLayout(data);
    data.nodes.forEach((node) => {
      const target = generationLayout.get(node.id);
      if (target && (node.x === undefined || node.y === undefined)) {
        node.x = target.x;
        node.y = target.y;
      }
    });

    simulation
      .force(
        'x',
        d3
          .forceX<GraphNode>(
            (node) => generationLayout.get(node.id)?.x || props.width / 2,
          )
          .strength(1),
      )
      .force(
        'y',
        d3
          .forceY<GraphNode>(
            (node) => generationLayout.get(node.id)?.y || props.height / 2,
          )
          .strength(1),
      )
      .force('charge', d3.forceManyBody().strength(-90))
      .force('center', null)
      .force('collision', collisionForce);

    linkForce.distance(80).strength(0.15);
  } else {
    simulation
      .force('x', d3.forceX(props.width / 2).strength(0.02))
      .force('y', d3.forceY(props.height / 2).strength(0.02))
      .force(
        'charge',
        d3.forceManyBody().strength(CONFIG.simulation.chargeStrength),
      )
      .force(
        'center',
        d3
          .forceCenter(props.width / 2, props.height / 2)
          .strength(CONFIG.simulation.centerStrength),
      )
      .force('collision', collisionForce);

    linkForce
      .distance(CONFIG.simulation.linkDistance)
      .strength(CONFIG.simulation.linkStrength);
  }

  simulation.nodes(data.nodes);
  linkForce.links(data.edges);
  simulation.alpha(1).restart();

  // 绑定更新函数
  simulation.on('tick', () => {
    linkSelection
      .attr('x1', (d) => (d.source as GraphNode).x!)
      .attr('y1', (d) => (d.source as GraphNode).y!)
      .attr('x2', (d) => (d.target as GraphNode).x!)
      .attr('y2', (d) => (d.target as GraphNode).y!);

    nodeSelection.attr('cx', (d) => d.x!).attr('cy', (d) => d.y!);

    labelSelection.attr('x', (d) => d.x!).attr('y', (d) => d.y! + 4);
  });
};

// 节点鼠标悬停事件
const handleNodeMouseOver = (event: MouseEvent, d: GraphNode) => {
  hoveredNode.value = d;
  tooltipVisible.value = true;
  tooltipPosition.value = {
    x: event.clientX + 10,
    y: event.clientY - 10,
  };

  // 高亮节点和相关连线
  highlightNode(d.id, true);
};

// 节点鼠标离开事件
const handleNodeMouseOut = () => {
  hoveredNode.value = null;
  tooltipVisible.value = false;

  // 取消高亮
  resetHighlight();
};

// 节点点击事件
const handleNodeClick = (event: MouseEvent, d: GraphNode) => {
  emit('nodeClick', d);
};

// 高亮节点及其相关连线
const highlightNode = (nodeId: string, highlight: boolean) => {
  const edgeColor = highlight
    ? CONFIG.colors.edgeHighlight
    : CONFIG.colors.edge;

  const connectedNodeIds = new Set<string>();
  graphData.value.edges.forEach((edge) => {
    const source = edge.source as GraphNode;
    const target = edge.target as GraphNode;
    if (source.id === nodeId) {
      connectedNodeIds.add(target.id);
    }
    if (target.id === nodeId) {
      connectedNodeIds.add(source.id);
    }
  });

  // 高亮目标节点
  nodeSelection
    .attr('fill', (d) => getNodeBaseColor(d))
    .attr('stroke', (d) => {
      if (d.id === nodeId) {
        return '#1f2937';
      }
      if (connectedNodeIds.has(d.id)) {
        return CONFIG.colors.nodeHighlight;
      }
      return '#ffffff';
    })
    .attr('stroke-width', (d) => {
      if (d.id === nodeId) {
        return 4;
      }
      if (connectedNodeIds.has(d.id)) {
        return 3;
      }
      return 2;
    });

  // 高亮相关连线
  linkSelection
    .attr('stroke', (d) => {
      const source = d.source as GraphNode;
      const target = d.target as GraphNode;
      return source.id === nodeId || target.id === nodeId
        ? edgeColor
        : getEdgeBaseColor(d);
    })
    .attr('stroke-width', (d) => {
      const source = d.source as GraphNode;
      const target = d.target as GraphNode;
      return source.id === nodeId || target.id === nodeId ? 2 : 1;
    });
};

// 重置高亮
const resetHighlight = () => {
  if (!nodeSelection || !linkSelection) return;

  nodeSelection
    .attr('fill', (d) => getNodeBaseColor(d))
    .attr('stroke', '#ffffff')
    .attr('stroke-width', 2);

  linkSelection
    .attr('stroke', (d) => getEdgeBaseColor(d))
    .attr('stroke-width', (d) =>
      d.relationshipType === 'father' || d.relationshipType === 'mother'
        ? 2
        : 1.2,
    );
};

// 搜索功能
const handleSearch = (value: string) => {
  if (!value.trim()) {
    resetHighlight();
    return;
  }

  const foundNode = graphData.value.nodes.find((node) =>
    node.id.toLowerCase().includes(value.toLowerCase()),
  );

  if (foundNode) {
    highlightSearchResult(foundNode.id);
    // 将视图中心移动到找到的节点
    centerOnNode(foundNode);
    message.success($t('component.graph.findGermplasm', { id: foundNode.id }));
  } else {
    message.warning($t('component.graph.germplasmNotFound', { keyword: value }));
  }
};

// 搜索输入变化
const handleSearchChange = (e: Event) => {
  const value = (e.target as HTMLInputElement).value;
  if (!value.trim()) {
    resetHighlight();
  }
};

// 高亮搜索结果
const highlightSearchResult = (nodeId: string) => {
  resetHighlight();

  nodeSelection
    .attr('fill', (d) =>
      d.id === nodeId ? CONFIG.colors.nodeSearch : getNodeBaseColor(d),
    )
    .attr('stroke-width', (d) => (d.id === nodeId ? 4 : 2));
};

// 将视图中心移动到指定节点
const centerOnNode = (node: GraphNode) => {
  if (!svg || !node.x || !node.y) return;

  const scale = 1.5;
  const x = -node.x * scale + props.width / 2;
  const y = -node.y * scale + props.height / 2;

  svg
    .transition()
    .duration(750)
    .call(
      d3.zoom<SVGSVGElement, unknown>().transform,
      d3.zoomIdentity.translate(x, y).scale(scale),
    );
};

// 重置视图
const resetView = () => {
  if (!svg) return;

  svg
    .transition()
    .duration(750)
    .call(d3.zoom<SVGSVGElement, unknown>().transform, d3.zoomIdentity);

  resetHighlight();
  searchKeyword.value = '';
};

// 适应内容
const fitToContent = () => {
  if (!svg || graphData.value.nodes.length === 0) return;

  const nodes = graphData.value.nodes;
  const xExtent = d3.extent(nodes, (d) => d.x!) as [number, number];
  const yExtent = d3.extent(nodes, (d) => d.y!) as [number, number];

  const width = xExtent[1] - xExtent[0];
  const height = yExtent[1] - yExtent[0];

  const centerX = (xExtent[0] + xExtent[1]) / 2;
  const centerY = (yExtent[0] + yExtent[1]) / 2;

  const scale = Math.min(
    (props.width * 0.8) / width,
    (props.height * 0.8) / height,
    2,
  );

  const x = -centerX * scale + props.width / 2;
  const y = -centerY * scale + props.height / 2;

  svg
    .transition()
    .duration(750)
    .call(
      d3.zoom<SVGSVGElement, unknown>().transform,
      d3.zoomIdentity.translate(x, y).scale(scale),
    );
};

// 监听数据变化
watch(
  () => props.data,
  (newData) => {
    if (newData && newData.nodes.length > 0) {
      nextTick(() => {
        updateGraph();
      });
    }
  },
  { deep: true, immediate: true },
);

watch(
  () => [props.layoutMode, props.width, props.height],
  () => {
    nextTick(() => {
      updateGraph();
    });
  },
);

// 生命周期
onMounted(() => {
  nextTick(() => {
    initGraph();
    if (props.data && props.data.nodes.length > 0) {
      updateGraph();
    }
  });
});

onUnmounted(() => {
  if (simulation) {
    simulation.stop();
  }
});
</script>

<template>
  <div class="knowledge-graph">
    <div class="graph-header">
      <div class="graph-controls">
        <AInputSearch
          v-model:value="searchKeyword"
          :placeholder="$t('component.graph.searchPlaceholder')"
          style="width: 200px"
          @search="handleSearch"
          @change="handleSearchChange"
        />
        <AButton @click="resetView" size="small" class="ml-2">
          {{ $t('component.graph.resetView') }}
        </AButton>
        <AButton @click="fitToContent" size="small" class="ml-2">
          {{ $t('component.graph.fitContent') }}
        </AButton>
      </div>
      <div class="graph-info">
        <span class="info-item">{{ $t('component.graph.nodes') }}: {{ graphData.nodes.length }}</span>
        <span class="info-item ml-4">{{ $t('component.graph.connections') }}: {{ graphData.edges.length }}</span>
      </div>
    </div>
    <div ref="graphContainer" class="graph-container"></div>
    <div v-if="loading" class="graph-loading">
      <ASpin size="large" :tip="$t('component.graph.buildingGraph')" />
    </div>
    <!-- 节点详情提示框 -->
    <div
      ref="tooltip"
      class="graph-tooltip"
      :style="{
        display: tooltipVisible ? 'block' : 'none',
        left: `${tooltipPosition.x}px`,
        top: `${tooltipPosition.y}px`,
      }"
    >
      <div v-if="hoveredNode">
        <div class="tooltip-title">{{ hoveredNode.id }}</div>
        <div class="tooltip-content">
          <div>{{ $t('component.graph.connectionCount') }}: {{ hoveredNode.degree }}</div>
          <div v-if="hoveredNode.attributes">
            <div
              v-for="(value, key) in hoveredNode.attributes"
              :key="key"
              class="tooltip-attr"
            >
              <span class="attr-key">{{ key }}:</span>
              <span class="attr-value">{{ value }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.knowledge-graph {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #fafafa;
  border: 1px solid #d1d5db;
  border-radius: 8px;
}

.graph-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}

.graph-controls {
  display: flex;
  align-items: center;
}

.graph-info {
  display: flex;
  align-items: center;
  font-size: 14px;
  color: #6b7280;
}

.info-item {
  font-weight: 500;
}

.graph-container {
  width: 100%;
  height: calc(100% - 65px);
  overflow: hidden;
}

.graph-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  padding: 20px;
  background: rgb(255 255 255 / 90%);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgb(0 0 0 / 15%);
  transform: translate(-50%, -50%);
}

.graph-tooltip {
  position: fixed;
  z-index: 1000;
  max-width: 250px;
  padding: 8px 12px;
  font-size: 12px;
  color: white;
  pointer-events: none;
  background: rgb(0 0 0 / 80%);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgb(0 0 0 / 15%);
}

.tooltip-title {
  margin-bottom: 4px;
  font-size: 14px;
  font-weight: bold;
}

.tooltip-content {
  line-height: 1.4;
}

.tooltip-attr {
  display: flex;
  margin-bottom: 2px;
}

.attr-key {
  min-width: 60px;
  margin-right: 6px;
  font-weight: 500;
}

.attr-value {
  flex: 1;
  word-break: break-word;
}

/* D3样式覆盖 */
:deep(.graph-content) {
  cursor: move;
}

:deep(.nodes circle) {
  transition: all 0.2s ease;
}

:deep(.nodes circle:hover) {
  stroke-width: 3px !important;
}

:deep(.links line) {
  transition: all 0.2s ease;
}
</style>
