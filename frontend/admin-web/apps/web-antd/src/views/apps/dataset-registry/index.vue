<script setup lang="ts">
import type {
  AssetFileTypeOption,
  AssetTypeOption,
  DatasetKindOption,
} from '#/api/apps/dataset';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Checkbox,
  Empty,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Tag,
} from 'ant-design-vue';

import {
  createAssetFileTypeRegistryApi,
  createAssetTypeRegistryApi,
  createDatasetKindRegistryApi,
  deleteAssetFileTypeRegistryApi,
  getAssetFileTypeRegistryListApi,
  getAssetTypeRegistryListApi,
  getDatasetKindRegistryListApi,
  updateAssetFileTypeRegistryApi,
  updateAssetTypeRegistryApi,
  updateDatasetKindRegistryApi,
} from '#/api/apps/dataset';
import { useMessage } from '#/hooks/web/useMessage';
import { useUserStore } from '#/store/modules/user';
import { $t } from '@vben/locales';

const { createMessage } = useMessage();
const userStore = useUserStore();

const registryEditable = computed(() => {
  const userInfo = userStore.userInfo as null | Record<string, any>;
  return Boolean(
    userInfo?.is_superman || Number(userInfo?.user_type || 0) === 1,
  );
});

const registryAccessDenied = ref(false);
const kindLoading = ref(false);
const kindRows = ref<DatasetKindOption[]>([]);
const assetTypeLoading = ref(false);
const assetTypeRows = ref<AssetTypeOption[]>([]);
const assetFileTypeLoading = ref(false);
const assetFileTypeRows = ref<AssetFileTypeOption[]>([]);
const expandedDatasetTypeCodes = ref<string[]>([]);

const kindRegistryVisible = ref(false);
const kindRegistryLoading = ref(false);
const kindRegistryEditMode = ref<'create' | 'update'>('create');
const editingKindRegistryId = ref<null | number>(null);
const kindRegistryForm = reactive({
  code: '',
  base_code: '',
  name: '',
  description: '',
  is_active: true,
  sort_order: 0,
  meta_json: '',
});

const assetTypeRegistryVisible = ref(false);
const assetTypeRegistryLoading = ref(false);
const assetTypeRegistryEditMode = ref<'create' | 'update'>('create');
const editingAssetTypeRegistryId = ref<null | number>(null);
const assetTypeRegistryForm = reactive({
  code: '',
  base_code: '',
  name: '',
  description: '',
  allowed_dataset_types: [] as string[],
  is_active: true,
  sort_order: 0,
  meta_json: '',
});

const assetFileTypeRegistryVisible = ref(false);
const assetFileTypeRegistryLoading = ref(false);
const assetFileTypeRegistryEditMode = ref<'create' | 'update'>('create');
const editingAssetFileTypeRegistryId = ref<null | number>(null);
const assetFileTypeRegistryForm = reactive({
  code: '',
  base_code: '',
  name: '',
  description: '',
  supported_file_formats_text: '',
  file_role: 'primary',
  allowed_asset_types: [] as string[],
  is_active: true,
  sort_order: 0,
  meta_json: '',
});

const PRIORITY_DATASET_TYPE_CODES = [
  'genome',
  'transcriptome',
  'variome',
  'phenome',
];

const FILE_ROLE_OPTIONS = [
  { label: $t('dataset.candidate.primaryFile'), value: 'primary' },
  { label: $t('dataset.candidate.indexFile'), value: 'index' },
  { label: $t('dataset.candidate.derivedFile'), value: 'derived' },
  { label: $t('dataset.staging.metadata'), value: 'metadata' },
];

const registryLoading = computed(
  () =>
    kindLoading.value || assetTypeLoading.value || assetFileTypeLoading.value,
);

const activeKindRows = computed(() =>
  kindRows.value.filter((item) => Boolean(item.is_active)),
);
const inactiveKindRows = computed(() =>
  kindRows.value.filter((item) => !item.is_active),
);
const activeAssetTypeRows = computed(() =>
  assetTypeRows.value.filter((item) => Boolean(item.is_active)),
);
const activeAssetFileTypeRows = computed(() =>
  assetFileTypeRows.value.filter((item) => Boolean(item.is_active)),
);

const unrestrictedAssetTypes = computed(() =>
  activeAssetTypeRows.value
    .filter((item) => (item.allowed_dataset_types || []).length === 0)
    .map((item) => ({
      ...item,
      fileTypes: activeAssetFileTypeRows.value.filter((fileType) =>
        (fileType.allowed_asset_types || []).includes(item.code),
      ),
    })),
);

