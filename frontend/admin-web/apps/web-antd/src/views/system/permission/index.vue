<script lang="ts" setup>
import type { VxeGridListeners } from '#/adapter/vxe-table';
import type { PermissionRowType } from '#/api/system/permission';

import { h } from 'vue';

import { Page } from '@vben/common-ui';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { delPermissionApi } from '#/api/system/permission';
import { Button } from '#/components/Button';
import { useModal } from '#/components/Modal';
import { TableAction } from '#/components/Table';
import { IconEnum } from '#/enums/appEnum';
import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';

import { formOptions, gridOptions } from './data';
import FormModel from './Modal.vue';

const { createMessage, createConfirm } = useMessage();
const [registerModal, { openModal }] = useModal();

const handleDelete = async (rows: any = null, isBatch: Boolean = false) => {
  if (isBatch) {
    const selectd = gridApi.grid.getCheckboxRecords();
    if (selectd.length === 0) {
      createMessage.warn(t('common.chooseSelect'));
    } else {
      const ids = selectd.flatMap((item) =>
        Array.isArray(item) ? item.map((obj) => obj.id) : item.id,
      );
      createConfirm({
        iconType: 'warning',
        content: t('common.delMessage'),
        centered: false,
        title: () => h('span', t('common.warnning')),
        onCancel() {},
        onOk: async () => {
          try {
            await delPermissionApi({ ids });
            createMessage.success(t('common.delSuccessText'));
            gridApi.reload();
          } catch {}
        },
      });
    }
  } else {
    await delPermissionApi({ id: rows.id });
    createMessage.success(t('common.delSuccessText'));
    gridApi.reload();
  }
};

const handleAction = async (
  actionType: any = '',
  row: any = '',
  isBatch: Boolean = false,
) => {
  switch (actionType) {
    case 'add': {
      openModal(true, { row, isUpdate: false, action: actionType });
      break;
    }
    case 'addOne': {
      openModal(true, { row, isUpdate: false, action: actionType });
      break;
    }
    case 'delete': {
      handleDelete(row, isBatch);
      break;
    }
    case 'edit': {
      openModal(true, { row, isUpdate: true, action: actionType });
      break;
    }
  }
};

const gridEvents: VxeGridListeners<PermissionRowType> = {};
const [Grid, gridApi] = useVbenVxeGrid({
  gridEvents,
  gridOptions,
  formOptions,
});
</script>

<template>
  <Page auto-content-height>
    <Grid :table-title="$t('system.permission.listTitle')" :table-title-help="$t('system.permission.listHelp')">
      <template #toolbar-tools>
        <Button
          class="mr-2"
          pre-icon="ant-design:plus-outlined"
          type="primary"
          ghost
          @click="handleAction('add')"
          v-access:code="['sys:permission:add']"
        >
          {{ t('system.permission.add') }}
        </Button>
        <Button
          pre-icon="ant-design:delete-outlined"
          danger
          @click="handleAction('delete', '', true)"
          v-access:code="['sys:permission:delete']"
        >
          {{ t('system.permission.delete') }}
        </Button>
      </template>
      <template #action="{ row }">
        <TableAction
          type="color:red"
          :outside="true"
          :actions="[
            {
              icon: IconEnum.ADD,
              label: $t('system.permission.addChild'),
              auth: 'sys:permission:add',
              onClick: handleAction.bind(null, 'addOne', row),
            },
            {
              icon: IconEnum.EDIT,
              label: t('component.action.edit'),
              auth: 'sys:permission:update',
              onClick: handleAction.bind(null, 'edit', row),
            },
            {
              icon: IconEnum.DELETE,
              danger: true,
              label: t('component.action.delete'),
              auth: 'sys:permission:delete',
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
    <FormModel
      width="550px"
      @register="registerModal"
      @success="gridApi.reload()"
    />
  </Page>
</template>
