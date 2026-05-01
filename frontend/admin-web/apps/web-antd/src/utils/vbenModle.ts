import { useNamespace } from '@vben/hooks';

const useDesign = (block: string) => {
  const { b } = useNamespace(block);
  const prefixCls = b();
  return { prefixCls };
};
export { useDesign, useNamespace };

export { $t as t } from '#/locales';
