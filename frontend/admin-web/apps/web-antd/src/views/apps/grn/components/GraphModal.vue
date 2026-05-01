<template>
  <GraphModal
    v-model:open="visible"
    :title="$t('grn.graph.title')"
    :file-path="filePath"
    :selected-nodes="selectedNodes"
    :show-relationship-controls="true"
    :data-loader="getGrnBatchRelationshipsApi"
    :list-data-loader="getGrnListApi"
    :build-options="buildOptions"
  />
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { $t } from '@vben/locales';
import { GraphModal } from '#/components/GraphModal';
import { getGrnListApi, getGrnBatchRelationshipsApi } from '../api';

interface Props {
  open: boolean;
  filePath?: string;
  selectedNodes?: string[];
}

interface Emits {
  (e: 'update:open', value: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = ref(false);

// 构建选项（基因调控网络可能有不同的构建选项）
const buildOptions = {
  parentKey: 'regulator',  // 调控因子
  motherKey: 'target',     // 目标基因
  enableCrossingEdges: true,
};

// 监听打开状态
watch(
  () => props.open,
  (val) => {
    visible.value = val;
  },
  { immediate: true }
);

watch(
  () => visible.value,
  (v) => emit('update:open', v)
);
</script>