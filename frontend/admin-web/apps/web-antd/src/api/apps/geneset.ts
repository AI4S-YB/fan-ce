import { requestClient } from '#/api/request';

export interface GeneSetItem {
  id: number;
  name: string;
  description?: string;
  gene_id?: string;
  is_delete: number;
  create_time?: string;
}

export interface GeneSetListResponse {
  total: number;
  dataList: GeneSetItem[];
}

export interface PageListParams {
  page?: number;
  size?: number;
  search?: string;
}

export interface DataInfoParams {
  id: number;
}

export interface DataDeleteParams {
  id?: number;
  ids?: number[];
}

export interface GeneSetCreateParams {
  name: string;
  description?: string;
  file_path: string;
  gene_list: string[];
  team_id: number;
  project_id: number;
}

export interface GeneSetUpdateParams extends GeneSetCreateParams {
  id: number;
}

// 获取基因集列表
export async function getGeneSetListApi(data: PageListParams) {
  return requestClient.post<GeneSetListResponse>('/gene/set/list', data);
}

// 获取基因集详情
export async function getGeneSetInfoApi(data: DataInfoParams) {
  return requestClient.post<GeneSetItem>('/gene/set/info', data);
}

// 新增基因集（新接口）
export async function addGeneSetApi(data: GeneSetCreateParams) {
  return requestClient.post('/gene/set/add', data);
}

// 更新基因集
export async function updateGeneSetApi(data: GeneSetUpdateParams) {
  return requestClient.post<GeneSetItem>('/gene/set/update', data);
}

// 删除基因集
export async function deleteGeneSetApi(data: DataDeleteParams) {
  return requestClient.post<{}>('/gene/set/delete', data);
}

// 基因集选项查询参数
export interface GeneSetOptionsParams {
  file_path?: string; // 可选：基因组文件路径，用于过滤特定基因组下的基因集
  team_id?: number;   // 可选：团队ID（通常由拦截器自动添加）
  project_id?: number; // 可选：项目ID（通常由拦截器自动添加）
}

// 获取基因集选项（用于下拉列表，支持file_path过滤）
export async function getGeneSetOptionsApi(params: GeneSetOptionsParams = {}) {
  return requestClient.post<{ 
    list: { gene_id: string; name: string }[]; 
    options: { id: string; name: string }[] 
  }>('/gene/set/options', params);
}

// === 新增的接口定义 ===

// 基因组维度的基因集列表参数
export interface GeneSetListByGenomeParams {
  file_path: string;
  team_id: number;
  project_id: number;
  page?: number;
  size?: number;
}

// 基因集详情参数
export interface GeneSetDetailParams {
  file_path: string;
  geneset_id: number;
  team_id: number;
  project_id: number;
  page?: number;
  size?: number;
}

// 基因集汇总信息（一级表格数据）
export interface GeneSetSummaryItem {
  geneset_id: number;
  geneset_name: string;
  description?: string;
  create_time?: number;
  gene_count: number;
}

// 基因集详情项（二级表格数据）
export interface GeneSetDetailItem {
  id: number;
  gene_id: string;
  file_path: string;
  geneset_id: number;
  create_time?: number;
}

// 基因组维度的基因集列表响应
export interface GeneSetListByGenomeResponse {
  total: number;
  dataList: GeneSetSummaryItem[];
  page: number;
  size: number;
}

// 基因集详情响应
export interface GeneSetDetailResponse {
  total: number;
  dataList: GeneSetDetailItem[];
  page: number;
  size: number;
}

// 按基因组获取基因集列表（一级表格）
export async function getGeneSetByGenomeApi(data: GeneSetListByGenomeParams) {
  return requestClient.post<GeneSetListByGenomeResponse>('/gene/set/genome/list', data);
}

// 获取基因集详情（二级表格）
export async function getGeneSetDetailApi(data: GeneSetDetailParams) {
  return requestClient.post<GeneSetDetailResponse>('/gene/set/detail', data);
}

// 获取有基因集数据的基因组选项
export interface GenomeOption {
  value: string;
  label: string;
}

export async function getGenomeOptionsApi() {
  return requestClient.post<GenomeOption[]>('/gene/set/genomes/options', {});
}
