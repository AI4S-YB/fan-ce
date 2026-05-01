import { useNamespace } from '@vben/hooks';

const bem = (block: string) => {
  const { bem } = useNamespace(block);
  const prefixCls = bem();
  return prefixCls;
};
export { bem, useNamespace };

export { $t as t } from '#/locales';