const registryOverviewRows = computed(() =>
  activeKindRows.value.map((kind) => {
    const assetTypes = activeAssetTypeRows.value
      .filter((item) => (item.allowed_dataset_types || []).includes(kind.code))
      .map((item) => ({
        ...item,
        fileTypes: activeAssetFileTypeRows.value.filter((fileType) =>
          (fileType.allowed_asset_types || []).includes(item.code),
        ),
      }));
    return {
      ...kind,
      assetTypes,
    };
  }),
);

const primaryRegistryOverviewRows = computed(() => {
  const priorityOrder = new Map(
    PRIORITY_DATASET_TYPE_CODES.map((code, index) => [code, index]),
  );
  return registryOverviewRows.value
    .filter((item) => PRIORITY_DATASET_TYPE_CODES.includes(item.code))
    .sort(
      (left, right) =>
        (priorityOrder.get(left.code) ?? 999) -
        (priorityOrder.get(right.code) ?? 999),
    );
});

const secondaryActiveKindRows = computed(() =>
  activeKindRows.value.filter(
    (item) => !PRIORITY_DATASET_TYPE_CODES.includes(item.code),
  ),
);

const datasetKindSelectOptions = computed(() =>
  kindRows.value.map((item) => ({
    label: `${item.name} (${item.code})`,
    value: item.code,
  })),
);

const assetTypeSelectOptions = computed(() =>
  assetTypeRows.value.map((item) => ({
    label: `${item.name} (${item.code})`,
    value: item.code,
  })),
);

function getErrorMessage(error: unknown) {
  const responseData = (error as any)?.response?.data ?? {};
  return (
    responseData?.msg ||
    responseData?.message ||
    (error instanceof Error ? error.message : '') ||
    $t('dataset.staging.requestFailed')
  );
}

function isPermissionDeniedError(error: unknown) {
  const response = (error as any)?.response ?? {};
  const responseData = response?.data ?? {};
  const status = response?.status;
  const code = responseData?.code;
  const message =
    `${getErrorMessage(error)} ${responseData?.detail || ''}`.toLowerCase();
  return (
    status === 401 ||
    status === 403 ||
    code === 4003 ||
    code === 4007 ||
    message.includes('401') ||
    message.includes('403') ||
    message.includes('forbidden') ||
    message.includes('permission') ||
    message.includes('access denied') ||
    message.includes('无权限')
  );
}

function resetKindRegistryForm() {
  editingKindRegistryId.value = null;
  kindRegistryForm.code = '';
  kindRegistryForm.base_code = '';
  kindRegistryForm.name = '';
  kindRegistryForm.description = '';
  kindRegistryForm.is_active = true;
  kindRegistryForm.sort_order = 0;
  kindRegistryForm.meta_json = '';
}

function resetAssetTypeRegistryForm() {
  editingAssetTypeRegistryId.value = null;
  assetTypeRegistryForm.code = '';
  assetTypeRegistryForm.base_code = '';
  assetTypeRegistryForm.name = '';
  assetTypeRegistryForm.description = '';
  assetTypeRegistryForm.allowed_dataset_types = [];
  assetTypeRegistryForm.is_active = true;
  assetTypeRegistryForm.sort_order = 0;
  assetTypeRegistryForm.meta_json = '';
}

function resetAssetFileTypeRegistryForm() {
  editingAssetFileTypeRegistryId.value = null;
  assetFileTypeRegistryForm.code = '';
  assetFileTypeRegistryForm.base_code = '';
  assetFileTypeRegistryForm.name = '';
  assetFileTypeRegistryForm.description = '';
  assetFileTypeRegistryForm.supported_file_formats_text = '';
  assetFileTypeRegistryForm.file_role = 'primary';
  assetFileTypeRegistryForm.allowed_asset_types = [];
  assetFileTypeRegistryForm.is_active = true;
  assetFileTypeRegistryForm.sort_order = 0;
  assetFileTypeRegistryForm.meta_json = '';
}

