<script setup lang="ts">
import type {
  PlatformModelApiPayload,
  PlatformModelApiSetting,
  PlatformSiteSetting,
} from '#/api/platform/setting';

import { onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Alert,
  AutoComplete,
  Button,
  Card,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  createPlatformModelApiApi,
  deletePlatformModelApiApi,
  getPlatformModelApiListApi,
  getPlatformSiteSettingApi,
  setPrimaryPlatformModelApiApi,
  testPlatformModelApi,
  updatePlatformModelApiApi,
  updatePlatformSiteSettingApi,
} from '#/api/platform/setting';
import FrpTunnelCard from './components/FrpTunnelCard.vue';
import { useMessage } from '#/hooks/web/useMessage';
import { $t } from '@vben/locales';

defineOptions({ name: 'PlatformSettingPage' });

const { createMessage } = useMessage();
const router = useRouter();

const pageLoading = ref(false);
const siteSaving = ref(false);
const modelLoading = ref(false);
const modelModalVisible = ref(false);
const modelModalSaving = ref(false);
const modelTesting = ref(false);
const modelTestResult = ref('');
const modelTestOk = ref(false);
const modelEditId = ref<null | number>(null);
const modelRows = ref<PlatformModelApiSetting[]>([]);

const siteForm = reactive<PlatformSiteSetting>({
  site_name: '',
  site_title: '',
  filing_no: '',
  domain: '',
  ip_address: '',
  port: 0,
  extra_json: '{}',
});

const modelForm = reactive<PlatformModelApiPayload>({
  provider_code: '',
  provider_name: '',
  model_name: '',
  api_base_url: '',
  api_key: '',
  is_primary: false,
  is_active: true,
  sort_order: 0,
  remark: '',
  extra_json: '{}',
});

const providerOptions = [
  { label: $t('platform.setting.providers_qwen'), value: 'qwen' },
  { label: $t('platform.setting.providers_glm'), value: 'glm' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'Moonshot / Kimi', value: 'kimi' },
  { label: $t('platform.setting.providers_wenxin'), value: 'baidu' },
  { label: $t('platform.setting.providers_doubao'), value: 'doubao' },
  { label: 'OpenAI', value: 'openai' },
  { label: $t('platform.setting.providers_custom'), value: 'custom' },
];

interface ProviderPreset {
  provider_name: string;
  api_base_url: string;
  models: string[];
}

const providerPresets: Record<string, ProviderPreset> = {
  qwen: {
    provider_name: $t('platform.setting.providers_qwen'),
    api_base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: ['qwen-max', 'qwen-plus', 'qwen-turbo', 'qwen3-max', 'qwen3-235b-a22b'],
  },
  glm: {
    provider_name: $t('platform.setting.providers_glm'),
    api_base_url: 'https://open.bigmodel.cn/api/paas/v4',
    models: ['glm-4-plus', 'glm-4-flash', 'glm-4-air', 'glm-4-long'],
  },
  deepseek: {
    provider_name: 'DeepSeek',
    api_base_url: 'https://api.deepseek.com/v1',
    models: ['deepseek-chat', 'deepseek-reasoner'],
  },
  kimi: {
    provider_name: 'Moonshot / Kimi',
    api_base_url: 'https://api.moonshot.cn/v1',
    models: ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'],
  },
  baidu: {
    provider_name: $t('platform.setting.providers_wenxin'),
    api_base_url: 'https://qianfan.baidubce.com/v2',
    models: ['ernie-4.0-8k', 'ernie-3.5-8k', 'ernie-speed-8k'],
  },
  doubao: {
    provider_name: $t('platform.setting.providers_doubao'),
    api_base_url: 'https://ark.cn-beijing.volces.com/api/v3',
    models: ['doubao-pro-32k', 'doubao-lite-32k'],
  },
  openai: {
    provider_name: 'OpenAI',
    api_base_url: 'https://api.openai.com/v1',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
  },
};

const providerNameMap = new Map(
  providerOptions.map((item) => [item.value, item.label]),
);

const modelOptions = ref<string[]>([]);

