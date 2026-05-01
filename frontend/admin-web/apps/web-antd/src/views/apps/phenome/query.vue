<script setup lang="ts">
import type {
  DatasetAssetItem,
  DatasetDetailItem,
  DatasetVersionDetail,
  DatasetVersionListResult,
  DatasetVersionQueryCapabilitiesResult,
} from '#/api/apps/dataset';

import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Input,
  List,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  executeDatasetVersionQueryApi,
  getDatasetInfoApi,
  getDatasetVersionInfoApi,
  getDatasetVersionListApi,
  getDatasetVersionQueryCapabilitiesApi,
} from '#/api/apps/dataset';
import { useMessage } from '#/hooks/web/useMessage';
import { $t } from '@vben/locales';

defineOptions({ name: 'PhenomeQueryPage' });

type TraitItem = {
  name?: string;
  trait_code?: string;
  trait_name?: string;
  declared_type?: string;
  position?: number;
  time_axis_type?: string | null;
};

type TraitValueItem = {
  subject_id?: string;
  value?: any;
  raw_value?: any;
  timepoint?: string | null;
};

const route = useRoute();
const router = useRouter();
const { createMessage } = useMessage();

const pageLoading = ref(false);
const summaryLoading = ref(false);
const traitLoading = ref(false);
const traitValueLoading = ref(false);
const subjectLoading = ref(false);
const subjectDetailLoading = ref(false);

const datasetInfo = ref<DatasetDetailItem | null>(null);
const versionList = ref<DatasetVersionListResult | null>(null);
const versionInfo = ref<DatasetVersionDetail | null>(null);
const capabilities = ref<DatasetVersionQueryCapabilitiesResult | null>(null);

const summaryData = ref<Record<string, any> | null>(null);
const traitRows = ref<TraitItem[]>([]);
const subjectRows = ref<string[]>([]);
const selectedTraitValues = ref<TraitValueItem[]>([]);
const selectedSubjectDetail = ref<Record<string, any> | null>(null);

const selectedTrait = ref('');
const selectedSubjectId = ref('');
const subjectKeyword = ref('');
const traitKeyword = ref('');
const loadedRouteKey = ref('');
const pageError = ref('');

const queryState = reactive({
  datasetId: 0,
  versionId: 0,
  assetCode: '',
});

const traitColumns = [
  { title: $t('phenome.query.traitName'), dataIndex: 'name', key: 'name', minWidth: 220 },
  { title: $t('phenome.query.traitCode'), dataIndex: 'trait_code', key: 'trait_code', width: 180 },
  { title: $t('phenome.query.type'), dataIndex: 'declared_type', key: 'declared_type', width: 120 },
  { title: $t('phenome.query.timeAxis'), dataIndex: 'time_axis_type', key: 'time_axis_type', width: 120 },
];

const traitValueColumns = [
  { title: $t('phenome.query.materialSample'), dataIndex: 'subject_id', key: 'subject_id', width: 180 },
  { title: $t('phenome.query.value'), dataIndex: 'value', key: 'value', width: 160 },
  { title: $t('phenome.query.timepoint'), dataIndex: 'timepoint', key: 'timepoint', width: 120 },
  { title: $t('phenome.query.rawValue'), dataIndex: 'raw_value', key: 'raw_value', minWidth: 180 },
];

const assetOptions = computed(() =>
  (capabilities.value?.assets || []).map((item) => ({
    label: `${item.asset_name || item.asset_code || item.id} (${item.asset_type || '-'})`,
    value: item.asset_code || '',
  })).filter((item) => item.value),
);

const versionOptions = computed(() =>
  (versionList.value?.items || []).map((item) => ({
    label: `${item.version || `v-${item.id}`}${item.is_current ? ' · ' + $t('phenome.query.current') : ''}${item.is_default_public ? ' · ' + $t('phenome.query.defaultPublic') : ''}`,
    value: item.id,
  })),
);

