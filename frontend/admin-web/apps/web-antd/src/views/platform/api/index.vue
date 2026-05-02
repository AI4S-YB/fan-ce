<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';
import { useAppConfig } from '@vben/hooks';
import { $t } from '@vben/locales';

import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Input,
  Segmented,
  Space,
  Spin,
  Tag,
} from 'ant-design-vue';

defineOptions({ name: 'PlatformApiManagementPage' });

type DocViewKey = 'openapi' | 'redoc' | 'swagger';
type HttpMethod =
  | 'delete'
  | 'get'
  | 'head'
  | 'options'
  | 'patch'
  | 'post'
  | 'put';

interface ApiOperationItem {
  id: string;
  method: HttpMethod;
  path: string;
  summary: string;
  tags: string[];
  operationId?: string;
}

interface SpotlightDefinition {
  key: string;
  title: string;
  description: string;
  matchers: string[];
}

const { apiURL } = useAppConfig(import.meta.env, import.meta.env.PROD);

const activeView = ref<DocViewKey>('swagger');
const openApiContent = ref('');
const openApiLoading = ref(false);
const openApiError = ref('');
const openApiSpec = ref<Record<string, any> | null>(null);
const selectedSpotlight = ref('germplasm');
const endpointKeyword = ref('');

const httpMethods: HttpMethod[] = [
  'get',
  'post',
  'put',
  'patch',
  'delete',
  'options',
  'head',
];

const spotlightDefinitions: SpotlightDefinition[] = [
  {
    key: 'germplasm',
    title: $t('page.germplasm'),
    description: $t('platform.api.spotlightGermplasmDesc'),
    matchers: ['/breeding/germplasm'],
  },
  {
    key: 'breeding',
    title: $t('platform.api.spotlightBreedingTitle'),
    description: $t('platform.api.spotlightBreedingDesc'),
    matchers: ['/breeding/program', '/breeding/material', '/breeding/trial', '/breeding/plot', '/breeding/biosample', '/breeding/observation', '/breeding/assay', '/breeding/data-file'],
  },
  {
    key: 'dataset',
    title: $t('platform.api.spotlightDatasetTitle'),
    description: $t('platform.api.spotlightDatasetDesc'),
    matchers: ['/dataset', '/datasets'],
  },
  {
    key: 'platform',
    title: $t('platform.api.spotlightPlatformTitle'),
    description: $t('platform.api.spotlightPlatformDesc'),
    matchers: ['/platform', '/system', '/auth', '/user', '/role', '/menu'],
  },
];

const docViewOptions: Array<{ label: string; value: DocViewKey }> = [
  { label: 'Swagger', value: 'swagger' },
  { label: 'ReDoc', value: 'redoc' },
  { label: 'OpenAPI JSON', value: 'openapi' },
];

function resolveApiRoot(url: string) {
  if (!/^https?:\/\//i.test(url)) {
    return window.location.origin;
  }
  const parsed = new URL(url, window.location.origin);
  const normalizedPath = parsed.pathname.replace(/\/+$/, '');

  if (normalizedPath.endsWith('/api/v1')) {
    parsed.pathname = normalizedPath.slice(0, -'/api/v1'.length) || '/';
  } else if (normalizedPath.endsWith('/api')) {
    parsed.pathname = normalizedPath.slice(0, -'/api'.length) || '/';
  } else {
    parsed.pathname = normalizedPath || '/';
  }

  return parsed.toString().replace(/\/$/, '');
}

const apiRoot = computed(() => resolveApiRoot(apiURL));
const docsBase = computed(() =>
  /^https?:\/\//i.test(apiURL) ? apiRoot.value : '',
);
const swaggerUrl = computed(() => `${docsBase.value}/docs`);
const redocUrl = computed(() => `${docsBase.value}/redoc`);
const openApiUrl = computed(() => `${docsBase.value}/openapi.json`);
const currentDocUrl = computed(() => {
  if (activeView.value === 'redoc') {
    return redocUrl.value;
  }
  if (activeView.value === 'openapi') {
    return openApiUrl.value;
  }
  return swaggerUrl.value;
});
const iframeUrl = computed(() =>
  activeView.value === 'redoc' ? redocUrl.value : swaggerUrl.value,
);

