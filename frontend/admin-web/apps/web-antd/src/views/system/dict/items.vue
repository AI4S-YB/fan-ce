<script lang="ts" setup>
import { Button } from '#/components/Button';
import { useModal } from '#/components/Modal';
import { TableAction } from '#/components/Table';
import { IconEnum } from '#/enums/appEnum';
import { $t as t } from '#/locales';

import { formApi, Grid, gridApi, handleDelete, reload } from './item';
import DictItemModal from './itmeModal.vue';

const props = defineProps({
  selected: { type: Object, default: () => ({}) },
});

const [registerModal, { openModal }] = useModal();
const handleAction = async (
  actionType: any = '',
  row: any = '',
  isBatch: boolean = false,
) => {
  switch (actionType) {
    case 'add': {
      openModal(true, { row, isUpdate: false, action: actionType });
      formApi.setValues({ type_id: 1 });
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

defineExpose({
  reload,
});
</script>

<template>
  <div style="margin-left: 10px">
    <Grid
      :table-title="$t('system.dict.fieldList', { name: props.selected?.name })"
      :table-title-help="$t('system.dict.identify', { key: props.selected?.key })"
    >
      <template #toolbar-tools>
        <Button
          class="mr-2"
          pre-icon="ant-design:plus-outlined"
          type="primary"
          @click="handleAction('add')"
        >
          {{ $t('system.dict.add') }}
        </Button>
        <Button
          danger
          pre-icon="ant-design:delete-outlined"
          type="primary"
          @click="handleAction('delete', '', true)"
        >
          {{ $t('system.dict.delete') }}
        </Button>
      </template>
      <template #action="{ row }">
        <TableAction
          :actions="[
            {
              icon: IconEnum.EDIT,
              label: t('component.action.edit'),
              auth: 'system:menu:update',
              onClick: handleAction.bind(null, 'edit', row),
            },
            {
              icon: IconEnum.DELETE,
              danger: true,
              label: t('component.action.delete'),
              auth: 'system:menu:delete',
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
    <DictItemModal
      :selected="props.selected"
      @register="registerModal"
      @success="gridApi.reload()"
    />
  </div>
</template>