const filteredSubjects = computed(() => {
  const keyword = subjectKeyword.value.trim().toLowerCase();
  if (!keyword) {
    return subjectRows.value;
  }
  return subjectRows.value.filter((item) => item.toLowerCase().includes(keyword));
});

const datasetTitle = computed(
  () => datasetInfo.value?.title || datasetInfo.value?.name || datasetInfo.value?.dataset_code || `Dataset ${queryState.datasetId}`,
);

const selectedAsset = computed<DatasetAssetItem | null>(() => {
  const assetCode = queryState.assetCode;
  const assets = capabilities.value?.assets || [];
  if (assetCode) {
    return assets.find((item) => item.asset_code === assetCode) || null;
  }
  return capabilities.value?.query_entry_asset || assets[0] || null;
});

function normalizeRouteState() {
  queryState.datasetId = Number(route.query.dataset_id || 0);
  queryState.versionId = Number(route.query.version_id || 0);
  queryState.assetCode = String(route.query.asset_code || '');
}

function syncRouteQuery() {
  router.replace({
    path: '/apps/phenome/query',
    query: {
      dataset_id: String(queryState.datasetId || ''),
      version_id: String(queryState.versionId || ''),
      asset_code: queryState.assetCode || undefined,
    },
  }).catch(() => {});
}

function isPhenomeDatasetType(datasetType?: string | null) {
  return datasetType === 'phenome' || datasetType === 'phenotype';
}

function buildRouteKey() {
  return `${queryState.datasetId || 0}|${queryState.versionId || 0}|${queryState.assetCode || ''}`;
}

function getTraitRowKey(record: TraitItem) {
  return record.trait_code || record.name || record.trait_name || '';
}

function getTraitValueRowKey(record: TraitValueItem, index: number) {
  return `${record.subject_id || 'subject'}-${record.timepoint || 'na'}-${index}`;
}

async function executeVersionQuery(operation: string, params?: Record<string, any>) {
  if (!queryState.versionId) {
    throw new Error($t('phenome.query.missingVersionId'));
  }
  return executeDatasetVersionQueryApi({
    id: queryState.versionId,
    operation,
    asset_code: queryState.assetCode || undefined,
    params,
  });
}

async function loadSummary() {
  summaryLoading.value = true;
  try {
    const result = await executeVersionQuery('dataset_summary', {});
    summaryData.value = result.data || null;
  } finally {
    summaryLoading.value = false;
  }
}

async function loadTraits(keyword?: string) {
  traitLoading.value = true;
  try {
    const result = keyword?.trim()
      ? await executeVersionQuery('trait_search', { keyword: keyword.trim(), limit: 200 })
      : await executeVersionQuery('trait_list', { limit: 200 });
    traitRows.value = result.data?.items || [];
    if (!traitRows.value.length) {
      selectedTrait.value = '';
      selectedTraitValues.value = [];
      return;
    }
    if (!selectedTrait.value && traitRows.value.length) {
      selectedTrait.value = String(
        traitRows.value[0]?.trait_code || traitRows.value[0]?.trait_name || traitRows.value[0]?.name || '',
      );
    }
  } finally {
    traitLoading.value = false;
  }
}

async function loadTraitValues(trait?: string) {
  const resolvedTrait = String(trait || selectedTrait.value || '').trim();
  if (!resolvedTrait) {
    selectedTraitValues.value = [];
    return;
  }
  traitValueLoading.value = true;
  try {
    const result = await executeVersionQuery('trait_values', {
      trait: resolvedTrait,
      limit: 200,
    });
    selectedTrait.value = String(result.data?.trait_code || result.data?.trait || resolvedTrait);
    selectedTraitValues.value = result.data?.items || [];
  } finally {
    traitValueLoading.value = false;
  }
}

async function loadSubjects() {
  subjectLoading.value = true;
  try {
    const result = await executeVersionQuery('subject_list', { limit: 500 });
    subjectRows.value = result.data?.items || [];
    if (!subjectRows.value.length) {
      selectedSubjectId.value = '';
      selectedSubjectDetail.value = null;
      return;
    }
    if (!selectedSubjectId.value && subjectRows.value.length) {
      selectedSubjectId.value = subjectRows.value[0] || '';
    }
  } finally {
    subjectLoading.value = false;
  }
}

