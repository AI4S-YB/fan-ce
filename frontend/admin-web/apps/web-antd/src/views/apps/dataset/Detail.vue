<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Button, Tag, Space, Modal, message } from 'ant-design-vue';
import { Page } from '@vben/common-ui';
import { deleteDatasetApi } from '#/api/apps/dataset';
import VersionTable from './components/VersionTable.vue';
import AssetPanel from './components/AssetPanel.vue';
import LineagePanel from './components/LineagePanel.vue';
import { $t } from '@vben/locales';
import {
  useDataset,
  lifecycleColor,
  visibilityColor,
  getPreferredDatasetTypeCode,
  type DatasetVersionItem,
} from './composables/useDataset';

const route = useRoute();
const router = useRouter();

const {
  detailLoading, detailData, loadDetail,
  versionListLoading, versionListData, loadVersionList,
  versionDetailLoading, versionDetailData, loadVersionDetail,
  activateVersion, releaseVersion, withdrawVersion, setDefaultPublicVersion,
  loadPublishRecords, publishRecords,
} = useDataset();

const datasetId = computed(() => Number(route.params.id));
const activeVersionId = ref<number | null>(null);
const actionLoadingKey = ref('');

// Load data
async function loadAll() {
  await Promise.all([
    loadDetail(datasetId.value),
    loadVersionList(datasetId.value),
  ]);
  // Default to current version
  if (versionListData.value?.current_version?.id) {
    activeVersionId.value = versionListData.value.current_version.id;
    await selectVersion(activeVersionId.value);
  }
}

async function selectVersion(versionId: number) {
  activeVersionId.value = versionId;
  await Promise.all([
    loadVersionDetail(versionId),
    loadPublishRecords(versionId),
  ]);
}

async function handleSelectVersion(version: DatasetVersionItem) {
  await selectVersion(version.id);
}

async function handleActivate(version: DatasetVersionItem) {
  actionLoadingKey.value = `activate-version-${version.id}`;
  try {
    await activateVersion(version.id);
    message.success($t('dataset.list.versionActivated'));
    await loadAll();
  } finally {
    actionLoadingKey.value = '';
  }
}

async function handleRelease(version: DatasetVersionItem) {
  actionLoadingKey.value = `release-version-${version.id}`;
  try {
    await releaseVersion(version.id);
    message.success($t('dataset.list.versionPublished'));
    await loadAll();
  } finally {
    actionLoadingKey.value = '';
  }
}

async function handleWithdraw(version: DatasetVersionItem) {
  actionLoadingKey.value = `withdraw-version-${version.id}`;
  try {
    await withdrawVersion(version.id);
    message.success($t('dataset.list.versionRevoked'));
    await loadAll();
  } finally {
    actionLoadingKey.value = '';
  }
}

async function handleSetDefault(version: DatasetVersionItem) {
  actionLoadingKey.value = `set-default-version-${version.id}`;
  try {
    await setDefaultPublicVersion(version.id);
    message.success($t('dataset.list.versionSetDefault'));
    await loadAll();
  } finally {
    actionLoadingKey.value = '';
  }
}

function handleDelete() {
  Modal.confirm({
    title: $t('dataset.list.delete') + ' Dataset',
    content: $t('dataset.list.deleteConfirmParam2', { name: detailData.value?.title || detailData.value?.dataset_code || String(datasetId.value) }),
    async onOk() {
      await deleteDatasetApi({ id: datasetId.value });
      message.success($t('dataset.list.datasetDeleted'));
      router.push('/dataset');
    },
  });
}

const versionMismatch = computed(() =>
  versionListData.value?.current_version?.id &&
  versionListData.value?.default_public_version?.id &&
  versionListData.value.current_version.id !== versionListData.value.default_public_version.id,
);

onMounted(() => loadAll());
</script>

