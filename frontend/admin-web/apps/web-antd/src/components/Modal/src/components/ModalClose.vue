<script lang="ts" setup>
import { computed } from 'vue';

import {
  CloseOutlined,
  FullscreenExitOutlined,
  FullscreenOutlined,
} from '@ant-design/icons-vue';
import { Tooltip } from 'ant-design-vue';

import { $t } from '#/locales';
import { useDesign } from '#/utils/vbenModle';

defineOptions({ name: 'ModalClose' });

const props = defineProps({
  canFullscreen: { type: Boolean, default: true },
  fullScreen: { type: Boolean },
});

const emit = defineEmits(['cancel', 'fullscreen']);

const t = $t;

const { prefixCls } = useDesign('basic-modal-close');

const getClass = computed(() => {
  return [
    prefixCls,
    `${prefixCls}--custom`,
    {
      [`${prefixCls}--can-full`]: props.canFullscreen,
    },
  ];
});

function handleCancel(e: Event) {
  emit('cancel', e);
}

function handleFullScreen(e: Event) {
  e?.stopPropagation();
  e?.preventDefault();
  emit('fullscreen');
}
</script>

<template>
  <div :class="getClass">
    <template v-if="canFullscreen">
      <Tooltip
        v-if="fullScreen"
        :title="t('component.modal.restore')"
        placement="bottom"
      >
        <FullscreenExitOutlined role="full" @click="handleFullScreen" />
      </Tooltip>
      <Tooltip v-else :title="t('component.modal.maximize')" placement="bottom">
        <FullscreenOutlined role="close" @click="handleFullScreen" />
      </Tooltip>
    </template>
    <Tooltip :title="t('component.modal.close')" placement="bottom">
      <CloseOutlined @click="handleCancel" />
    </Tooltip>
  </div>
</template>

<style lang="less">
@namespace: 'vben';
@prefix-cls: ~'@{namespace}-basic-modal-close';
.@{prefix-cls} {
  display: flex;
  align-items: center;
  height: 95%;

  > span {
    margin-left: 48px;
    font-size: 16px;
  }

  &--can-full {
    > span {
      margin-left: 12px;
    }
  }

  &:not(&--can-full) {
    > span:nth-child(1) {
      &:hover {
        font-weight: 700;
      }
    }
  }

  & span:nth-child(1) {
    display: inline-block;
    // padding: 10px;
  }
}
</style>
