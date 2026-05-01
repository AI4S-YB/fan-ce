import { acceptHMRUpdate, defineStore } from 'pinia';

import { getProjectOptionsApi } from '#/api/system/project';
import { store } from '#/store';

interface DataSelected {
  genome: any | object;
  rnaseq: any | object;
  variant: any | object;
}
interface UserState {
  projectInfo?: any | object;
  projectOptions?: any[];
  dataSelected: DataSelected;
}

export const useAppUserStore = defineStore('app-user', {
  state: (): UserState => ({
    projectInfo: {},
    projectOptions: [],
    dataSelected: {
      genome: {},
      rnaseq: {},
      variant: {},
    } as any,
  }),
  getters: {
    getProjectInfo: (state) => state.projectInfo,
    getProjectOptions: (state) => state.projectOptions,
    getDataSelected: (state) => state.dataSelected,
  },
  actions: {
    setProjectInfo(info: any) {
      this.projectInfo = info;
    },
    setProjectOptions(options: any[]) {
      this.projectOptions = options;
    },
    setDataGenomeSelected(data: DataSelected['genome']) {
      this.dataSelected.genome = data;
    },
    setDataRnaseqSelected(data: DataSelected['rnaseq']) {
      this.dataSelected.rnaseq = data;
    },
    setDataVariantSelected(data: DataSelected['variant']) {
      this.dataSelected.variant = data;
    },

    async fetchProjectOptions() {
      const data: any = await getProjectOptionsApi({});
      this.projectOptions = data;
      return data;
    },
    async updateProjectOptions() {
      const data: any = await getProjectOptionsApi({});
      this.projectOptions = data;
      this.projectInfo = data?.[0];
      return data;
    },
  },
  persist: {
    // 持久化
    pick: ['projectInfo'],
  },
});
// 解决热更新问题
const hot = import.meta.hot;
if (hot) {
  hot.accept(acceptHMRUpdate(useAppUserStore, hot));
}
export function useProjectStoreWithOut() {
  return useAppUserStore(store);
}
//
// import { useProjectStoreWithOut } from '#/store/modules/project';
// const proStore = useProjectStoreWithOut();
