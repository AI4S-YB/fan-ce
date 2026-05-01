import type { VbenFormProps } from '#/adapter/form';
import type { VxeGridProps } from '#/adapter/vxe-table';
import type { TeamRowType } from '#/api/system/team';

import { useVbenForm } from '#/adapter/form';
import { getTeamListApi } from '#/api/system/team';
import { $t } from '@vben/locales';

export { type TeamRowType };
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
      formItemClass: 'col-span-2 items-baseline',
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
    // {
    //   fieldName: 'project_ids',
    //   label: $t('workspace.stats.project'),
    //   component: 'ApiSelect',
    //   // rules: 'required',
    //   componentProps: {
    //     mode: 'multiple',
    //     api: getProjectOptionsApi,
    //     params: {},
    //     filterOption: (input: string, option: Recordable<any>) => {
    //       return option.label.toLowerCase().includes(input.toLowerCase());
    //     },
    //     // onChange: (value: any) => {
    //     //   formApi.setFieldValue('projects', value);
    //     // },
    //     showSearch: true,
    //   },
    //   formItemClass: 'col-span-2 items-baseline',
    // },
    {
      fieldName: 'database_path',
      label: $t('system.team.databasePath'),
      component: 'Input',
      rules: 'required',
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
export const [PermissionForm, permissionFormApi] = useVbenForm({
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
      disabled: true,
      // labelWidth: 80,
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Select',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
        mode: 'multiple',
      },
      fieldName: 'user_role_list',
      label: $t('system.role.auth'),
      // rules: 'required',
      modelPropName: 'modelValue',
      // labelWidth: 80,
      formItemClass: 'col-span-2 items-baseline',
    },
  ],
  showDefaultActions: false,
  wrapperClass: 'grid-cols-2',
});
// 表格列表
export const gridOptions: VxeGridProps<TeamRowType> = {
  columns: [
    { fixed: 'left', title: '', type: 'checkbox', width: 50 },
    { fixed: 'left', title: $t('component.table.index'), type: 'seq', width: 50 },
    { field: 'name', title: $t('system.user.realName'), align: 'left' },
    { field: 'code', title: $t('system.role.code'), visible: false },
    {
      field: 'is_active',
      title: $t('system.role.enabled'),
      cellRender: {
        name: 'DictTagStatus',
        props: { dictType: 'is_active', valueType: 'boolean' },
      },
    },
    {
      field: 'create_time',
      formatter: 'formatDateTime10',
      title: $t('system.user.createTime'),
    },
    {
      field: 'remark',
      title: $t('system.project.description'),
    },
    {
      field: 'action',
      fixed: 'right',
      slots: { default: 'action' },
      title: $t('system.user.action'),
      minWidth: 120,
    },
  ],
  height: 'auto',
  align: 'center',
  columnConfig: {
    resizable: true,
  },
  exportConfig: {},
  importConfig: {},
  keepSource: true,
  pagerConfig: {
    pageSize: 10,
  },
  proxyConfig: {
    ajax: {
      query: async ({ page }, formData) => {
        return await getTeamListApi({
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
