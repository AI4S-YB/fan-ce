<script setup lang="ts">
import { ref, computed } from 'vue';
import {
  Button, Space, Tag, Input, Select, Modal, Empty, message,
} from 'ant-design-vue';
import { getAssetTypeOptionsApi } from '#/api/apps/dataset';
import { $t } from '@vben/locales';
import {
  useDataset,
  FILE_ROLE_OPTIONS,
  getFileRoleLabel,
  getFileRoleColor,
  type DatasetVersionDetail,
  type DatasetAssetItem,
  type AssetFileItem,
} from '../composables/useDataset';

const props = defineProps<{
  versionDetail: DatasetVersionDetail | null;
  loading: boolean;
}>();

const emit = defineEmits<{ refresh: [] }>();

const {
  createAsset, updateAsset, deleteAsset,
  registerFile, updateFile, deleteFile,
} = useDataset();

// Filter
const keyword = ref('');
const assetTypeOptions = ref<{ label: string; value: string }[]>([]);

const filteredAssets = computed(() => {
  const assets = props.versionDetail?.assets || [];
  const kw = keyword.value.trim().toLowerCase();
  if (!kw) return assets;
  return assets.filter(a =>
    [a.asset_code, a.asset_name, a.asset_type, a.file_format, a.query_engine]
      .filter(Boolean)
      .some(v => String(v).toLowerCase().includes(kw)),
  );
});

// Asset create/edit modal
const assetModalVisible = ref(false);
const assetModalLoading = ref(false);
const editingAsset = ref<DatasetAssetItem | null>(null);
const assetForm = ref({
  asset_name: '',
  asset_type: undefined as string | undefined,
  file_format: '',
  query_engine: '',
  is_query_entry: false,
});

function openAssetCreate() {
  editingAsset.value = null;
  assetForm.value = { asset_name: '', asset_type: undefined, file_format: '', query_engine: '', is_query_entry: false };
  assetModalVisible.value = true;
}

function openAssetEdit(asset: DatasetAssetItem) {
  editingAsset.value = asset;
  assetForm.value = {
    asset_name: asset.asset_name || '',
    asset_type: asset.asset_type,
    file_format: asset.file_format || '',
    query_engine: asset.query_engine || '',
    is_query_entry: asset.is_query_entry || false,
  };
  assetModalVisible.value = true;
}

async function submitAsset() {
  assetModalLoading.value = true;
  try {
    if (editingAsset.value) {
      await updateAsset({ id: editingAsset.value.id, ...assetForm.value });
      message.success($t('dataset.list.assetUpdated'));
    } else {
      await createAsset({ version_id: props.versionDetail?.id, ...assetForm.value });
      message.success($t('dataset.list.assetCreated'));
    }
    assetModalVisible.value = false;
    emit('refresh');
  } finally {
    assetModalLoading.value = false;
  }
}

// File register modal
const fileModalVisible = ref(false);
const fileModalLoading = ref(false);
const editingFile = ref<AssetFileItem | null>(null);
const currentAssetForFile = ref<DatasetAssetItem | null>(null);
const fileForm = ref({
  file_role: 'primary',
  local_path: '',
  file_format: '',
  index_of_file_id: undefined as number | undefined,
});

function openFileRegister(asset: DatasetAssetItem) {
  currentAssetForFile.value = asset;
  editingFile.value = null;
  fileForm.value = { file_role: 'primary', local_path: '', file_format: '', index_of_file_id: undefined };
  fileModalVisible.value = true;
}

function openFileEdit(asset: DatasetAssetItem, file: AssetFileItem) {
  currentAssetForFile.value = asset;
  editingFile.value = file;
  fileForm.value = {
    file_role: file.file_role || 'primary',
    local_path: file.local_path || '',
    file_format: file.file_format || '',
    index_of_file_id: file.index_of_file_id,
  };
  fileModalVisible.value = true;
}

async function submitFile() {
  if (!currentAssetForFile.value) return;
  fileModalLoading.value = true;
  try {
    if (editingFile.value) {
      await updateFile({ id: editingFile.value.id, ...fileForm.value });
      message.success($t('dataset.list.fileUpdated'));
    } else {
      await registerFile({ asset_id: currentAssetForFile.value.id, ...fileForm.value });
      message.success($t('dataset.list.fileRegistered'));
    }
    fileModalVisible.value = false;
    emit('refresh');
  } finally {
    fileModalLoading.value = false;
  }
}

async function handleDeleteAsset(asset: DatasetAssetItem) {
  await deleteAsset(asset.id);
  message.success($t('dataset.list.assetDeleted'));
  emit('refresh');
}

async function handleDeleteFile(file: AssetFileItem) {
  await deleteFile(file.id);
  message.success($t('dataset.list.fileDeleted'));
  emit('refresh');
}
</script>

