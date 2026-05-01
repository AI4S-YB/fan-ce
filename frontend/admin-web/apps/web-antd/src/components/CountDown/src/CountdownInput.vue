<script lang="ts" setup>
import { useRuleFormItem } from '#/hooks/component/useFormItem';
import { useDesign } from '#/utils/vbenModle';

import CountButton from './CountButton.vue';

defineOptions({ name: 'CountDownInput', inheritAttrs: false });

const props = defineProps({
  value: { type: String },
  size: {
    type: String,
    validator: (v: string) => ['default', 'large', 'small'].includes(v),
  },
  count: { type: Number, default: 60 },
  sendCodeApi: {
    type: Function as PropType<() => Promise<any>>,
    default: null,
  },
});

const { prefixCls } = useDesign('countdown-input');
const [state] = useRuleFormItem(props);
</script>

<template>
  <a-input v-bind="$attrs" :class="prefixCls" :size="size" :value="state">
    <template #addonAfter>
      <CountButton
        :size="size"
        :count="count"
        :value="state"
        :before-start-func="sendCodeApi"
      />
    </template>
    <template
      v-for="item in Object.keys($slots).filter((k) => k !== 'addonAfter')"
      #[item]="data"
    >
      <slot :name="item" v-bind="data || {}"></slot>
    </template>
  </a-input>
</template>

<style lang="less">
@namespace: 'vben';
@prefix-cls: ~'@{namespace}-countdown-input';

.@{prefix-cls} {
  .ant-input-group-addon {
    padding-right: 0;
    background-color: transparent;
    border: none;

    button {
      font-size: 14px;
    }
  }
}
</style>
