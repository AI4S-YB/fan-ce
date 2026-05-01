import type { AxiosProgressEvent } from 'axios';

import { requestClient } from '#/api/request';

// Legacy compatibility API module.
// New dataset management and query capabilities should use `#/api/apps/dataset`.

export interface DatabaseRowType {
  id: number;
  name: string;
  status: string;
  is_delete: number;
  create_time: number;
}

export interface DatabaseSetRowType {
  id: number;
  name: string;
  status: string;
  is_delete: number;
  create_time: number;
}
export interface ResultPage {
  total: number;
  dataList: DatabaseRowType[];
}
/**
 * 获取分析数据
 */
const pre = '/database';

export async function getDatabaseListApi(data: any) {
  return requestClient.post<ResultPage>(`${pre}/list`, data);
}
export async function getDatabaseOptionsApi(data: any) {
  return requestClient.post<ResultPage>(`${pre}/options`, data);
}
export async function getDatabaseInfoApi(data: any) {
  return requestClient.post<DatabaseRowType>(`${pre}/info`, data);
}

export async function addDatabaseApi(data: any) {
  return requestClient.post<DatabaseRowType>(`${pre}/add`, data);
}
export async function addDataBatchbaseApi(data: any) {
  return requestClient.post<DatabaseRowType>(`${pre}/batch/add`, data);
}

export async function delDatabaseApi(data: any) {
  return requestClient.post<DatabaseRowType>(`${pre}/delete`, data);
}
export async function updateDatabaseApi(data: any) {
  return requestClient.post<DatabaseRowType>(`${pre}/update`, data);
}
// 修改名称
export async function updateDatabaseNameApi(data: any) {
  return requestClient.post<DatabaseRowType>(`${pre}/rename`, data);
}

export async function buildDatabaseMetaApi(data: any) {
  return requestClient.post<DatabaseRowType>(`${pre}/buildmeta`, data);
}

export async function databaseFileUploadApi(
  data: any,
  onUploadProgress?: (progressEvent: AxiosProgressEvent) => void,
) {
  return requestClient.upload(`${pre}/upload`, data, { onUploadProgress });
}
// 文件接口
export async function getDatabaseFileListApi(data: any) {
  return requestClient.post<ResultPage>(`${pre}/file/list`, data);
}
// 数据集合接口

export async function getDatabaseSetListApi(data: any) {
  return requestClient.post<ResultPage>(`${pre}/set/list`, data);
}
export async function addDatabaseSetApi(data: any) {
  return requestClient.post<DatabaseRowType>(`${pre}/set/add`, data);
}
export async function delDatabaseSetApi(data: any) {
  return requestClient.post<DatabaseRowType>(`${pre}/set/delete`, data);
}
export async function updateDatabaseSetApi(data: any) {
  return requestClient.post<DatabaseRowType>(`${pre}/set/update`, data);
}
export async function getDatabaseSetInfoApi(data: any) {
  return requestClient.post<DatabaseRowType>(`${pre}/set/info`, data);
}
export async function getDatabaseFileSearch(data: any) {
  return requestClient.post<DatabaseRowType[]>(`${pre}/file/search`, data);
}

export async function getDataFormatFun(data: any) {
  return requestClient.post<DatabaseRowType[]>(`${pre}/file/search`, data);
}

// 关联项目接口
export async function linkProjectApi(data: any) {
  return requestClient.post(`${pre}/link-project`, data);
}

// 查询数据库关联的项目接口
export async function getLinkedProjectsApi(data: any) {
  return requestClient.post(`${pre}/get-linked-projects`, data);
}

// meta
export async function addDataMetaApi(data: any) {
  return requestClient.post<DatabaseRowType[]>(`${pre}/meta/add`, data);
}
export async function delDataMetaApi(data: any) {
  return requestClient.post<DatabaseRowType[]>(`${pre}/meta/delete`, data);
}
export async function updateDataMetaApi(data: any) {
  return requestClient.post<DatabaseRowType[]>(`${pre}/meta/update`, data);
}
export async function getDataMetaListApi(data: any) {
  return requestClient.post<DatabaseRowType[]>(`${pre}/meta/list`, data);
}

// action
export async function dataFormatApi(data: any) {
  return requestClient.post<DatabaseRowType[]>('/database/action/format', data);
}