const modelColumns = [
  {
    title: $t('platform.setting.platform'),
    dataIndex: 'provider_name',
    key: 'provider_name',
  },
  {
    title: $t('platform.setting.model'),
    dataIndex: 'model_name',
    key: 'model_name',
  },
  {
    title: $t('platform.setting.apiAddress'),
    dataIndex: 'api_base_url',
    key: 'api_base_url',
    ellipsis: true,
  },
  {
    title: $t('platform.setting.apiKeyMasked'),
    dataIndex: 'api_key_masked',
    key: 'api_key_masked',
  },
  {
    title: $t('platform.setting.status'),
    dataIndex: 'is_active',
    key: 'is_active',
  },
  {
    title: $t('platform.setting.primaryModel'),
    dataIndex: 'is_primary',
    key: 'is_primary',
  },
  {
    title: $t('platform.setting.remark'),
    dataIndex: 'remark',
    key: 'remark',
    ellipsis: true,
  },
  {
    title: $t('platform.setting.action'),
    key: 'action',
    width: 260,
  },
];

function resetModelForm() {
  modelEditId.value = null;
  modelForm.provider_code = '';
  modelForm.provider_name = '';
  modelForm.model_name = '';
  modelForm.api_base_url = '';
  modelForm.api_key = '';
  modelForm.is_primary = false;
  modelForm.is_active = true;
  modelForm.sort_order = 0;
  modelForm.remark = '';
  modelForm.extra_json = '{}';
  modelOptions.value = [];
  modelTestResult.value = '';
  modelTestOk.value = false;
}

async function loadSiteSetting() {
  const data = await getPlatformSiteSettingApi();
  siteForm.id = data.id;
  siteForm.site_name = data.site_name || '';
  siteForm.site_title = data.site_title || '';
  siteForm.filing_no = data.filing_no || '';
  siteForm.domain = data.domain || '';
  siteForm.ip_address = data.ip_address || '';
  siteForm.port = Number(data.port || 0);
  siteForm.extra_json = data.extra_json || '{}';
}

async function loadModelApis() {
  modelLoading.value = true;
  try {
    const data = await getPlatformModelApiListApi();
    modelRows.value = data.items || [];
  } finally {
    modelLoading.value = false;
  }
}

async function initializePage() {
  pageLoading.value = true;
  try {
    await Promise.all([loadSiteSetting(), loadModelApis()]);
  } finally {
    pageLoading.value = false;
  }
}

async function handleSaveSite() {
  siteSaving.value = true;
  try {
    await updatePlatformSiteSettingApi(siteForm);
    createMessage.success($t('platform.setting.siteConfigSaved'));
    await loadSiteSetting();
  } finally {
    siteSaving.value = false;
  }
}

function openCreateModelModal() {
  resetModelForm();
  modelModalVisible.value = true;
}

function openEditModelModal(record: PlatformModelApiSetting) {
  modelEditId.value = record.id;
  modelForm.provider_code = record.provider_code || '';
  modelForm.provider_name = record.provider_name || '';
  modelForm.model_name = record.model_name || '';
  modelForm.api_base_url = record.api_base_url || '';
  modelForm.api_key = record.api_key || '';
  modelForm.is_primary = Boolean(record.is_primary);
  modelForm.is_active = Boolean(record.is_active);
  modelForm.sort_order = Number(record.sort_order || 0);
  modelForm.remark = record.remark || '';
  modelForm.extra_json = record.extra_json || '{}';
  const preset = providerPresets[record.provider_code];
  modelOptions.value = preset ? [...preset.models] : [];
  modelModalVisible.value = true;
}

