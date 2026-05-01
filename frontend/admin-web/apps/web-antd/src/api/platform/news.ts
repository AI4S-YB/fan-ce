import { requestClient } from '#/api/request';

export interface NewsRowType {
  id: number;
  title: string;
  type: string;
  content: string;
  author: string;
  is_public: boolean;
  create_time: number;
  user_id: number;
  is_delete: boolean;
}

export interface NewsCreateType {
  title: string;
  type: string;
  content: string;
  author: string;
  is_public?: boolean;
  create_time?: number;
  user_id?: number;
  [key: string]: any; // 允许额外属性
}

export interface NewsUpdateType extends NewsCreateType {
  id: number;
}

export interface NewsListParams {
  page?: number;
  size?: number;
  type?: string;
}

export interface NewsDeleteParams {
  id?: number;
  ids?: number[];
}

/**
 * 获取消息列表
 */
export async function getNewsListApi(data: NewsListParams) {
  return requestClient.post<any>('/platform/list', data);
}

/**
 * 获取消息详情
 */
export async function getNewsInfoApi(data: { id: number }) {
  return requestClient.post<NewsRowType>('/platform/info', data);
}

/**
 * 添加消息
 */
export async function addNewsApi(data: NewsCreateType) {
  return requestClient.post<NewsRowType>('/platform/add', data);
}

/**
 * 更新消息
 */
export async function updateNewsApi(data: NewsUpdateType) {
  return requestClient.post<NewsRowType>('/platform/update', data);
}

/**
 * 删除消息
 */
export async function deleteNewsApi(data: NewsDeleteParams) {
  return requestClient.post<any>('/platform/delete', data);
}
