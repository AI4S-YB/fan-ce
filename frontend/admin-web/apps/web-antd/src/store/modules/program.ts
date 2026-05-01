import { acceptHMRUpdate, defineStore } from 'pinia';

import { getBreedingProgramListApi } from '#/api/breeding/program';
import { store } from '#/store';

interface DataSelected {
  genome: any | object;
  rnaseq: any | object;
  variant: any | object;
}
interface ProgramState {
  programInfo?: any | object;
  programOptions?: any[];
  dataSelected: DataSelected;
}

export const useProgramStore = defineStore('app-program', {
  state: (): ProgramState => ({
    programInfo: {},
    programOptions: [],
    dataSelected: {
      genome: {},
      rnaseq: {},
      variant: {},
    } as any,
  }),
  getters: {
    getProgramInfo: (state) => state.programInfo,
    getProgramOptions: (state) => state.programOptions,
    getDataSelected: (state) => state.dataSelected,
  },
  actions: {
    setProgramInfo(info: any) {
      this.programInfo = info;
    },
    setProgramOptions(options: any[]) {
      this.programOptions = options;
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

    async fetchProgramOptions() {
      const data: any = await getBreedingProgramListApi({
        page: 1, size: 100,
        keyword: undefined,
        species_name: undefined,
        status: 'active',
      });
      const items = data?.dataList || data?.items || [];
      this.programOptions = items.map((p: any) => ({
        label: p.name, value: p.id, id: p.id, name: p.name, code: p.code,
      }));
      return this.programOptions;
    },
    async updateProgramOptions() {
      await this.fetchProgramOptions();
      this.programInfo = this.programOptions?.[0] || {};
      return this.programOptions;
    },
  },
  persist: {
    pick: ['programInfo'],
  },
});

const hot = import.meta.hot;
if (hot) {
  hot.accept(acceptHMRUpdate(useProgramStore, hot));
}

export function useProgramStoreWithOut() {
  return useProgramStore(store);
}
