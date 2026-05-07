<template>
  <Page>
    <div style="padding: 24px;">
      <h2>任务管理</h2>
      <p style="color: #888; margin-bottom: 16px;">管理所有分析任务的执行状态和结果。</p>

      <Space style="margin-bottom: 16px;">
        <Select v-model:value="filterStatus" style="width: 140px;" placeholder="筛选状态" @change="loadJobs" allow-clear>
          <SelectOption value="">全部</SelectOption>
          <SelectOption value="pending">pending</SelectOption>
          <SelectOption value="running">running</SelectOption>
          <SelectOption value="success">success</SelectOption>
          <SelectOption value="failed">failed</SelectOption>
          <SelectOption value="timeout">timeout</SelectOption>
        </Select>
        <a-button @click="loadJobs">刷新</a-button>
        <span v-if="hasRunning" style="color: #409eff; font-size: 12px;">自动刷新中...</span>
      </Space>

      <a-table :columns="columns" :data-source="jobs" :loading="loading" row-key="id" size="small" bordered
        :pagination="{ current: page, pageSize: size, total, showSizeChanger: true, onChange: onPageChange }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'tool_id'">
            <a-tag color="blue">{{ record.tool_id }}</a-tag>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag>
          </template>
          <template v-else-if="column.key === 'created_at'">
            {{ formatTime(record.created_at) }}
          </template>
          <template v-else-if="column.key === 'finished_at'">
            {{ record.finished_at ? formatTime(record.finished_at) : '-' }}
          </template>
          <template v-else-if="column.key === 'action'">
            <a-button size="small" @click="showDetail(record)">详情</a-button>
            <Popconfirm v-if="record.status === 'pending' || record.status === 'running'"
              title="确定取消？" @confirm="cancelJob(record.id)">
              <a-button size="small" danger>取消</a-button>
            </Popconfirm>
            <a-button v-if="record.status === 'failed' || record.status === 'timeout'"
              size="small" type="primary" @click="retryJob(record.id)">重试</a-button>
          </template>
        </template>
      </a-table>

      <!-- Detail Modal -->
      <Modal v-model:open="detailVisible" title="任务详情" width="700px" :footer="null">
        <template v-if="detail">
          <Descriptions :column="2" size="small" bordered>
            <Descriptions.Item label="Job ID">{{ detail.id }}</Descriptions.Item>
            <Descriptions.Item label="Tool">{{ detail.tool_id }}</Descriptions.Item>
            <Descriptions.Item label="Status">
              <a-tag :color="statusColor(detail.status)">{{ detail.status }}</a-tag>
            </Descriptions.Item>
            <Descriptions.Item label="Exit Code">{{ detail.exit_code ?? '-' }}</Descriptions.Item>
            <Descriptions.Item label="Created">{{ formatTime(detail.created_at) }}</Descriptions.Item>
            <Descriptions.Item label="Started">{{ detail.started_at ? formatTime(detail.started_at) : '-' }}</Descriptions.Item>
            <Descriptions.Item label="Finished">{{ detail.finished_at ? formatTime(detail.finished_at) : '-' }}</Descriptions.Item>
            <Descriptions.Item label="Error" :span="2" v-if="detail.error_message">
              <pre style="color: red; white-space: pre-wrap; margin: 0;">{{ detail.error_message }}</pre>
            </Descriptions.Item>
          </Descriptions>

          <h4 style="margin-top: 16px;" v-if="detail.output_files?.length">Output Files</h4>
          <a-table v-if="detail.output_files?.length" :columns="outputCols" :data-source="detail.output_files"
            size="small" bordered :pagination="false" />

          <h4 style="margin-top: 16px;" v-if="detail.command_log">Command</h4>
          <pre v-if="detail.command_log" style="background: #1e1e1e; color: #d4d4d4; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{{ detail.command_log }}</pre>
        </template>
      </Modal>
    </div>
  </Page>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { Page } from '@vben/common-ui';
import { requestClient } from '#/api/request';
import { message, Space, Select, Popconfirm, Tag, Descriptions, DescriptionsItem, Modal } from 'ant-design-vue';

interface JobItem {
  id: number; tool_id: string; status: string;
  created_at?: number; started_at?: number; finished_at?: number;
  exit_code?: number; error_message?: string;
  command_log?: string; output_files?: { name: string; path: string; size: number }[];
}

const jobs = ref<JobItem[]>([]);
const loading = ref(false);
const page = ref(1);
const size = ref(20);
const total = ref(0);
const detailVisible = ref(false);
const detail = ref<JobItem | null>(null);
const filterStatus = ref('');
const autoRefreshTimer = ref<ReturnType<typeof setInterval> | null>(null);

const hasRunning = computed(() => jobs.value.some(j => j.status === 'pending' || j.status === 'running'));

const columns = [
  { title: 'Job ID', key: 'id', dataIndex: 'id', width: 80 },
  { title: 'Tool', key: 'tool_id', width: 140 },
  { title: 'Status', key: 'status', width: 100 },
  { title: 'Created', key: 'created_at', width: 160 },
  { title: 'Finished', key: 'finished_at', width: 160 },
  { title: '', key: 'action', width: 160 },
];

const outputCols = [
  { title: 'Name', dataIndex: 'name', width: 180 },
  { title: 'Size', dataIndex: 'size', width: 100 },
  { title: 'Path', dataIndex: 'path' },
];

function statusColor(s: string) {
  return s === 'success' ? 'green' : s === 'failed' || s === 'timeout' ? 'red' : s === 'running' ? 'blue' : 'default';
}

function formatTime(ts?: number) {
  if (!ts) return '-';
  return new Date(ts * 1000).toLocaleString();
}

async function loadJobs() {
  loading.value = true;
  try {
    const params: any = { page: page.value, size: size.value };
    if (filterStatus.value) params.status = filterStatus.value;
    const resp: any = await requestClient.get('/analysis/jobs', { params });
    const data = resp?.data || resp || {};
    jobs.value = data.items || [];
    total.value = data.total || 0;
  } finally {
    loading.value = false;
  }
}

async function retryJob(id: number) {
  try {
    await requestClient.post(`/analysis/jobs/${id}/retry`);
    message.success('已重新提交');
    loadJobs();
  } catch (e: any) { message.error('重试失败'); }
}

function startAutoRefresh() {
  if (autoRefreshTimer.value) return;
  autoRefreshTimer.value = setInterval(() => {
    if (hasRunning.value) loadJobs();
  }, 3000);
}

async function showDetail(record: JobItem) {
  try {
    const resp: any = await requestClient.get(`/analysis/jobs/${record.id}`);
    detail.value = resp?.data || resp;
    detailVisible.value = true;
  } catch (e: any) {
    message.error('Failed to load detail');
  }
}

async function cancelJob(id: number) {
  try {
    await requestClient.post(`/analysis/jobs/${id}/cancel`);
    message.success('Task cancelled');
    loadJobs();
  } catch (e: any) {
    message.error('Failed to cancel');
  }
}

function onPageChange(p: number, ps: number) {
  page.value = p;
  size.value = ps;
  loadJobs();
}

onMounted(() => {
  loadJobs();
  startAutoRefresh();
});

onUnmounted(() => {
  if (autoRefreshTimer.value) clearInterval(autoRefreshTimer.value);
});
</script>
