<script setup lang="ts">
import { Table, Tag, Space, Button, Empty } from 'ant-design-vue';
import type { DatasetVersionItem, DatasetVersionListResult } from '#/api/apps/dataset';
import { $t } from '@vben/locales';
import {
  lifecycleColor,
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
  createVersion: [];
}>();

const columns = [
  { title: '', dataIndex: 'radio', key: 'radio', width: 40 },
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: $t('dataset.list.version'), dataIndex: 'version', key: 'version', width: 120 },
  { title: $t('system.menu.title'), dataIndex: 'title', key: 'title', width: 180 },
  { title: $t('dataset.list.lifecycleHeader'), dataIndex: 'lifecycle_state', key: 'lifecycle_state', width: 120 },
  { title: $t('dataset.list.visibility'), dataIndex: 'visibility', key: 'visibility', width: 110 },
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
        <template v-else-if="column.key === 'visibility'">
          <Tag :color="visibilityColor((record as DatasetVersionItem).visibility)">
            {{ (record as DatasetVersionItem).visibility || '-' }}
          </Tag>
        </template>
        <template v-else-if="column.key === 'actions'">
          <Space size="small">
            <template v-if="!(record as DatasetVersionItem).is_current">
              <Button
                type="link"
                size="small"
                :loading="isActionLoading('activate-version', (record as DatasetVersionItem).id)"
                @click="emit('activate', record as DatasetVersionItem)"
              >
                {{ $t('dataset.list.setAsMainVersion') || '设为主版本' }}
              </Button>
            </template>
            <template v-if="(record as DatasetVersionItem).visibility !== 'public'">
              <Button
                type="link"
                size="small"
                :loading="isActionLoading('release-version', (record as DatasetVersionItem).id)"
                @click="emit('release', record as DatasetVersionItem)"
              >
                {{ $t('dataset.list.releaseVersion') }} (公开)
              </Button>
            </template>
            <template v-if="(record as DatasetVersionItem).visibility === 'public'">
              <Button
                type="link"
                danger
                size="small"
                :loading="isActionLoading('withdraw-version', (record as DatasetVersionItem).id)"
                @click="emit('withdraw', record as DatasetVersionItem)"
              >
                {{ $t('dataset.list.withdrawVersion') }} (私有)
              </Button>
            </template>
          </Space>
        </template>
      </template>
    </Table>
  </div>
</template>
