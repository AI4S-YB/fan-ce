<script setup lang="ts">
import type { SiteItem } from '#/api/platform/sites';

import { onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  InputNumber,
  message,
  Popconfirm,
  Space,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  bindDatasetApi,
  listSiteDatasetsApi,
  listSitesApi,
  unbindDatasetApi,
} from '#/api/platform/sites';

defineOptions({ name: 'PlatformSiteDatasetsPage' });

const route = useRoute();
const siteCode = route.params.siteCode as string;

const siteInfo = ref<SiteItem | null>(null);
const datasets = ref<
  Array<{
    id: number;
    dataset_code?: string;
    dataset_name?: string;
    species_name?: string;
  }>
>([]);
const loading = ref(false);
const bindDatasetId = ref<number | null>(null);
const bindSubmitting = ref(false);

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '数据集代码', dataIndex: 'dataset_code', key: 'dataset_code' },
  { title: '数据集名称', dataIndex: 'dataset_name', key: 'dataset_name' },
  { title: '物种', dataIndex: 'species_name', key: 'species_name' },
  {
    title: '操作',
    key: 'action',
    width: 120,
  },
];

async function loadSiteInfo() {
  try {
    const res = await listSitesApi();
    const sites = res.items ?? [];
    siteInfo.value = sites.find((s) => s.site_code === siteCode) ?? null;
  } catch {
    // handled by request interceptor
  }
}

async function loadDatasets() {
  loading.value = true;
  try {
    const res = await listSiteDatasetsApi(siteCode);
    datasets.value = res.items ?? [];
  } catch {
    // handled by request interceptor
  } finally {
    loading.value = false;
  }
}

async function handleBind() {
  if (!bindDatasetId.value) {
    message.warn('请输入数据集 ID');
    return;
  }
  bindSubmitting.value = true;
  try {
    await bindDatasetApi(siteCode, bindDatasetId.value);
    message.success('数据集绑定成功');
    bindDatasetId.value = null;
    await loadDatasets();
  } catch {
    // handled by request interceptor
  } finally {
    bindSubmitting.value = false;
  }
}

async function handleUnbind(datasetId: number) {
  try {
    await unbindDatasetApi(siteCode, datasetId);
    message.success('数据集已解绑');
    await loadDatasets();
  } catch {
    // handled by request interceptor
  }
}

onMounted(() => {
  loadSiteInfo();
  loadDatasets();
});
</script>

<template>
  <Page auto-content-height content-class="p-5">
    <div class="site-datasets-page">
      <Card :bordered="false" title="站点数据集管理">
        <template #extra>
          <Button @click="$router.push('/platform/sites')">返回站点列表</Button>
        </template>

        <div v-if="siteInfo" class="site-summary">
          <Space wrap>
            <Tag color="blue">{{ siteInfo.site_code }}</Tag>
            <span class="site-name">{{ siteInfo.site_name }}</span>
            <span v-if="siteInfo.site_title" class="site-title">
              — {{ siteInfo.site_title }}
            </span>
          </Space>
        </div>

        <div class="bind-section">
          <Space>
            <span>绑定数据集：</span>
            <InputNumber
              v-model:value="bindDatasetId"
              :min="1"
              placeholder="数据集 ID"
              style="width: 160px"
            />
            <Button
              type="primary"
              :loading="bindSubmitting"
              @click="handleBind"
            >
              绑定
            </Button>
          </Space>
        </div>

        <Table
          :columns="columns"
          :data-source="datasets"
          :loading="loading"
          :pagination="false"
          row-key="id"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'action'">
              <Popconfirm
                title="确定解绑该数据集吗？"
                @confirm="handleUnbind(record.id)"
              >
                <Button size="small" danger>解绑</Button>
              </Popconfirm>
            </template>
          </template>
        </Table>

        <div v-if="!loading && datasets.length === 0" class="empty-hint">
          暂无绑定的数据集，请在上方输入数据集 ID 进行绑定。
        </div>
      </Card>
    </div>
  </Page>
</template>

<style scoped lang="less">
.site-datasets-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.site-summary {
  margin-bottom: 20px;
  padding: 12px 16px;
  background: #f7fbf7;
  border-radius: 8px;
  border: 1px solid #e8edea;
}

.site-name {
  font-size: 16px;
  font-weight: 600;
  color: #183128;
}

.site-title {
  color: #5c6e67;
  font-size: 14px;
}

.bind-section {
  margin-bottom: 20px;
  padding: 12px 0;
}

.empty-hint {
  margin-top: 24px;
  text-align: center;
  color: #a0b0a8;
  font-size: 14px;
}
</style>
