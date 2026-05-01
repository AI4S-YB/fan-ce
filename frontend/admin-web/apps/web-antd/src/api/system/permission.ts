import { requestClient } from '#/api/request';

export interface PermissionRowType {
  id: number;
  name: string;
  code: string;
  create_time: string;
}

export interface PageResultType {
  total: number;
  dataList: Array<any | object>;
}
/**
 * 获取角色信息
 */
export async function getPermissionInfoApi(data: any) {
  return requestClient.post<PermissionRowType>('/system/permission/info', data);
}
export async function getPermissionListApi(data: any) {
  return requestClient.post<PageResultType>('/system/permission/list', data);
}
export async function addPermissionApi(data: any) {
  return requestClient.post<PermissionRowType>('/system/permission/add', data);
}
export async function delPermissionApi(data: any) {
  return requestClient.post<PermissionRowType>(
    '/system/permission/delete',
    data,
  );
}
export async function updatePermissionApi(data: any) {
  return requestClient.post<PermissionRowType>(
    '/system/permission/update',
    data,
  );
}

export async function getPermissionControllerApi(data: any) {
  return requestClient.post<PermissionRowType>(
    '/system/permission/controller',
    data,
  );
}
export async function getPermissionMapApi(data: any) {
  return requestClient.post<PageResultType[]>('/system/permission/map', data);
}
export async function getPermissionOptionsTreeApi(data: any) {
  return requestClient.post<PageResultType[]>(
    '/system/permission/options/tree',
    data,
  );
}

export async function getPermissionTreeApi(data: any) {
  return requestClient.post<PageResultType[]>('/system/permission/tree', data);
}
