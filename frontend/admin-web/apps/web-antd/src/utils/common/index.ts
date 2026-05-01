import { getDictOptionApi } from '#/api/system/dict';
import { EnumEnum } from '#/enums/commonEnum';
import { isString } from '#/utils/is';

/**
 * form 嵌套组件属性
 * @param type
 * @param extendFirst
 * @param extend
 * @param excludes
 * @returns
 */
export const enumComponentProps = (
  type: EnumEnum | string,
  extendFirst = true,
  extend?: any,
  excludes?: string | string[],
) => {
  if (excludes && isString(excludes)) {
    excludes = [excludes];
  }
  return {
    api: () => getDictOptionApi({ type }),
    params: { type, extendFirst, extend, excludes },
    resultField: 'data',
    showSearch: true,
    filterOption: (input: string, option: any) => {
      return option.label.toUpperCase().includes(input.toUpperCase());
    },
  };
};

export const enumComponentStringProps = (
  type: EnumEnum | string,
  extendFirst = true,
  extend?: any,
  excludes?: string | string[],
) => {
  if (excludes && isString(excludes)) {
    excludes = [excludes];
  }
  return {
    api: () => getDictOptionApi({ type }),
    params: { type, extendFirst, extend, excludes },
    resultField: 'data',
    showSearch: true,
    filterOption: (input: string, option: any) => {
      return option.label.toUpperCase().includes(input.toUpperCase());
    },
  };
};
