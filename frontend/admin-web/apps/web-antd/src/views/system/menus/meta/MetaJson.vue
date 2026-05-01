<script lang="ts" setup>
import { ref, watch } from 'vue';

import { Button } from 'ant-design-vue';
import { forEach } from 'lodash-es';

import { useModal } from '#/components/Modal';
import { BasicTable, TableAction, useTable } from '#/components/Table';
import { ActionEnum } from '#/enums/commonEnum';
import { $t as t } from '#/locales';

import { metaJsonColumns } from './metadata';
import EditModal from './MetaEdit.vue';

defineOptions({ name: 'MetaJson' });
const props = defineProps({
  value: { type: String, default: '{}' },
  type: { type: String, default: ActionEnum.ADD },
});
const emit = defineEmits(['update:value', 'change']);

const [registerModal, { openModal }] = useModal();
const keys = ref<Recordable[]>([]);
const innerVal = ref<Recordable>({});
const [registerTable] = useTable({
  title: $t('system.menu.metaRouteTitle'),
  dataSource: keys,
  scroll: { y: 250 },
  columns: metaJsonColumns,
  bordered: true,
  canResize: false,
  rowClassName: () => 'rows',
  actionColumn: {
    width: 120,
    title: t('common.action'),
    dataIndex: 'action',
  },
});
watch(
  () => props.value,
  (value: any) => {
    innerVal.value = JSON.parse(value || '{}');
    const list: Recordable[] = [];
    forEach(innerVal.value, (v, key) => {
      list.push({ key, value: v });
    });
    keys.value = list;
  },
  { deep: true },
);
watch(
  () => innerVal.value,
  (value) => {
    const list: Recordable[] = [];
    forEach(value, (v, key) => {
      list.push({ key, value: v });
    });
    keys.value = list;
  },
  { deep: true },
);
function handleEdit(record: Recordable, e: Event) {
  e?.stopPropagation();
  openModal(true, {
    record,
    type: ActionEnum.EDIT,
  });
}
function handleAdd() {
  openModal(true, {
    type: ActionEnum.ADD,
  });
}
function handleDelete(record: Recordable, e: Event) {
  e?.stopPropagation();
  if (record && record?.key) {
    delete innerVal.value[record?.key];

    emit('change', JSON.stringify(innerVal.value));
    emit('update:value', JSON.stringify(innerVal.value));
  }
}

function handleSuccess(metaItem: any) {
  const data = { ...innerVal.value };
  data[metaItem.key] = metaItem.value;
  for (const key in data) {
    let value = data[key];
    if (value === 'false') {
      value = false;
    } else if (value === 'true') {
      value = true;
    } else if (/^\d+$/.test(value)) {
      value = Number.parseInt(value);
    } else if (/^\d+\.\d+$/.test(value)) {
      value = Number.parseFloat(value);
    }
    data[key] = value;
  }

  innerVal.value = data;
  emit('change', JSON.stringify(data));
  emit('update:value', JSON.stringify(data));
}
</script>
<template>
  <div class="meta-input">
    <BasicTable @register="registerTable">
      <template #toolbar>
        <Button
          v-if="type !== ActionEnum.VIEW"
          type="primary"
          @click="handleAdd"
        >
          {{ t('common.title.add') }}
        </Button>
      </template>
      <template #bodyCell="{ column, record }">
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

    <EditModal @register="registerModal" @success="handleSuccess" />
  </div>
</template>
<style lang="scss" scoped>
:global(.ant-table-thead > tr > th) {
  color: royalblue;
  text-align: center;
}

.meta-input {
  display: block;
  width: 100%;
  padding: 10px;
  border: 1px solid #d9d9d9;
}

:deep(.ant-table-cell) {
  // padding: 6px 8px !important;
}

:deep(.rows) {
  // padding: 1px 16px;
}
</style>
