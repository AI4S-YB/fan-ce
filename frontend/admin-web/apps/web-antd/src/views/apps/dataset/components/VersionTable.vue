<script setup lang="ts">
import { ref } from 'vue';
import { Table, Tag, Space, Button, Empty, Input, Select, message } from 'ant-design-vue';
import { EditOutlined } from '@ant-design/icons-vue';
import type { DatasetVersionItem, DatasetVersionListResult } from '#/api/apps/dataset';
import { updateDatasetApi, releaseDatasetVersionApi, withdrawDatasetVersionApi } from '#/api/apps/dataset';
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
  refresh: [];
}>();

const columns = [
  { title: '', dataIndex: 'radio', key: 'radio', width: 40 },
  { title: $t('system.menu.title'), dataIndex: 'title', key: 'title', width: 200 },
  { title: $t('dataset.list.version'), dataIndex: 'version', key: 'version', width: 120 },
  { title: $t('dataset.list.lifecycleHeader'), dataIndex: 'lifecycle_state', key: 'lifecycle_state', width: 100 },
  { title: $t('dataset.list.visibility'), dataIndex: 'visibility', key: 'visibility', width: 120 },
  { title: '主版本', dataIndex: 'is_main', key: 'is_main', width: 120 },
];

// ── Inline title editing ──
const editingTitleId = ref<number | null>(null);
const editingTitleText = ref('');
const editingTitleSaving = ref(false);

function startEditTitle(v: DatasetVersionItem) { editingTitleId.value = v.id; editingTitleText.value = v.title || ''; }
async function saveTitle() {
  if (editingTitleId.value == null) return;
  editingTitleSaving.value = true;
  try { await updateDatasetApi({ id: editingTitleId.value, title: editingTitleText.value.trim() || undefined }); message.success('Updated'); editingTitleId.value = null; emit('refresh'); }
  catch (e: any) { message.error(e?.message || 'Failed'); }
  finally { editingTitleSaving.value = false; }
}

// ── Inline version name editing ──
const editingVerId = ref<number | null>(null);
const editingVerText = ref('');
const editingVerSaving = ref(false);

function startEditVer(v: DatasetVersionItem) { editingVerId.value = v.id; editingVerText.value = v.version || ''; }
async function saveVer() {
  if (editingVerId.value == null) return;
  editingVerSaving.value = true;
  try { await updateDatasetApi({ id: editingVerId.value, version: editingVerText.value.trim() || undefined }); message.success('Updated'); editingVerId.value = null; emit('refresh'); }
  catch (e: any) { message.error(e?.message || 'Failed'); }
  finally { editingVerSaving.value = false; }
}

// ── Inline visibility editing ──
const editingVisId = ref<number | null>(null);
const editingVisValue = ref('');
const editingVisSaving = ref(false);

function startEditVis(v: DatasetVersionItem) { editingVisId.value = v.id; editingVisValue.value = v.visibility || 'private'; }
async function saveVis() {
  if (editingVisId.value == null) return;
  editingVisSaving.value = true;
  try {
    if (editingVisValue.value === 'public') await releaseDatasetVersionApi({ id: editingVisId.value });
    else await withdrawDatasetVersionApi({ id: editingVisId.value });
    message.success('Updated'); editingVisId.value = null; emit('refresh');
  } catch (e: any) { message.error(e?.message || 'Failed'); }
  finally { editingVisSaving.value = false; }
}

function isActive(version: DatasetVersionItem) { return version.id === props.activeVersionId; }
function isActionLoading(prefix: string, id: number) { return props.actionLoadingKey === `${prefix}-${id}`; }
</script>

<template>
  <div>
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
          <input type="radio" :checked="isActive(record as DatasetVersionItem)" @change="emit('select', record as DatasetVersionItem)" />
        </template>
        <template v-else-if="column.key === 'title'">
          <div v-if="editingTitleId !== (record as DatasetVersionItem).id" style="display:flex;align-items:center;gap:4px;">
            <span>{{ (record as DatasetVersionItem).title || '-' }}</span>
            <Button size="small" type="text" @click="startEditTitle(record as DatasetVersionItem)"><EditOutlined style="font-size:12px;color:#1677ff;" /></Button>
          </div>
          <div v-else style="display:flex;align-items:center;gap:4px;">
            <Input v-model:value="editingTitleText" size="small" style="width:150px;" />
            <Button size="small" type="primary" :loading="editingTitleSaving" @click="saveTitle">OK</Button>
            <Button size="small" @click="editingTitleId = null">Cancel</Button>
          </div>
        </template>
        <template v-else-if="column.key === 'version'">
          <div v-if="editingVerId !== (record as DatasetVersionItem).id" style="display:flex;align-items:center;gap:4px;">
            <span>{{ (record as DatasetVersionItem).version || '-' }}</span>
            <Button size="small" type="text" @click="startEditVer(record as DatasetVersionItem)"><EditOutlined style="font-size:12px;color:#1677ff;" /></Button>
          </div>
          <div v-else style="display:flex;align-items:center;gap:4px;">
            <Input v-model:value="editingVerText" size="small" style="width:100px;" />
            <Button size="small" type="primary" :loading="editingVerSaving" @click="saveVer">OK</Button>
            <Button size="small" @click="editingVerId = null">Cancel</Button>
          </div>
        </template>
        <template v-else-if="column.key === 'lifecycle_state'">
          <Tag :color="lifecycleColor((record as DatasetVersionItem).lifecycle_state)">
            {{ (record as DatasetVersionItem).lifecycle_state || '-' }}
          </Tag>
        </template>
        <template v-else-if="column.key === 'visibility'">
          <div v-if="editingVisId !== (record as DatasetVersionItem).id" style="display:flex;align-items:center;gap:4px;">
            <Tag :color="visibilityColor((record as DatasetVersionItem).visibility)">{{ (record as DatasetVersionItem).visibility || '-' }}</Tag>
            <Button size="small" type="text" @click="startEditVis(record as DatasetVersionItem)"><EditOutlined style="font-size:12px;color:#1677ff;" /></Button>
          </div>
          <div v-else style="display:flex;align-items:center;gap:4px;">
            <Select v-model:value="editingVisValue" size="small" style="width:100px;" :options="[{label:'public',value:'public'},{label:'private',value:'private'}]" />
            <Button size="small" type="primary" :loading="editingVisSaving" @click="saveVis">OK</Button>
            <Button size="small" @click="editingVisId = null">Cancel</Button>
          </div>
        </template>
        <template v-else-if="column.key === 'is_main'">
          <Button v-if="(record as DatasetVersionItem).is_current" size="small" disabled style="color:#999;">主版本</Button>
          <Button v-else size="small" type="primary" ghost :loading="isActionLoading('activate-version', (record as DatasetVersionItem).id)" @click="emit('activate', record as DatasetVersionItem)">设为主版本</Button>
        </template>
      </template>
    </Table>
  </div>
</template>