async function copyCurrentUrl() {
  await navigator.clipboard.writeText(currentDocUrl.value);
}

function openCurrentDoc() {
  window.open(currentDocUrl.value, '_blank', 'noopener,noreferrer');
}

async function loadOpenApiSpec() {
  openApiLoading.value = true;
  openApiError.value = '';
  try {
    const response = await fetch(openApiUrl.value, {
      credentials: 'include',
    });
    if (!response.ok) {
      throw new Error($t('platform.api.openApiFetchFailed', { status: response.status }));
    }
    const json = await response.json();
    openApiSpec.value = json;
    openApiContent.value = JSON.stringify(json, null, 2);
  } catch (error) {
    openApiSpec.value = null;
    openApiContent.value = '';
    openApiError.value =
      error instanceof Error ? error.message : $t('platform.api.openApiLoadFailed');
  } finally {
    openApiLoading.value = false;
  }
}

const apiOperations = computed<ApiOperationItem[]>(() => {
  const paths = openApiSpec.value?.paths || {};
  const operations: ApiOperationItem[] = [];

  Object.entries(paths).forEach(([path, methodMap]) => {
    httpMethods.forEach((method) => {
      const operation = (methodMap as Record<string, any>)?.[method];
      if (!operation) {
        return;
      }
      operations.push({
        id: `${method}:${path}`,
        method,
        path,
        summary: operation.summary || operation.description || '-',
        tags: Array.isArray(operation.tags) ? operation.tags : [],
        operationId: operation.operationId,
      });
    });
  });

  return operations.sort(
    (a, b) => a.path.localeCompare(b.path) || a.method.localeCompare(b.method),
  );
});

const apiStats = computed(() => ({
  operationCount: apiOperations.value.length,
  pathCount: new Set(apiOperations.value.map((item) => item.path)).size,
  tagCount: new Set(apiOperations.value.flatMap((item) => item.tags)).size,
}));

const spotlightGroups = computed(() =>
  spotlightDefinitions.map((definition) => {
    const operations = apiOperations.value.filter((item) =>
      definition.matchers.some((matcher) => item.path.startsWith(matcher)),
    );
    return {
      ...definition,
      operations,
      count: operations.length,
      pathCount: new Set(operations.map((item) => item.path)).size,
    };
  }),
);

const filteredOperations = computed(() => {
  const keyword = endpointKeyword.value.trim().toLowerCase();
  let operations = apiOperations.value;

  if (selectedSpotlight.value !== 'all') {
    const spotlight = spotlightGroups.value.find(
      (item) => item.key === selectedSpotlight.value,
    );
    operations = spotlight?.operations || [];
  }

  if (!keyword) {
    return operations.slice(0, 80);
  }

  return operations
    .filter((item) => {
      const haystacks = [
        item.path,
        item.summary,
        item.operationId || '',
        item.tags.join(' '),
      ].map((text) => text.toLowerCase());
      return haystacks.some((text) => text.includes(keyword));
    })
    .slice(0, 80);
});

function methodColor(method: HttpMethod) {
  const colorMap: Record<HttpMethod, string> = {
    delete: 'red',
    get: 'blue',
    head: 'default',
    options: 'default',
    patch: 'orange',
    post: 'green',
    put: 'purple',
  };
  return colorMap[method];
}

watch(
  activeView,
  (value) => {
    if (value === 'openapi' && !openApiContent.value && !openApiLoading.value) {
      void loadOpenApiSpec();
    }
  },
  { immediate: false },
);

onMounted(() => {
  void loadOpenApiSpec();
});
</script>

