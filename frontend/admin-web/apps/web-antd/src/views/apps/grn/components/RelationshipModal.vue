<template>
  <Modal v-model:open="visible" :title="$t('grn.relationship.comparisonTitle')" width="800px" @cancel="handleCancel" :footer="null">
    <div v-if="props.relationship1 && props.relationship2" class="space-y-4">
      <!-- 对比概览 -->
      <Card :title="$t('grn.relationship.comparisonOverview')" size="small">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <h4 class="font-medium mb-2">{{ $t('grn.relationship.relationshipN', { n: 1 }) }}</h4>
            <Descriptions bordered :column="1" size="small">
              <DescriptionsItem :label="$t('grn.list.targetGene')">{{ props.relationship1.target_gene }}</DescriptionsItem>
              <DescriptionsItem :label="$t('grn.list.transcriptionFactor')">{{ props.relationship1.tf_gene }}</DescriptionsItem>
              <DescriptionsItem :label="$t('grn.list.tfFamily')">{{ props.relationship1.tf_family }}</DescriptionsItem>
              <DescriptionsItem :label="$t('grn.list.regulationStrength')">{{ props.relationship1.peak_fold_change }}</DescriptionsItem>
              <DescriptionsItem :label="$t('grn.list.confidence')">{{ props.relationship1.c_score }}</DescriptionsItem>
            </Descriptions>
          </div>
          <div>
            <h4 class="font-medium mb-2">{{ $t('grn.relationship.relationshipN', { n: 2 }) }}</h4>
            <Descriptions bordered :column="1" size="small">
              <DescriptionsItem :label="$t('grn.list.targetGene')">{{ props.relationship2.target_gene }}</DescriptionsItem>
              <DescriptionsItem :label="$t('grn.list.transcriptionFactor')">{{ props.relationship2.tf_gene }}</DescriptionsItem>
              <DescriptionsItem :label="$t('grn.list.tfFamily')">{{ props.relationship2.tf_family }}</DescriptionsItem>
              <DescriptionsItem :label="$t('grn.list.regulationStrength')">{{ props.relationship2.peak_fold_change }}</DescriptionsItem>
              <DescriptionsItem :label="$t('grn.list.confidence')">{{ props.relationship2.c_score }}</DescriptionsItem>
            </Descriptions>
          </div>
        </div>
      </Card>

      <!-- 共同基因分析 -->
      <Card :title="$t('grn.relationship.commonGeneAnalysis')" size="small">
        <Descriptions bordered :column="2">
          <DescriptionsItem :label="$t('grn.relationship.commonTargetGene')">
            {{ commonTargetGenes.length > 0 ? commonTargetGenes.join(', ') : $t('grn.relationship.none') }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('grn.relationship.commonTranscriptionFactor')">
            {{ commonTFs.length > 0 ? commonTFs.join(', ') : $t('grn.relationship.none') }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('grn.relationship.sameTfFamily')">
            {{ props.relationship1.tf_family === props.relationship2.tf_family ? $t('grn.relationship.yes') : $t('grn.relationship.no') }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('grn.relationship.strengthComparison')">
            {{ compareStrength }}
          </DescriptionsItem>
        </Descriptions>
      </Card>
    </div>
    <div v-else class="text-center text-gray-500">{{ $t('grn.relationship.pleaseSelectTwo') }}</div>
  </Modal>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { $t } from '@vben/locales';
import { Modal, Descriptions, DescriptionsItem, Card } from 'ant-design-vue';
import type { GrnItem } from '../types';

interface Props {
  open: boolean;
  relationship1?: GrnItem & Record<string, any>;
  relationship2?: GrnItem & Record<string, any>;
  filePath?: string;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = ref(false);

watch(
  () => props.open,
  (val) => {
    visible.value = val;
  },
  { immediate: true },
);

watch(
  () => visible.value,
  (val) => {
    emit('update:open', val);
  },
);

// 共同靶基因
const commonTargetGenes = computed(() => {
  if (!props.relationship1 || !props.relationship2) return [];
  const genes1 = [props.relationship1.target_gene];
  const genes2 = [props.relationship2.target_gene];
  return genes1.filter(gene => genes2.includes(gene));
});

// 共同转录因子
const commonTFs = computed(() => {
  if (!props.relationship1 || !props.relationship2) return [];
  const tfs1 = [props.relationship1.tf_gene];
  const tfs2 = [props.relationship2.tf_gene];
  return tfs1.filter(tf => tfs2.includes(tf));
});

// 调控强度比较
const compareStrength = computed(() => {
  if (!props.relationship1 || !props.relationship2) return '';
  const strength1 = parseFloat(props.relationship1.peak_fold_change || '0');
  const strength2 = parseFloat(props.relationship2.peak_fold_change || '0');
  
  if (strength1 > strength2) {
    return $t('grn.relationship.stronger1', { val1: strength1, val2: strength2 });
  } else if (strength1 < strength2) {
    return $t('grn.relationship.stronger2', { val1: strength1, val2: strength2 });
  } else {
    return $t('grn.relationship.equalStrength', { val: strength1 });
  }
});

const handleCancel = () => {
  visible.value = false;
};
</script>

<style scoped>
.space-y-4 > * + * {
  margin-top: 1rem;
}
</style>