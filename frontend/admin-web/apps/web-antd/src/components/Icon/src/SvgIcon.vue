<script setup lang="ts">
import { computed } from 'vue';

// 接收 props
const props = defineProps({
  prefix: {
    type: String,
    default: 'icons',
  },
  iconClass: {
    type: String,
    default: 'iconClass',
  },
  name: {
    type: String,
    required: true,
  },
  color: {
    type: String,
    default: '#861e1e',
  },
});

// 计算符号 ID
const symbolId = computed(() => `#${props.prefix}-${props.name}`);
</script>

<template>
  <svg aria-hidden="false" :fill="color" :class="iconClass">
    <use :xlink:href="symbolId" />
  </svg>
</template>

<style scoped lang="scss">
.iconClass {
  width: auto;
  height: auto;
  color: #861e1e;
}

/* 可以根据需求添加样式 */
</style>
