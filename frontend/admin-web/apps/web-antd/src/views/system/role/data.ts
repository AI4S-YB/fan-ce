import type { VbenFormProps } from '#/adapter/form';
import type { VxeGridProps } from '#/adapter/vxe-table';
import type { RoleRowType } from '#/api/system/role';

import { useVbenForm } from '#/adapter/form';
import { getRoleListApi } from '#/api/system/role';
import { $t } from '@vben/locales';

export { type RoleRowType };
// 列表搜索
export const formOptions: VbenFormProps = {
  // 默认展开
  collapsed: false,
  submitOnEnter: true,
  schema: [
    {
      component: 'Input',
      fieldName: 'name',
      label: $t('system.user.realName'),
      componentProps: { allowClear: true },
    },
  ],
  // 控制表单是否显示折叠按钮
  showCollapseButton: true,
  // 按下回车时是否提交表单
  wrapperClass: 'grid-cols-4',
};
// 表单提交
export const [Form, formApi] = useVbenForm({
  commonConfig: {
    // 所有表单项
    componentProps: {
      class: 'w-full',
    },
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
      // labelWidth: 80,
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
        if: false,
      },
      fieldName: 'code',
      label: $t('system.role.code'),
      rules: 'required',
      // labelWidth: 80,
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Input',
      fieldName: 'permissions',
      label: $t('system.role.auth'),
      modelPropName: 'modelValue',
      formItemClass: 'col-span-3 items-baseline',
    },
    {
      component: 'Textarea',
      fieldName: 'remark',
      formItemClass: 'col-span-3 items-baseline',
      label: $t('system.user.remark'),
    },
  ],
  showDefaultActions: false,
  wrapperClass: 'grid-cols-3',
});
// 表格列表
export const gridOptions: VxeGridProps<RoleRowType> = {
  columns: [
    { fixed: 'left', title: '', type: 'checkbox', width: 50 },
    { fixed: 'left', title: $t('component.table.index'), type: 'seq', width: 50, align: 'center' },
    { field: 'name', title: $t('system.user.realName') },
    { field: 'code', title: $t('system.role.code') },
    {
      field: 'is_active',
      title: $t('system.role.enabled'),
      align: 'center',
      cellRender: {
        name: 'DictTagStatus',
        props: { dictType: 'is_active', valueType: 'boolean' },
      },
    },
    {
      field: 'create_time',
      align: 'center',
      formatter: 'formatDateTime10',
      title: $t('system.user.createTime'),
    },
    {
      field: 'action',
      fixed: 'right',
      align: 'center',
      slots: { default: 'action' },
      title: $t('system.user.action'),
      minWidth: 120,
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
    ajax: {
      query: async ({ page }, formData) => {
        return await getRoleListApi({
          page: page.currentPage,
          size: page.pageSize,
          ...formData,
        });
      },
    },
  },
  rowConfig: {
    isHover: true,
  },
  toolbarConfig: {
    custom: true,
    export: true,
    import: true,
    refresh: true,
    zoom: true,
    loading: false,
  },
};
