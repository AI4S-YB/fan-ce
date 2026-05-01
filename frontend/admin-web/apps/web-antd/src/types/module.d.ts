declare module '*.vue' {
  import type { DefineComponent } from 'vue';

  const Component: DefineComponent<object, object, any>;
  export default Component;
}

declare module 'ant-design-vue/es/locale/*' {
  import type { Locale } from 'ant-design-vue/types/locale-provider';

  const locale: Locale & ReadonlyRecordable;
  export default locale;
}

declare module 'virtual:*' {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const result: any;
  export default content;
}
