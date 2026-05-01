<script lang="ts" setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue';

// 由于找不到模块声明文件，使用 @ts-ignore 暂时忽略类型检查
// @ts-ignore
import Iconify from '@purge-icons/generated';

interface Props {
  icon: string;
  color?: string;
  size?: number | string;
  spin?: boolean | false;
  prefix?: string;
}
const props = withDefaults(defineProps<Props>(), {
  size: 16,
  spin: false,
  prefix: '',
  color: '',
});

const SVG_END_WITH_FLAG = '|svg';

const elRef = ref<HTMLElement | null>(null);

const isSvgIcon = computed(() => props.icon?.endsWith(SVG_END_WITH_FLAG));
const processedIcon = computed(() => ({
  name: props.icon.replace(SVG_END_WITH_FLAG, ''),
  ref: `${props.prefix ? `${props.prefix}:` : ''}${props.icon}`,
}));

const update = async () => {
  if (!elRef.value || !elRef.value?.isConnected || isSvgIcon.value) return;

  await nextTick();
  const icon = processedIcon.value.ref;
  if (!icon) return;

  const svg = Iconify.renderSVG(icon, {});
  if (elRef.value) {
    elRef.value.innerHTML = ''; // 清空内容
    elRef.value.append(svg || createIconSpan(icon));
  }
};

const createIconSpan = (icon: string) => {
  const span = document.createElement('span');
  span.className = 'iconify';
  span.dataset.icon = icon;
  return span;
};

const getWrapStyle = computed(() => {
  const fontSize =
    typeof props.size === 'string'
      ? Number.parseInt(props.size, 10)
      : props.size;
  return {
    fontSize: `${fontSize}px`,
    color: props.color,
    display: 'inline-flex',
  };
});

watch(() => props.icon, update, { flush: 'post' });
onMounted(update);
</script>

<template>
  <span
    style="margin-top: 1px"
    ref="elRef"
    :class="[$attrs.class, props.spin && 'app-iconify-spin']"
    :style="getWrapStyle"
    class="app-iconify anticon"
  ></span>
</template>

<style lang="less" scoped>
.app-iconify {
  display: inline-block;
  &-spin {
    svg {
      animation: loadingCircle 1s infinite linear;
    }
  }
}

span.iconify {
  display: block;
  min-width: 1em;
  min-height: 1em;
  border-radius: 100%;
}
</style>
