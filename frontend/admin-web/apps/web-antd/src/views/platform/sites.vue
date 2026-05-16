<script setup lang="ts">
import type { SiteItem } from '#/api/platform/sites';

import { onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Space,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  createSiteApi,
  deleteSiteApi,
  listSitesApi,
  updateSiteApi,
} from '#/api/platform/sites';

defineOptions({ name: 'PlatformSitesPage' });

const sites = ref<SiteItem[]>([]);
const loading = ref(false);
const modalVisible = ref(false);
const modalSubmitting = ref(false);
const editingSite = ref<SiteItem | null>(null);
const formRef = ref();

const formState = ref<Partial<SiteItem>>({
  site_code: '',
  site_name: '',
  site_title: '',
  domain: '',
  test_port: '',
  logo_text: '',
  contact_email: '',
  footer_copyright: '',
});

const isEditing = ref(false);

const columns = [
  { title: '站点代码', dataIndex: 'site_code', key: 'site_code' },
  { title: '站点名称', dataIndex: 'site_name', key: 'site_name' },
  { title: '域名', dataIndex: 'domain', key: 'domain' },
  { title: '测试端口', dataIndex: 'test_port', key: 'test_port', width: 100 },
  {
    title: '绑定数据集',
    dataIndex: 'dataset_count',
    key: 'dataset_count',
    width: 100,
  },
  {
    title: '操作',
    key: 'action',
    width: 320,
  },
];

async function loadSites() {
  loading.value = true;
  try {
    const res = await listSitesApi();
    sites.value = res.items ?? [];
  } catch {
    // handled by request interceptor
  } finally {
    loading.value = false;
  }
}

function openCreateModal() {
  isEditing.value = false;
  editingSite.value = null;
  formState.value = {
    site_code: '',
    site_name: '',
    site_title: '',
    domain: '',
    test_port: '',
    logo_text: '',
    contact_email: '',
    footer_copyright: '',
  };
  modalVisible.value = true;
}

function openEditModal(record: SiteItem) {
  isEditing.value = true;
  editingSite.value = record;
  formState.value = { ...record };
  modalVisible.value = true;
}

async function handleSubmit() {
  modalSubmitting.value = true;
  try {
    if (isEditing.value && editingSite.value) {
      await updateSiteApi(editingSite.value.site_code, formState.value);
      message.success('站点更新成功');
    } else {
      await createSiteApi(formState.value);
      message.success('站点创建成功');
    }
    modalVisible.value = false;
    await loadSites();
  } catch {
    // handled by request interceptor
  } finally {
    modalSubmitting.value = false;
  }
}

async function handleDelete(siteCode: string) {
  try {
    await deleteSiteApi(siteCode);
    message.success('站点已删除');
    await loadSites();
  } catch {
    // handled by request interceptor
  }
}

function handleManageDatasets(record: SiteItem) {
  window.open(`/platform/sites/${record.site_code}/datasets`, '_self');
}

function handleCancel() {
  modalVisible.value = false;
}

onMounted(() => {
  loadSites();
});
</script>

<template>
  <Page auto-content-height content-class="p-5">
    <Card :bordered="false" title="站点管理">
      <template #extra>
        <Button type="primary" @click="openCreateModal">新建站点</Button>
      </template>

      <Table
        :columns="columns"
        :data-source="sites"
        :loading="loading"
        :pagination="false"
        row-key="site_code"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'dataset_count'">
            <Tag :color="record.dataset_count ? 'blue' : 'default'">
              {{ record.dataset_count ?? 0 }}
            </Tag>
          </template>
          <template v-if="column.key === 'action'">
            <Space>
              <Button size="small" @click="openEditModal(record)">编辑</Button>
              <Button
                size="small"
                @click="handleManageDatasets(record)"
              >
                管理数据集
              </Button>
              <Popconfirm
                title="确定删除该站点吗？"
                @confirm="handleDelete(record.site_code)"
              >
                <Button size="small" danger>删除</Button>
              </Popconfirm>
            </Space>
          </template>
        </template>
      </Table>

      <Modal
        v-model:open="modalVisible"
        :title="isEditing ? '编辑站点' : '新建站点'"
        :confirm-loading="modalSubmitting"
        @ok="handleSubmit"
        @cancel="handleCancel"
      >
        <Form
          ref="formRef"
          :model="formState"
          layout="vertical"
          class="site-form"
        >
          <Form.Item label="站点代码" required>
            <Input
              v-model:value="formState.site_code"
              :disabled="isEditing"
              placeholder="唯一标识，如 default"
            />
          </Form.Item>
          <Form.Item label="站点名称" required>
            <Input
              v-model:value="formState.site_name"
              placeholder="项目内部名称"
            />
          </Form.Item>
          <Form.Item label="站点标题">
            <Input
              v-model:value="formState.site_title"
              placeholder="页面标题，显示在浏览器标签页"
            />
          </Form.Item>
          <Form.Item label="域名">
            <Input
              v-model:value="formState.domain"
              placeholder="如 example.com"
            />
          </Form.Item>
          <Form.Item label="测试端口">
            <Input
              v-model:value="formState.test_port"
              placeholder="如 5677"
            />
          </Form.Item>
          <Form.Item label="Logo 文字">
            <Input
              v-model:value="formState.logo_text"
              placeholder="导航栏 Logo 旁文字"
            />
          </Form.Item>
          <Form.Item label="联系邮箱">
            <Input
              v-model:value="formState.contact_email"
              placeholder="admin@example.com"
            />
          </Form.Item>
          <Form.Item label="页脚版权">
            <Input
              v-model:value="formState.footer_copyright"
              placeholder="如 © 2024 FAN-CE"
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  </Page>
</template>

<style scoped lang="less">
.site-form {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 8px;
}
</style>
