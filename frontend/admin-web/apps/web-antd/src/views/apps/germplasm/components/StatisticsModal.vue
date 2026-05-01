<template>
  <Modal v-model:open="visible" :title="$t('germplasm.statistics.title')" width="640px" @cancel="handleCancel" :footer="null">
    <div v-if="data" class="space-y-4">
      <Descriptions bordered :column="2">
        <DescriptionsItem :label="$t('germplasm.statistics.nodeCount')">{{ data.node_count }}</DescriptionsItem>
        <DescriptionsItem :label="$t('germplasm.statistics.edgeCount')">{{ data.edge_count }}</DescriptionsItem>
        <DescriptionsItem :label="$t('germplasm.statistics.registeredGermplasm')">{{ data.germplasm_record_count }}</DescriptionsItem>
        <DescriptionsItem :label="$t('germplasm.statistics.isConnected')">{{ data.is_connected ? $t('germplasm.detail.yes') : $t('germplasm.detail.no') }}</DescriptionsItem>
        <DescriptionsItem :label="$t('germplasm.statistics.connectedComponents')">{{ data.connected_components }}</DescriptionsItem>
        <DescriptionsItem :label="$t('germplasm.statistics.averageDegree')">{{ data.average_degree }}</DescriptionsItem>
        <DescriptionsItem :label="$t('germplasm.statistics.maxDegree')">{{ data.max_degree }}</DescriptionsItem>
        <DescriptionsItem :label="$t('germplasm.statistics.minDegree')">{{ data.min_degree }}</DescriptionsItem>
      </Descriptions>

      <Card :title="$t('germplasm.statistics.edgeType')" size="small">
        <Descriptions bordered :column="3">
          <DescriptionsItem :label="$t('germplasm.statistics.fatherEdge')">{{ data.role_counts?.father ?? 0 }}</DescriptionsItem>
          <DescriptionsItem :label="$t('germplasm.statistics.motherEdge')">{{ data.role_counts?.mother ?? 0 }}</DescriptionsItem>
          <DescriptionsItem :label="$t('germplasm.statistics.other')">{{ data.role_counts?.other ?? 0 }}</DescriptionsItem>
        </Descriptions>
      </Card>

      <Card :title="$t('germplasm.statistics.highConnectionNodes')" size="small">
        <div v-if="data.top_hubs?.length" class="hub-list">
          <div v-for="item in data.top_hubs" :key="item.accession_id" class="hub-item">
            <span>{{ item.accession_id }}<span v-if="item.display_name"> / {{ item.display_name }}</span></span>
            <span class="hub-degree">degree {{ item.degree }}</span>
          </div>
        </div>
        <div v-else class="text-gray-500">{{ $t('germplasm.statistics.noHighConnectionNodes') }}</div>
      </Card>

      <Card :title="$t('germplasm.statistics.metadata')" size="small">
        <Descriptions bordered :column="1">
          <DescriptionsItem :label="$t('germplasm.statistics.dataSource')">{{ data.metadata?.source_model }}</DescriptionsItem>
          <DescriptionsItem :label="$t('germplasm.statistics.species')">{{ data.metadata?.taxonomy?.scientific_name || '-' }}</DescriptionsItem>
          <DescriptionsItem :label="$t('germplasm.statistics.batch')">{{ data.metadata?.batch?.batch_code || '-' }}</DescriptionsItem>
          <DescriptionsItem :label="$t('germplasm.statistics.generatedAt')">{{ data.metadata?.generated_at }}</DescriptionsItem>
        </Descriptions>
      </Card>
    </div>
    <div v-else class="text-center text-gray-500">{{ $t('germplasm.statistics.noData') }}</div>
  </Modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { Modal, Descriptions, DescriptionsItem, Card, message } from 'ant-design-vue';
import { $t } from '@vben/locales';
import { getGermplasmStatisticsApi } from '../api';
import type { GermplasmStatisticsResult } from '../types';

interface Props {
  open: boolean;
  taxonomyTaxId?: number;
  batchId?: number;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = ref(false);
const data = ref<GermplasmStatisticsResult | null>(null);

watch(
  () => props.open,
  async (val) => {
    visible.value = val;
    if (val && props.taxonomyTaxId) {
      await fetchData();
    }
  },
  { immediate: true },
);

watch(
  () => visible.value,
  (v) => emit('update:open', v),
);

async function fetchData() {
  try {
    const res: any = await getGermplasmStatisticsApi({
      taxonomy_tax_id: props.taxonomyTaxId!,
      batch_id: props.batchId,
      status: 'active',
    });
    data.value = res?.data ?? res;
  } catch (e) {
    message.error($t('germplasm.statistics.fetchError'));
  }
}

function handleCancel() {
  visible.value = false;
}
</script>

<style scoped>
.hub-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hub-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  background: #f8fbff;
}

.hub-degree {
  color: #1677ff;
  font-weight: 600;
}
</style>

