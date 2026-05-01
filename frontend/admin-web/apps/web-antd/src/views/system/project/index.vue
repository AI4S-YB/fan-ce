<script lang="ts" setup>
import { h } from 'vue';

import { Page } from '@vben/common-ui';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { delProjectApi } from '#/api/system/project';
import { Button } from '#/components/Button';
import { Loading } from '#/components/Loading';
import { useModal } from '#/components/Modal';
import { TableAction } from '#/components/Table';
import { IconEnum } from '#/enums/appEnum';
import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';
import { useAppUserStore } from '#/store/modules/project';

import { formOptions, gridOptions } from './data';
import UserModel from './Modal.vue';
import MetaJsonModal from './MetaJsonModal.vue';

const useAppUser = useAppUserStore();
const { createMessage, createConfirm } = useMessage();
const [registerModal, { openModal }] = useModal();
const [registerMetaJsonModal, { openModal: openMetaJsonModal }] = useModal();
const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions,
  formOptions,
});

// 删除方法
const handleDelete = async (rows: any = null, isBatch: Boolean = false) => {
  if (isBatch) {
    const selecteds = gridApi.grid.getCheckboxRecords();
    if (Object.keys(selecteds).length === 0) {
      createMessage.warn(t('common.chooseSelect'));
    } else {
      const ids = selecteds.flatMap(
        (item: { id: any; map: (arg0: (obj: any) => any) => any }) =>
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
            await delProjectApi({ ids });
            createMessage.success(t('common.delSuccessText'));
            await useAppUser.updateProjectOptions();
            gridApi.reload();
          } catch {}
        },
      });
    }
  } else {
    await delProjectApi({ id: rows.id });
    createMessage.success(t('common.delSuccessText'));
    await useAppUser.updateProjectOptions();
    gridApi.reload();
  }
};

// gridApi.setLoading(true);

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
    case 'link': {
      openModal(true, { row, isUpdate: true, action: actionType });
      break;
    }
    case 'meta': {
      openMetaJsonModal(true, { row, isUpdate: true, action: actionType });
      break;
    }
  }
};
</script>

<template>
  <Page auto-content-height>
    <Grid :table-title="t('system.project.listTitle')" :table-title-help="t('system.project.tooltip')">
      <template #toolbarButtons>
        <Button status="primary">按钮1</Button>
        <Button status="primary">按钮2</Button>
        <Button status="primary">按钮3</Button>
      </template>
      <template #toolbar-tools>
        <Button
          class="mr-2"
          pre-icon="ant-design:plus-outlined"
          type="primary"
          @click="handleAction('add')"
          v-access:code="['sys:project:add']"
        >
          {{ t('system.project.add') }}
        </Button>
        <Button
          pre-icon="ant-design:delete-outlined"
          @click="handleAction('delete', '', true)"
          v-access:code="['sys:project:delete']"
        >
          {{ t('system.project.delete') }}
        </Button>
      </template>
      <template #loading>
        <Loading
          :absolute="true"
          background="dark"
          :loading="true"
          :tip="t('common.loadingText')"
        />
      </template>
      <template #action="{ row }">
        <TableAction
          :actions="[
            {
              icon: IconEnum.EDIT,
              label: t('component.action.edit'),
              auth: 'sys:project:update',
              onClick: handleAction.bind(null, 'edit', row),
            },
            {
              icon: 'ic:baseline-layers',
              danger: false,
              label: $t('system.project.metaJson'),
              auth: 'sys:project:delete',
              size: 'small',
              onClick: handleAction.bind(null, 'meta', row),
            },
          ]"
          :drop-down-actions="[
            {
              icon: 'mdi:attachment',
              label: $t('system.project.linkData'),
              auth: 'sys:project:database',
              onClick: handleAction.bind(null, 'link', row),
            },
            {
              icon: 'bx:analyse',
              danger: true,
              label: $t('system.project.dataAnalysis'),
              auth: 'system:menu:delete',
              size: 'small',
            },
            {
              icon: 'bx:analyse',
              danger: true,
              label: $t('system.project.projectTransfer'),
              auth: 'system:menu:delete',
              size: 'small',
            },
            {
              icon: IconEnum.DELETE,
              danger: true,
              label: t('component.action.delete'),
              auth: 'sys:project:delete',
              size: 'small',
              popConfirm: {
                title: t('common.delMessage'),
                placement: 'left',
                confirm: handleAction.bind(null, 'delete', row, false),
              },
            },
          ]"
          :outside="true"
          type="color:red"
        />
      </template>
    </Grid>
    <UserModel @register="registerModal" @success="gridApi.reload()" />
    <MetaJsonModal @register="registerMetaJsonModal" @success="gridApi.reload()" />
  </Page>
</template>