<template>
  <div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px;">
      <Button type="primary" ghost @click="openAssetCreate">{{ $t('dataset.list.newAsset') }}</Button>
      <Input v-model:value="keyword" allow-clear :placeholder="$t('dataset.list.filterAsset')" style="width: 200px;" />
      <span style="font-size: 12px; color: #888; line-height: 32px;">
        {{ $t('dataset.list.assetCount', { filtered: filteredAssets.length, total: versionDetail?.assets?.length || 0 }) }}
      </span>
    </div>

    <div v-if="loading" style="text-align: center; padding: 40px;">{{ $t('dataset.list.loading') }}</div>
    <Empty v-else-if="!filteredAssets.length" :description="$t('dataset.list.noAsset')" />

    <div v-for="asset in filteredAssets" :key="asset.id" style="border: 1px solid #e0e0e0; border-radius: 4px; padding: 12px; margin-bottom: 8px; background: #fff;">
      <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
        <div>
          <strong>{{ asset.asset_name || asset.asset_code || `asset-${asset.id}` }}</strong>
          <span style="color: #888; font-size: 12px;"> / {{ asset.asset_type || '-' }}</span>
        </div>
        <Space size="small">
          <Tag v-if="asset.is_query_entry" color="blue">{{ $t('dataset.list.queryEntryAsset') }}</Tag>
          <Tag>{{ asset.asset_type || '-' }}</Tag>
        </Space>
      </div>

      <div style="font-size: 12px; color: #888; margin-bottom: 8px;">
        {{ $t('dataset.list.fileCount', { count: asset.files?.length || 0 }) }} · {{ $t('dataset.list.mainFormat') }} {{ asset.file_format || '-' }} · {{ $t('dataset.list.queryEngineLabel') }} {{ asset.query_engine || '-' }}
      </div>

      <!-- Files -->
      <div v-if="asset.files?.length" style="margin-bottom: 8px;">
        <div v-for="file in asset.files" :key="file.id" style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px; border-bottom: 1px dashed #f0f0f0;">
          <div>
            <Tag :color="getFileRoleColor(file as AssetFileItem)">{{ getFileRoleLabel(file as AssetFileItem) }}</Tag>
            <Tag v-if="file.file_format">{{ file.file_format }}</Tag>
            {{ file.file_name || file.local_path || '-' }}
          </div>
          <Space size="small">
            <Button type="link" size="small" @click="openFileEdit(asset as DatasetAssetItem, file as AssetFileItem)">{{ $t('common.title.edit') }}</Button>
            <Button type="link" size="small" danger @click="handleDeleteFile(file as AssetFileItem)">{{ $t('dataset.list.delete') }}</Button>
          </Space>
        </div>
      </div>

      <div style="display: flex; gap: 4px;">
        <Button size="small" @click="openAssetEdit(asset as DatasetAssetItem)">{{ $t('dataset.list.editAsset') }}</Button>
        <Button size="small" @click="openFileRegister(asset as DatasetAssetItem)">{{ $t('dataset.list.registerFile') }}</Button>
        <Button size="small" danger @click="handleDeleteAsset(asset as DatasetAssetItem)">{{ $t('dataset.list.delete') }}{{ $t('dataset.list.asset') }}</Button>
      </div>
    </div>

    <!-- Asset Modal -->
    <Modal
      v-model:open="assetModalVisible"
      :title="editingAsset ? $t('system.dict.edit') + $t('dataset.list.asset') : $t('system.dict.add') + $t('dataset.list.asset')"
      :confirm-loading="assetModalLoading"
      @ok="submitAsset"
    >
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <Input v-model:value="assetForm.asset_name" :placeholder="$t('dataset.list.assetName')" />
        <Select v-model:value="assetForm.asset_type" :options="assetTypeOptions" :placeholder="$t('dataset.list.assetType')" />
        <Input v-model:value="assetForm.file_format" :placeholder="$t('dataset.list.fileFormat')" />
        <Input v-model:value="assetForm.query_engine" :placeholder="$t('dataset.list.queryEngine')" />
        <label>
          <input type="checkbox" v-model="assetForm.is_query_entry" /> {{ $t('dataset.list.setAsQueryEntry') }}
        </label>
      </div>
    </Modal>

    <!-- File Modal -->
    <Modal
      v-model:open="fileModalVisible"
      :title="editingFile ? $t('dataset.list.editFile') : $t('dataset.list.registerFile')"
      :confirm-loading="fileModalLoading"
      @ok="submitFile"
    >
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <div>{{ currentAssetForFile?.asset_name || '-' }}</div>
        <Select v-model:value="fileForm.file_role" :options="FILE_ROLE_OPTIONS" :placeholder="$t('dataset.list.fileRole')" />
        <Input v-model:value="fileForm.local_path" :placeholder="$t('dataset.list.filePath')" />
        <Input v-model:value="fileForm.file_format" :placeholder="$t('dataset.list.fileFormat')" />
      </div>
    </Modal>
  </div>
</template>