function parseMultiValueText(value: string) {
  return [
    ...new Set(
      value
        .split(/[\n,，;]/)
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  ];
}

async function loadRegistryData() {
  kindLoading.value = true;
  assetTypeLoading.value = true;
  assetFileTypeLoading.value = true;
  try {
    const [kindResult, assetTypeResult, assetFileTypeResult] =
      await Promise.all([
        getDatasetKindRegistryListApi({ page: 1, size: 500 }),
        getAssetTypeRegistryListApi({ page: 1, size: 500 }),
        getAssetFileTypeRegistryListApi({ page: 1, size: 500 }),
      ]);
    kindRows.value = kindResult.dataList || [];
    assetTypeRows.value = assetTypeResult.dataList || [];
    assetFileTypeRows.value = assetFileTypeResult.dataList || [];
    registryAccessDenied.value = false;
  } catch (error) {
    kindRows.value = [];
    assetTypeRows.value = [];
    assetFileTypeRows.value = [];
    registryAccessDenied.value = isPermissionDeniedError(error);
    if (!registryAccessDenied.value) {
      createMessage.error(getErrorMessage(error));
    }
  } finally {
    kindLoading.value = false;
    assetTypeLoading.value = false;
    assetFileTypeLoading.value = false;
  }
}

function getFileRoleLabel(fileRole?: string) {
  if (fileRole === 'primary') return $t('dataset.candidate.primaryFile');
  if (fileRole === 'index') return $t('dataset.candidate.indexFile');
  if (fileRole === 'derived') return $t('dataset.candidate.derivedFile');
  if (fileRole === 'metadata') return $t('dataset.staging.metadata');
  return fileRole || '-';
}

function getAssetTypeCount(kindCode: string) {
  return activeAssetTypeRows.value.filter((item) =>
    (item.allowed_dataset_types || []).includes(kindCode),
  ).length;
}

function getAssetFileTypeCount(kindCode: string) {
  const assetTypeCodes = new Set(
    activeAssetTypeRows.value
      .filter((item) => (item.allowed_dataset_types || []).includes(kindCode))
      .map((item) => item.code),
  );
  return activeAssetFileTypeRows.value.filter((item) =>
    (item.allowed_asset_types || []).some((assetTypeCode) =>
      assetTypeCodes.has(assetTypeCode),
    ),
  ).length;
}

function isDatasetTypeExpanded(kindCode: string) {
  return expandedDatasetTypeCodes.value.includes(kindCode);
}

function toggleDatasetType(kindCode: string) {
  if (isDatasetTypeExpanded(kindCode)) {
    expandedDatasetTypeCodes.value = expandedDatasetTypeCodes.value.filter(
      (item) => item !== kindCode,
    );
    return;
  }
  expandedDatasetTypeCodes.value = [
    ...expandedDatasetTypeCodes.value,
    kindCode,
  ];
}

function openKindRegistryCreateModal() {
  kindRegistryEditMode.value = 'create';
  resetKindRegistryForm();
  kindRegistryVisible.value = true;
}

function openAssetTypeRegistryCreateModal() {
  assetTypeRegistryEditMode.value = 'create';
  resetAssetTypeRegistryForm();
  assetTypeRegistryVisible.value = true;
}

function openAssetFileTypeRegistryCreateModal(assetTypeCode?: string) {
  assetFileTypeRegistryEditMode.value = 'create';
  resetAssetFileTypeRegistryForm();
  if (assetTypeCode) {
    assetFileTypeRegistryForm.allowed_asset_types = [assetTypeCode];
  }
  assetFileTypeRegistryVisible.value = true;
}

function openAssetFileTypeRegistryUpdateModal(fileType: AssetFileTypeOption) {
  assetFileTypeRegistryEditMode.value = 'update';
  editingAssetFileTypeRegistryId.value = fileType.id;
  assetFileTypeRegistryForm.code = fileType.code || '';
  assetFileTypeRegistryForm.base_code = fileType.base_code || '';
  assetFileTypeRegistryForm.name = fileType.name || '';
  assetFileTypeRegistryForm.description = fileType.description || '';
  assetFileTypeRegistryForm.supported_file_formats_text = (
    fileType.supported_file_formats || []
  ).join(', ');
  assetFileTypeRegistryForm.file_role = fileType.file_role || 'primary';
  assetFileTypeRegistryForm.allowed_asset_types = [
    ...(fileType.allowed_asset_types || []),
  ];
  assetFileTypeRegistryForm.is_active = Boolean(fileType.is_active);
  assetFileTypeRegistryForm.sort_order = Number(fileType.sort_order || 0);
  assetFileTypeRegistryForm.meta_json = fileType.meta_json || '';
  assetFileTypeRegistryVisible.value = true;
}

async function submitKindRegistry() {
  kindRegistryLoading.value = true;
  try {
    if (kindRegistryEditMode.value === 'create') {
      await createDatasetKindRegistryApi({ ...kindRegistryForm });
      createMessage.success($t('dataset.registry.datasetTypeCreated'));
    } else {
      await updateDatasetKindRegistryApi({
        id: editingKindRegistryId.value,
        ...kindRegistryForm,
      });
      createMessage.success($t('dataset.registry.datasetTypeUpdated'));
    }
    kindRegistryVisible.value = false;
    await loadRegistryData();
  } catch (error) {
    createMessage.error(getErrorMessage(error));
  } finally {
    kindRegistryLoading.value = false;
  }
}

async function submitAssetTypeRegistry() {
  assetTypeRegistryLoading.value = true;
  try {
    if (assetTypeRegistryEditMode.value === 'create') {
      await createAssetTypeRegistryApi({ ...assetTypeRegistryForm });
      createMessage.success($t('dataset.registry.assetTypeCreated'));
    } else {
      await updateAssetTypeRegistryApi({
        id: editingAssetTypeRegistryId.value,
        ...assetTypeRegistryForm,
      });
      createMessage.success($t('dataset.registry.assetTypeUpdated'));
    }
    assetTypeRegistryVisible.value = false;
    await loadRegistryData();
  } catch (error) {
    createMessage.error(getErrorMessage(error));
  } finally {
    assetTypeRegistryLoading.value = false;
  }
}

async function submitAssetFileTypeRegistry() {
  assetFileTypeRegistryLoading.value = true;
  try {
    const payload = {
      code: assetFileTypeRegistryForm.code.trim(),
      base_code: assetFileTypeRegistryForm.base_code.trim(),
      name: assetFileTypeRegistryForm.name.trim(),
      description: assetFileTypeRegistryForm.description.trim() || undefined,
      supported_file_formats: parseMultiValueText(
        assetFileTypeRegistryForm.supported_file_formats_text,
      ),
      file_role: assetFileTypeRegistryForm.file_role,
      allowed_asset_types: [...assetFileTypeRegistryForm.allowed_asset_types],
      is_active: assetFileTypeRegistryForm.is_active,
      sort_order: Number(assetFileTypeRegistryForm.sort_order || 0),
      meta_json: assetFileTypeRegistryForm.meta_json.trim() || undefined,
    };

    if (payload.supported_file_formats.length === 0) {
      createMessage.error($t('dataset.registry.fillFileFormatRequired'));
      return;
    }
    if (payload.allowed_asset_types.length === 0) {
      createMessage.error($t('dataset.registry.bindAssetTypeRequired'));
      return;
    }

    if (assetFileTypeRegistryEditMode.value === 'create') {
      await createAssetFileTypeRegistryApi(payload);
      createMessage.success($t('dataset.registry.assetFileTypeCreated'));
    } else {
      await updateAssetFileTypeRegistryApi({
        id: editingAssetFileTypeRegistryId.value,
        ...payload,
      });
      createMessage.success($t('dataset.registry.assetFileTypeUpdated'));
    }

    assetFileTypeRegistryVisible.value = false;
    await loadRegistryData();
  } catch (error) {
    createMessage.error(getErrorMessage(error));
  } finally {
    assetFileTypeRegistryLoading.value = false;
  }
}

async function handleDeleteAssetFileType(fileType: AssetFileTypeOption) {
  try {
    await deleteAssetFileTypeRegistryApi({ id: fileType.id });
    createMessage.success($t('dataset.registry.assetFileTypeDeleted', { code: fileType.code }));
    await loadRegistryData();
  } catch (error) {
    createMessage.error(getErrorMessage(error));
  }
}

onMounted(() => {
  loadRegistryData();
});
</script>

<template>
  <Page auto-content-height class="registry-page">
    <div class="registry-block">
      <div class="registry-header">
        <div>
          <div class="section-title">{{ $t('dataset.registry.typeRegistryTitle') }}</div>
          <div class="section-sub">
            {{ $t('dataset.registry.typeRegistryDesc') }}
          </div>
          <div v-if="!registryEditable" class="section-sub">
            {{ $t('dataset.registry.readonlyModeHint') }}
          </div>
        </div>
        <Space wrap>
          <Button @click="loadRegistryData">{{ $t('dataset.registry.refreshRegistry') }}</Button>
          <Button
            type="primary"
            ghost
            :disabled="registryAccessDenied || !registryEditable"
            @click="openKindRegistryCreateModal"
          >
            {{ $t('dataset.registry.addDatasetTypeBtn') }}
          </Button>
          <Button
            type="primary"
            ghost
            :disabled="registryAccessDenied || !registryEditable"
            @click="openAssetTypeRegistryCreateModal"
          >
            {{ $t('dataset.registry.addAssetTypeBtn') }}
          </Button>
          <Button
            type="primary"
            ghost
            :disabled="registryAccessDenied || !registryEditable"
            @click="openAssetFileTypeRegistryCreateModal()"
          >
            {{ $t('dataset.registry.addAssetFileTypeBtn') }}
          </Button>
        </Space>
      </div>

      <div v-if="registryAccessDenied" class="empty-wrap">
        <Empty :description="$t('dataset.registry.accessDeniedHint')" />
      </div>

      <div v-else class="registry-grid">
        <div class="registry-card registry-card-full">
          <div class="section-title">{{ $t('dataset.registry.typeOverviewTitle') }}</div>
          <div class="section-sub">
            {{ $t('dataset.registry.typeOverviewDesc') }}
          </div>

          <div class="summary-grid">
            <div class="summary-tile">
              <div class="summary-value">{{ activeKindRows.length }}</div>
              <div class="muted">{{ $t('dataset.registry.enabledDatasetType') }}</div>
            </div>
            <div class="summary-tile">
              <div class="summary-value">{{ activeAssetTypeRows.length }}</div>
              <div class="muted">{{ $t('dataset.registry.enabledAssetType') }}</div>
            </div>
            <div class="summary-tile">
              <div class="summary-value">
                {{ activeAssetFileTypeRows.length }}
              </div>
              <div class="muted">{{ $t('dataset.registry.enabledAssetFileType') }}</div>
            </div>
          </div>

          <div v-if="registryLoading" class="empty-wrap">
            <Empty :description="$t('dataset.registry.loadingTypeInfo')" />
          </div>

          <div v-else class="type-overview">
            <div
              v-for="group in primaryRegistryOverviewRows"
              :key="group.id"
              class="type-group"
            >
              <button
                type="button"
                class="type-group-header type-group-toggle"
                @click="toggleDatasetType(group.code)"
              >
                <div>
                  <div class="type-group-title">
                    {{ group.name || group.code }}
                  </div>
                  <div class="muted">
                    {{ group.description || group.base_code || '-' }}
                  </div>
                </div>
                <Space wrap>
                  <Tag color="blue">{{ group.code }}</Tag>
                  <Tag color="processing">
                    {{ $t('dataset.registry.assetTypeCount', { count: getAssetTypeCount(group.code) }) }}
                  </Tag>
                  <Tag color="purple">
                    {{ $t('dataset.registry.assetFileTypeCount', { count: getAssetFileTypeCount(group.code) }) }}
                  </Tag>
                  <Tag
                    :color="
                      isDatasetTypeExpanded(group.code) ? 'green' : 'default'
                    "
                  >
                    {{
                      isDatasetTypeExpanded(group.code) ? $t('dataset.registry.expanded') : $t('dataset.registry.clickToExpand')
                    }}
                  </Tag>
                </Space>
              </button>

              <div
                v-if="
                  isDatasetTypeExpanded(group.code) &&
                  group.assetTypes.length > 0
                "
                class="asset-type-list"
              >
                <div
                  v-for="assetType in group.assetTypes"
                  :key="assetType.id"
                  class="asset-type-item"
                >
                  <div class="asset-type-header">
                    <div>
                      <div class="asset-type-title">
                        {{ assetType.name || assetType.code }}
                      </div>
                      <div class="muted">
                        {{
                          assetType.description || assetType.base_code || '-'
                        }}
                      </div>
                    </div>
                    <Space wrap>
                      <Tag color="gold">{{ assetType.code }}</Tag>
                      <Button
                        v-if="registryEditable"
                        size="small"
                        type="link"
                        @click.stop="
                          openAssetFileTypeRegistryCreateModal(assetType.code)
                        "
                      >
                        {{ $t('dataset.registry.addFileType') }}
                      </Button>
                    </Space>
                  </div>

                  <div
                    v-if="assetType.fileTypes.length > 0"
                    class="file-type-list"
                  >
                    <div
                      v-for="fileType in assetType.fileTypes"
                      :key="fileType.id"
                      class="file-type-item"
                    >
                      <div class="file-type-header">
                        <div>
                          <div class="file-type-title">
                            {{ fileType.name || fileType.code }}
                          </div>
                          <div class="muted">
                            {{
                              fileType.description || fileType.base_code || '-'
                            }}
                          </div>
                        </div>
                        <Space wrap>
                          <Tag color="cyan">{{ fileType.code }}</Tag>
                          <Tag
                            :color="
                              fileType.file_role === 'index'
                                ? 'orange'
                                : 'green'
                            "
                          >
                            {{ getFileRoleLabel(fileType.file_role) }}
                          </Tag>
                          <Button
                            v-if="registryEditable"
                            size="small"
                            type="link"
                            @click.stop="
                              openAssetFileTypeRegistryUpdateModal(fileType)
                            "
                          >
                            {{ $t('dataset.staging.edit') }}
                          </Button>
                          <Popconfirm
                            v-if="registryEditable"
                            :title="$t('dataset.registry.deleteAssetFileTypeConfirm')"
                            :ok-text="$t('dataset.list.delete')"
                            :cancel-text="$t('platform.setting.cancelText')"
                            @confirm="handleDeleteAssetFileType(fileType)"
                          >
                            <Button size="small" type="link" danger @click.stop>
                              {{ $t('dataset.list.delete') }}
                            </Button>
                          </Popconfirm>
                        </Space>
                      </div>
                      <Space wrap>
                        <Tag
                          v-for="format in fileType.supported_file_formats ||
                          []"
                          :key="`${fileType.id}-${format}`"
                        >
                          {{ format }}
                        </Tag>
                      </Space>
                    </div>
                  </div>
                  <Empty
                    v-else
                    :description="$t('dataset.registry.noThirdLayerFileTypes')"
                  />
                </div>
              </div>
              <Empty
                v-else-if="isDatasetTypeExpanded(group.code)"
                :description="$t('dataset.registry.noBoundAssetTypes')"
              />
            </div>

            <div v-if="unrestrictedAssetTypes.length > 0" class="type-group">
              <div class="type-group-header">
                <div>
                  <div class="type-group-title">{{ $t('dataset.registry.genericAssetTypeTitle') }}</div>
                  <div class="muted">
                    {{ $t('dataset.registry.genericAssetTypeDesc') }}
                  </div>
                </div>
              </div>
              <div class="asset-type-list">
                <div
                  v-for="assetType in unrestrictedAssetTypes"
                  :key="assetType.id"
                  class="asset-type-item"
                >
                  <div class="asset-type-header">
                    <div>
                      <div class="asset-type-title">
                        {{ assetType.name || assetType.code }}
                      </div>
                      <div class="muted">
                        {{
                          assetType.description || assetType.base_code || '-'
                        }}
                      </div>
                    </div>
                    <Space wrap>
                      <Tag color="gold">{{ assetType.code }}</Tag>
                      <Button
                        v-if="registryEditable"
                        size="small"
                        type="link"
                        @click.stop="
                          openAssetFileTypeRegistryCreateModal(assetType.code)
                        "
                      >
                        {{ $t('dataset.registry.addFileType') }}
                      </Button>
                    </Space>
                  </div>
                  <div
                    v-if="assetType.fileTypes.length > 0"
                    class="file-type-list"
                  >
                    <div
                      v-for="fileType in assetType.fileTypes"
                      :key="fileType.id"
                      class="file-type-item"
                    >
                      <div class="file-type-header">
                        <div class="file-type-title">
                          {{ fileType.name || fileType.code }}
                        </div>
                        <Space wrap>
                          <Tag
                            :color="
                              fileType.file_role === 'index'
                                ? 'orange'
                                : 'green'
                            "
                          >
                            {{ getFileRoleLabel(fileType.file_role) }}
                          </Tag>
                          <Button
                            v-if="registryEditable"
                            size="small"
                            type="link"
                            @click.stop="
                              openAssetFileTypeRegistryUpdateModal(fileType)
                            "
                          >
                            {{ $t('dataset.staging.edit') }}
                          </Button>
                          <Popconfirm
                            v-if="registryEditable"
                            :title="$t('dataset.registry.deleteAssetFileTypeConfirm')"
                            :ok-text="$t('dataset.list.delete')"
                            :cancel-text="$t('platform.setting.cancelText')"
                            @confirm="handleDeleteAssetFileType(fileType)"
                          >
                            <Button size="small" type="link" danger @click.stop>
                              {{ $t('dataset.list.delete') }}
                            </Button>
                          </Popconfirm>
                        </Space>
                      </div>
                      <Space wrap>
                        <Tag
                          v-for="format in fileType.supported_file_formats ||
                          []"
                          :key="`${fileType.id}-${format}`"
                        >
                          {{ format }}
                        </Tag>
                      </Space>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="secondaryActiveKindRows.length > 0" class="type-group">
              <div class="type-group-header">
                <div>
                  <div class="type-group-title">{{ $t('dataset.registry.otherRegisteredDatasetType') }}</div>
                  <div class="muted">
                    {{ $t('dataset.registry.otherRegisteredDesc') }}
                  </div>
                </div>
              </div>
              <Space wrap>
                <Tag
                  v-for="item in secondaryActiveKindRows"
                  :key="item.id"
                  color="default"
                >
                  {{ item.name || item.code }} / {{ item.code }}
                </Tag>
              </Space>
            </div>

            <div v-if="inactiveKindRows.length > 0" class="type-group">
              <div class="type-group-header">
                <div>
                  <div class="type-group-title">{{ $t('dataset.registry.deprecatedTypeTitle') }}</div>
                  <div class="muted">
                    {{ $t('dataset.registry.deprecatedTypeDesc') }}
                  </div>
                </div>
              </div>
              <Space wrap>
                <Tag v-for="item in inactiveKindRows" :key="item.id">
                  {{ item.name || item.code }} / {{ item.code }}
                </Tag>
              </Space>
            </div>
          </div>
        </div>
      </div>
    </div>

    <Modal
      v-model:open="kindRegistryVisible"
      :title="
        kindRegistryEditMode === 'create'
          ? $t('dataset.registry.addDatasetType')
          : $t('dataset.staging.editDatasetType')
      "
      :confirm-loading="kindRegistryLoading"
      @ok="submitKindRegistry"
    >
      <div class="modal-form">
        <Input
          v-model:value="kindRegistryForm.code"
          :placeholder="$t('dataset.registry.kindCodePlaceholder')"
        />
        <Input
          v-model:value="kindRegistryForm.base_code"
          :placeholder="$t('dataset.registry.kindBaseCodePlaceholder')"
        />
        <Input v-model:value="kindRegistryForm.name" :placeholder="$t('system.dict.name')" />
        <Input
          v-model:value="kindRegistryForm.description"
          allow-clear
          :placeholder="$t('platform.setting.note')"
        />
        <Input
          v-model:value="kindRegistryForm.meta_json"
          allow-clear
          :placeholder="$t('dataset.staging.optionalMetaJson')"
        />
        <Input
          v-model:value="kindRegistryForm.sort_order"
          type="number"
          :placeholder="$t('platform.setting.sortOrderValue')"
        />
        <Checkbox v-model:checked="kindRegistryForm.is_active">{{ $t('dataset.staging.enabled') }}</Checkbox>
      </div>
    </Modal>

    <Modal
      v-model:open="assetTypeRegistryVisible"
      :title="
        assetTypeRegistryEditMode === 'create'
          ? $t('dataset.registry.addAssetType')
          : $t('dataset.registry.editAssetType')
      "
      :confirm-loading="assetTypeRegistryLoading"
      @ok="submitAssetTypeRegistry"
    >
      <div class="modal-form">
        <Input
          v-model:value="assetTypeRegistryForm.code"
          :placeholder="$t('dataset.registry.assetTypeCodePlaceholder')"
        />
        <Input
          v-model:value="assetTypeRegistryForm.base_code"
          :placeholder="$t('dataset.registry.assetTypeBaseCodePlaceholder')"
        />
        <Input v-model:value="assetTypeRegistryForm.name" :placeholder="$t('system.dict.name')" />
        <Input
          v-model:value="assetTypeRegistryForm.description"
          allow-clear
          :placeholder="$t('platform.setting.note')"
        />
        <Select
          v-model:value="assetTypeRegistryForm.allowed_dataset_types"
          mode="multiple"
          allow-clear
          :options="datasetKindSelectOptions"
          :placeholder="$t('dataset.registry.allowedDatasetKinds')"
        />
        <Input
          v-model:value="assetTypeRegistryForm.meta_json"
          allow-clear
          :placeholder="$t('dataset.staging.optionalMetaJson')"
        />
        <Input
          v-model:value="assetTypeRegistryForm.sort_order"
          type="number"
          :placeholder="$t('platform.setting.sortOrderValue')"
        />
        <Checkbox v-model:checked="assetTypeRegistryForm.is_active">
          {{ $t('dataset.staging.enabled') }}
        </Checkbox>
      </div>
    </Modal>

    <Modal
      v-model:open="assetFileTypeRegistryVisible"
      :title="
        assetFileTypeRegistryEditMode === 'create'
          ? $t('dataset.registry.addAssetFileType')
          : $t('dataset.registry.editAssetFileType')
      "
      :confirm-loading="assetFileTypeRegistryLoading"
      @ok="submitAssetFileTypeRegistry"
    >
      <div class="modal-form">
        <Input
          v-model:value="assetFileTypeRegistryForm.code"
          :placeholder="$t('dataset.registry.assetFileTypeCodePlaceholder')"
        />
        <Input
          v-model:value="assetFileTypeRegistryForm.base_code"
          :placeholder="$t('dataset.registry.assetFileTypeBaseCodePlaceholder')"
        />
        <Input
          v-model:value="assetFileTypeRegistryForm.name"
          :placeholder="$t('system.dict.name')"
        />
        <Input
          v-model:value="assetFileTypeRegistryForm.description"
          allow-clear
          :placeholder="$t('platform.setting.note')"
        />
        <Select
          v-model:value="assetFileTypeRegistryForm.file_role"
          :options="FILE_ROLE_OPTIONS"
          :placeholder="$t('dataset.registry.fileRolePlaceholder')"
        />
        <Select
          v-model:value="assetFileTypeRegistryForm.allowed_asset_types"
          mode="multiple"
          allow-clear
          :options="assetTypeSelectOptions"
          :placeholder="$t('dataset.registry.bindAssetTypePlaceholder')"
        />
        <Input.TextArea
          v-model:value="assetFileTypeRegistryForm.supported_file_formats_text"
          :auto-size="{ minRows: 2, maxRows: 4 }"
          :placeholder="$t('dataset.registry.supportedFormatsPlaceholder')"
        />
        <Input
          v-model:value="assetFileTypeRegistryForm.meta_json"
          allow-clear
          :placeholder="$t('dataset.staging.optionalMetaJson')"
        />
        <Input
          v-model:value="assetFileTypeRegistryForm.sort_order"
          type="number"
          :placeholder="$t('platform.setting.sortOrderValue')"
        />
        <Checkbox v-model:checked="assetFileTypeRegistryForm.is_active">
          {{ $t('dataset.staging.enabled') }}
        </Checkbox>
      </div>
    </Modal>
  </Page>
</template>

<style scoped>
.registry-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.registry-block,
.registry-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  border: 1px solid rgb(226 232 240);
  border-radius: 16px;
  background: #fff;
}