async function handleSaveModel() {
  if (
    !modelForm.provider_code ||
    !modelForm.model_name ||
    !modelForm.api_base_url ||
    !modelForm.api_key
  ) {
    createMessage.warning($t('platform.setting.fillAllFields'));
    return;
  }
  if (!modelForm.provider_name) {
    modelForm.provider_name =
      providerNameMap.get(modelForm.provider_code) || modelForm.provider_code;
  }
  modelModalSaving.value = true;
  try {
    if (modelEditId.value) {
      await updatePlatformModelApiApi({
        id: modelEditId.value,
        ...modelForm,
      });
      createMessage.success($t('platform.setting.modelUpdated'));
    } else {
      await createPlatformModelApiApi(modelForm);
      createMessage.success($t('platform.setting.modelAdded'));
    }
    modelModalVisible.value = false;
    await loadModelApis();
  } finally {
    modelModalSaving.value = false;
  }
}

async function handleTestModel() {
  if (!modelForm.api_base_url || !modelForm.model_name || !modelForm.api_key) {
    createMessage.warning($t('platform.setting.fillRequired'));
    return;
  }
  modelTesting.value = true;
  modelTestResult.value = '';
  modelTestOk.value = false;
  try {
    const result = await testPlatformModelApi({
      model_name: modelForm.model_name,
      api_base_url: modelForm.api_base_url,
      api_key: modelForm.api_key,
    });
    if (result.ok) {
      const msg = $t('platform.setting.testSuccessDetail', { model: result.model || '-', preview: result.reply_preview || $t('platform.setting.testSuccessEmpty') });
      modelTestResult.value = msg;
      modelTestOk.value = true;
      createMessage.success($t('platform.setting.testSuccess'));
    } else {
      modelTestResult.value = $t('platform.setting.testFailedDetail', { code: result.status_code, error: result.error || $t('platform.setting.unknownError') });
      createMessage.error($t('platform.setting.testFailed'));
    }
  } catch (error: any) {
    modelTestResult.value = $t('platform.setting.testErrorDetail', { error: error?.message || $t('platform.setting.unknownError') });
    createMessage.error($t('platform.setting.testError'));
  } finally {
    modelTesting.value = false;
  }
}

async function handleDeleteModel(id: number) {
  await deletePlatformModelApiApi({ id });
  createMessage.success($t('platform.setting.modelDeleted'));
  await loadModelApis();
}

async function handleSetPrimary(id: number) {
  await setPrimaryPlatformModelApiApi({ id });
  createMessage.success($t('platform.setting.primarySwitched'));
  await loadModelApis();
}

function handleProviderChange(value: string) {
  const preset = providerPresets[value];
  if (preset) {
    modelForm.provider_name = preset.provider_name;
    modelForm.api_base_url = preset.api_base_url;
    modelOptions.value = preset.models;
    if (!preset.models.includes(modelForm.model_name)) {
      modelForm.model_name = preset.models[0] || '';
    }
  } else {
    if (!modelForm.provider_name || providerNameMap.has(modelForm.provider_code)) {
      modelForm.provider_name = providerNameMap.get(value) || value;
    }
    modelOptions.value = [];
  }
}

function goToTaxonomySetup() {
  router.push('/platform/setup/taxonomy').catch(() => undefined);
}

onMounted(() => {
  void initializePage();
});
</script>

