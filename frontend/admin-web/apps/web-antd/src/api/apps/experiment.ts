import { requestClient } from '#/api/request';

export interface ExperimentRowType {
  id: number;
  name: string;
  status: string;
  is_delete: number;
  create_time: number;
}

export interface ExperimentSetRowType {
  id: number;
  name: string;
  status: string;
  is_delete: number;
  create_time: number;
}
export interface ResultPage {
  total: number;
  dataList: ExperimentRowType[];
}
export async function getExperimentListApi(data: any) {
  return requestClient.post<ResultPage>('/experiment/list', data);
}
export async function getExperimentOptionsApi(data: any) {
  return requestClient.post<ResultPage>('/experiment/options', data);
}
export async function getExperimentInfoApi(data: any) {
  return requestClient.post<ExperimentRowType>('/experiment/info', data);
}
export async function addExperimentApi(data: any) {
  return requestClient.post<ExperimentRowType>('/experiment/add', data);
}
export async function updateExperimentApi(data: any) {
  return requestClient.post<ExperimentRowType>('/experiment/update', data);
}
export async function delExperimentApi(data: any) {
  return requestClient.post<ExperimentRowType>('/experiment/delete', data);
}

// meta
export async function getExperimentMetaListApi(data: any) {
  return requestClient.post<ResultPage>('/experiment/meta/list', data);
}
export async function getExperimentMetaOptionsApi(data: any) {
  return requestClient.post<ResultPage>('/experiment/meta/options', data);
}
export async function getExperimentMetaInfoApi(data: any) {
  return requestClient.post<ExperimentRowType>('/experiment/meta/info', data);
}
export async function addExperimentMetaApi(data: any) {
  return requestClient.post<ExperimentRowType>('/experiment/meta/add', data);
}
export async function updateExperimentMetaApi(data: any) {
  return requestClient.post<ExperimentRowType>('/experiment/meta/update', data);
}
export async function delExperimentMetaApi(data: any) {
  return requestClient.post<ExperimentRowType>('/experiment/meta/delete', data);
}
