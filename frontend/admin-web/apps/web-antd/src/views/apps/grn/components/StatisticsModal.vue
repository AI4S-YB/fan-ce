<template>
  <Modal v-model:open="visible" :title="$t('grn.statistics.title')" width="640px" @cancel="handleCancel" :footer="null">
    <div v-if="data" class="space-y-4">
      <Descriptions bordered :column="2">
        <DescriptionsItem :label="$t('grn.statistics.geneNodeCount')">{{ data.node_count }}</DescriptionsItem>
        <DescriptionsItem :label="$t('grn.statistics.regulationEdgeCount')">{{ data.edge_count }}</DescriptionsItem>
        <DescriptionsItem :label="$t('grn.statistics.isConnected')">{{ data.is_connected ? $t('grn.relationship.yes') : $t('grn.relationship.no') }}</DescriptionsItem>
        <DescriptionsItem :label="$t('grn.statistics.connectedComponents')">{{ data.connected_components }}</DescriptionsItem>
        <DescriptionsItem :label="$t('grn.statistics.averageDegree')">{{ data.average_degree }}</DescriptionsItem>
        <DescriptionsItem :label="$t('grn.statistics.maxDegree')">{{ data.max_degree }}</DescriptionsItem>
        <DescriptionsItem :label="$t('grn.statistics.minDegree')">{{ data.min_degree }}</DescriptionsItem>
      </Descriptions>

      <Card :title="$t('grn.statistics.networkInfo')" size="small">
        <Descriptions bordered :column="1">
          <DescriptionsItem :label="$t('grn.statistics.dataSource')">{{ data.metadata?.source_file }}</DescriptionsItem>
          <DescriptionsItem :label="$t('system.menu.createTime')">{{ data.metadata?.created_at }}</DescriptionsItem>
          <DescriptionsItem :label="$t('grn.statistics.updatedAt')">{{ data.metadata?.updated_at }}</DescriptionsItem>
        </Descriptions>
      </Card>
    </div>
    <div v-else class="text-center text-gray-500">{{ $t('grn.statistics.noData') }}</div>
  </Modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { $t } from '@vben/locales';
import { Modal, Descriptions, DescriptionsItem, Card, message } from 'ant-design-vue';
import { getGrnStatisticsApi } from '../api';

interface Props {
  open: boolean;
  filePath?: string;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = ref(false);
const data = ref<any>(null);

watch(
  () => props.open,
  async (val) => {
    visible.value = val;
    if (val && props.filePath) {
      await fetchData();
    }
  },
  { immediate: true },
);

watch(
  () => visible.value,
  (val) => {
    emit('update:open', val);
  },
);

const fetchData = async () => {
  if (!props.filePath) return;
  
  try {
    const response = await getGrnStatisticsApi({
      file_path: props.filePath,
    });
    // 兼容后端返回包裹在 data 中的结构
    data.value = (response as any)?.data ?? (response as any);
  } catch (error) {
    console.error('获取调控网络统计失败:', error);
    message.error($t('grn.statistics.fetchError'));
  }
};

const handleCancel = () => {
  visible.value = false;
  data.value = null;
};
</script>

<style scoped>
.space-y-4 > * + * {
  margin-top: 1rem;
}
</style>