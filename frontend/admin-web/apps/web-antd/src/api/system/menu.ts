import type { RouteRecordStringComponent } from '@vben/types';

import { requestClient } from '#/api/request';

export interface MenuRowType {
  id: number;
  name: string;
  title: string;
  path: string;
  component: string;
  create_time: string;
}

export interface PageResultType {
  total: number;
  dataList: Array<any | object>;
}

/**
 * 获取用户所有菜单
 */
export async function getAllMenusApi(data: any) {
  return requestClient.post<PageResultType>('/system/menu/option', data);
}

export async function getMenuListApi(data: any) {
  return requestClient.post<MenuRowType[]>('/system/menu/list', data);
}
export async function getMenuTreeApi(data: any) {
  return requestClient.post<MenuRowType[]>('/system/menu/tree', data);
}
export async function getMenuPermissonTreeApi(data: any) {
  return requestClient.post<MenuRowType[]>('/system/menu/permission', data);
}
export async function getMenuInfoApi(data: any) {
  return requestClient.post<MenuRowType>('/system/menu/info', data);
}
export async function createMenuApi(data: any) {
  return requestClient.post<RouteRecordStringComponent>(
    '/system/menu/add',
    data,
  );
}
export async function updateMenuApi(data: any) {
  return requestClient.post<RouteRecordStringComponent>(
    '/system/menu/update',
    data,
  );
}
export async function deleteMenuApi(data: any) {
  return requestClient.post<RouteRecordStringComponent>(
    '/system/menu/delete',
    data,
  );
}
