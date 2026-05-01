/**
 * 知识图谱组件类型定义
 */

export interface GraphNode {
  id: string;
  label: string;
  degree: number;
  selected?: boolean;
  size?: number;
  color?: string;
  attributes?: Record<string, any>;
  x?: number;
  y?: number;
  fx?: null | number;
  fy?: null | number;
}

export interface GraphEdge {
  id: string;
  source: GraphNode | string;
  target: GraphNode | string;
  relationshipType?: string;
  weight?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphConfig {
  width?: number;
  height?: number;
  nodeRadius?: {
    max: number;
    min: number;
    scale: number;
  };
  colors?: {
    edge: string;
    edgeHighlight: string;
    node: string;
    nodeHighlight: string;
    nodeSearch: string;
  };
  simulation?: {
    centerStrength: number;
    chargeStrength: number;
    linkDistance: number;
    linkStrength: number;
  };
}
