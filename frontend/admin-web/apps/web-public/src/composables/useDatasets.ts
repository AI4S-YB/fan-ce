import { ref } from 'vue';
import { useRequest } from './useRequest';
import type {
  PublicDatasetItem,
  PublicDatasetDetail,
  PublicLineageItem,
  QueryCapabilities,
  QueryResult,
} from '@/types/dataset';

const { get, post } = useRequest();
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
      id: datasetId,
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
        id: datasetId,
        asset_code: assetCode,
        version_id: versionId,
        operation,
        params,
      });
      queryResult.value = data;
      return data;
    } finally {
      queryLoading.value = false;
    }
  }

  return { queryLoading, queryResult, capabilities, loadCapabilities, execute };
}

// ── Dataset downloads ──
export function useDownloads() {
  const loading = ref(false);
  const files = ref<any[]>([]);

  async function loadDownloads(datasetCode: string) {
    loading.value = true;
    try {
      const data: any = await get(`${PRE}/${datasetCode}/downloads`);
      files.value = data?.files || [];
    } finally {
      loading.value = false;
    }
  }

  function downloadUrl(datasetCode: string, fileId: number) {
    const base = import.meta.env.VITE_API_BASE_URL || '/api/v1';
    return `${base}${PRE}/${datasetCode}/download/${fileId}`;
  }

  return { loading, files, loadDownloads, downloadUrl };
}
