<template>
  <Modal
    v-model:open="visible"
    :title="$t('grn.detail.title')"
    width="860px"
    :footer="null"
    @cancel="handleCancel"
  >
    <div v-if="loading" class="text-center p-4">
      <Spin size="large" />
    </div>
    
    <div v-else-if="relationshipData" class="space-y-4">
      <!-- 调控关系概览 -->
      <Card :title="$t('grn.detail.overview')" size="small">
        <Descriptions :column="2" bordered>
          <DescriptionsItem :label="$t('grn.detail.targetGene')">{{ relationshipData.target_gene }}</DescriptionsItem>
          <DescriptionsItem :label="$t('grn.detail.targetGeneName')">{{ relationshipData.target_gene_name }}</DescriptionsItem>
          <DescriptionsItem :label="$t('grn.detail.transcriptionFactor')">{{ relationshipData.tf_gene }}</DescriptionsItem>
          <DescriptionsItem :label="$t('grn.detail.tfName')">{{ relationshipData.tf_name }}</DescriptionsItem>
          <DescriptionsItem :label="$t('grn.list.tfFamily')">{{ relationshipData.tf_family }}</DescriptionsItem>
          <DescriptionsItem :label="$t('grn.list.regulationStrength')">{{ relationshipData.peak_fold_change }}</DescriptionsItem>
          <DescriptionsItem :label="$t('grn.list.confidence')">{{ relationshipData.c_score }}</DescriptionsItem>
          <DescriptionsItem :label="$t('grn.list.weight')">{{ relationshipData.weight }}</DescriptionsItem>
        </Descriptions>
      </Card>

      <!-- 靶基因信息 -->
      <Card :title="$t('grn.detail.targetGene')" size="small">
        <Descriptions :column="1" bordered>
          <DescriptionsItem :label="$t('grn.detail.geneName')">{{ relationshipData.node1?.name }}</DescriptionsItem>
          <DescriptionsItem 
            v-if="relationshipData.target_gene_description" 
            :label="$t('grn.detail.geneName')"
          >
            <div class="max-h-32 overflow-y-auto">
              <span class="text-sm">{{ relationshipData.target_gene_description }}</span>
            </div>
          </DescriptionsItem>
          <DescriptionsItem 
            v-for="(value, key) in targetGeneAttributes" 
            :key="key" 
            :label="formatLabel(key)"
          >
            <span>{{ formatValue(value) }}</span>
          </DescriptionsItem>
        </Descriptions>
      </Card>

      <!-- 转录因子信息 -->
      <Card :title="$t('grn.detail.transcriptionFactorLabel')" size="small">
        <Descriptions :column="1" bordered>
          <DescriptionsItem :label="$t('grn.detail.tfName')">{{ relationshipData.node2?.name }}</DescriptionsItem>
          <DescriptionsItem 
            v-for="(value, key) in tfAttributes" 
            :key="key" 
            :label="formatLabel(key)"
          >
            <span>{{ formatValue(value) }}</span>
          </DescriptionsItem>
        </Descriptions>
      </Card>

      <!-- 调控关系属性 -->
      <Card :title="$t('grn.detail.edgeInfo')" size="small">
        <Descriptions :column="1" bordered>
          <DescriptionsItem :label="$t('grn.detail.createdAt')">{{ relationshipData.created_at }}</DescriptionsItem>
          <DescriptionsItem 
            v-for="(value, key) in edgeAttributes" 
            :key="key" 
            :label="formatLabel(key)"
          >
            <span>{{ formatValue(value) }}</span>
          </DescriptionsItem>
        </Descriptions>
      </Card>
    </div>

    <div v-else class="text-center p-4 text-gray-500">
      {{ $t('grn.detail.noData') }}
    </div>
  </Modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { $t } from '@vben/locales';
import {
  Card, 
  Descriptions, 
  DescriptionsItem, 
  Modal, 
  Spin
} from 'ant-design-vue';
import type { GrnItem } from '../types';

interface Props {
  open: boolean;
  relationshipData?: GrnItem & Record<string, any>; // 包含展平后的数据
  filePath?: string;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = ref(false);
const loading = ref(false);

// 监听 props 变化
watch(
  () => props.open,
  (newVal) => {
    visible.value = newVal;
  },
  { immediate: true }
);

watch(
  () => visible.value,
  (newVal) => {
    emit('update:open', newVal);
  }
);

// 关闭弹窗
const handleCancel = () => {
  visible.value = false;
};

// 衍生数据 - 靶基因属性
const targetGeneAttributes = computed<Record<string, any>>(() => {
  const attrs = (props.relationshipData?.node1?.attributes || {}) as Record<string, any>;
  const exclude = new Set(['target_gene_name', 'target_gene_description']);
  const result: Record<string, any> = {};
  Object.keys(attrs).forEach((key) => {
    if (!exclude.has(key)) result[key] = attrs[key];
  });
  return result;
});

// 衍生数据 - 转录因子属性
const tfAttributes = computed<Record<string, any>>(() => {
  const attrs = (props.relationshipData?.node2?.attributes || {}) as Record<string, any>;
  const exclude = new Set(['tf_name', 'tf_family']);
  const result: Record<string, any> = {};
  Object.keys(attrs).forEach((key) => {
    if (!exclude.has(key)) result[key] = attrs[key];
  });
  return result;
});

// 衍生数据 - 边属性
const edgeAttributes = computed<Record<string, any>>(() => {
  const attrs = (props.relationshipData?.edge_attributes || {}) as Record<string, any>;
  const exclude = new Set(['peak_fold-change', 'c_score', 'weight', 'created_at']);
  const result: Record<string, any> = {};
  Object.keys(attrs).forEach((key) => {
    if (!exclude.has(key)) result[key] = attrs[key];
  });
  return result;
});

// 格式化标签
const formatLabel = (key: string) => {
  const labelMap: Record<string, string> = {
    gene_symbol: $t('grn.detail.geneSymbol'),
    gene_name: $t('grn.detail.geneName'),
    gene_type: $t('grn.detail.geneType'),
    chromosome: $t('grn.detail.chromosome'),
    start_position: $t('grn.detail.startPosition'),
    end_position: $t('grn.detail.endPosition'),
    expression_level: $t('grn.detail.expressionLevel'),
    regulation_type: $t('grn.detail.regulationType'),
    target_genes: $t('grn.detail.targetGenes'),
    transcription_factor: $t('grn.detail.transcriptionFactorLabel'),
    pathway: $t('grn.detail.pathway'),
    function: $t('grn.detail.function'),
    created_at: $t('grn.detail.createdAt'),
    degree: $t('grn.detail.degree'),
  };
  
  return labelMap[key] || key;
};

// 格式化值
const formatValue = (value: any) => {
  if (value === null || value === undefined) {
    return '-';
  }
  if (typeof value === 'boolean') {
    return value ? $t('grn.relationship.yes') : $t('grn.relationship.no');
  }
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
};

// 判断是否为长文本
const isLongText = (value: any) => {
  if (typeof value !== 'string') return false;
  return value.length > 100 || value.includes('\n');
};
</script>

<style scoped>
.space-y-4 > * + * {
  margin-top: 1rem;
}
</style>