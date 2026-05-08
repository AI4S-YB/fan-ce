<template>
  <Page>
    <div style="padding:24px;">
      <h2>BLAST Databases</h2>
      <p style="color:#888;margin-bottom:16px;">
        Select FASTA files from registered datasets to build BLAST indexes.
      </p>

      <Space style="margin-bottom:16px;">
        <Button type="primary" @click="loadDatabases">Refresh</Button>
        <span style="color:#888;font-size:12px;">
          {{ indexedCount }} / {{ databases.length }} indexed
        </span>
      </Space>

      <Table
        :columns="columns"
        :data-source="databases"
        :loading="loading"
        row-key="id"
        size="small"
        bordered
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'type'">
            <Tag :color="record.type === 'prot' ? 'green' : 'blue'">{{ record.type }}</Tag>
          </template>
          <template v-else-if="column.key === 'indexed'">
            <Tag :color="record.indexed ? 'green' : 'default'">
              {{ record.indexed ? 'Indexed' : 'Not Indexed' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'size'">
            {{ record.size ? (record.size / 1024 / 1024).toFixed(0) + ' MB' : '-' }}
          </template>
          <template v-else-if="column.key === 'action'">
            <Popconfirm
              v-if="!record.indexed"
              title="Build BLAST index for this file?"
              @confirm="createIndex(record.id)"
            >
              <Button size="small" type="primary" :loading="indexingId === record.id">
                Build Index
              </Button>
            </Popconfirm>
            <Popconfirm
              v-else
              title="Delete BLAST index?"
              @confirm="deleteIndex(record.id)"
            >
              <Button size="small" danger>Delete Index</Button>
            </Popconfirm>
          </template>
        </template>
      </Table>
    </div>
  </Page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { Page } from '@vben/common-ui';
import { requestClient } from '#/api/request';
import { message, Space, Table, Button, Tag, Popconfirm } from 'ant-design-vue';

interface BlastDatabase {
  id: number;
  name: string;
  path: string;
  format: string;
  type: string;
  size: number;
  dataset: string;
  dataset_code: string;
  lifecycle: string;
  visibility: string;
  indexed: boolean;
}

const databases = ref<BlastDatabase[]>([]);
const loading = ref(false);
const indexingId = ref<number | null>(null);

const indexedCount = computed(() => databases.value.filter(d => d.indexed).length);

const columns = [
  { title: 'Dataset', dataIndex: 'dataset', key: 'dataset', width: 260 },
  { title: 'File', dataIndex: 'name', key: 'name', width: 200 },
  { title: 'Type', key: 'type', width: 80 },
  { title: 'Format', dataIndex: 'format', key: 'format', width: 80 },
  { title: 'Size', key: 'size', width: 80 },
  { title: 'Visibility', dataIndex: 'visibility', key: 'visibility', width: 80 },
  { title: 'Status', key: 'indexed', width: 110 },
  { title: '', key: 'action', width: 140 },
];

async function loadDatabases() {
  loading.value = true;
  try {
    const resp: any = await requestClient.get('/analysis/admin/blast/databases');
    databases.value = (resp?.data || resp)?.databases || [];
  } finally {
    loading.value = false;
  }
}

async function createIndex(id: number) {
  indexingId.value = id;
  try {
    await requestClient.post(`/analysis/admin/blast/databases/${id}/index`);
    message.success('BLAST index created');
    loadDatabases();
  } catch (e: any) {
    message.error(e?.message || 'Index creation failed');
  } finally {
    indexingId.value = null;
  }
}

async function deleteIndex(id: number) {
  try {
    await requestClient.delete(`/analysis/admin/blast/databases/${id}/index`);
    message.success('BLAST index deleted');
    loadDatabases();
  } catch (e: any) {
    message.error(e?.message || 'Index deletion failed');
  }
}

onMounted(loadDatabases);
</script>
