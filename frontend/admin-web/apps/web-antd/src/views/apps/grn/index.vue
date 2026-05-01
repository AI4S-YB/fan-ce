<template>
  <Page auto-content-height>
    <Grid :table-title="$t('grn.list.tableTitle')" :table-title-help="$t('grn.list.tableTitleHelp')">
      <template #toolbar-tools>
        <Button type="default" class="mr-2" :disabled="!canViewStatistics" @click="openStatistics">
          {{ $t('grn.list.viewStats') }}
        </Button>
        <Button type="primary" danger :disabled="!canViewRelationship" @click="openRelationship">
          {{ $t('grn.list.viewRelation') }}
        </Button>
        <Button type="primary" class="ml-2" :disabled="!canViewKnowledgeGraph" @click="openGraphView">
          {{ $t('grn.list.viewLineage') }} ({{ selectedRelationships.length }})
        </Button>
      </template>
      <template #action="{ row }">
        <TableAction
          type="color:red"
          :outside="true"
          :actions="[
            {
              icon: 'proicons:info-square',
              danger: false,
              label: $t('platform.api.detail'),
              auth: 'app:grn:list',
              size: 'small',
              onClick: handleAction.bind(null, 'detail', row),
            },
          ]"
        />
      </template>
    </Grid>

    <!-- 详情弹窗 -->
    <DetailModal
      v-model:open="detailModalVisible"
      :relationship-data="selectedRelationshipData"
      :file-path="currentFilePath"
    />
    <RelationshipModal
      v-model:open="relationshipModalVisible"
      :relationship1="selectedRelationships[0]"
      :relationship2="selectedRelationships[1]"
      :file-path="currentFilePath"
    />
    <StatisticsModal
      v-model:open="statisticsModalVisible"
      :file-path="currentFilePath"
    />
    <GraphModal
      v-model:open="graphModalVisible"
      :file-path="currentFilePath"
      :selected-nodes="selectedGenes"
    />
  </Page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue';
import { $t } from '@vben/locales';
import type { VxeGridListeners } from '#/adapter/vxe-table';

import { Page } from '@vben/common-ui';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { useModal } from '#/components/Modal';
import { TableAction } from '#/components/Table';
import { Button, message } from 'ant-design-vue';

import DetailModal from './components/DetailModal.vue';
import RelationshipModal from './components/RelationshipModal.vue';
import StatisticsModal from './components/StatisticsModal.vue';
import GraphModal from './components/GraphModal.vue';
import { gridOptions, formOptions } from './data';
import type { GrnItem } from './types';

// 详情弹窗
const detailModalVisible = ref(false);
const selectedRelationshipData = ref<(GrnItem & Record<string, any>) | null>(null);

// 选择与按钮控制
const relationshipModalVisible = ref(false);
const statisticsModalVisible = ref(false);
const graphModalVisible = ref(false);
const selectedNodes = ref<string[]>([]);  // 存储选中调控关系的ID
const selectedRelationships = ref<(GrnItem & Record<string, any>)[]>([]);  // 存储选中的调控关系数据
const selectedGenes = ref<string[]>([]);  // 存储选中的基因ID用于知识图谱
const currentFilePath = ref('');

// 多选联动：支持多选调控关系用于知识图谱，关联查询仍限制2个
async function onCheckboxChange() {
  const records = gridApi.grid.getCheckboxRecords() as (GrnItem & Record<string, any>)[];

  // 为知识图谱功能，允许选择更多调控关系，但设置合理上限
  if (records.length > 50) {
    message.warning($t('grn.list.maxSelectionWarning'));
    const toUncheck = records.slice(50);
    toUncheck.forEach((row) => gridApi.grid.setCheckboxRow(row, false));
    await nextTick();
  }

  const updated = gridApi.grid.getCheckboxRecords() as (GrnItem & Record<string, any>)[];
  selectedNodes.value = updated.map((r) => r.id || '');
  selectedRelationships.value = updated;

  // 提取所有相关的基因ID（target_gene 和 tf_gene）用于知识图谱
  const geneSet = new Set<string>();
  updated.forEach((relationship) => {
    if (relationship.target_gene) geneSet.add(relationship.target_gene);
    if (relationship.tf_gene) geneSet.add(relationship.tf_gene);
  });
  selectedGenes.value = Array.from(geneSet);

  console.log('selectedNodes updated:', selectedNodes.value, 'length:', selectedNodes.value.length);
  console.log('selectedRelationships updated:', selectedRelationships.value.length);
  console.log('selectedGenes for graph:', selectedGenes.value, 'length:', selectedGenes.value.length);
}

// Grid配置（在初始化时就注册事件，避免后续赋值不生效）
const gridEvents: VxeGridListeners<GrnItem & Record<string, any>> = {
  checkboxChange: onCheckboxChange,
  checkboxAll: onCheckboxChange, // 全选/取消全选时也要更新状态
};

const [Grid, gridApi] = useVbenVxeGrid({
  gridEvents,
  gridOptions: gridOptions(null), // 先传null，组件挂载后会更新
  formOptions: formOptions((filePath: string) => {
    currentFilePath.value = filePath;
    console.log('currentFilePath updated via onChange:', filePath);
  }),
});

// 组件挂载后，更新gridOptions以传递gridApi
onMounted(() => {
  // 重新设置gridOptions，这次传入gridApi，以便在查询完成后自动更新动态列
  gridApi.setGridOptions(gridOptions(gridApi));
});

// 处理操作
const handleAction = async (actionType: string, row: GrnItem & Record<string, any>) => {
  switch (actionType) {
    case 'detail': {
      selectedRelationshipData.value = row;
      detailModalVisible.value = true;
      break;
    }
  }
};

// （已在初始化时通过 gridEvents 注册 onCheckboxChange）

const canViewStatistics = computed(() => {
  const result = !!currentFilePath.value;
  console.log('canViewStatistics:', result, 'currentFilePath:', currentFilePath.value);
  return result;
});

const canViewRelationship = computed(() => {
  const result = selectedRelationships.value.length === 2 && !!currentFilePath.value;
  console.log('canViewRelationship:', result, 'selectedRelationships.length:', selectedRelationships.value.length, 'currentFilePath:', currentFilePath.value);
  return result;
});

const canViewKnowledgeGraph = computed(() => {
  const result = selectedRelationships.value.length >= 1 && !!currentFilePath.value;
  return result;
});
function openRelationship() {
  if (!canViewRelationship.value) return;
  relationshipModalVisible.value = true;
}

function openStatistics() {
  if (!canViewStatistics.value) return;
  statisticsModalVisible.value = true;
}

function openGraphView() {
  if (!canViewKnowledgeGraph.value) {
    message.warning($t('grn.list.pleaseSelectRelationship'));
    return;
  }
  graphModalVisible.value = true;
}
</script>

<style scoped>
/* 移除行点击相关样式 */
</style>
