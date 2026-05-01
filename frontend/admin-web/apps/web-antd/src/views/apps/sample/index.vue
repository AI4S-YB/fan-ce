<script lang="ts" setup>
import type { VxeGridListeners } from '#/adapter/vxe-table';

import { h } from 'vue';

import { Page } from '@vben/common-ui';

import { Badge } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { delSampleApi } from '#/api/apps/sample';
import { Button } from '#/components/Button';
import { useModal } from '#/components/Modal';
import { TableAction } from '#/components/Table';
import { Title } from '#/components/Title';
import { IconEnum } from '#/enums/appEnum';
import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';

import { formOptions, gridOptions } from './data';
import MetaList from './meta/MetaList.vue';
import UserModel from './Modal.vue';

const { createMessage, createConfirm } = useMessage();
const [registerModal, { openModal }] = useModal();
const onStatusChange = () => {};
const gridEvents: VxeGridListeners<any> = {};
const [Grid, gridApi] = useVbenVxeGrid({
  gridEvents,
  gridOptions: gridOptions(onStatusChange),
  formOptions,
});
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
            await delSampleApi({ ids });
            createMessage.success(t('common.delSuccessText'));
            gridApi.reload();
          } catch {}
        },
      });
    }
  } else {
    await delSampleApi({ id: rows.id });
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
</script>

<template>
  <Page auto-content-height>
    <Grid :table-title="$t('system.sample.listTitle')" :table-title-help="$t('system.project.tooltip')">
      <template #expand_default="{ row }">
        <Badge
          :count="row.meta_count"
          show-zero
          :number-style="{ backgroundColor: '#52c41a' }"
        />
      </template>
      <template #expand_content="{ row }">
        <div class="ext-cont m-2">
          <Title
            :title="$t('dataset.staging.metadata')"
            style="background-color: #e8f3ff"
            :line-width="3"
          />
          <MetaList :raw-data="row" />
        </div>
      </template>
      <template #toolbar-tools>
        <Button
          class="mr-2"
          pre-icon="ant-design:plus-outlined"
          type="primary"
          ghost
          @click="handleAction('add')"
          v-access:code="['app:sample:add']"
        >
          {{ $t('system.project.add') }}
        </Button>
        <Button
          pre-icon="ant-design:delete-outlined"
          danger
          @click="handleAction('delete', '', true)"
          v-access:code="['app:sample:delete']"
        >
          {{ $t('system.project.delete') }}
        </Button>
      </template>
      <template #action="{ row }">
        <TableAction
          type="color:red"
          :outside="true"
          :actions="[
            {
              icon: IconEnum.EDIT,
              label: t('component.action.edit'),
              auth: 'app:sample:update',
              onClick: handleAction.bind(null, 'edit', row),
            },
            {
              icon: IconEnum.DELETE,
              danger: true,
              label: t('component.action.delete'),
              auth: 'app:sample:delete',
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
    <UserModel @register="registerModal" @success="gridApi.reload()" />
  </Page>
</template>
<style lang="less" scoped>
.ext-cont {
  position: relative;
}
</style>
