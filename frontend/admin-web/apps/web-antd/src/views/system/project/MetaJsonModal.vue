<script setup lang="ts">
import { ref } from 'vue';

import { Card, Spin, Tree, Empty, Tag } from 'ant-design-vue';

import { getSampleMetaJsonApi } from '#/api/apps/sample';
import { BasicModal, useModalInner } from '#/components/Modal';
import { useMessage } from '#/hooks/web/useMessage';
import { $t } from '@vben/locales';

defineOptions({ name: 'MetaJsonModal' });

const emit = defineEmits(['success', 'register']);
const { createMessage } = useMessage();

const loading = ref(false);
const metaJsonData = ref<any>(null);
const currentRow = ref<any>(null);
const selectedSample = ref<any>(null);
const treeData = ref<any[]>([]);

// 获取meta-json数据
const fetchMetaJsonData = async (projectId: number) => {
  try {
    loading.value = true;
    const data = await getSampleMetaJsonApi({
      project_id: projectId,
      page: 1,
      size: 100
    });
    metaJsonData.value = data;
    
    // 构建树形数据
    treeData.value = data.dataList?.map((item: any) => ({
      key: item.sample_id,
      title: item.sample_name,
      sample_id: item.sample_id,
      meta_json: item.meta_json,
      isLeaf: true
    })) || [];
    
    console.log('Meta JSON 数据:', data);
  } catch (error) {
    console.error('获取Meta JSON数据失败:', error);
    createMessage.error($t('system.project.metaJsonFetchFailed'));
  } finally {
    loading.value = false;
  }
};

const [registerModal, { setModalProps, closeModal }] = useModalInner(
  async (data) => {
    setModalProps({ confirmLoading: false });
    currentRow.value = data?.row;
    metaJsonData.value = null;
    selectedSample.value = null;
    treeData.value = [];
    
    if (currentRow.value?.id) {
      await fetchMetaJsonData(currentRow.value.id);
    }
  },
);

// 处理树节点选择
const handleTreeSelect = (selectedKeys: any[], _info: any) => {
  if (selectedKeys.length > 0) {
    const sampleId = selectedKeys[0];
    const sample = metaJsonData.value.dataList.find((item: any) => item.sample_id.toString() === sampleId.toString());
    selectedSample.value = sample;
  } else {
    selectedSample.value = null;
  }
};

// 解析JSON数据
const parseJsonData = (jsonString: string) => {
  if (!jsonString) return null;
  try {
    return JSON.parse(jsonString);
  } catch (error) {
    console.error('JSON解析失败:', error);
    return null;
  }
};
</script>

<template>
  <BasicModal
    v-bind="$attrs"
    show-footer
    :title="$t('system.project.sampleMetaJson')"
    :width="1200"
    :min-height="600"
    @register="registerModal"
  >
    <div v-if="loading" class="flex justify-center items-center h-64">
      <Spin size="large" />
    </div>
    
    <div v-else-if="metaJsonData" class="flex h-96">
      <!-- 左侧：样本树列表 -->
      <div class="w-1/3 border-r border-gray-200 pr-4">
        <div class="mb-4">
          <div class="text-sm text-gray-600 mb-2">
            {{ $t('system.project.projectWithId', { name: currentRow?.name, id: currentRow?.id }) }}
          </div>
          <div class="text-sm text-gray-600">
            {{ $t('system.project.totalSamples', { count: metaJsonData.total || 0 }) }}
          </div>
        </div>
        
        <div class="h-full overflow-auto">
          <Tree
            :tree-data="treeData"
            :selected-keys="selectedSample ? [selectedSample.sample_id.toString()] : []"
            @select="handleTreeSelect"
            show-line
            default-expand-all
          >
            <template #title="{ title, sample_id, meta_json }">
              <span>
                {{ title }}
                <Tag v-if="!meta_json" color="red" size="small">{{ $t('system.project.emptyLabel') }}</Tag>
              </span>
            </template>
          </Tree>
        </div>
      </div>
      
      <!-- 右侧：JSON预览器 -->
      <div class="w-2/3 pl-4">
        <div v-if="selectedSample" class="h-full">
          <div class="mb-4">
            <h3 class="text-lg font-medium">{{ $t('system.project.sample') }}: {{ selectedSample.sample_name }}</h3>
            <p class="text-sm text-gray-500">ID: {{ selectedSample.sample_id }}</p>
          </div>
          
          <div v-if="selectedSample.meta_json" class="h-full overflow-auto">
            <JsonViewer
              :value="parseJsonData(selectedSample.meta_json)"
              :copyable="{ copyText: $t('common.title.copy'), copiedText: $t('system.project.copySuccess') }"
              boxed
              sort
              expanded
              :preview-mode="false"
              :expand-depth="3"
            />
          </div>
          
          <div v-else class="h-full flex items-center justify-center">
            <Empty :description="$t('system.project.noMetaJsonData')" />
          </div>
        </div>
        
        <div v-else class="h-full flex items-center justify-center">
          <Empty :description="$t('system.project.pleaseSelectSample')" />
        </div>
      </div>
    </div>
    
    <div v-else class="text-center text-gray-500 py-8">
      {{ $t('system.project.loading') }}
    </div>
  </BasicModal>
</template>

<style lang="scss" scoped>
:deep(.ant-tree-node-content-wrapper) {
  padding: 4px 8px;
}

:deep(.ant-tree-node-content-wrapper:hover) {
  background-color: #f5f5f5;
}

:deep(.ant-tree-node-selected) {
  background-color: #e6f7ff;
}
</style> 
