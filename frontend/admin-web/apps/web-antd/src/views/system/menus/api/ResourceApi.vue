<script setup lang="ts">
import type { PermissionRowType } from '#/api/system/permission';

import { ref, unref, watch } from 'vue';

import { Button, Tag, Tooltip } from 'ant-design-vue';
import { cloneDeep, uniqueId } from 'lodash-es';

import { addPermissionApi, updatePermissionApi } from '#/api/system/permission';
import { useModal } from '#/components/Modal';
import { BasicTable, TableAction, useTable } from '#/components/Table';
import { ActionEnum } from '#/enums/commonEnum';
import { HTTP_TAG_MAP } from '#/enums/httpEnum';
import { $t as t } from '#/locales';

import EditModal from './ApiEdit.vue';
import SelectModal from './ApiSelect.vue';
import { resourceApiColumns } from './data';

defineOptions({ name: 'ResourceApi' });
const props = defineProps({
  value: { type: [Array], default: () => [] },
  type: { type: String, default: ActionEnum.ADD },
});
const emit = defineEmits(['update:value', 'change']);
const [registerModal, { openModal }] = useModal();
const [registerEditModal, { openModal: openEditModal }] = useModal();
const innerVal = ref<Recordable[]>([]);
const [registerTable, { setTableData }] = useTable({
  title: $t('system.menu.resourceApiTitle'),
  dataSource: innerVal,
  scroll: { y: 220 },
  canResize: false,
  columns: resourceApiColumns,
  bordered: true,
  rowKey: 'tempId',
  actionColumn: {
    width: 100,
    title: t('system.user.action'),
    dataIndex: 'action',
  },
});

watch(
  () => props.value,
  (value: any = []) => {
    innerVal.value = cloneDeep(value);
    innerVal.value.forEach((v) => (v.tempId = uniqueId()));
  },
  { deep: true },
);
// 选择
function handleSelect() {
  openModal(true, {
    selectedData: [...unref(innerVal)],
  });
}
// 手工录入
function handleAdd() {
  openEditModal(true, {
    record: { tempId: uniqueId(), isInput: true },
  });
}

// 编辑录入
function handleEdit(record: Recordable, e: Event) {
  e?.stopPropagation();
  openEditModal(true, { record });
}
// 删除接口
function handleDelete(record: Recordable, e: Event) {
  e?.stopPropagation();

  const index = unref(innerVal).findIndex(
    (selected) =>
      selected.name === record.name &&
      selected.uri === record.uri &&
      selected.method === record.method,
  );

  if (index !== -1) {
    innerVal.value.splice(index, 1);
  }
  // addPermissionApi()
  emit('change', innerVal.value);
  emit('update:value', innerVal.value);
}

function handleSuccess(selectedData: PermissionRowType[]) {
  innerVal.value = selectedData;
  setTableData(selectedData);
  emit('change', selectedData);
  emit('update:value', selectedData);
}

async function handleEditSuccess(addData: any) {
  await (addData.isInput
    ? addPermissionApi(addData).then((res) => {
        addData = { ...addData, ...res };
      })
    : updatePermissionApi(addData));

  const index = unref(innerVal).findIndex(
    (selected) => selected.tempId === addData.tempId,
  );

  if (index === -1) {
    innerVal.value.push(addData);
  } else {
    unref(innerVal).forEach((selected) => {
      if (selected.tempId === addData.tempId) {
        selected.isInput = addData.isInput;
        selected.tempId = addData.tempId;
        selected.name = addData.name;
        selected.controller = addData.controller;
        selected.uri = addData.uri;
        selected.method = addData.method;
      }
    });
  }
  emit('change', innerVal.value);
  emit('update:value', innerVal.value);
}
</script>
<template>
  <div class="resource-api">
    <BasicTable @register="registerTable">
      <template #toolbar>
        <Button
          v-if="type !== ActionEnum.VIEW"
          type="primary"
          @click="handleAdd"
        >
          {{ $t('system.menu.manualEntry') }}
        </Button>
        <Button
          v-if="type !== ActionEnum.VIEW"
          type="primary"
          @click="handleSelect"
        >
          {{ $t('system.menu.selectEntry') }}
        </Button>
      </template>
      <template #bodyCell="{ column, record }">
        <template v-if="column.dataIndex === 'uri'">
          <Tooltip>
            <template #title>
              {{ $t('system.menu.apiTooltipName', { name: record.name }) }} <br />
              {{ $t('system.menu.apiTooltipCode', { code: record.code }) }} <br />
              {{ $t('system.menu.apiTooltipUri', { uri: record.uri }) }} <br />
              {{ $t('system.menu.apiTooltipMethod', { method: record.method }) }}
            </template>
            <Tag :color="HTTP_TAG_MAP.get(record.method)">
              {{ record.method }}
            </Tag>
            {{ record.uri }}
          </Tooltip>
        </template>
        <template v-if="column.dataIndex === 'action'">
          <TableAction
            :actions="[
              {
                label: t('common.title.delete'),
                ifShow: () => type !== ActionEnum.VIEW,
                popConfirm: {
                  title: $t('dataset.staging.confirmDelete'),
                  confirm: handleDelete.bind(null, record),
                },
              },
              {
                label: t('common.title.edit'),
                ifShow: () => type !== ActionEnum.VIEW,
                onClick: handleEdit.bind(null, record),
              },
            ]"
          />
        </template>
      </template>
    </BasicTable>

    <SelectModal @register="registerModal" @success="handleSuccess" />
    <EditModal @register="registerEditModal" @success="handleEditSuccess" />
  </div>
</template>
<style lang="scss" scoped>
.resource-api {
  display: grid;
  width: 100%;
  // padding: 10px;
  // position: relative;
  border: 1px solid #d9d9d9;
}

:deep(.ant-table-cell) {
  // padding: 6px 8px !important;
}
</style>
