import { ref } from 'vue';
import { useRequest } from './useRequest';
import type {
  PublicDatasetItem,
  PublicDatasetDetail,
  PublicLineageItem,
  QueryCapabilities,
  QueryResult,
} from '@/types/dataset';

const { post } = useRequest();
const PRE = '/public/dataset';

// ── Dataset list ──
export function useDatasetList() {
  const loading = ref(false);
  const items = ref<PublicDatasetItem[]>([]);
  const total = ref(0);

  async function load(params: Record<string, unknown> = {}) {
    loading.value = true;
    try {
      const data: any = await post(`${PRE}/list`, { page: 1, size: 50, ...params });
      items.value = data?.items || data?.dataList || [];
      total.value = data?.total ?? 0;
    } finally {
      loading.value = false;
    }
  }

  return { loading, items, total, load };
}

// ── Dataset detail ──
export function useDatasetDetail() {
  const loading = ref(false);
  const detail = ref<PublicDatasetDetail | null>(null);
  const lineage = ref<PublicLineageItem[]>([]);

  async function load(id: number) {
    loading.value = true;
    detail.value = null;
    lineage.value = [];
    try {
      const data: any = await post(`${PRE}/info`, { id });
      detail.value = data;
      if (data?.dataset_code) {
        try {
          const lin: any = await post(`${PRE}/${data.dataset_code}/lineage`);
          lineage.value = lin?.items || lin || [];
        } catch { /* lineage optional */ }
      }
    } catch (e: any) {
      console.error('Failed to load dataset detail:', id, e?.message || e);
    } finally {
      loading.value = false;
    }
  }
  return { loading, detail, lineage, load };
}

// ── Dataset query ──
export function useDatasetQuery() {
  const queryLoading = ref(false);
  const queryResult = ref<QueryResult | null>(null);
  const capabilities = ref<QueryCapabilities | null>(null);

  async function loadCapabilities(datasetId: number, assetCode?: string, versionId?: number) {
    const data: any = await post(`${PRE}/query/capabilities`, {
      dataset_id: datasetId,
      asset_code: assetCode,
      version_id: versionId,
    });
    capabilities.value = data;
    return data as QueryCapabilities;
  }

  async function execute(
    datasetId: number,
    operation: string,
    params: Record<string, unknown>,
    assetCode?: string,
    versionId?: number,
  ) {
    queryLoading.value = true;
    try {
      const data: any = await post(`${PRE}/query/execute`, {
        dataset_id: datasetId,
        asset_code: assetCode,
        version_id: versionId,
        operation,
        params,
      });
      queryResult.value = data;
    } finally {
      queryLoading.value = false;
    }
  }

  return { queryLoading, queryResult, capabilities, loadCapabilities, execute };
}
