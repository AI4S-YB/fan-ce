<script lang="ts" setup>
import { computed, ref, unref, watchEffect } from 'vue';

import { Button } from 'ant-design-vue';

import { $t as t } from '#/locales';
import { isFunction } from '#/utils/is';

import { useCountdown } from './useCountdown';

defineOptions({ name: 'CountButton' });

const props = defineProps({
  value: { type: [Object, Number, String, Array] },
  count: { type: Number, default: 60 },
  beforeStartFunc: {
    type: Function as PropType<() => Promise<any>>,
    default: null,
  },
});

const loading = ref(false);

const { currentCount, isStart, start, reset } = useCountdown(props.count);

const getButtonText = computed(() => {
  return unref(isStart)
    ? t('component.countdown.sendText', [unref(currentCount)])
    : t('component.countdown.normalText');
});

watchEffect(() => {
  props.value === undefined && reset();
});

/**
 * @description: Judge whether there is an external function before execution, and decide whether to start after execution
 */
async function handleStart() {
  const { beforeStartFunc } = props;
  if (beforeStartFunc && isFunction(beforeStartFunc)) {
    loading.value = true;
    try {
      const canStart = await beforeStartFunc();
      if (canStart) start();
    } finally {
      loading.value = false;
    }
  } else {
    start();
  }
}
</script>

<template>
  <Button
    v-bind="$attrs"
    :disabled="isStart"
    :loading="loading"
    @click="handleStart"
  >
    {{ getButtonText }}
  </Button>
</template>
