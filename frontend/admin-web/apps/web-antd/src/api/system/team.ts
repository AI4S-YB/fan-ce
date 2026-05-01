import { requestClient } from '#/api/request';

export interface TeamRowType {
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
export async function getTeamListApi(data: any) {
  return requestClient.post<PageResultType>('/system/team/list', data);
}
export async function getTeamInfoApi(data: any) {
  return requestClient.post<TeamRowType>('/system/team/info', data);
}
export async function getTeamOptionApi(data: any) {
  return requestClient.post<PageResultType>('/system/team/options', data);
}
export async function addTeamApi(data: any) {
  return requestClient.post<TeamRowType>('/system/team/add', data);
}
export async function delTeamApi(data: any) {
  return requestClient.post<TeamRowType>('/system/team/delete', data);
}
export async function updateTeamApi(data: any) {
  return requestClient.post<TeamRowType>('/system/team/update', data);
}

export async function updateTeamUserRoleApi(data: any) {
  return requestClient.post<TeamRowType>('/system/team/user/role', data);
}
