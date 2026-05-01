<script lang="ts" setup>
import { Button } from 'ant-design-vue';

import { basicProps } from '../props';

defineOptions({ name: 'BasicModalFooter' });

defineProps(basicProps);

const emit = defineEmits(['ok', 'cancel']);

function handleOk(e: Event) {
  emit('ok', e);
}

function handleCancel(e: Event) {
  emit('cancel', e);
}
</script>

<template>
  <div>
    <hr style="margin-bottom: 10px" />
    <slot name="insertFooter"></slot>
    <Button
      v-if="showCancelBtn"
      v-bind="cancelButtonProps"
      @click="handleCancel"
    >
      {{ cancelText }}
    </Button>
    <slot name="centerFooter"></slot>
    <Button
      v-if="showOkBtn"
      :type="okType"
      :loading="confirmLoading"
      v-bind="okButtonProps"
      @click="handleOk"
    >
      {{ okText }}
    </Button>
    <slot name="appendFooter"></slot>
  </div>
</template>
