<script lang="ts" setup>
import { RedoOutlined } from '@ant-design/icons-vue';
import { Tooltip } from 'ant-design-vue';

import { $t as t } from '#/locales';

import { useTableContext } from '../../hooks/useTableContext';

defineOptions({ name: 'RedoSetting' });

const table = useTableContext();

function redo() {
  table.reload();
}
</script>

<template>
  <Tooltip placement="top">
    <template #title>
      <span>{{ t('common.redo') }}</span>
    </template>
    <RedoOutlined @click="redo" />
  </Tooltip>
</template>
