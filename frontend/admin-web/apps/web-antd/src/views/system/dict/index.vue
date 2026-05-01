<script lang="ts" setup>
import { ref, watch } from 'vue';

import { Page } from '@vben/common-ui';

import { Button } from '#/components/Button';
import { useModal } from '#/components/Modal';
import { TableAction } from '#/components/Table';
import { IconEnum } from '#/enums/appEnum';
import { $t as t } from '#/locales';

import { Grid, gridApi, handleDelete, selected } from './data';
import items from './items.vue';
import DictModal from './Modal.vue';

const itemRef = ref<any>(null);

const [registerModal, { openModal }] = useModal();
const handleAction = async (
  actionType: any = '',
  row: any = '',
  isBatch: boolean = false,
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
watch(selected, (newValue: any) => {
  itemRef.value?.reload({ type_id: newValue.id });
});

// onMounted(() => {
//   setTimeout(() => {
//     defaultCelected();
//   }, 1000);
// });
</script>

<template>
  <Page auto-content-height content-class="flex p-5">
    <Grid
      :table-title="$t('system.dict.listTitle')"
      class="p-1 md:w-1/3 xl:w-1/3"
      :table-title-help="$t('system.dict.tooltip')"
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
          type="color:red"
          :outside="true"
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
        />
      </template>
    </Grid>
    <DictModal @register="registerModal" @success="gridApi.reload()" />
    <items class="md:w-2/3 xl:w-2/3" ref="itemRef" :selected="selected" />
  </Page>
</template>