async function loadSubjectDetail(subjectId?: string) {
  const resolvedSubjectId = String(subjectId || selectedSubjectId.value || '').trim();
  if (!resolvedSubjectId) {
    selectedSubjectDetail.value = null;
    return;
  }
  subjectDetailLoading.value = true;
  try {
    const result = await executeVersionQuery('subject_detail', {
      subject_id: resolvedSubjectId,
    });
    selectedSubjectId.value = String(result.data?.subject_id || resolvedSubjectId);
    selectedSubjectDetail.value = result.data || null;
  } finally {
    subjectDetailLoading.value = false;
  }
}

async function loadPage() {
  if (!queryState.datasetId) {
    pageError.value = $t('phenome.query.missingDatasetId');
    createMessage.error(pageError.value);
    return;
  }
  pageLoading.value = true;
  pageError.value = '';
  try {
    const [dataset, versions] = await Promise.all([
      getDatasetInfoApi({ id: queryState.datasetId }),
      getDatasetVersionListApi({ dataset_id: queryState.datasetId }),
    ]);
    datasetInfo.value = dataset;
    versionList.value = versions;
    if (!isPhenomeDatasetType(dataset.dataset_type)) {
      throw new Error($t('phenome.query.notPhenomeType', { type: dataset.dataset_type || '-' }));
    }

    const resolvedVersionId =
      queryState.versionId ||
      versions.current_version?.id ||
      versions.default_public_version?.id ||
      versions.published_version?.id ||
      versions.items?.[0]?.id ||
      0;
    if (!resolvedVersionId) {
      throw new Error($t('phenome.query.noVersionAvailable'));
    }
    queryState.versionId = resolvedVersionId;

    const [version, capability] = await Promise.all([
      getDatasetVersionInfoApi({ id: resolvedVersionId }),
      getDatasetVersionQueryCapabilitiesApi({
        id: resolvedVersionId,
        asset_code: queryState.assetCode || undefined,
      }),
    ]);
    versionInfo.value = version;
    capabilities.value = capability;

    if (capability.query_adapter?.adapter !== 'phenome') {
      throw new Error($t('phenome.query.notPhenomeAdapter', { adapter: capability.query_adapter?.adapter || '-' }));
    }

    await Promise.all([loadSummary(), loadTraits(traitKeyword.value), loadSubjects()]);
    await Promise.all([
      selectedTrait.value ? loadTraitValues(selectedTrait.value) : Promise.resolve(),
      selectedSubjectId.value ? loadSubjectDetail(selectedSubjectId.value) : Promise.resolve(),
    ]);
    loadedRouteKey.value = buildRouteKey();
    syncRouteQuery();
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : $t('phenome.query.loadError');
    createMessage.error(pageError.value);
  } finally {
    pageLoading.value = false;
  }
}

async function handleAssetChange(value?: string) {
  queryState.assetCode = value || '';
  selectedTrait.value = '';
  selectedSubjectId.value = '';
  selectedTraitValues.value = [];
  selectedSubjectDetail.value = null;
  await loadPage();
}

async function handleVersionChange(value?: number) {
  if (!value) {
    return;
  }
  queryState.versionId = Number(value);
  selectedTrait.value = '';
  selectedSubjectId.value = '';
  selectedTraitValues.value = [];
  selectedSubjectDetail.value = null;
  await loadPage();
}

function openVersionWorkspace() {
  router.push('/apps/dataset').catch(() => {});
}

async function handleTraitSearch() {
  await loadTraits(traitKeyword.value);
  if (selectedTrait.value) {
    await loadTraitValues(selectedTrait.value);
  }
}

async function handleTraitReset() {
  traitKeyword.value = '';
  await handleTraitSearch();
}

