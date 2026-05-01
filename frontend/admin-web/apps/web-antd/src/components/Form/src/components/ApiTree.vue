<script lang="ts" setup>
import type { TreeProps } from 'ant-design-vue';
import type { DataNode } from 'ant-design-vue/es/tree';

import type { AnyFunction, Recordable } from '#/utils/types';

import { computed, onMounted, ref, unref, useAttrs, watch } from 'vue';

import { Tree } from 'ant-design-vue';
import { get } from 'lodash-es';

import { useRuleFormItem } from '#/hooks/component/useFormItem';
import { isArray, isFunction } from '#/utils/is';
import { propTypes } from '#/utils/propTypes';
import { handleTree as handleTreeFn } from '#/utils/tree';

defineOptions({ name: 'ApiTree' });

const props = defineProps({
  api: {
    type: Function as PropType<
      (arg?: Recordable<any>) => Promise<Recordable<any>>
    >,
  },
  params: { type: Object },
  immediate: propTypes.bool.def(true),
  resultField: propTypes.string.def(''),
  afterFetch: { type: Function as PropType<AnyFunction> },
  handleTree: propTypes.string.def(''),
  alwaysLoad: propTypes.bool.def(true),
  value: {
    type: Array as PropType<TreeProps['selectedKeys']>,
  },
});
const emit = defineEmits(['options-change', 'change', 'update:value']);
const attrs = useAttrs();
const treeData = ref<DataNode[]>([]);
const isFirstLoaded = ref<boolean>(false);
const loading = ref(false);
const emitData = ref<any[]>([]);

const [state] = useRuleFormItem(props, 'value', 'change', emitData);

const getAttrs = computed(() => {
  return {
    ...(props.api ? { treeData: unref(treeData) } : {}),
    ...attrs,
  };
});

watch(
  () => state.value,
  (v) => {
    emit('update:value', v);
  },
);

watch(
  () => props.params,
  () => {
    !unref(isFirstLoaded) && fetch();
  },
  { deep: true },
);

watch(
  () => props.immediate,
  (v) => {
    v && !isFirstLoaded.value && fetch();
  },
);

onMounted(() => {
  props.immediate && fetch();
});

async function fetch() {
  const { api, afterFetch } = props;
  if (!api || !isFunction(api)) return;
  loading.value = true;
  treeData.value = [];
  let result;
  try {
    result = await api(props.params);
  } catch (error) {
    console.error(error);
  }
  if (afterFetch && isFunction(afterFetch)) result = afterFetch(result);

  loading.value = false;
  if (!result) return;
  if (props.handleTree) result = handleTreeFn(result, props.handleTree);

  if (!isArray(result)) result = get(result, props.resultField);

  treeData.value = (result as (Recordable & { key: number | string })[]) || [];
  isFirstLoaded.value = true;
  emit('options-change', treeData.value);
}
</script>

<template>
  <Tree v-bind="getAttrs" v-model:selected-keys="state">
    <template v-for="item in Object.keys($slots)" #[item]="data">
      <slot :name="item" v-bind="data || {}"></slot>
    </template>
  </Tree>
</template>
