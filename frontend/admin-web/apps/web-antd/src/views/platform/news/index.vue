<script lang="ts" setup>
import { ref } from 'vue';

import { Page } from '@vben/common-ui';

import { Button } from '#/components/Button';
import { useModal } from '#/components/Modal';
import { TableAction } from '#/components/Table';
import { IconEnum } from '#/enums/appEnum';
import { $t as t } from '#/locales';

import { handleDelete, selected, createGrid } from './data';
import NewsModal from './Modal.vue';

defineOptions({ name: 'NewsManagement' });

const [registerModal, { openModal }] = useModal();

const handleAction = async (
  actionType: any = '',
  row: any = '',
  isBatch: boolean = false,
) => {
  switch (actionType) {
    case 'add': {
      openModal(true, { record: {}, isUpdate: false, action: actionType });
      break;
    }
    case 'delete': {
      handleDelete(row, isBatch);
      break;
    }
    case 'edit': {
      openModal(true, { record: row, isUpdate: true, action: actionType });
      break;
    }
  }
};

const { Grid, gridApi } = createGrid(handleAction);
</script>

<template>
  <Page auto-content-height content-class="flex p-5">
    <div class="w-full">
      <Grid
        :table-title="$t('page.newsManagement')"
        :table-title-help="$t('platform.news.tableTitleHelp')"
      >
        <template #toolbar-tools>
          <Button
            class="mr-2"
            size="middle"
            type="primary"
            @click="handleAction('add')"
          >
            {{ t('component.action.create') }}
          </Button>
          <Button
            type="primary"
            size="middle"
            danger
            @click="handleAction('delete', '', true)"
          >
            {{ t('component.action.delete') }}
          </Button>
        </template>
        
        <template #action="{ row }">
          <TableAction
            type="color:blue"
            :outside="true"
            :actions="[
              {
                icon: IconEnum.EDIT,
                label: t('component.action.edit'),
                auth: 'platform:news:update',
                onClick: handleAction.bind(null, 'edit', row),
              },
              {
                icon: IconEnum.DELETE,
                danger: true,
                label: t('component.action.delete'),
                auth: 'platform:news:delete',
                size: 'small',
                popConfirm: {
                  title: t('common.delMessage'),
                  placement: 'left',
                  confirm: handleAction.bind(null, 'delete', row, false),
                },
              },
            ]"
          />
        </template>
      </Grid>
    </div>
    
    <NewsModal @register="registerModal" @success="gridApi.reload()" />
  </Page>
</template>

<style lang="less" scoped>
:deep(.vxe-table--body-wrapper) {
  .vxe-body--row {
    &:hover {
      background-color: #f5f5f5;
    }
  }
}

:deep(.vxe-table) {
  .vxe-header--column {
    font-weight: 600;
  }
}
</style>