watch(
  () => route.query,
  () => {
    normalizeRouteState();
    const nextRouteKey = buildRouteKey();
    if (nextRouteKey && nextRouteKey !== loadedRouteKey.value) {
      void loadPage();
    }
  },
);

onMounted(async () => {
  normalizeRouteState();
  await loadPage();
});
</script>

<template>
  <Page auto-content-height content-class="p-5">
    <div class="phenome-query-page">
      <Card :bordered="false" class="hero-card">
        <div class="hero-eyebrow">{{ $t('phenome.query.heroEyebrow') }}</div>
        <div class="hero-header">
          <div>
            <h2 class="hero-title">{{ $t('phenome.query.title') }}</h2>
            <p class="hero-description">
              {{ $t('phenome.query.description') }}
            </p>
          </div>
          <Space>
            <Button @click="openVersionWorkspace">{{ $t('phenome.query.backToDataset') }}</Button>
            <Button type="primary" @click="loadPage">{{ $t('phenome.query.refresh') }}</Button>
          </Space>
        </div>
      </Card>

      <Spin :spinning="pageLoading">
        <Alert
          v-if="pageError"
          type="error"
          show-icon
          :message="pageError"
          class="page-error"
        />

        <Card :bordered="false">
          <Descriptions bordered :column="2" size="small">
            <Descriptions.Item :label="$t('phenome.query.dataset')">
              {{ datasetTitle }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('phenome.query.datasetCode')">
              {{ datasetInfo?.dataset_code || '-' }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('phenome.query.datasetType')">
              <Tag color="processing">{{ datasetInfo?.dataset_type || '-' }}</Tag>
            </Descriptions.Item>
            <Descriptions.Item :label="$t('phenome.query.adapter')">
              {{ capabilities?.query_adapter?.display_name || '-' }}
            </Descriptions.Item>
            <Descriptions.Item :label="$t('phenome.query.version')">
              <Select
                v-model:value="queryState.versionId"
                style="min-width: 240px"
                :options="versionOptions"
                @change="(value) => { handleVersionChange(value as number | undefined); }"
              />
            </Descriptions.Item>
            <Descriptions.Item :label="$t('phenome.query.queryAsset')">
              <Select
                v-model:value="queryState.assetCode"
                allow-clear
                style="min-width: 260px"
                :options="assetOptions"
                :placeholder="$t('phenome.query.defaultAssetPlaceholder')"
                @change="(value) => { handleAssetChange(value as string | undefined); }"
              />
            </Descriptions.Item>
            <Descriptions.Item :label="$t('phenome.query.mainFilePath')" :span="2">
              {{ capabilities?.file_path || versionInfo?.file_path || '-' }}
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <div class="summary-grid">
          <Card :bordered="false">
            <Statistic :title="$t('phenome.query.sampleCount')" :value="summaryData?.subject_count || 0" />
          </Card>
          <Card :bordered="false">
            <Statistic :title="$t('phenome.query.traitCount')" :value="summaryData?.trait_count || 0" />
          </Card>
          <Card :bordered="false">
            <Statistic :title="$t('phenome.query.observationCount')" :value="summaryData?.observation_count || 0" />
          </Card>
          <Card :bordered="false">
            <Statistic :title="$t('phenome.query.currentAsset')" :value="selectedAsset?.asset_code || $t('phenome.query.default')" />
          </Card>
        </div>

        <div class="content-grid">
          <Card :bordered="false" class="panel-card">
            <template #title>{{ $t('phenome.query.traitBrowse') }}</template>
            <div class="panel-toolbar">
              <Input
                v-model:value="traitKeyword"
                allow-clear
                :placeholder="$t('phenome.query.traitSearchPlaceholder')"
                @press-enter="handleTraitSearch"
              />
              <Space>
                <Button type="primary" @click="handleTraitSearch">{{ $t('phenome.query.query') }}</Button>
                <Button @click="handleTraitReset">{{ $t('phenome.query.reset') }}</Button>
              </Space>
            </div>
            <Table
              :columns="traitColumns"
              :data-source="traitRows"
              :loading="traitLoading"
              :pagination="false"
              :scroll="{ x: 760, y: 320 }"
              size="small"
              :row-key="getTraitRowKey"
            >
              <template #emptyText>
                <Empty :description="$t('phenome.query.noTraits')" />
              </template>
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'name'">
                  <Button
                    type="link"
                    class="link-cell"
                    @click="() => { void loadTraitValues(String(record.trait_code || record.name || '')); }"
                  >
                    {{ record.name || '-' }}
                  </Button>
                </template>
              </template>
            </Table>
          </Card>

          <Card :bordered="false" class="panel-card">
            <template #title>{{ $t('phenome.query.sampleBrowse') }}</template>
            <div class="panel-toolbar">
              <Input
                v-model:value="subjectKeyword"
                allow-clear
                :placeholder="$t('phenome.query.sampleFilterPlaceholder')"
              />
            </div>
            <List
              v-if="filteredSubjects.length"
              bordered
              size="small"
              :data-source="filteredSubjects"
              class="subject-list"
            >
              <template #renderItem="{ item }">
                <List.Item>
                  <Button type="link" class="link-cell" @click="() => { void loadSubjectDetail(String(item)); }">
                    {{ item }}
                  </Button>
                </List.Item>
              </template>
            </List>
            <Empty v-else :description="$t('phenome.query.noSamples')" />
          </Card>
        </div>

        <div class="content-grid">
          <Card :bordered="false" class="panel-card">
            <template #title>
              {{ $t('phenome.query.traitValue') }}
              <Tag v-if="selectedTrait" color="success">{{ selectedTrait }}</Tag>
            </template>
            <Table
              :columns="traitValueColumns"
              :data-source="selectedTraitValues"
              :loading="traitValueLoading"
              :pagination="false"
              :scroll="{ x: 760, y: 360 }"
              size="small"
              :row-key="getTraitValueRowKey"
            >
              <template #emptyText>
                <Empty :description="$t('phenome.query.selectTraitHint')" />
              </template>
            </Table>
          </Card>

          <Card :bordered="false" class="panel-card">
            <template #title>
              {{ $t('phenome.query.sampleDetail') }}
              <Tag v-if="selectedSubjectId" color="processing">{{ selectedSubjectId }}</Tag>
            </template>
            <Spin :spinning="subjectDetailLoading || summaryLoading || subjectLoading">
              <Descriptions
                v-if="selectedSubjectDetail?.traits && Object.keys(selectedSubjectDetail.traits || {}).length"
                bordered
                :column="1"
                size="small"
              >
                <Descriptions.Item
                  v-for="(value, key) in selectedSubjectDetail.traits"
                  :key="String(key)"
                  :label="String(key)"
                >
                  {{ value ?? '-' }}
                </Descriptions.Item>
              </Descriptions>
              <Empty v-else :description="$t('phenome.query.selectSampleHint')" />
            </Spin>
          </Card>
        </div>
      </Spin>
    </div>
  </Page>
</template>

<style scoped lang="less">
.phenome-query-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-error {
  margin-bottom: 16px;
}

.hero-card {
  background:
    radial-gradient(circle at top right, rgba(22, 119, 255, 0.12), transparent 34%),
    linear-gradient(135deg, #f8fbff 0%, #f6f8fc 100%);
}

.hero-eyebrow {
  color: #1677ff;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.hero-title {
  margin: 8px 0;
  color: #13213a;
  font-size: 26px;
  font-weight: 700;
}

.hero-description {
  margin: 0;
  max-width: 820px;
  color: #4d5d7a;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: 16px;
}

.panel-card {
  min-height: 320px;
}

.panel-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}

.subject-list {
  max-height: 360px;
  overflow: auto;
}

.link-cell {
  padding-inline: 0;
}

@media (max-width: 1200px) {
  .summary-grid,
  .content-grid {
    grid-template-columns: 1fr;
  }

  .hero-header,
  .panel-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
