import type { DictRowType } from '#/api/system/dict';

import { getDictMapApi } from '#/api/system/dict';
/**
 * 数据字典工具类
 */
import { useDictStoreWithOut } from '#/store/modules/dict';

export * from './general';

const dictStore = useDictStoreWithOut();
/**
 * 获取 dictType 对应的数据字典数组
 *
 * @param dictType 数据类型
 * @returns {*|Array} 数据字典数组
 */
export interface DictDataType {
  dictType: string;
  label: string;
  value: boolean | number | string;
  key?: any;
  color: string;
  colorType: string;
  cssClass: string;
}

export function getDictDatas(dictType: string) {
  return dictStore.getDictMap[dictType] || [];
}

export function getDictOpts(dictType: string) {
  return dictStore.getDictMap[dictType] || [];
}
/**
 *
 * @param dictType 获取字典options选项List
 * @param valueType
 * @returns
 */
export function getDictOptions(
  dictType: string,
  valueType?: 'boolean' | 'number' | 'string',
) {
  const dictOption: DictRowType[] = [];
  const dictOptions: DictRowType[] = getDictDatas(dictType);
  if (dictOptions && dictOptions.length > 0) {
    dictOptions.forEach((dict: DictRowType) => {
      dictOption.push({
        ...dict,
        value:
          valueType === 'string'
            ? `${dict.value}`
            : // eslint-disable-next-line unicorn/no-nested-ternary
              valueType === 'boolean'
              ? `${dict.value}` === 'true'
              : Number.parseInt(`${dict.value}`),
      });
    });
  }
  return dictOption;
}
// 获取字典对象值
export function getDictObj(dictType: string, value?: any) {
  const dictOptions: DictDataType[] = getDictDatas(dictType);
  if (dictOptions.length > 0) {
    return dictOptions.find((dict) => dict.value === value.toString());
  }
}
export async function getDictTypeData(key?: string) {
  return await getDictMapApi({ key });
}
