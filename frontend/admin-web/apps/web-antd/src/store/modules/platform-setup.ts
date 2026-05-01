import type { PlatformSetupStatusResponse } from '#/api/platform/setup';

import { acceptHMRUpdate, defineStore } from 'pinia';

import { getPlatformSetupStatusApi } from '#/api/platform/setup';
import { store } from '#/store';

interface PlatformSetupState {
  lastLoadedAt: number;
  loadingPromise: null | Promise<null | PlatformSetupStatusResponse>;
  taxonomyStatus: null | PlatformSetupStatusResponse;
}

const CACHE_TTL_MS = 30_000;

export const usePlatformSetupStore = defineStore('platform-setup', {
  state: (): PlatformSetupState => ({
    lastLoadedAt: 0,
    loadingPromise: null,
    taxonomyStatus: null,
  }),
  getters: {
    getTaxonomyStatus: (state) => state.taxonomyStatus,
    getTaxonomyReady: (state) => state.taxonomyStatus?.taxonomy_ready ?? true,
  },
  actions: {
    setTaxonomyStatus(data: null | PlatformSetupStatusResponse) {
      this.taxonomyStatus = data;
      this.lastLoadedAt = data ? Date.now() : 0;
      this.loadingPromise = null;
    },
    async fetchTaxonomyStatus(force = false) {
      const now = Date.now();
      if (
        !force &&
        this.taxonomyStatus &&
        now - this.lastLoadedAt < CACHE_TTL_MS
      ) {
        return this.taxonomyStatus;
      }
      if (this.loadingPromise) {
        return this.loadingPromise;
      }
      this.loadingPromise = getPlatformSetupStatusApi()
        .then((data) => {
          this.setTaxonomyStatus(data);
          return data;
        })
        .catch((error) => {
          this.setTaxonomyStatus(null);
          throw error;
        })
        .finally(() => {
          this.loadingPromise = null;
        });
      return this.loadingPromise;
    },
    clearTaxonomyStatus() {
      this.setTaxonomyStatus(null);
    },
  },
});

const hot = import.meta.hot;
if (hot) {
  hot.accept(acceptHMRUpdate(usePlatformSetupStore, hot));
}

export function usePlatformSetupStoreWithOut() {
  return usePlatformSetupStore(store);
}
