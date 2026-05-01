<script setup lang="ts">
import type { GermplasmDetail } from '../types';

import { computed, ref, watch } from 'vue';

import {
  Card,
  Descriptions,
  DescriptionsItem,
  Modal,
  Spin,
  Tag,
} from 'ant-design-vue';

import { $t } from '@vben/locales';
import { getGermplasmDetailApi } from '../api';

interface Props {
  open: boolean;
  germplasmId?: string;
  taxonomyTaxId?: number;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = ref(false);
const loading = ref(false);
const detailData = ref<GermplasmDetail | null>(null);
const currentId = ref<string | undefined>(undefined);

// 监听 props 变化
watch(
  () => props.open,
  (newVal) => {
    visible.value = newVal;
    if (newVal && props.germplasmId && props.taxonomyTaxId) {
      currentId.value = props.germplasmId;
      fetchDetail();
    }
  },
  { immediate: true },
);

watch(
  () => visible.value,
  (newVal) => {
    emit('update:open', newVal);
  },
);

// 获取详情数据
const fetchDetail = async () => {
  if (!currentId.value || !props.taxonomyTaxId) return;

  loading.value = true;
  try {
    const response = await getGermplasmDetailApi(
      currentId.value,
      props.taxonomyTaxId,
    );
    // 兼容后端返回包裹在 data 中的结构
    detailData.value = (response as any)?.data ?? (response as any);
  } catch {
    detailData.value = null;
  } finally {
    loading.value = false;
  }
};

// 关闭弹窗
const handleCancel = () => {
  visible.value = false;
  detailData.value = null;
};

// 衍生数据
const createdAt = computed(() => detailData.value?.audit?.created_at);
const displayedAttributes = computed<Record<string, any>>(() => {
  const attrs = (detailData.value?.attributes || {}) as Record<string, any>;
  const exclude = new Set(['created_at', 'degree']);
  const result: Record<string, any> = {};
  Object.keys(attrs).forEach((key) => {
    if (!exclude.has(key)) result[key] = attrs[key];
  });
  return result;
});
const dynamicAttributeItems = computed(() => {
  const attrs = displayedAttributes.value;
  const schemaItems = [...(detailData.value?.field_schema || [])]
    .filter((item) => item.is_dynamic)
    .sort((left, right) => left.display_order - right.display_order);
  const mapped = schemaItems
    .map((field) => ({
      key: field.field_label || field.source_header || field.field_key,
      value: attrs[field.field_label || field.source_header || field.field_key],
    }))
    .filter((item) => item.value !== undefined);
  const usedKeys = new Set(mapped.map((item) => item.key));
  const extraItems = Object.entries(attrs)
    .filter(([key]) => !usedKeys.has(key))
    .map(([key, value]) => ({
      key,
      value,
    }));
  return [...mapped, ...extraItems];
});

// 格式化值
const formatValue = (value: any) => {
  if (value === null || value === undefined) {
    return '-';
  }
  if (typeof value === 'boolean') {
    return value ? $t('germplasm.detail.yes') : $t('germplasm.detail.no');
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

<template>
  <Modal
    v-model:open="visible"
    :title="$t('germplasm.detail.title')"
    width="860px"
    :footer="null"
    @cancel="handleCancel"
  >
    <div v-if="loading" class="p-4 text-center">
      <Spin size="large" />
    </div>

    <div v-else-if="detailData" class="space-y-4">
      <!-- 概览 -->
      <Card :title="$t('germplasm.detail.overview')" size="small">
        <Descriptions :column="2" bordered>
          <DescriptionsItem label="ID">{{ detailData.id }}</DescriptionsItem>
          <DescriptionsItem :label="$t('germplasm.detail.displayName')">
            {{ detailData.display_name || '-' }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('germplasm.detail.englishName')">
            {{ detailData.english_name || '-' }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('germplasm.detail.species')">
            {{ detailData.taxonomy?.scientific_name || '-' }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('germplasm.detail.fatherAccession')">
            {{ detailData.father_accession || '-' }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('germplasm.detail.motherAccession')">
            {{ detailData.mother_accession || '-' }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('germplasm.detail.parentCount')">
            {{ detailData.lineage_summary?.parent_count || 0 }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('germplasm.detail.childCount')">
            {{ detailData.lineage_summary?.child_count || 0 }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('germplasm.detail.importBatch')">
            {{ detailData.audit?.batch_code || '-' }}
          </DescriptionsItem>
          <DescriptionsItem v-if="createdAt" :label="$t('germplasm.detail.createdAt')">
            {{ createdAt }}
          </DescriptionsItem>
        </Descriptions>
      </Card>

      <!-- 谱系关系 -->
      <Card
        v-if="detailData.lineage_summary?.parents?.length"
        :title="$t('germplasm.detail.parentInfo')"
        size="small"
      >
        <div class="flex flex-wrap gap-2">
          <Tag
            v-for="parent in detailData.lineage_summary.parents"
            :key="`${parent.parent_role}-${parent.parent_accession}`"
            color="blue"
          >
            {{ parent.parent_role === 'father' ? $t('germplasm.detail.father') : $t('germplasm.detail.mother') }} /
            {{ parent.parent_accession }}
          </Tag>
        </div>
      </Card>

      <!-- 动态属性 -->
      <Card
        v-if="dynamicAttributeItems.length > 0"
        :title="$t('germplasm.detail.dynamicFields')"
        size="small"
      >
        <Descriptions :column="1" bordered>
          <DescriptionsItem
            v-for="item in dynamicAttributeItems"
            :key="item.key"
            :label="item.key"
          >
            <div v-if="isLongText(item.value)" class="max-h-40 overflow-y-auto">
              <pre class="whitespace-pre-wrap text-sm">{{ item.value }}</pre>
            </div>
            <span v-else>{{ formatValue(item.value) }}</span>
          </DescriptionsItem>
        </Descriptions>
      </Card>
    </div>

    <div v-else class="p-4 text-center text-gray-500">{{ $t('germplasm.detail.noData') }}</div>
  </Modal>
</template>

<style scoped>
.space-y-4 > * + * {
  margin-top: 1rem;
}
</style>