<template>
  <Page auto-content-height>
    <div v-if="detailLoading" style="text-align: center; padding: 80px;">{{ $t('dataset.list.loading') }}</div>
    <template v-else-if="detailData">
      <!-- Section 1: Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
        <div>
          <h2 style="margin: 0;">{{ detailData.dataset_code || '-' }}</h2>
          <div style="color: #888; font-size: 13px;">
            <span>{{ detailData.organism || '-' }} · {{ detailData.assembly || '-' }}</span>
            <span style="margin-left: 8px;">{{ getPreferredDatasetTypeCode(detailData.dataset_type) }}</span>
            <span style="margin-left: 8px;">{{ detailData.query_profile?.file_format || detailData.file_format || '-' }}</span>
          </div>
        </div>
        <Space>
          <Tag :color="lifecycleColor(detailData.lifecycle_state)">{{ detailData.lifecycle_state || '-' }}</Tag>
          <Tag :color="visibilityColor(detailData.visibility)">{{ detailData.visibility || '-' }}</Tag>
          <Button type="primary" ghost @click="router.push(`/dataset/${datasetId}/query`)">{{ $t('dataset.list.dataQuery') }}</Button>
          <Button danger @click="handleDelete">{{ $t('dataset.list.delete') }}</Button>
        </Space>
      </div>

      <!-- Section 2: Status Bar -->
      <div style="display: flex; gap: 24px; font-size: 13px; padding: 8px 12px; background: #fafafa; border-radius: 4px; margin-bottom: 16px;">
        <span>{{ $t('dataset.list.queryEntry') }}<strong>{{ detailData.query_entry_asset?.asset_code || $t('dataset.list.notConfigured') }}</strong></span>
        <span>{{ $t('dataset.list.currentVersion') }}：<strong>{{ versionListData?.current_version?.version || '-' }}</strong></span>
        <span>{{ $t('dataset.list.defaultPublicVersion') }}：<strong>{{ versionListData?.default_public_version?.version || '-' }}</strong></span>
      </div>

      <div v-if="versionMismatch" style="background: #fffbe6; border: 1px solid #ffe58f; padding: 6px 12px; border-radius: 4px; margin-bottom: 12px; font-size: 12px;">
        {{ $t('dataset.list.versionMismatch', { version: versionListData?.default_public_version?.version }) }}
      </div>

      <!-- Section 3: Version Table -->
      <div style="margin-bottom: 20px;">
        <h3>{{ $t('dataset.list.versionManage') }}</h3>
        <VersionTable
          :version-data="versionListData"
          :active-version-id="activeVersionId"
          :action-loading-key="actionLoadingKey"
          @select="handleSelectVersion"
          @activate="handleActivate"
          @release="handleRelease"
          @withdraw="handleWithdraw"
          @set-default="handleSetDefault"
          @create-version="() => {}"
        />
      </div>

      <!-- Section 4 & 5: Assets & Lineage (side-by-side) -->
      <div v-if="activeVersionId" style="display: flex; gap: 16px;">
        <div style="flex: 1;">
          <h3>{{ $t('dataset.list.asset') }}</h3>
          <AssetPanel
            :version-detail="versionDetailData"
            :loading="versionDetailLoading"
            @refresh="selectVersion(activeVersionId!)"
          />
        </div>
        <div style="flex: 1;">
          <h3>{{ $t('dataset.list.lineage') }}</h3>
          <LineagePanel
            :version-detail="versionDetailData"
            :version-id="activeVersionId"
            :loading="versionDetailLoading"
            @refresh="selectVersion(activeVersionId!)"
          />
        </div>
      </div>

      <!-- Section 6: Publish History (collapsed) -->
      <details style="margin-top: 20px; font-size: 12px; color: #888;">
        <summary>{{ $t('dataset.list.publishHistory', { count: publishRecords.length }) }}</summary>
        <table style="width: 100%; border-collapse: collapse; margin-top: 8px;">
          <thead>
          <tr style="background: #f5f5f5;">
            <th style="padding: 4px 8px; text-align: left; border: 1px solid #e0e0e0;">{{ $t('dataset.list.time') }}</th>
            <th style="padding: 4px 8px; text-align: left; border: 1px solid #e0e0e0;">{{ $t('dataset.list.action2') }}</th>
            <th style="padding: 4px 8px; text-align: left; border: 1px solid #e0e0e0;">{{ $t('dataset.list.visibility') }}</th>
            <th style="padding: 4px 8px; text-align: left; border: 1px solid #e0e0e0;">{{ $t('dataset.list.lifecycleHeader') }}</th>
            <th style="padding: 4px 8px; text-align: left; border: 1px solid #e0e0e0;">{{ $t('dataset.list.remark2') }}</th>
          </tr>
          </thead>
          <tbody>
          <tr v-for="r in publishRecords" :key="r.id">
            <td style="padding: 3px 6px; border: 1px solid #e0e0e0;">{{ r.create_time ? new Date(r.create_time * 1000).toLocaleString('zh-CN') : '-' }}</td>
            <td style="padding: 3px 6px; border: 1px solid #e0e0e0;">{{ r.action || '-' }}</td>
            <td style="padding: 3px 6px; border: 1px solid #e0e0e0;">{{ r.visibility_before || '-' }} → {{ r.visibility_after || '-' }}</td>
            <td style="padding: 3px 6px; border: 1px solid #e0e0e0;">{{ r.lifecycle_before || '-' }} → {{ r.lifecycle_after || '-' }}</td>
            <td style="padding: 3px 6px; border: 1px solid #e0e0e0;">{{ r.note || '-' }}</td>
          </tr>
          </tbody>
        </table>
      </details>

      <!-- Section 7: System Info (collapsed) -->
      <details style="margin-top: 12px; font-size: 12px; color: #888;">
        <summary>{{ $t('dataset.list.systemInfo') }}</summary>
        <div style="display: flex; gap: 24px; margin-top: 8px;">
          <span>ID: {{ detailData.id }}</span>
          <span>Code: {{ detailData.dataset_code }}</span>
          <span>创建: {{ detailData.create_time ? new Date(detailData.create_time * 1000).toLocaleString('zh-CN') : '-' }}</span>
          <span>更新: {{ detailData.update_time ? new Date(detailData.update_time * 1000).toLocaleString('zh-CN') : '-' }}</span>
        </div>
      </details>
    </template>
    <div v-else style="text-align: center; padding: 80px; color: #888;">{{ $t('dataset.list.noDetail') }}</div>
  </Page>
</template>
