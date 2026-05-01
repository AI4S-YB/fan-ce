/**
 * 调控网络相关类型定义
 */

/**
 * 基因节点接口
 */
export interface GeneNode {
  name: string;
  attributes: {
    target_gene_name?: string;
    target_gene_description?: string;
    tf_name?: string;
    tf_family?: string;
    [key: string]: any;
  };
}

/**
 * 调控关系边属性接口
 */
export interface EdgeAttributes {
  'peak_fold-change': string;
  c_score: string;
  weight: number;
  created_at: string;
  [key: string]: any;
}

/**
 * 基因调控关系列表项接口（调控网络的基本单元）
 */
export interface GrnItem {
  node1: GeneNode;  // 靶基因
  node2: GeneNode;  // 转录因子
  edge_attributes: EdgeAttributes;  // 调控关系属性
  
  // 为了兼容表格操作，添加唯一标识
  id?: string;
}

/**
 * 基因调控网络详情接口（单个基因的详细信息）
 */
export interface GrnDetail {
  node: string;
  degree: number;
  neighbors: string[];
  neighbor_count: number;
  attributes: Record<string, any>;
  id: string;
}

/**
 * 列表查询参数接口
 */
export interface GrnListParams {
  page?: number;
  page_size?: number;
  file_path?: string;
  keyword?: string;
}

/**
 * 列表响应接口
 */
export interface GrnListResponse {
  code: number;
  msg: string;
  data: {
    items: GrnItem[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

/**
 * 详情响应接口
 */
export interface GrnDetailResponse {
  code: number;
  msg: string;
  data: GrnDetail;
}

/**
 * 动态列配置接口
 */
export interface DynamicColumnConfig {
  dataIndex: string;
  title: string;
  type?: 'text' | 'number' | 'date';
  width?: number;
}