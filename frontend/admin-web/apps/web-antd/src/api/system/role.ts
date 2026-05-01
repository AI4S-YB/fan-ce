import { requestClient } from '#/api/request';

export interface RoleRowType {
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
export async function getRoleInfoApi(data: any) {
  return requestClient.post<RoleRowType>('/system/role/info', data);
}
export async function getRoleListApi(data: any) {
  return requestClient.post<PageResultType>('/system/role/list', data);
}
export async function getRoleOptionApi(data: any) {
  return requestClient.post<PageResultType>('/system/role/options', data);
}
export async function addRoleApi(data: any) {
  return requestClient.post<RoleRowType>('/system/role/add', data);
}
export async function delRoleApi(data: any) {
  return requestClient.post<RoleRowType>('/system/role/delete', data);
}
export async function updateRoleApi(data: any) {
  return requestClient.post<RoleRowType>('/system/role/update', data);
}
