import { requestClient } from '#/api/request';

export interface ProjectRowType {
  id: number;
  code?: string;
  name: string;
  isPublic: boolean;
  create_time?: number;
}
export interface ResultPage {
  total: number;
  dataList: ProjectRowType[];
}

export async function getProjectListApi(data: any) {
  return requestClient.post<any>('/system/project/list', data);
}
export async function getProjectOptionsApi(data: any) {
  return requestClient.post<any>('/system/project/options', data);
}
export async function getProjectInfoApi(data: any) {
  return requestClient.post<ProjectRowType>('/system/project/info', data);
}

export async function addProjectApi(data: any) {
  return requestClient.post<ProjectRowType>('/system/project/add', data);
}
export async function delProjectApi(data: any) {
  return requestClient.post<ProjectRowType>('/system/project/delete', data);
}
export async function updateProjectApi(data: any) {
  return requestClient.post<ProjectRowType>('/system/project/update', data);
}