<template>
  <Page auto-content-height content-class="p-5">
    <div class="api-management-page">
      <Card :bordered="false" class="hero-card">
        <div class="hero-header">
          <div>
            <div class="hero-eyebrow">Platform API Portal</div>
            <h2 class="hero-title">{{ $t('platform.api.title') }}</h2>
            <p class="hero-description">
              {{ $t('platform.api.pageDescription') }}
            </p>
          </div>
          <Space wrap>
            <Button @click="copyCurrentUrl">{{ $t('platform.api.copyUrl') }}</Button>
            <Button type="primary" @click="openCurrentDoc">{{ $t('platform.api.openNewWindow') }}</Button>
          </Space>
        </div>

        <Descriptions bordered :column="1" class="hero-meta">
          <Descriptions.Item :label="$t('platform.api.apiBaseUrl')">
            <code class="meta-url">{{ apiRoot }}</code>
          </Descriptions.Item>
          <Descriptions.Item :label="$t('platform.api.currentView')">
            <Space wrap>
              <Tag color="blue">{{ activeView }}</Tag>
              <span>{{ currentDocUrl }}</span>
            </Space>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card :bordered="false" class="doc-card">
        <div class="doc-toolbar">
          <Segmented v-model:value="activeView" :options="docViewOptions" />
          <Space wrap>
            <Button size="small" @click="activeView = 'swagger'">Swagger</Button>
            <Button size="small" @click="activeView = 'redoc'">ReDoc</Button>
            <Button size="small" @click="activeView = 'openapi'">
              JSON
            </Button>
          </Space>
        </div>

        <Alert
          class="mb-4"
          type="info"
          show-icon
          :message="$t('platform.setting.note')"
          :description="$t('platform.api.docNoteDesc')"
        />

        <div class="overview-grid">
          <Card size="small" class="overview-stat">
            <div class="overview-label">{{ $t('platform.api.endpointCount') }}</div>
            <div class="overview-value">{{ apiStats.operationCount }}</div>
          </Card>
          <Card size="small" class="overview-stat">
            <div class="overview-label">{{ $t('platform.api.pathCount') }}</div>
            <div class="overview-value">{{ apiStats.pathCount }}</div>
          </Card>
          <Card size="small" class="overview-stat">
            <div class="overview-label">{{ $t('platform.api.tagCount') }}</div>
            <div class="overview-value">{{ apiStats.tagCount }}</div>
          </Card>
          <Card size="small" class="overview-stat focus-stat">
            <div class="overview-label">{{ $t('platform.api.currentFocus') }}</div>
            <div class="overview-value">breeding/germplasm</div>
          </Card>
        </div>

        <Card size="small" class="spotlight-card" :bordered="false">
          <template #title>{{ $t('platform.api.spotlightGroups') }}</template>
          <div class="spotlight-grid">
            <button
              v-for="group in spotlightGroups"
              :key="group.key"
              type="button"
              class="spotlight-item"
              :class="{ active: selectedSpotlight === group.key }"
              @click="selectedSpotlight = group.key"
            >
              <div class="spotlight-header">
                <span class="spotlight-title">{{ group.title }}</span>
                <Tag color="blue">{{ group.count }}</Tag>
              </div>
              <div class="spotlight-description">{{ group.description }}</div>
              <div class="spotlight-meta">{{ group.pathCount }}{{ $t('platform.api.pathSuffix') }}</div>
            </button>
          </div>
        </Card>

        <Card size="small" class="endpoint-card" :bordered="false">
          <template #title>{{ $t('platform.api.endpointOverview') }}</template>
          <template #extra>
            <Space wrap>
              <Button
                size="small"
                :type="selectedSpotlight === 'all' ? 'primary' : 'default'"
                @click="selectedSpotlight = 'all'"
              >
                {{ $t('platform.api.showAll') }}
              </Button>
              <Input
                v-model:value="endpointKeyword"
                allow-clear
                :placeholder="$t('platform.api.searchEndpointPlaceholder')"
                style="width: 260px"
              />
            </Space>
          </template>
          <div v-if="filteredOperations.length" class="endpoint-list">
            <div
              v-for="item in filteredOperations"
              :key="item.id"
              class="endpoint-item"
            >
              <div class="endpoint-main">
                <Space wrap>
                  <Tag :color="methodColor(item.method)">{{ item.method.toUpperCase() }}</Tag>
                  <code class="endpoint-path">{{ item.path }}</code>
                </Space>
                <div class="endpoint-summary">{{ item.summary }}</div>
              </div>
              <div class="endpoint-side">
                <Tag
                  v-for="tag in item.tags.slice(0, 3)"
                  :key="`${item.id}-${tag}`"
                  color="default"
                >
                  {{ tag }}
                </Tag>
              </div>
            </div>
          </div>
          <Empty v-else :description="$t('platform.api.noEndpointFound')" />
        </Card>

        <div v-if="activeView === 'openapi'" class="json-viewer">
          <Spin :spinning="openApiLoading">
            <Alert
              v-if="openApiError"
              :message="openApiError"
              type="warning"
              show-icon
              class="mb-4"
            />
            <pre v-if="openApiContent" class="json-content">{{
              openApiContent
            }}</pre>
            <Empty
              v-else-if="!openApiLoading && !openApiError"
              :description="$t('platform.api.openApiEmpty')"
            />
          </Spin>
        </div>

        <iframe
          v-else
          :src="iframeUrl"
          class="doc-frame"
          frameborder="0"
          title="API documentation"
        />
      </Card>
    </div>
  </Page>
