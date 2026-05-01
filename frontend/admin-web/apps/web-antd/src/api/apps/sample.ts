import { requestClient } from '#/api/request';

export interface SampleRowType {
  id: number;
  name: string;
  status: string;
  is_delete: number;
  create_time: number;
}

export interface SampleSetRowType {
  id: number;
  name: string;
  status: string;
  is_delete: number;
  create_time: number;
}
export interface ResultPage {
  total: number;
  dataList: SampleRowType[];
}
export async function getSampleListApi(data: any) {
  return requestClient.post<ResultPage>('/sample/list', data);
}
export async function getSampleOptionsApi(data: any) {
  return requestClient.post<SampleSetRowType[]>('/sample/options', data);
}
export async function getSampleInfoApi(data: any) {
  return requestClient.post<SampleRowType>('/sample/info', data);
}
export async function addSampleApi(data: any) {
  return requestClient.post<SampleRowType>('/sample/add', data);
}
export async function updateSampleApi(data: any) {
  return requestClient.post<SampleRowType>('/sample/update', data);
}
export async function delSampleApi(data: any) {
  return requestClient.post<SampleRowType>('/sample/delete', data);
}

// meta

export async function getSampleMetaListApi(data: any) {
  return requestClient.post<ResultPage>('/sample/meta/list', data);
}
export async function getSampleMetaOptionsApi(data: any) {
  return requestClient.post<ResultPage>('/sample/meta/options', data);
}
export async function getSampleIMetanfoApi(data: any) {
  return requestClient.post<SampleRowType>('/sample/meta/info', data);
}
export async function addSampleMetaApi(data: any) {
  return requestClient.post<SampleRowType>('/sample/meta/add', data);
}
export async function updateSampleMetaApi(data: any) {
  return requestClient.post<SampleRowType>('/sample/meta/update', data);
}
export async function delSampleMetaApi(data: any) {
  return requestClient.post<SampleRowType>('/sample/meta/delete', data);
}

// meta-json接口
export async function getSampleMetaJsonApi(data: any) {
  return requestClient.post<any>('/sample/meta-json', data);
}
