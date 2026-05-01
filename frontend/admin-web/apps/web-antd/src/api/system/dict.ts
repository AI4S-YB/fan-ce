import { requestClient } from '#/api/request';

export interface DictRowType {
  id: number;
  sort: number;
  label: string;
  value: boolean | number | string;
  dictType: string;
  status: number;
  color: string;
  colorType: string;
  cssClass: string;
  remark: string;
  createTime: Date;
}

/**
 * 获取用户所有菜单
 */
export async function getDictMapApi(data: any) {
  return requestClient.post<any>('/system/dict/map', data);
}
export async function getDictOptionApi(data: any) {
  return requestClient.post<any>('/system/dict/options', data);
}
export async function getDictListApi(data: any) {
  return requestClient.post<any>('/system/dict/list', data);
}
export async function getDictInfoApi(data: any) {
  return requestClient.post<DictRowType[]>('/system/dict/info', data);
}
export async function addDictApi(data: any) {
  return requestClient.post<DictRowType[]>('/system/dict/add', data);
}
export async function updateDictApi(data: any) {
  return requestClient.post<DictRowType[]>('/system/dict/update', data);
}
export async function deleteDictApi(data: any) {
  return requestClient.post<DictRowType[]>('/system/dict/delete', data);
}

export async function getDictFieldListApi(data: any) {
  return requestClient.post<DictRowType[]>('/system/dict/field/list', data);
}
export async function getDictFieldInfoApi(data: any) {
  return requestClient.post<DictRowType[]>('/system/dict/field/info', data);
}
export async function addDictFieldApi(data: any) {
  return requestClient.post<DictRowType[]>('/system/dict/field/add', data);
}
export async function updateDictFieldApi(data: any) {
  return requestClient.post<DictRowType[]>('/system/dict/field/update', data);
}
export async function deleteDictFieldApi(data: any) {
  return requestClient.post<DictRowType[]>('/system/dict/field/delete', data);
}
