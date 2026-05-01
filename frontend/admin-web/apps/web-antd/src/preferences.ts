import { defineOverridesPreferences } from '@vben/preferences';

/**
 * @description 项目配置文件
 * 只需要覆盖项目中的一部分配置，不需要的配置不用覆盖，会自动使用默认配置
 */
export const overridesPreferences = defineOverridesPreferences({
  // overrides
  app: {
    name: import.meta.env.VITE_APP_TITLE,
    defaultHomePath: '/workspace',
    accessMode: 'backend', // frontend 'backend' | 'frontend' | 'other';
  },
  breadcrumb: {
    styleType: 'background',
  },
  logo: {
    source: '/logo.png',
  },
  theme: {
    mode: 'light',
    radius: '0',
    semiDarkHeader: true,
  },
  tabbar: {
    enable: false,
    showMaximize: false,
  },
  widget: {
    fullscreen: false,
    globalSearch: false,
    languageToggle: false,
  },
});
