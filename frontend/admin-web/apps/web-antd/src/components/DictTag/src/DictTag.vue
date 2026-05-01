<script lang="ts" setup>
import { computed } from 'vue';

import { Tag } from 'ant-design-vue';

import { Icon } from '#/components/Icon';
import { $t } from '@vben/locales';
import { isHexColor } from '#/utils/color';
import { getDictOptions } from '#/utils/dict/index';

interface DictTagProps {
  /** 字典类型 */
  type: string;
  /** 当前值 */
  value?: boolean | number | string;
  /** 值类型 */
  valueType?: 'boolean' | 'number' | 'string';
  /** 默认图标 */
  icon?: string;
}
interface DictItem {
  value: boolean | number | string;
  label: string;
  colorType?: string;
  cssClass?: string;
}
const props = withDefaults(defineProps<DictTagProps>(), {
  value: undefined,
  valueType: 'string',
  icon: '',
});
const COLOR_TYPE_MAP = {
  primary: 'processing',
  danger: 'error',
  info: 'default',
} as const;
// 颜色类型转换
const normalizeColorType = (color?: string) => {
  if (!color) return undefined;
  return COLOR_TYPE_MAP[color as keyof typeof COLOR_TYPE_MAP] || color;
};
// 值类型解析
const parseValue = (rawValue: unknown) => {
  switch (props.valueType) {
    case 'boolean': {
      return (
        String(rawValue).toLowerCase() === 'true' || Number(rawValue) === 1
      );
    }
    case 'number': {
      return Number(rawValue);
    }
    default: {
      return String(rawValue);
    }
  }
};

// 标签颜色计算
const tagColor = computed(() => {
  if (!dictData.value) return undefined;
  const colorType = normalizeColorType(dictData.value.colorType);
  if (colorType) return colorType;
  return dictData.value.cssClass && isHexColor(dictData.value.cssClass)
    ? dictData.value.cssClass
    : undefined;
});
// 标签样式计算
const tagStyle = computed(() => {
  if (!dictData.value) return undefined;

  const color = normalizeColorType(dictData.value.colorType);
  if (color) return { color };

  if (dictData.value.cssClass && isHexColor(dictData.value.cssClass)) {
    return { color: dictData.value.cssClass };
  }
  return undefined;
});
// 标签类名计算
const tagClass = computed(() => {
  return dictData.value?.cssClass && !isHexColor(dictData.value.cssClass)
    ? dictData.value.cssClass
    : undefined;
});
// 字典数据计算
const dictData = computed<DictItem | null>(() => {
  if (!props.type) return null;
  const parsedValue = parseValue(props.value);
  const options = getDictOptions(props.type);
  return (
    options.find((option) => parseValue(option.value) === parsedValue) ?? null
  );
});
// 显示文本
const displayText = computed(() => {
  return dictData.value?.label || $t('component.dict.unknownStatus', { value: props.value });
});
</script>
<template>
  <Tag
    v-if="value !== null && value !== undefined"
    :class="tagClass"
    :style="tagStyle"
    :color="tagColor"
  >
    <template #icon v-if="props.icon">
      <Icon :icon="props.icon" />
    </template>
    {{ displayText }}
  </Tag>
</template>
<style lang="less" scoped>
.dict-tag {
  transition: all 0.3s ease;

  &:not(.ant-tag-has-color) {
    background-color: rgb(0 0 0 / 4%);
    border-color: #d9d9d9;
  }

  :deep(.anticon) {
    vertical-align: -0.125em;
  }
}
</style>
