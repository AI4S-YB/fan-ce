/**
 * 基因调控网络 API 接口
 */

import { requestClient } from '#/api/request';
import type { 
  GrnDetailResponse, 
  GrnListParams, 
  GrnListResponse 
} from './types';

/**
 * 获取基因调控网络列表
 */
export async function getGrnListApi(params: GrnListParams = {}) {
  const defaultParams = {
    page: 1,
    page_size: 10,
    file_path: '/data/biodata/grn/demo_grn.xlsx',
    ...params,
  };

  return requestClient.post<GrnListResponse>('/grn/list', null, defaultParams);
}

/**
 * 获取基因详情（单个基因的调控网络信息）
 */
export async function getGrnDetailApi(
  gene_id: string,
  file_path: string = '/data/biodata/grn/demo_grn.xlsx'
) {
  return requestClient.post<GrnDetailResponse>('/grn/info', null, {
    gene_id,
    file_path,
  });
}

/**
 * 获取调控关系详情（特定调控关系的详细信息）
 */
export async function getGrnRelationshipDetailApi(params: {
  target_gene: string;
  tf_gene: string;
  file_path: string;
}) {
  return requestClient.post('/grn/relationship/detail', null, params);
}

/**
 * 获取两个基因的关系信息
 */
export async function getGrnRelationshipApi(params: {
  node1: string;
  node2: string;
  file_path: string;
}) {
  return requestClient.post('/grn/relationship', null, params);
}

/**
 * 获取基因调控网络统计信息
 */
export async function getGrnStatisticsApi(params: { file_path: string }) {
  return requestClient.post('/grn/statistics', null, params);
}

/**
 * 获取勾选基因的批量调控关系信息
 */
export async function getGrnBatchRelationshipsApi(params: {
  selected_nodes: string[];
  include_internal?: boolean;
  include_external?: boolean;
  max_connections_per_node?: number;
  max_path_length?: number;
  file_path: string;
}) {
  return requestClient.post('/grn/relationships/batch', params);
}