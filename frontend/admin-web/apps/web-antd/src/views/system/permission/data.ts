import type { VbenFormProps } from '#/adapter/form';
import type { VxeGridProps } from '#/adapter/vxe-table';
import type { PageResultType } from '#/api/system/permission';

import { getPermissionTreeApi } from '#/api/system/permission';
import { $t } from '@vben/locales';

export { type PageResultType };
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
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        autoSelect: 'first',
        options: [
          {
            label: 'POST',
            value: 'POST',
          },
          {
            label: 'GET',
            value: 'GET',
          },
          { label: 'PUT', value: 'PUT' },
          { label: 'DELETE', value: 'DELETE' },
        ],
        placeholder: $t('system.project.pleaseInput'),
      },
      fieldName: 'method',
      label: $t('system.permission.requestMethod'),
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        autoSelect: 'first',
        options: [
          { value: 'system', label: $t('system.permission.systemService') },
          { value: 'app', label: $t('system.permission.appService') },
        ],
        placeholder: $t('system.project.pleaseInput'),
      },
      fieldName: 'type',
      label: $t('system.permission.serviceType'),
    },
  ],
  // 控制表单是否显示折叠按钮
  showCollapseButton: true,
  // 按下回车时是否提交表单
  wrapperClass: 'grid-cols-4',
};
export const gridOptions: VxeGridProps<PageResultType> = {
  columns: [
    { fixed: 'left', title: '', type: 'checkbox', width: 50 },
    // { fixed: 'left', title: $t('component.table.index'), type: 'seq', width: 50 },
    {
      field: 'name',
      title: $t('system.user.realName'),
      titlePrefix: { content: 'name' },
      treeNode: true,
      // slots: { default: 'name' },
    },
    { field: 'code', title: $t('system.role.code') },
    { field: 'uri', title: $t('system.permission.accessUri') },
    { field: 'method', title: $t('system.permission.requestMethod') },
    {
      field: 'create_time',
      formatter: 'formatDateTime10',
      title: $t('system.user.createTime'),
    },
    {
      field: 'action',
      fixed: 'right',
      slots: { default: 'action' },
      title: $t('system.user.action'),
      align: 'center',
      width: 225,
    },
  ],

  height: 'auto',
  exportConfig: {},
  importConfig: {},
  keepSource: true,
  round: false,
  pagerConfig: {
    pageSize: 10,
    enabled: false,
  },
  proxyConfig: {
    response: {
      result: 'dataList',
      total: 'total',
      list: 'dataList',
    },
    ajax: {
      query: async ({ page }, formValues) => {
        return await getPermissionTreeApi({
          page: page.currentPage,
          size: page.pageSize,
          ...formValues,
        });
      },
    },
  },
  rowConfig: {
    isHover: true,
    useKey: true,
  },
  treeConfig: {
    childrenField: 'children',
    rowField: 'id',
    parentField: 'pid',
    transform: false,
    showLine: true,
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
