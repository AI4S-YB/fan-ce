import type { InjectionKey, Ref, UnwrapRef } from 'vue';

import { inject } from 'vue';

// 定义 ShallowUnwrap 类型
type ShallowUnwrap<T> = {
  [P in keyof T]: UnwrapRef<T[P]>;
};

// 定义上下文接口
export interface AppProviderContextProps {
  prefixCls: Ref<string>;
  isMobile: Ref<boolean>;
}

// 定义 InjectionKey
export const key: InjectionKey<AppProviderContextProps> =
  Symbol('AppProviderContext');

// useContext 函数
export function useContext<T>(
  key: InjectionKey<T>,
  defaultValue?: any,
): ShallowUnwrap<T> {
  return inject(key, defaultValue || {});
}

// 使用应用提供者上下文的函数
export function useAppProviderContext() {
  return useContext<AppProviderContextProps>(key);
}

// 使用设计的函数
export function useDesign(scope: string) {
  const values = useAppProviderContext();

  return {
    prefixCls: `${values.prefixCls}-${scope}`, // 确保使用 .value 来访问 Ref 的值
    prefixVar: values.prefixCls,
  };
}
