import type { VbenFormProps } from '#/adapter/form';
import type { VxeGridListeners, VxeGridProps } from '#/adapter/vxe-table';
import type { DictRowType } from '#/api/system/dict';

import { h, ref } from 'vue';

import { useVbenForm } from '#/adapter/form';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { deleteDictFieldApi, getDictFieldListApi } from '#/api/system/dict';
import { useMessage } from '#/hooks/web/useMessage';
import { $t } from '#/locales';

const { createMessage, createConfirm } = useMessage();
const filters = ref({});
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
      fieldName: 'type_id',
      label: 'type_id',
      dependencies: { show: false, triggerFields: ['id'] },
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
      },
      dependencies: { disabled: true, triggerFields: ['id'] },
      fieldName: 'type_name',
      label: $t('system.dict.typeName'),
      rules: 'required',
      labelWidth: 100,
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
      },
      dependencies: { disabled: true, triggerFields: ['id'] },
      fieldName: 'type_key',
      label: $t('system.dict.typeCode'),
      rules: 'required',
      labelWidth: 100,
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
        if: false,
      },
      fieldName: 'label',
      label: $t('system.user.realName'),
      rules: 'required',
      labelWidth: 100,
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
      },
      // dependencies: {
      //   if(values) {
      //     return !values.id;
      //   },
      //   triggerFields: ['id'],
      // },
      fieldName: 'value',
      label: $t('system.role.code'),
      rules: 'required',
      formItemClass: 'col-span-2 items-baseline',
      labelWidth: 100,
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
      },
      fieldName: 'color',
      label: $t('system.dict.color'),
      labelWidth: 100,
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Textarea',
      fieldName: 'remark',
      formItemClass: 'col-span-3 items-baseline',
      label: $t('system.user.remark'),
      labelWidth: 100,
    },
  ],
  showDefaultActions: false,
  wrapperClass: 'grid-cols-3',
});

export const gridOptions: VxeGridProps<DictRowType> = {
  columns: [
    { fixed: 'left', title: '', type: 'checkbox', width: 50 },
    { fixed: 'left', title: $t('component.table.index'), type: 'seq', width: 50 },
    { field: 'label', title: $t('system.user.realName') },
    { field: 'value', title: $t('system.role.code') },
    {
      field: 'create_time',
      formatter: 'formatDateTime10',
      title: $t('system.user.createTime'),
    },
    {
      field: 'action',
      slots: { default: 'action' },
      title: $t('system.user.action'),
    },
  ],
  height: 'auto',
  exportConfig: {},
  importConfig: {},
  keepSource: true,
  pagerConfig: {
    pageSize: 10,
  },
  proxyConfig: {
    form: true,
    ajax: {
      query: async ({ page }, formValues) => {
        return await getDictFieldListApi({
          page: page.currentPage,
          size: page.pageSize,
          ...filters.value,
          ...formValues,
        });
      },
    },
  },
  rowConfig: {
    isHover: true,
  },
  toolbarConfig: {
    custom: false,
    export: false,
    import: false,
    refresh: true,
    zoom: true,
    loading: false,
  },
};
const gridEvents: VxeGridListeners<DictRowType> = {};
const [Grid, gridApi] = useVbenVxeGrid({
  gridEvents,
  gridOptions,
  formOptions: searchOption,
});
const setSelect = (row: { [key: string]: any }) => {
  filters.value = { ...filters.value, ...row };
};
const reload = (option: {}) => {
  setSelect(option);
  gridApi.reload();
};

const handleDelete = async (rows: any = null, isBatch: boolean = false) => {
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
            await deleteDictFieldApi({ ids });
            createMessage.success($t('common.delSuccessText'));
            gridApi.reload();
          } catch {}
        },
      });
    }
  } else {
    await deleteDictFieldApi({ id: rows.id });
    createMessage.success($t('common.delSuccessText'));
    gridApi.reload();
  }
};

export { Grid, gridApi, handleDelete, reload, setSelect };
