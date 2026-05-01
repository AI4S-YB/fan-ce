<script lang="ts" setup>
import { SearchOutlined } from '@ant-design/icons-vue';
import { Tooltip } from 'ant-design-vue';

import { $t as t } from '#/locales';

import { useTableContext } from '../../hooks/useTableContext';

defineOptions({ name: 'FormSetting' });

const table = useTableContext();

function redo() {
  table.setShowForm(!table.getShowForm());
  table.redoHeight();
}
</script>

<template>
  <Tooltip placement="top">
    <template #title>
      <span>{{ t('common.searchText') }}</span>
    </template>
    <SearchOutlined @click="redo" />
  </Tooltip>
</template>
