<script lang="ts" setup>
import {
  FullscreenExitOutlined,
  FullscreenOutlined,
} from '@ant-design/icons-vue';
import { useFullscreen } from '@vueuse/core';
import { Tooltip } from 'ant-design-vue';

import { $t as t } from '#/locales';

import { useTableContext } from '../../hooks/useTableContext';

defineOptions({ name: 'FullScreenSetting' });

const table = useTableContext();

const { toggle, isFullscreen } = useFullscreen(table.wrapRef);
</script>

<template>
  <Tooltip placement="top">
    <template #title>
      <span>{{ t('component.table.settingFullScreen') }}</span>
    </template>
    <FullscreenOutlined v-if="!isFullscreen" @click="toggle" />
    <FullscreenExitOutlined v-else @click="toggle" />
  </Tooltip>
</template>
