declare interface Fn<T = any, R = T> {
  (...arg: T[]): R;
}

declare interface PromiseFn<T = any, R = T> {
  (...arg: T[]): Promise<R>;
}

declare type RefType<T> = null | T;

declare interface PageParam {
  pageSize?: number;
  pageNo?: number;
}

declare interface PageResult<T = any> {
  list: T[];
  total: number;
}

declare type LabelValueOptions = {
  [key: string]: boolean | number | string;
  label: string;
  value: any;
}[];

declare type EmitType = (event: string, ...args: any[]) => void;

declare type TargetContext = '_blank' | '_self';

declare interface ComponentElRef<T extends HTMLElement = HTMLDivElement> {
  $el: T;
}

declare type ComponentRef<T extends HTMLElement = HTMLDivElement> =
  ComponentElRef<T> | null;

declare type ElRef<T extends HTMLElement = HTMLDivElement> = Nullable<T>;

declare module '*.vue' {
  import type { DefineComponent } from 'vue';

  const Component: DefineComponent<object, object, any>;
  export default Component;
}
