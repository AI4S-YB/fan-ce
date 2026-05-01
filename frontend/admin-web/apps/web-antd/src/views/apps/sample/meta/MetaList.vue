<script setup lang="ts">
import type { OnActionClickParams, VxeGridProps } from '#/adapter/vxe-table';

import { reactive } from 'vue';

import { Button, message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { $t } from '@vben/locales';
import { delSampleMetaApi, getSampleMetaListApi } from '#/api/apps/sample';
import { useModal } from '#/components/Modal';

import MetaModal from './MetaModal.vue';

const prop = defineProps({
  rawData: { type: Object, default: () => {} },
});
const [registerMetaModal, { openModal: metaOpenModal }] = useModal();
//

function onDelete(row: any) {
  const hideLoading = message.loading({
    content: $t('system.sample.deleting', { key: row.key }),
    duration: 0,
    key: 'action_process_msg',
  });
  delSampleMetaApi({ ids: [row.id] })
    .then(() => {
      gridApi.setGridOptions({ data: row });
      const dataSource = gridApi.grid.getTableData().fullData;
      const index = dataSource.findIndex((item) => item.id === row.id);
      if (index !== -1) {
        dataSource.splice(index, 1);
      }
      gridApi.setGridOptions({ data: [...dataSource] });
      message.success({
        content: $t('system.sample.deleteSuccess', { key: row.key }),
        key: 'action_process_msg',
      });
    })
    .catch(() => {
      hideLoading();
    });
}
function onEdit(row: any) {
  metaOpenModal(true, { row, isUpdate: true, action: 'edit' });
}
function onActionClick(e: OnActionClickParams<any>) {
  switch (e.code) {
    case 'add': {
      const row = e.row;
      row.sample_id = prop.rawData.id;
      metaOpenModal(true, { row, isUpdate: false, action: 'add' });
      break;
    }
    case 'delete': {
      onDelete(e.row);
      break;
    }
    case 'edit': {
      onEdit(e.row);
      break;
    }
  }
}

const childGridOptions = reactive<VxeGridProps<any>>({
  border: false,
  minHeight: 200,
  columns: [
    { field: 'key', title: $t('system.dict.name') },
    { field: 'value', title: $t('system.dict.value') },
    { field: 'description', title: $t('system.project.description') },
    {
      align: 'center',
      cellRender: {
        attrs: {
          nameField: 'key',
          nameTitle: '',
          onClick: onActionClick,
        },
        name: 'CellOperation',
      },
      field: 'operation',
      fixed: 'right',
      title: $t('system.dict.action'),
      width: 130,
    },
  ],
  proxyConfig: {
    ajax: {
      query: async ({ page }) => {
        return await getSampleMetaListApi({
          page: page.currentPage,
          size: page.pageSize,
          sample_id: prop.rawData.id,
        });
      },
    },
  },
});
const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: childGridOptions,
});
</script>

<template>
  <div :auto-content-height="false">
    <Grid>
      <template #toolbar-tools>
        <Button
          class="mr-2"
          size="small"
          pre-icon="ant-design:plus-outlined"
          type="primary"
          ghost
          @click="onActionClick({ code: 'add', row: {} })"
        >
          {{ $t('system.project.add') }}
        </Button>
      </template>
    </Grid>
    <MetaModal @register="registerMetaModal" @success="gridApi.reload()" />
  </div>
</template>
