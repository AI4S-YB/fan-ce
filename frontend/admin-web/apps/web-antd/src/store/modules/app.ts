import type { ThemeConfig } from 'ant-design-vue/es/config-provider/context';

import type { ThemeEnum } from '#/enums/appEnum';
import type {
  AppSizeType,
  HeaderSetting,
  MenuSetting,
  MultiTabsSetting,
  ProjectConfig,
  TransitionSetting,
} from '#/types/config';
import type { BeforeMiniState } from '#/types/store';

import { theme as antdTheme } from 'ant-design-vue/es';
import { defineStore } from 'pinia';

import { APP_DARK_MODE_KEY_, PROJ_CFG_KEY } from '#/enums/cacheEnum';
import { darkMode } from '#/settings/designSetting';
import { store } from '#/store';
import { deepMerge } from '#/utils';
import { Persistent } from '#/utils/cache/persistent';

interface AppState {
  darkMode?: ThemeEnum;
  themeConfig: ThemeConfig;
  // Page loading status
  pageLoading: boolean;
  // project config
  projectConfig: null | ProjectConfig;
  // When the window shrinks, remember some states, and restore these states when the window is restored
  beforeMiniInfo: BeforeMiniState;
  componentSize: 'large' | 'middle' | 'small' | undefined;
}
let timeId: TimeoutHandle;
export const useAppStore = defineStore('app', {
  state: (): AppState => ({
    darkMode: undefined,
    themeConfig: {
      algorithm: antdTheme.defaultAlgorithm,
      token: {
        colorBgContainer: '#fff',
      },
      components: {},
    },
    pageLoading: false,
    projectConfig: Persistent.getLocal(PROJ_CFG_KEY),
    beforeMiniInfo: {},
    componentSize: 'middle',
  }),
  getters: {
    getPageLoading(state): boolean {
      return state.pageLoading;
    },
    getDarkMode(state): 'dark' | 'light' | string {
      return (
        state.darkMode || localStorage.getItem(APP_DARK_MODE_KEY_) || darkMode
      );
    },

    getBeforeMiniInfo(state): BeforeMiniState {
      return state.beforeMiniInfo;
    },

    getProjectConfig(state): ProjectConfig {
      return state.projectConfig || ({} as ProjectConfig);
    },

    getHeaderSetting(): HeaderSetting {
      return this.getProjectConfig.headerSetting;
    },
    getMenuSetting(): MenuSetting {
      return this.getProjectConfig.menuSetting;
    },
    getTransitionSetting(): TransitionSetting {
      return this.getProjectConfig.transitionSetting;
    },
    getMultiTabsSetting(): MultiTabsSetting {
      return this.getProjectConfig.multiTabsSetting;
    },
    getComponentSize(state): AppSizeType | undefined {
      return state.componentSize;
    },
  },
  actions: {
    setPageLoading(loading: boolean): void {
      this.pageLoading = loading;
    },
    // eslint-disable-next-line no-empty-pattern
    setProjectConfig({}): any {},
    setBeforeMiniInfo(state: BeforeMiniState): void {
      this.beforeMiniInfo = state;
    },

    setComponentSize(size: AppSizeType): void {
      this.componentSize = size;
    },

    setMenuSetting(setting: Partial<MenuSetting>): void {
      if (!this.projectConfig) return;
      this.projectConfig.menuSetting = deepMerge(
        this.projectConfig.menuSetting,
        setting,
      );
      Persistent.setLocal(PROJ_CFG_KEY, this.projectConfig);
    },

    setPageLoadingAction(loading: boolean) {
      if (loading) {
        clearTimeout(timeId);
        // Prevent flicker
        timeId = setTimeout(() => {
          this.setPageLoading(loading);
        }, 50);
      } else {
        this.setPageLoading(loading);
        clearTimeout(timeId);
      }
    },
  },
});

// Need to be used outside the setup
export function useAppStoreWithOut() {
  return useAppStore(store);
}
