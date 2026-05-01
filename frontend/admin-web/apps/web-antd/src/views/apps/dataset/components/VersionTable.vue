<script setup lang="ts">
import { Table, Tag, Space, Button, Empty } from 'ant-design-vue';
import type { DatasetVersionItem, DatasetVersionListResult } from '#/api/apps/dataset';
import { $t } from '@vben/locales';
import {
  lifecycleColor,
  releaseStateColor,
  visibilityColor,
} from '../composables/useDataset';

const props = defineProps<{
  versionData: DatasetVersionListResult | null;
  activeVersionId: number | null;
  actionLoadingKey: string;
}>();

const emit = defineEmits<{
  select: [version: DatasetVersionItem];
  activate: [version: DatasetVersionItem];
  release: [version: DatasetVersionItem];
  withdraw: [version: DatasetVersionItem];
  setDefault: [version: DatasetVersionItem];
  createVersion: [];
}>();

const columns = [
  { title: '', dataIndex: 'radio', key: 'radio', width: 40 },
  { title: $t('dataset.list.version'), dataIndex: 'version', key: 'version', width: 140 },
  { title: $t('system.menu.title'), dataIndex: 'title', key: 'title', width: 180 },
  { title: $t('dataset.list.lifecycleHeader'), dataIndex: 'lifecycle_state', key: 'lifecycle_state', width: 120 },
  { title: $t('platform.news.publish') + $t('dataset.list.status'), dataIndex: 'release_state', key: 'release_state', width: 120 },
  { title: $t('dataset.list.visibility'), dataIndex: 'visibility', key: 'visibility', width: 110 },
  { title: $t('dataset.staging.format'), dataIndex: 'file_format', key: 'file_format', width: 120 },
  { title: $t('dataset.list.action'), dataIndex: 'actions', key: 'actions' },
];

function isActive(version: DatasetVersionItem) {
  return version.id === props.activeVersionId;
}

function isActionLoading(prefix: string, id: number) {
  return props.actionLoadingKey === `${prefix}-${id}`;
}
</script>

<template>
  <div>
    <div style="margin-bottom: 12px;">
      <Button type="primary" ghost @click="emit('createVersion')">{{ $t('dataset.list.createVersion') }}</Button>
    </div>
    <Table
      :columns="columns"
      :data-source="versionData?.items || []"
      :pagination="false"
      :row-key="(r: DatasetVersionItem) => r.id"
      bordered
      size="small"
    >
      <template #emptyText>
        <Empty :description="$t('dataset.list.noVersion')" />
      </template>
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'radio'">
          <input
            type="radio"
            :checked="isActive(record as DatasetVersionItem)"
            @change="emit('select', record as DatasetVersionItem)"
          />
        </template>
        <template v-else-if="column.key === 'version'">
          {{ (record as DatasetVersionItem).version || '-' }}
        </template>
        <template v-else-if="column.key === 'lifecycle_state'">
          <Tag :color="lifecycleColor((record as DatasetVersionItem).lifecycle_state)">
            {{ (record as DatasetVersionItem).lifecycle_state || '-' }}
          </Tag>
        </template>
        <template v-else-if="column.key === 'release_state'">
          <Tag :color="releaseStateColor((record as DatasetVersionItem).release_state)">
            {{ (record as DatasetVersionItem).release_state || '-' }}
          </Tag>
        </template>
        <template v-else-if="column.key === 'visibility'">
          <Tag :color="visibilityColor((record as DatasetVersionItem).visibility)">
            {{ (record as DatasetVersionItem).visibility || '-' }}
          </Tag>
        </template>
        <template v-else-if="column.key === 'actions'">
          <Space size="small">
            <template v-if="(record as DatasetVersionItem).lifecycle_state !== 'ready' && (record as DatasetVersionItem).lifecycle_state !== 'public'">
              <Button
                type="link"
                size="small"
                :loading="isActionLoading('activate-version', (record as DatasetVersionItem).id)"
                @click="emit('activate', record as DatasetVersionItem)"
              >
                {{ $t('dataset.list.activateVersion') }}
              </Button>
            </template>
            <template v-if="(record as DatasetVersionItem).release_state !== 'released'">
              <Button
                type="link"
                size="small"
                :loading="isActionLoading('release-version', (record as DatasetVersionItem).id)"
                @click="emit('release', record as DatasetVersionItem)"
              >
                {{ $t('dataset.list.releaseVersion') }}
              </Button>
            </template>
            <template v-if="(record as DatasetVersionItem).release_state === 'released' && !(record as DatasetVersionItem).is_default_public">
              <Button
                type="link"
                size="small"
                :loading="isActionLoading('set-default-version', (record as DatasetVersionItem).id)"
                @click="emit('setDefault', record as DatasetVersionItem)"
              >
                {{ $t('dataset.list.setDefaultPublic') }}
              </Button>
            </template>
            <template v-if="(record as DatasetVersionItem).release_state === 'released'">
              <Button
                type="link"
                danger
                size="small"
                :loading="isActionLoading('withdraw-version', (record as DatasetVersionItem).id)"
                @click="emit('withdraw', record as DatasetVersionItem)"
              >
                {{ $t('dataset.list.withdrawVersion') }}
              </Button>
            </template>
          </Space>
        </template>
      </template>
    </Table>
  </div>
</template>
