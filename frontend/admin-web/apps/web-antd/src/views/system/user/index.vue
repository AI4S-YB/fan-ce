<script lang="ts" setup>
import type { UserRowType } from './data';

import type { VxeGridListeners } from '#/adapter/vxe-table';

import { h } from 'vue';

import { Page, useVbenModal } from '@vben/common-ui';

import { Modal } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { delUserApi, updateUserActiveApi } from '#/api/system/user';
import { Button } from '#/components/Button';
import { useModal } from '#/components/Modal';
import { TableAction } from '#/components/Table';
import { IconEnum } from '#/enums/appEnum';
import { useMessage } from '#/hooks/web/useMessage';
import { $t } from '@vben/locales';

import { formOptions, gridOptions } from './data';
import UserModel from './Modal.vue';
import PwdModal from './PwdModal.vue';
import AuthKeyModal from './AuthKeyModal.vue';

const { createMessage, createConfirm } = useMessage();
const [registerModal, { openModal }] = useModal();

const [PwdFormModal, formModalApi] = useVbenModal({
  connectedComponent: PwdModal,
  destroyOnClose: false,
});

const [registerAuthKeyModal, { openModal: openAuthKeyModal }] = useModal();

const handleDelete = async (rows: any = null, isBatch: Boolean = false) => {
  if (isBatch) {
    const selectd = gridApi.grid.getCheckboxRecords();
    if (selectd.length === 0) {
      createMessage.warn($t('common.chooseSelect'));
    } else {
      const ids = selectd.flatMap((item) =>
        Array.isArray(item) ? item.map((obj) => obj.id) : item.id,
      );
      createConfirm({
        iconType: 'warning',
        content: $t('common.delMessage'),
        centered: false,
        title: () => h('span', $t('common.warnning')),
        onCancel() {},
        onOk: async () => {
          try {
            await delUserApi({ ids });
            createMessage.success($t('common.delSuccessText'));
            gridApi.reload();
          } catch {}
        },
      });
    }
  } else {
    await delUserApi({ id: rows.id });
    createMessage.success($t('common.delSuccessText'));
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
    case 'delete': {
      handleDelete(row, isBatch);
      break;
    }
    case 'edit': {
      openModal(true, { row, isUpdate: true, action: actionType });
      break;
    }
    case 'reset': {
      formModalApi.setData(row).open();
      break;
    }
    case 'authKey': {
      openAuthKeyModal(true, { row });
      break;
    }
  }
};
// 禁用和启用
async function onStatusChange(newStatus: number, row: any) {
  const status: Recordable<string> = {
    0: $t('system.user.disable'),
    1: $t('system.user.enable'),
  };
  try {
    await confirm(
      $t('system.user.statusSwitchConfirm', { name: row.user_name, status: status[newStatus.toString()] }),
      $t('system.user.switchStatus'),
    );
    await updateUserActiveApi({ id: row.id, is_active: newStatus });
    return true;
  } catch {
    return false;
  }
}
function confirm(content: string, title: string) {
  return new Promise((reslove, reject) => {
    Modal.confirm({
      content,
      onCancel() {
        reject(new Error($t('workspace.chat.cancelled')));
      },
      onOk() {
        reslove(true);
      },
      title,
    });
  });
}
const gridEvents: VxeGridListeners<UserRowType> = {};
const [Grid, gridApi] = useVbenVxeGrid({
  gridEvents,
  gridOptions: gridOptions(onStatusChange),
  formOptions,
});
</script>

<template>
  <Page auto-content-height>
    <Grid :table-title="$t('system.user.listTitle')" :table-title-help="$t('system.user.tooltip')">
      <template #toolbar-tools>
        <Button
          class="mr-2"
          pre-icon="ant-design:plus-outlined"
          type="primary"
          ghost
          @click="handleAction('add')"
          v-access:code="['sys:user:add']"
        >
          {{ $t('system.user.add') }}
        </Button>
        <Button
          pre-icon="ant-design:delete-outlined"
          danger
          @click="handleAction('delete', '', true)"
          v-access:code="['sys:user:delete']"
        >
          {{ $t('system.user.delete') }}
        </Button>
      </template>
      <template #action="{ row }">
        <TableAction
          type="color:red"
          :outside="true"
          :actions="[
            {
              icon: IconEnum.EDIT,
              label: $t('component.action.edit'),
              auth: 'sys:user:update',
              onClick: handleAction.bind(null, 'edit', row),
            },
            {
              icon: IconEnum.EDIT,
              label: $t('system.user.resetPassword'),
              auth: 'sys:user:reset',
              onClick: handleAction.bind(null, 'reset', row),
            },
            {
              icon: 'ant-design:key-outlined',
              label: $t('system.user.keyManagement'),
              auth: 'sys:user:update',
              onClick: handleAction.bind(null, 'authKey', row),
            },
            {
              icon: IconEnum.DELETE,
              danger: true,
              label: $t('component.action.delete'),
              auth: 'sys:user:delete',
              size: 'small',
              popConfirm: {
                title: $t('common.delMessage'),
                placement: 'left',
                confirm: handleAction.bind(null, 'delete', row, false),
              },
            },
          ]"
        />
      </template>
    </Grid>
    <UserModel @register="registerModal" @success="gridApi.reload()" />
    <PwdFormModal @success="gridApi.reload()" />
    <AuthKeyModal @register="registerAuthKeyModal" @success="gridApi.reload()" />
  </Page>
</template>
