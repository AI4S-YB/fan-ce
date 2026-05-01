<script setup lang="ts">
import { computed, nextTick, ref, unref, watch } from 'vue';

import { renderSVG } from '@iconify/iconify';
import { Icon } from '@iconify/vue';

interface Props {
  icon: string;
  color?: string;
  size?: number | string;
  spin?: boolean | false;
  prefix?: string;
  rotate?: number;
  animation?: number;
  iconClass?: string;
}
const props = withDefaults(defineProps<Props>(), {
  size: 16,
  spin: false,
  prefix: '',
  color: 'red',
  hoverColor: 'var(--el-color-primary)',
  rotate: 0,
  animation: 0,
  iconClass: 'iconClass',
});

const prefixCls = 'abd';
const ICON_PREFIX = 'vi';

const isLocal = computed(() => props.icon?.startsWith('svg-icon:'));

const symbolId = computed(() => {
  if (unref(isLocal)) {
    return `#icons-${props.icon.split('svg-icon:')[1]}`;
  }
  if (props.icon?.startsWith(ICON_PREFIX)) {
    return `${props.icon.replace(ICON_PREFIX, '')}`;
  }
  return props.icon;
});
// const hasViDash = computed(() => props.icon?.includes('vi-') || false)
const hasViDash = false;
// 是否使用在线图标
const isUseOnline = computed(() => {
  return false;
});
const getIconName = computed(() => {
  return props.icon?.startsWith(ICON_PREFIX)
    ? props.icon.replace(ICON_PREFIX, '')
    : props.icon;
});
const getIconifyStyle = computed(() => {
  const { color, size, rotate, animation } = props;
  const style: any = {
    fontSize: `${size}px`,
    color,
  };
  if (rotate !== 0) {
    style.transform = `rotate(${rotate}deg)`;
  }
  if (animation !== 0) {
    style.animation = `spin-icon ${animation}s linear infinite`;
    style.transformOrigin = 'center';
    style.margin = '0';
    style.padding = '0';
    style.display = 'flex';
  }

  return style;
});

// 图标元素
const elRef = ref<ElRef>(null);
const updateIcon = async (icon: string) => {
  const el = unref(elRef);
  if (!el) return;
  await nextTick();
  if (!icon) return;
  const svg = renderSVG(icon, {});

  if (svg) {
    el.textContent = '';
    el.append(svg);
  } else {
    const span = document.createElement('span');
    span.className = 'iconify';
    span.dataset.icon = icon;
    el.textContent = '';
    el.append(span);
  }
};

watch(
  () => props.icon,
  (icon) => {
    updateIcon(icon);
  },
  { immediate: true },
);
</script>

<template>
  <div
    :class="[prefixCls, $attrs.class]"
    :style="[getIconifyStyle, $attrs.style]"
  >
    <svg
      v-if="isLocal"
      aria-hidden="true"
      :fill="color"
      :class="[prefixCls, $attrs.class]"
      :style="[getIconifyStyle, $attrs.style]"
    >
      <use :xlink:href="symbolId" />
    </svg>
    <Icon
      v-else-if="isUseOnline"
      :icon="getIconName"
      :style="getIconifyStyle"
    />
    <div v-else style="position: initial">
      <div v-if="hasViDash" :class="`${icon} iconify`" :style="getIconifyStyle">
        {{ icon }}
      </div>
      <span v-else ref="elRef" :class="$attrs.class" :style="getIconifyStyle">
        <span class="iconify" :data-icon="symbolId"></span>
      </span>
    </div>
  </div>
</template>

<style lang="less" scoped>
.iconClass {
  display: block;
  height: auto;
  width: auto;
  color: #861e1e;
}
</style>
