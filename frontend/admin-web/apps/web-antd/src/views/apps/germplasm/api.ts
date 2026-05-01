/**
 * 种质资源 API 接口
 */

import type {
  GermplasmBatchRelationshipResult,
  GermplasmDetailResponse,
  GermplasmImportBatchDeleteResult,
  GermplasmImportBatchDetail,
  GermplasmImportBatchItem,
  GermplasmImportCommitResult,
  GermplasmListParams,
  GermplasmListResponse,
  GermplasmRelationshipResult,
  GermplasmStatisticsResult,
  GermplasmTaxonomyAuditResult,
  GermplasmTaxonomyOption,
} from './types';

import { requestClient } from '#/api/request';

/**
 * 获取种质资源列表
 */
export async function getGermplasmListApi(params: GermplasmListParams = {}) {
  const defaultParams = {
    page: 1,
    size: 10,
    ...params,
  };

  return requestClient.post<GermplasmListResponse>(
    '/breeding/germplasm/list',
    defaultParams,
  );
}

/**
 * 获取种质资源详情
 */
export async function getGermplasmDetailApi(
  germplasm_id: string,
  taxonomy_tax_id: number,
) {
  return requestClient.post<GermplasmDetailResponse>(
    '/breeding/germplasm/info',
    {
      accession_id: germplasm_id,
      taxonomy_tax_id,
    },
  );
}

export async function getGermplasmTaxonomyOptionsApi(
  params: {
    active_only?: number;
    keyword?: string;
    limit?: number;
    with_germplasm_only?: number;
  } = {},
) {
  const response = await requestClient.post<{
    code: number;
    data: {
      items: GermplasmTaxonomyOption[];
      total: number;
    };
    msg: string;
  }>('/breeding/germplasm/taxonomy/options', {
    limit: 100,
    active_only: 1,
    ...params,
  });
  return response;
}

export async function syncGermplasmTaxonomyApi(params: {
  active_only?: number;
  force_refresh?: number;
  keyword?: string;
  limit?: number;
  tax_id?: number;
}) {
  return requestClient.post('/breeding/germplasm/taxonomy/sync', params);
}

export async function auditGermplasmTaxonomyApi(params: {
  active_only?: number;
  keyword?: string;
  limit?: number;
  tax_id?: number;
}) {
  return requestClient.post<GermplasmTaxonomyAuditResult>(
    '/breeding/germplasm/taxonomy/audit',
    params,
  );
}

export async function validateGermplasmImportApi(
  data: {
    file: File;
    taxonomy_tax_id: number | string;
    template_profile: string;
  },
  onUploadProgress?: (progressEvent: any) => void,
) {
  const formData = new FormData();
  formData.append('file', data.file);
  formData.append('taxonomy_tax_id', String(data.taxonomy_tax_id));
  formData.append('template_profile', data.template_profile);
  return requestClient.post2('/breeding/germplasm/import/validate', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress,
    timeout: 3_600_000,
  });
}

export async function commitGermplasmImportApi(data: {
  validation_token: string;
}) {
  return requestClient.post<GermplasmImportCommitResult>(
    '/breeding/germplasm/import/commit',
    data,
  );
}

export async function getGermplasmImportBatchListApi(data: {
  keyword?: string;
  page?: number;
  size?: number;
  status?: string;
  taxonomy_tax_id?: number;
}) {
  return requestClient.post<{
    items: GermplasmImportBatchItem[];
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  }>('/breeding/germplasm/import/batches', data);
}

export async function getGermplasmImportBatchInfoApi(data: { id: number }) {
  return requestClient.post<GermplasmImportBatchDetail>(
    '/breeding/germplasm/import/batch-info',
    data,
  );
}

export async function deleteGermplasmImportBatchApi(data: { id: number }) {
  return requestClient.post<GermplasmImportBatchDeleteResult>(
    '/breeding/germplasm/import/batch-delete',
    data,
  );
}

/**
 * 获取两个节点的关系信息
 */
export async function getGermplasmRelationshipApi(params: {
  accession_id_1: string;
  accession_id_2: string;
  batch_id?: number;
  taxonomy_tax_id: number;
}) {
  return requestClient.post<GermplasmRelationshipResult>(
    '/breeding/germplasm/relationship',
    params,
  );
}

/**
 * 获取统计信息
 */
export async function getGermplasmStatisticsApi(params: {
  batch_id?: number;
  status?: string;
  taxonomy_tax_id: number;
}) {
  return requestClient.post<GermplasmStatisticsResult>(
    '/breeding/germplasm/statistics',
    params,
  );
}

/**
 * 获取勾选节点的批量关系信息
 */
export async function getGermplasmBatchRelationshipsApi(params: {
  batch_id?: number;
  include_external?: boolean;
  include_internal?: boolean;
  max_connections_per_node?: number;
  selected_nodes: string[];
  taxonomy_tax_id: number;
}) {
  return requestClient.post<GermplasmBatchRelationshipResult>(
    '/breeding/germplasm/relationships/batch',
    params,
  );
}
