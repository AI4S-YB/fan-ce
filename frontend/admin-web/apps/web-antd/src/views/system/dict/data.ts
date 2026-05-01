import type { VbenFormProps } from '#/adapter/form';
import type { VxeGridListeners, VxeGridProps } from '#/adapter/vxe-table';
import type { DictRowType } from '#/api/system/dict';

import { h, ref } from 'vue';

import { useVbenForm } from '#/adapter/form';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { deleteDictApi, getDictListApi } from '#/api/system/dict';
import { useMessage } from '#/hooks/web/useMessage';
import { $t } from '#/locales';

const { createMessage, createConfirm } = useMessage();
export { type DictRowType };

export const searchOption: VbenFormProps = {
  // 默认展开
  collapsed: false,
  submitOnEnter: true,
  schema: [
    {
      component: 'Input',
      fieldName: 'name',
      label: $t('system.user.realName'),
      labelWidth: 50,
      componentProps: { allowClear: true },
    },
    {
      component: 'Input',
      fieldName: 'key',
      label: $t('system.role.code'),
      labelWidth: 50,
    },
  ],
  // 控制表单是否显示折叠按钮
  showCollapseButton: true,
  // 按下回车时是否提交表单
  wrapperClass: 'grid-cols-2',
};
export const [Form, formApi] = useVbenForm({
  commonConfig: {
    // 所有表单项
    // componentProps: {
    //   class: 'w-full',
    // },
  },
  // handleSubmit: handleSubmit,
  layout: 'horizontal',
  schema: [
    {
      component: 'Input',
      fieldName: 'id',
      label: 'id',
      dependencies: {
        show: false,
        triggerFields: ['name'],
      },
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
        if: false,
      },
      fieldName: 'name',
      label: $t('system.user.realName'),
      rules: 'required',
      labelWidth: 50,
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
      },
      dependencies: {
        if(values) {
          return !values.id;
        },
        triggerFields: ['id'],
      },
      fieldName: 'key',
      label: $t('system.role.code'),
      rules: 'required',
      formItemClass: 'col-span-2 items-baseline',
      labelWidth: 50,
    },
    {
      component: 'Textarea',
      fieldName: 'remark',
      formItemClass: 'col-span-3 items-baseline',
      label: $t('system.user.remark'),
      labelWidth: 50,
    },
  ],
  showDefaultActions: false,
  wrapperClass: 'grid-cols-3',
});

export const gridOptions: VxeGridProps<DictRowType> = {
  columns: [
    { field: 'i', fixed: 'left', title: '', type: 'radio', width: 50 },
    { field: 'index', fixed: 'left', title: $t('component.table.index'), type: 'seq', width: 50 },
    { field: 'name', title: $t('system.user.realName') },
    { field: 'key', title: $t('system.role.code') },
  ],
  border: false,
  height: 'auto',
  exportConfig: {},
  importConfig: {},
  keepSource: true,
  pagerConfig: {
    pageSize: 10,
  },
  filterConfig: {
    remote: true,
  },
  radioConfig: {
    checkRowKey: '',
    reserve: true,
    highlight: true,
  },
  proxyConfig: {
    seq: true, // 启用动态序号代理
    sort: true, // 启用排序代理
    filter: true, // 启用筛选代理
    form: true,
    ajax: {
      query: async ({ page }) => {
        return await getDictListApi({
          page: page.currentPage,
          size: page.pageSize,
        });
      },
      querySuccess: ({ response }) => {
        if (response.total !== 0) {
          if (Object.keys(selected.value).length > 0) {
            gridApi.grid.setRadioRow(selected.value);
          } else {
            gridApi.grid.setRadioRow(response.dataList[0]);
            selected.value = response.dataList[0];
          }
        }
      },
    },
  },
  rowConfig: {
    isHover: true,
    keyField: 'id',
  },
  stripe: true,
  toolbarConfig: {
    custom: false,
    export: false,
    import: false,
    refresh: true,
    zoom: true,
    loading: false,
  },
};

const clickOption = ref<any>({});
const selected = ref<any>({});
const gridEvents: VxeGridListeners<DictRowType> = {
  cellClick: ({ row }) => {
    selected.value = row;
    gridApi.grid.setRadioRow(selected.value);
  },
  radioChange: ({ row }) => {
    selected.value = row;
  },
};
const [Grid, gridApi] = useVbenVxeGrid({
  gridEvents,
  gridOptions,
  formOptions: searchOption,
});

const handleDelete = async (rows: any = null, isBatch: boolean = false) => {
  if (isBatch) {
    const selecteds = gridApi.grid.getRadioRecord();
    if (Object.keys(selecteds).length === 0) {
      createMessage.warn($t('common.chooseSelect'));
    } else {
      createConfirm({
        iconType: 'warning',
        content: $t('common.delMessage'),
        centered: false,
        title: () => h('span', $t('common.warnning')),
        onCancel() {},
        onOk: async () => {
          try {
            await deleteDictApi({ id: selecteds?.id });
            createMessage.success($t('common.delSuccessText'));
            gridApi.reload();
          } catch {}
        },
      });
    }
  } else {
    await deleteDictApi({ id: rows.id });
    createMessage.success($t('common.delSuccessText'));
    gridApi.reload();
  }
};

export { clickOption, Grid, gridApi, handleDelete, selected };
