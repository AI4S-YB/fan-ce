<template>
  <Page>
    <div style="padding: 24px;">
      <h2>工具插件管理</h2>

      <a-card title="安装插件" size="small" style="margin-bottom: 16px;">
        <a-upload-dragger
          name="file"
          :multiple="false"
          accept=".whl"
          :before-upload="beforeInstall"
          :show-upload-list="false"
        >
          <p style="font-size: 36px; margin: 8px 0;">📦</p>
          <p>点击或拖放 .whl 文件到此区域安装</p>
          <p style="color: #bbb; font-size: 12px;">安装后默认为禁用状态，需手动启用</p>
        </a-upload-dragger>
        <a-space style="margin-top: 12px;">
          <a-button @click="scanDirectory" :loading="scanning">扫描 plugin/ 目录</a-button>
        </a-space>
      </a-card>

      <a-table :columns="columns" :data-source="tools" :loading="loading" row-key="tool_id" size="small" bordered
        :pagination="false">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'tool_id'">
            <strong>{{ record.display_name }}</strong>
            <br /><span style="font-size: 11px; color: #999;">{{ record.tool_id }}</span>
          </template>
          <template v-else-if="column.key === 'category'">
            <a-tag>{{ record.category }}</a-tag>
          </template>
          <template v-else-if="column.key === 'version'">v{{ record.version }}</template>
          <template v-else-if="column.key === 'status'">
            <a-tag :color="record.status === 'active' ? 'green' : record.status === 'inactive' ? 'orange' : 'default'">
              {{ record.status === 'active' ? '已启用' : record.status === 'inactive' ? '待启用' : '已禁用' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'deps'">
            <span v-if="record.dependencies?.conda?.length" style="font-size: 12px;">
              {{ record.dependencies.conda.slice(0, 2).join(', ') }}
            </span>
            <span v-else style="color: #ccc;">-</span>
          </template>
          <template v-else-if="column.key === 'class'">
            <code style="font-size: 10px; color: #888;">{{ record.plugin_class?.split('.').slice(-1)[0] }}</code>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button size="small" @click="showDetail(record)">详情</a-button>
              <a-button v-if="record.status !== 'active'" size="small" type="primary"
                @click="enableTool(record.tool_id)">启用</a-button>
              <a-button v-if="record.status === 'active'" size="small"
                @click="disableTool(record.tool_id)">禁用</a-button>
              <a-popconfirm title="确定卸载此工具？" ok-text="确定" cancel-text="取消"
                @confirm="uninstallTool(record.tool_id)">
                <a-button size="small" danger>卸载</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>

      <a-divider />
      <p style="color: #888; margin: 0;">共 {{ tools.length }} 个工具</p>
    </div>

    <!-- Detail Drawer -->
    <a-drawer :open="drawerVisible" title="工具详情" width="640px" @close="drawerVisible = false">
      <template v-if="detail">
        <h3>{{ detail.display_name }}</h3>
        <a-descriptions :column="2" size="small" bordered>
          <a-descriptions-item label="Tool ID">{{ detail.tool_id }}</a-descriptions-item>
          <a-descriptions-item label="Version">v{{ detail.version }}</a-descriptions-item>
          <a-descriptions-item label="Category">{{ detail.category }}</a-descriptions-item>
          <a-descriptions-item label="Status">
            <a-tag :color="detail.status === 'active' ? 'green' : 'default'">{{ detail.status }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="Timeout">{{ detail.timeout_seconds }}s</a-descriptions-item>
          <a-descriptions-item label="Class"><code style="font-size: 11px;">{{ detail.plugin_class }}</code></a-descriptions-item>
        </a-descriptions>
        <h4 style="margin-top: 16px;">Inputs</h4>
        <a-table :columns="schemaCols.inp" :data-source="detail.input_schema" size="small" bordered :pagination="false" />
        <h4 style="margin-top: 16px;">Parameters</h4>
        <a-table :columns="schemaCols.par" :data-source="detail.parameter_schema" size="small" bordered :pagination="false" />
        <h4 style="margin-top: 16px;">Outputs</h4>
        <a-table :columns="schemaCols.out" :data-source="detail.output_schema" size="small" bordered :pagination="false" />
      </template>
    </a-drawer>
  </Page>
</template>

<script setup lang="ts">
import { ref, onMounted, message } from 'vue';
import { Page } from '@vben/common-ui';
import { requestClient } from '#/api/request';

const tools = ref<any[]>([]);
const loading = ref(false);
const scanning = ref(false);
const drawerVisible = ref(false);
const detail = ref<any>(null);

const columns = [
  { title: '工具名称', key: 'tool_id', width: 200 },
  { title: '分类', key: 'category', width: 90 },
  { title: '版本', key: 'version', width: 70 },
  { title: '状态', key: 'status', width: 80 },
  { title: '依赖', key: 'deps', width: 140 },
  { title: '类名', key: 'class', width: 130 },
  { title: '操作', key: 'action', width: 220 },
];

const schemaCols = {
  inp: [
    { title: 'Name', dataIndex: 'name', width: 120 },
    { title: 'Label', dataIndex: 'label', width: 120 },
    { title: 'Formats', dataIndex: 'accepted_formats', width: 100 },
    { title: 'Roles', dataIndex: 'accepted_file_roles', width: 130 },
    { title: 'Required', dataIndex: 'required', width: 70 },
  ],
  par: [
    { title: 'Name', dataIndex: 'name', width: 120 },
    { title: 'Label', dataIndex: 'label', width: 120 },
    { title: 'Type', dataIndex: 'type', width: 100 },
    { title: 'Default', dataIndex: 'default', width: 100 },
  ],
  out: [
    { title: 'Name', dataIndex: 'name', width: 120 },
    { title: 'Label', dataIndex: 'label', width: 120 },
    { title: 'Format', dataIndex: 'format', width: 100 },
  ],
};

async function loadTools() {
  loading.value = true;
  try {
    const resp: any = await requestClient.get('/analysis/admin/tools');
    tools.value = resp?.data || resp || [];
  } finally {
    loading.value = false;
  }
}

function showDetail(record: any) {
  detail.value = record;
  drawerVisible.value = true;
}

async function beforeInstall(file: File) {
  const form = new FormData();
  form.append('file', file);
  try {
    await requestClient.post('/analysis/admin/plugins/install', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    message.success(`插件 ${file.name} 安装成功`);
    loadTools();
  } catch (e: any) {
    message.error(`安装失败: ${e?.message || e}`);
  }
  return false; // prevent default upload
}

async function scanDirectory() {
  scanning.value = true;
  try {
    const resp: any = await requestClient.post('/analysis/admin/plugins/scan');
    const data = resp?.data || resp || {};
    const n = data.new_tools?.length || 0;
    message.success(`扫描完成，发现 ${n} 个新工具`);
    loadTools();
  } catch (e: any) {
    message.error(`扫描失败: ${e?.message || e}`);
  } finally {
    scanning.value = false;
  }
}

async function enableTool(id: string) {
  try {
    await requestClient.post(`/analysis/admin/tools/${id}/enable`);
    message.success(`${id} 已启用`);
    loadTools();
  } catch (e: any) { message.error(`启用失败`); }
}

async function disableTool(id: string) {
  try {
    await requestClient.post(`/analysis/admin/tools/${id}/disable`);
    message.success(`${id} 已禁用`);
    loadTools();
  } catch (e: any) { message.error(`禁用失败`); }
}

async function uninstallTool(id: string) {
  try {
    await requestClient.post(`/analysis/admin/tools/${id}/uninstall`);
    message.success(`${id} 已卸载`);
    loadTools();
  } catch (e: any) { message.error(`卸载失败`); }
}

onMounted(loadTools);
</script>