</template>

<style scoped lang="less">
.api-management-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero-card {
  overflow: hidden;
  background:
    radial-gradient(circle at top right, rgba(22, 119, 255, 0.12), transparent 34%),
    linear-gradient(135deg, #f8fbff 0%, #f6f8fc 100%);
}

.hero-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
}

.hero-eyebrow {
  margin-bottom: 8px;
  color: #1677ff;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-title {
  margin: 0;
  color: #13213a;
  font-size: 28px;
  font-weight: 700;
}

.hero-description {
  max-width: 760px;
  margin: 12px 0 0;
  color: #4f5f7c;
  font-size: 14px;
  line-height: 1.75;
}

.hero-meta {
  margin-top: 20px;
}

.meta-url {
  display: inline-block;
  padding: 6px 10px;
  color: #15417e;
  word-break: break-all;
  background: rgba(22, 119, 255, 0.08);
  border-radius: 8px;
}

.doc-card {
  min-height: 780px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.overview-stat {
  border-radius: 14px;
  background: #f8fbff;
}

.overview-label {
  color: #6b7890;
  font-size: 12px;
}

.overview-value {
  margin-top: 8px;
  color: #13213a;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.focus-stat {
  background:
    linear-gradient(135deg, rgba(22, 119, 255, 0.1), rgba(22, 119, 255, 0.02));
}

.doc-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.spotlight-card,
.endpoint-card {
  margin-bottom: 16px;
}

.spotlight-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.spotlight-item {
  padding: 14px;
  text-align: left;
  background: #f8fbff;
  border: 1px solid transparent;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.spotlight-item:hover,
.spotlight-item.active {
  border-color: rgba(22, 119, 255, 0.35);
  box-shadow: 0 8px 18px rgba(22, 119, 255, 0.08);
}

.spotlight-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.spotlight-title {
  color: #13213a;
  font-weight: 700;
}

.spotlight-description {
  margin-top: 10px;
  color: #50607b;
  font-size: 13px;
  line-height: 1.6;
}

.spotlight-meta {
  margin-top: 10px;
  color: #1677ff;
  font-size: 12px;
  font-weight: 600;
}

.endpoint-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.endpoint-item {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  padding: 14px 16px;
  background: #fbfcfe;
  border: 1px solid #edf2f8;
  border-radius: 14px;
}

.endpoint-main {
  min-width: 0;
  flex: 1;
}

.endpoint-path {
  padding: 2px 8px;
  color: #15417e;
  word-break: break-all;
  background: rgba(22, 119, 255, 0.08);
  border-radius: 8px;
}

.endpoint-summary {
  margin-top: 8px;
  color: #53627a;
  line-height: 1.6;
}

.endpoint-side {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  max-width: 260px;
}

.doc-frame {
  width: 100%;
  min-height: 980px;
  border: 1px solid #eef2f7;
  border-radius: 14px;
  background: #fff;
}

.json-viewer {
  min-height: 720px;
}

.json-content {
  min-height: 720px;
  padding: 20px;
  overflow: auto;
  color: #dce7ff;
  white-space: pre-wrap;
  word-break: break-word;
  background:
    linear-gradient(180deg, rgba(18, 31, 54, 0.98), rgba(13, 23, 40, 0.98));
  border-radius: 14px;
}

@media (max-width: 960px) {
  .hero-header,
  .doc-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .overview-grid,
  .spotlight-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .endpoint-item {
    flex-direction: column;
  }

  .endpoint-side {
    justify-content: flex-start;
    max-width: none;
  }

  .doc-frame,
  .json-content,
  .json-viewer {
    min-height: 640px;
  }
}

@media (max-width: 640px) {
  .overview-grid,
  .spotlight-grid {
    grid-template-columns: 1fr;
  }
}
</style>
