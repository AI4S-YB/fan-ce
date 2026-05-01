<script lang="ts" setup>
import type { MenuProps } from 'ant-design-vue';

import type { SizeType } from '../../types/table';

import { ref } from 'vue';

import { ColumnHeightOutlined } from '@ant-design/icons-vue';
import { Dropdown, Menu, Tooltip } from 'ant-design-vue';

import { $t as t } from '#/locales';
import { getPopupContainer } from '#/utils';

import { useTableContext } from '../../hooks/useTableContext';

defineOptions({ name: 'SizeSetting' });

const table = useTableContext();

const selectedKeysRef = ref<SizeType[]>([table.getSize()]);

const handleTitleClick: MenuProps['onClick'] = ({ key }) => {
  selectedKeysRef.value = [key as SizeType];
  table.setProps({
    size: key as SizeType,
  });
};
</script>

<template>
  <Tooltip placement="top">
    <template #title>
      <span>{{ t('component.table.settingDens') }}</span>
    </template>

    <Dropdown
      placement="bottom"
      :trigger="['click']"
      :get-popup-container="getPopupContainer"
    >
      <ColumnHeightOutlined />
      <template #overlay>
        <Menu
          v-model:selected-keys="selectedKeysRef"
          selectable
          @click="handleTitleClick"
        >
          <Menu.Item key="default">
            <span>{{ t('component.table.settingDensDefault') }}</span>
          </Menu.Item>
          <Menu.Item key="middle">
            <span>{{ t('component.table.settingDensMiddle') }}</span>
          </Menu.Item>
          <Menu.Item key="small">
            <span>{{ t('component.table.settingDensSmall') }}</span>
          </Menu.Item>
        </Menu>
      </template>
    </Dropdown>
  </Tooltip>
</template>
