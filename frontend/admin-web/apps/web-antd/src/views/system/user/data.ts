import type { VbenFormProps } from '#/adapter/form';
import type { VxeGridProps } from '#/adapter/vxe-table';
import type { UserRowType } from '#/api/system';

import { useVbenForm } from '#/adapter/form';
import { getUserListApi } from '#/api/system';
import { getRoleOptionApi } from '#/api/system/role';
import { $t } from '@vben/locales';

export { type UserRowType };
// 列表搜索
export const formOptions: VbenFormProps = {
  // 默认展开
  collapsed: false,
  submitOnEnter: true,
  schema: [
    {
      component: 'Input',
      fieldName: 'user_name',
      label: $t('system.user.username'),
      componentProps: { allowClear: true },
    },
    {
      component: 'Input',
      fieldName: 'user_email',
      label: $t('system.user.email'),
    },
  ],
  // 控制表单是否显示折叠按钮
  showCollapseButton: true,
  // 按下回车时是否提交表单
  wrapperClass: 'grid-cols-4',
};
// 列表表单
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
        triggerFields: ['id'],
      },
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
        if: false,
      },
      fieldName: 'user_name',
      label: $t('system.user.realName'),
      rules: 'required',
      // labelWidth: 80,
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'InputPassword',
      componentProps: {
        placeholder: $t('system.user.passwordTip'),
        autocomplete: 'off',
      },
      dependencies: {
        if(values) {
          return !values.id;
        },
        triggerFields: ['id'],
      },
      fieldName: 'user_password',
      label: $t('system.user.password'),
      rules: 'required',
      formItemClass: 'col-span-2 items-baseline',
      // labelWidth: 50,
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
      },
      fieldName: 'user_phone',
      label: $t('system.user.phone'),
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      fieldName: 'user_roles',
      label: $t('system.user.role'),
      component: 'ApiSelect',
      componentProps: {
        // 菜单接口转options格式
        afterFetch: (data: { name: string; path: string }[]) => {
          return data.map((item: any) => ({
            label: item.label,
            value: item.value,
          }));
        },
        // 菜单接口
        api: getRoleOptionApi,
        mode: 'multiple',
        allowClear: true,
      },
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
      },
      fieldName: 'user_email',
      label: $t('system.user.email'),
      formItemClass: 'col-span-2 items-baseline',
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
// 列表表格
export const gridOptions = (onStatusChange: any): VxeGridProps<UserRowType> => {
  return {
    columns: [
      { fixed: 'left', title: '', type: 'checkbox', width: 50 },
      { fixed: 'left', title: $t('common.index'), type: 'seq', width: 50 },
      { field: 'user_name', title: $t('system.user.username') },
      { field: 'user_email', title: $t('system.user.email') },
      { field: 'user_phone', title: $t('system.user.phone') },
      {
        field: 'is_active',
        title: $t('system.user.status'),
        cellRender: {
          attrs: { beforeChange: onStatusChange },
          name: onStatusChange ? 'CellSwitch' : 'CellTag',
        },
      },
      {
        field: 'create_time',
        formatter: 'formatDateTime10',
        align: 'center',
        title: $t('system.user.createTime'),
      },
      {
        field: 'action',
        fixed: 'right',
        align: 'center',
        slots: { default: 'action' },
        title: $t('system.user.action'),
        width: 360,
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
        query: async ({ page }: any, formData: any) => {
          return await getUserListApi({
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
};
