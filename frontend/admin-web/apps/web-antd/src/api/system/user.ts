import type { UserInfo } from '@vben/types';

import { requestClient } from '#/api/request';

/**
 * 获取用户信息
 */
export async function getUserInfoApi(data: any) {
  return requestClient.post<UserInfo>('/system/user/info', data);
}
export async function getUserListApi(data: any) {
  return requestClient.post<UserInfo>('/system/user/list', data);
}
export async function getUserOptionsApi(data: any) {
  return requestClient.post<UserInfo>('/system/user/options', data);
}
export async function addUserApi(data: any) {
  return requestClient.post<UserInfo>('/system/user/add', data);
}
export async function delUserApi(data: any) {
  return requestClient.post<UserInfo>('/system/user/delete', data);
}
export async function updateUserApi(data: any) {
  return requestClient.post<UserInfo>('/system/user/update', data);
}

export async function getUserProfileApi() {
  return requestClient.post<any>('/system/user/auth/info');
}
export async function resetPwdApi(data: any) {
  return requestClient.post<any>('/system/user/pwd/reset', data);
}
export async function updatePwdApi(data: any) {
  return requestClient.post<any>('/system/user/pwd/update', data);
}
export async function updateUserActiveApi(data: any) {
  return requestClient.post<UserInfo>('/system/user/active', data);
}

// === 认证密钥管理API ===

/**
 * 认证密钥信息接口
 */
export interface AuthKeyInfo {
  auth_key: string;
  status: 'active' | 'disabled';
  user_id: number;
  team_id: number;
  has_key: boolean;
}

/**
 * 认证密钥创建响应接口
 */
export interface AuthKeyCreateResponse {
  auth_key: string;
  status: 'active' | 'disabled';
  user_id: number;
  team_id: number;
}

/**
 * 认证密钥状态更新请求接口
 */
export interface AuthKeyUpdateRequest {
  status: 'active' | 'disabled';
}

/**
 * 认证密钥状态更新响应接口
 */
export interface AuthKeyUpdateResponse {
  auth_key: string;
  status: 'active' | 'disabled';
  updated: boolean;
}

/**
 * 认证密钥删除响应接口
 */
export interface AuthKeyDeleteResponse {
  deleted: boolean;
  user_id: number;
}

/**
 * 批量查询认证密钥请求接口
 */
export interface AuthKeyBatchQueryRequest {
  page?: number;
  size?: number;
  team_id?: number;
  status?: 'active' | 'disabled';
}

/**
 * 批量查询密钥项接口
 */
export interface AuthKeyBatchItem {
  user_id: number;
  username: string;
  auth_key: string;
  status: 'active' | 'disabled';
  team_id: number;
}

/**
 * 批量查询认证密钥响应接口
 */
export interface AuthKeyBatchQueryResponse {
  total: number;
  page: number;
  size: number;
  items: AuthKeyBatchItem[];
}

/**
 * 获取用户认证密钥信息
 */
export async function getUserAuthKeyApi(userId: number) {
  return requestClient.get<AuthKeyInfo>(`/system/user/${userId}/auth-key`);
}

/**
 * 生成用户认证密钥
 */
export async function generateUserAuthKeyApi(userId: number) {
  return requestClient.post<AuthKeyCreateResponse>(`/system/user/${userId}/auth-key`);
}

/**
 * 重新生成用户认证密钥
 */
export async function regenerateUserAuthKeyApi(userId: number) {
  return requestClient.post<AuthKeyCreateResponse>(`/system/user/${userId}/auth-key/regenerate`);
}

/**
 * 更新用户认证密钥状态
 */
export async function updateUserAuthKeyStatusApi(userId: number, data: AuthKeyUpdateRequest) {
  return requestClient.post<AuthKeyUpdateResponse>(`/system/user/${userId}/auth-key/status`, data);
}

/**
 * 删除用户认证密钥
 */
export async function deleteUserAuthKeyApi(userId: number) {
  return requestClient.delete<AuthKeyDeleteResponse>(`/system/user/${userId}/auth-key`);
}

/**
 * 批量查询用户认证密钥
 */
export async function batchQueryAuthKeysApi(data: AuthKeyBatchQueryRequest) {
  return requestClient.post<AuthKeyBatchQueryResponse>('/system/user/auth-keys/batch', data);
}