<template>
  <Page auto-content-height content-class="p-5">
    <div class="platform-setting-page">
      <Card :bordered="false" class="hero-card">
        <div class="hero-title-wrap">
          <div>
            <div class="hero-eyebrow">Platform Configuration Center</div>
            <h2 class="hero-title">{{ $t('platform.setting.title') }}</h2>
            <p class="hero-description">
              $t('platform.setting.heroDescription')
            </p>
          </div>
        </div>
      </Card>

      <Alert
        type="info"
        show-icon
        :message="$t('platform.setting.note')"
        :description="$t('platform.setting.infoDescription', { primary: $t('platform.setting.primaryModel') })"
      />

      <Card :title="$t('platform.setting.systemInit')" :bordered="false">
        <div class="setup-card">
          <div>
            <div class="setup-card__title">{{ $t('platform.setting.taxonomyBaseData') }}</div>
            <div class="setup-card__desc">
              $t('platform.setting.taxonomyBaseDataDesc')
            </div>
          </div>
          <Button type="primary" ghost @click="goToTaxonomySetup">
            $t('platform.setting.enterTaxonomyInit')
          </Button>
        </div>
      </Card>

      <Card :title="$t('platform.setting.siteConfig')" :bordered="false" :loading="pageLoading">
        <Form layout="vertical">
          <div class="form-grid">
            <Form.Item :label="$t('platform.setting.siteNameLabel')">
              <Input
                v-model:value="siteForm.site_name"
                :placeholder="$t('platform.setting.exampleFanCe')"
              />
            </Form.Item>
            <Form.Item :label="$t('platform.setting.siteTitleLabel')">
              <Input
                v-model:value="siteForm.site_title"
                :placeholder="$t('platform.setting.siteTitlePlaceholder')"
              />
            </Form.Item>
            <Form.Item :label="$t('platform.setting.icpRecordLabel')">
              <Input
                v-model:value="siteForm.filing_no"
                :placeholder="$t('platform.setting.exampleIcp')"
              />
            </Form.Item>
            <Form.Item :label="$t('platform.setting.domainLabel')">
              <Input
                v-model:value="siteForm.domain"
                :placeholder="$t('platform.setting.exampleDomain')"
              />
            </Form.Item>
            <Form.Item :label="$t('platform.setting.ip')">
              <Input
                v-model:value="siteForm.ip_address"
                :placeholder="$t('platform.setting.exampleIp')"
              />
            </Form.Item>
            <Form.Item :label="$t('platform.setting.portLabel')">
              <InputNumber
                v-model:value="siteForm.port"
                :min="0"
                :max="65535"
                class="w-full"
              />
            </Form.Item>
          </div>
          <div class="actions-row">
            <Button
              type="primary"
              :loading="siteSaving"
              @click="handleSaveSite"
            >
              {{ $t('platform.setting.saveSiteConfig') }}
            </Button>
          </div>
        </Form>
      </Card>

      <FrpTunnelCard :site-setting="siteForm" @refresh="loadSiteSetting" />

      <Card :title="$t('platform.setting.modelApiConfig')" :bordered="false" :loading="pageLoading">
        <template #extra>
          <Button type="primary" @click="openCreateModelModal">
            $t('platform.setting.addModel') API
          </Button>
        </template>

        <Table
          :columns="modelColumns"
          :data-source="modelRows"
          :loading="modelLoading"
          :pagination="false"
          :scroll="{ x: 1100 }"
          row-key="id"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'is_active'">
              <Tag :color="record.is_active ? 'green' : 'default'">
                {{ record.is_active ? $t('platform.setting.enabled') : $t('platform.setting.disabled') }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'is_primary'">
              <Tag :color="record.is_primary ? 'blue' : 'default'">
                {{ record.is_primary ? $t('platform.setting.primaryModel') : $t('platform.setting.candidateModel') }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <Space wrap>
                <Button size="small" @click="openEditModelModal(record)">
                  $t('platform.setting.edit')
                </Button>
                <Button
                  size="small"
                  type="primary"
                  ghost
                  :disabled="record.is_primary"
                  @click="handleSetPrimary(record.id)"
                >
                  {{ $t('platform.setting.setAsPrimary') }}
                </Button>
                <Popconfirm
                  :title="$t('platform.setting.deleteConfirm')"
                  @confirm="handleDeleteModel(record.id)"
                >
                  <Button size="small" danger>{{ $t('platform.setting.delete') }}</Button>
                </Popconfirm>
              </Space>
            </template>
          </template>
          <template #emptyText>
            <Empty :description="$t('platform.setting.emptyHint')" />
          </template>
        </Table>
      </Card>

      <Modal
        v-model:open="modelModalVisible"
        :confirm-loading="modelModalSaving"
        :title="(modelEditId ? $t('platform.setting.editModel') : $t('platform.setting.addModel')) + ' API'"
        width="720px"
        @cancel="resetModelForm"
      >
        <Form layout="vertical">
          <div class="form-grid">
            <Form.Item :label="$t('platform.setting.modelPlatform')">
              <Select
                v-model:value="modelForm.provider_code"
                :options="providerOptions"
                :placeholder="$t('platform.setting.selectModelPlatform')"
                @change="handleProviderChange"
              />
            </Form.Item>
            <Form.Item :label="$t('platform.setting.platformName')">
              <Input
                v-model:value="modelForm.provider_name"
                :placeholder="$t('platform.setting.exampleQwen')"
              />
            </Form.Item>
            <Form.Item :label="$t('platform.setting.modelName')">
              <AutoComplete
                v-model:value="modelForm.model_name"
                :options="modelOptions.map(m => ({ label: m, value: m }))"
                :placeholder="$t('platform.setting.selectOrInputModel')"
                allow-clear
              />
            </Form.Item>
            <Form.Item :label="$t('platform.setting.sortOrderValue')">
              <InputNumber
                v-model:value="modelForm.sort_order"
                :min="0"
                class="w-full"
              />
            </Form.Item>
          </div>

          <Form.Item :label="$t('platform.setting.apiAddress')">
            <Input
              v-model:value="modelForm.api_base_url"
              :placeholder="$t('platform.setting.exampleApiUrl')"
            />
          </Form.Item>

          <Form.Item :label="$t('platform.setting.apiKey')">
            <Input.Password
              v-model:value="modelForm.api_key"
              :placeholder="$t('platform.setting.pleaseInputApiKey')"
            />
          </Form.Item>

          <Form.Item :label="$t('platform.setting.remark')">
            <Input.TextArea
              v-model:value="modelForm.remark"
              :rows="3"
              :placeholder="$t('platform.setting.remarkPlaceholder')"
            />
          </Form.Item>

          <div class="switch-row">
            <div class="switch-item">
              <span>{{ $t('platform.setting.enabled') }}</span>
              <Switch v-model:checked="modelForm.is_active" />
            </div>
            <div class="switch-item">
              <span>{{ $t('platform.setting.setAsPrimary') }}</span>
              <Switch v-model:checked="modelForm.is_primary" />
            </div>
          </div>

          <div v-if="modelTestResult" class="model-test-result" :class="modelTestOk ? 'model-test-result--ok' : 'model-test-result--fail'">
            {{ modelTestResult }}
          </div>
        </Form>

        <template #footer>
          <div class="modal-footer">
            <Button
              :loading="modelTesting"
              @click="handleTestModel"
            >
              {{ modelTesting ? $t('platform.setting.testing') : $t('platform.setting.testConnection') }}
            </Button>
            <Space>
              <Button @click="resetModelForm(); modelModalVisible = false;">{{ $t('platform.setting.cancelText') }}</Button>
              <Button type="primary" :loading="modelModalSaving" @click="handleSaveModel">
                {{ modelEditId ? $t('platform.setting.update') : $t('platform.setting.add') }}
              </Button>
            </Space>
          </div>
        </template>
      </Modal>
    </div>
  </Page>
</template>

<style scoped lang="less">
.platform-setting-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero-card {
  overflow: hidden;
  background:
    radial-gradient(
      circle at top right,
      rgba(22, 119, 255, 0.14),
      transparent 34%
    ),
    linear-gradient(135deg, #f8fbff 0%, #f5f8fd 100%);
}

.hero-title-wrap {
  display: flex;
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

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.setup-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.setup-card__title {
  color: #13213a;
  font-size: 16px;
  font-weight: 600;
}

.setup-card__desc {
  margin-top: 8px;
  color: #4f5f7c;
  font-size: 13px;
  line-height: 1.7;
}

.actions-row {
  display: flex;
  justify-content: flex-end;
}

.switch-row {
  display: flex;
  gap: 24px;
  align-items: center;
}

.switch-item {
  display: flex;
  gap: 12px;
  align-items: center;
}

@media (max-width: 960px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .setup-card,
  .switch-row {
    flex-direction: column;
    align-items: flex-start;
  }
}

.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.model-test-result {
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
}

.model-test-result--ok {
  color: #135200;
  background: #f6ffed;
  border: 1px solid #b7eb8f;
}

.model-test-result--fail {
  color: #820014;
  background: #fff2f0;
  border: 1px solid #ffccc7;
}

</style>
