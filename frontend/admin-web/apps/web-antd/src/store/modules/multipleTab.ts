import type { RouteLocationNormalized } from 'vue-router';

import { defineStore } from 'pinia';

export interface MultipleTabState {
  // 缓存标签页路由名称
  cacheTabList: Set<string>;
  // 标签页路由列表,标准化的路由地址
  tabList: RouteLocationNormalized[];
  // 最后一次拖动标签的索引
  lastDragEndIndex: number;
}
export const useMultipleTabStore = defineStore('app-multiple-tab', {
  state: (): MultipleTabState => ({
    cacheTabList: new Set(),
    tabList: [], // 优先加载缓存/本地存储内容
    lastDragEndIndex: 0,
  }),
  getters: {
    // 获取标签页路由列表
    getTabList(): RouteLocationNormalized[] {
      return this.tabList;
    },
    // 获取缓存标签页路由名称列表
    getCachedTabList(): string[] {
      return [...this.cacheTabList];
    },
    // 获取最后一次拖动标签的索引
    getLastDragEndIndex(): number {
      return this.lastDragEndIndex;
    },
  },
});