.registry-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.registry-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.registry-card-full {
  grid-column: 1 / -1;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.summary-tile {
  padding: 16px;
  border: 1px solid rgb(226 232 240);
  border-radius: 12px;
  background: rgb(248 250 252);
}

.summary-value {
  color: rgb(15 23 42);
  font-size: 24px;
  font-weight: 700;
}

.type-overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.type-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border: 1px solid rgb(226 232 240);
  border-radius: 14px;
  background: rgb(250 250 250);
}

.type-group-header,
.asset-type-header,
.file-type-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.type-group-toggle {
  width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.type-group-toggle:hover .type-group-title {
  color: rgb(3 105 161);
}

.type-group-title,
.asset-type-title,
.file-type-title {
  color: rgb(15 23 42);
  font-size: 15px;
  font-weight: 600;
}

.asset-type-list,
.file-type-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.asset-type-item,
.file-type-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  border: 1px solid rgb(226 232 240);
  border-radius: 12px;
  background: #fff;
}

.section-title {
  color: rgb(15 23 42);
  font-size: 16px;
  font-weight: 600;
}

.section-sub,
.muted {
  color: rgb(100 116 139);
  font-size: 12px;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-wrap {
  padding: 32px 0;
}

@media (max-width: 1200px) {
  .registry-grid {
    grid-template-columns: 1fr;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .type-group-header,
  .asset-type-header,
  .file-type-header {
    flex-direction: column;
  }
}
</style>
