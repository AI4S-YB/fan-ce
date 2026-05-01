<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Button, Tag, Space, Empty, Descriptions, message } from 'ant-design-vue';
import { Page } from '@vben/common-ui';
import QueryForm from './components/QueryForm.vue';
import {
  getPreferredDatasetTypeCode,
  useDataset,
} from './composables/useDataset';
import type { DatasetVersionQueryExecuteResult } from '#/api/apps/dataset';
import { $t } from '@vben/locales';

const route = useRoute();
const router = useRouter();

const datasetId = computed(() => Number(route.params.id));

const {
  detailLoading, detailData, loadDetail,
  versionListData, loadVersionList,
  queryCapabilitiesLoading, queryCapabilities, loadQueryCapabilities,
  executeQuery,
} = useDataset();

const queryResult = ref<DatasetVersionQueryExecuteResult | null>(null);
const queryError = ref('');

const activeVersionId = computed(() =>
  versionListData.value?.current_version?.id || null,
);

async function loadPageData() {
  await Promise.all([
    loadDetail(datasetId.value),
    loadVersionList(datasetId.value),
  ]);
  if (activeVersionId.value) {
    await loadQueryCapabilities(activeVersionId.value);
  }
}

async function handleExecute(operation: string, params: Record<string, any>) {
  if (!activeVersionId.value) return;
  queryError.value = '';
  queryResult.value = null;
  try {
    queryResult.value = await executeQuery(activeVersionId.value, operation, params);
  } catch (e: any) {
    queryError.value = e?.message || $t('dataset.query.execFailedMsg');
  }
}

function copyResult() {
  if (queryResult.value) {
    navigator.clipboard.writeText(JSON.stringify(queryResult.value, null, 2));
    message.success($t('dataset.query.resultCopied'));
  }
}

onMounted(() => loadPageData());
</script>

<template>
  <Page auto-content-height>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <div>
        <h2 style="margin: 0;">{{ $t('dataset.query.queryPageTitle', { code: detailData?.dataset_code || '-' }) }}</h2>
        <div style="color: #888; font-size: 13px;">
          {{ versionListData?.current_version?.version || '-' }}
          · {{ getPreferredDatasetTypeCode(detailData?.dataset_type) }}
          · {{ detailData?.query_profile?.file_format || detailData?.file_format || '-' }}
        </div>
      </div>
      <Button @click="router.push(`/dataset/${datasetId}`)">{{ $t('dataset.query.backToDetailBtn') }}</Button>
    </div>

    <div style="display: flex; gap: 16px;">
      <!-- Left: Query Form -->
      <div style="width: 360px; flex-shrink: 0;">
        <h3>{{ $t('dataset.query.queryConfigLabel') }}</h3>
        <Descriptions bordered :column="1" size="small" style="margin-bottom: 12px;">
          <Descriptions.Item :label="$t('dataset.query.queryEntryAssetLabel')">
            {{ queryCapabilities?.query_entry_asset?.asset_code || '-' }}
          </Descriptions.Item>
          <Descriptions.Item :label="$t('dataset.query.mainFilePath')">
            {{ queryCapabilities?.file_path || '-' }}
          </Descriptions.Item>
          <Descriptions.Item :label="$t('dataset.query.availableActionLabel')">
            {{ queryCapabilities?.query_adapter?.supported_operations?.join(', ') || '-' }}
          </Descriptions.Item>
        </Descriptions>
        <QueryForm
          :capabilities="queryCapabilities"
          :loading="queryCapabilitiesLoading"
          @execute="handleExecute"
        />
      </div>

      <!-- Right: Results -->
      <div style="flex: 1;">
        <h3>{{ $t('dataset.query.queryResultLabel') }}</h3>
        <div v-if="queryError" style="color: #ff4d4f; padding: 20px; background: #fff2f0; border-radius: 4px;">
          {{ queryError }}
        </div>
        <div v-else-if="queryResult" style="background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 4px; padding: 12px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <Space>
              <Tag color="processing">{{ queryResult.operation }}</Tag>
              <Tag>{{ queryResult.adapter }}</Tag>
            </Space>
            <Button size="small" @click="copyResult">{{ $t('dataset.query.copyJson') }}</Button>
          </div>
          <pre style="max-height: 500px; overflow: auto; font-size: 11px; background: #fff; padding: 8px; border-radius: 4px;">{{ JSON.stringify(queryResult.data || queryResult, null, 2) }}</pre>
        </div>
        <Empty v-else :description="$t('dataset.query.selectActionAndParamsHint')" />
      </div>
    </div>
  </Page>
</template>
