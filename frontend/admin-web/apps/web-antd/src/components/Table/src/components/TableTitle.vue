<script lang="ts" setup>
import type { PropType } from 'vue';

import { computed } from 'vue';

import { BasicTitle } from '#/components/Basic';
import { isFunction } from '#/utils/is';
import { useDesign } from '#/utils/vbenModle';

defineOptions({ name: 'BasicTableTitle' });

const props = defineProps({
  title: {
    type: [Function, String] as PropType<((data: any) => string) | string>,
  },
  getSelectRows: {
    type: Function as PropType<() => any[]>,
  },
  helpMessage: {
    type: [String, Array] as PropType<string | string[]>,
  },
});

const { prefixCls } = useDesign('basic-table-title');

const getTitle = computed(() => {
  const { title, getSelectRows = () => {} } = props;
  let tit = title;

  if (isFunction(title)) {
    tit = title({
      selectRows: getSelectRows(),
    });
  }
  return tit;
});
</script>

<template>
  <BasicTitle v-if="getTitle" :class="prefixCls" :help-message="helpMessage">
    {{ getTitle }}
  </BasicTitle>
</template>

<style lang="less">
@namespace: 'vben';
@prefix-cls: ~'@{namespace}-basic-table-title';

.@{prefix-cls} {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
