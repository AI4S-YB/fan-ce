import type { VbenFormProps } from '#/adapter/form';
import type { VxeGridProps } from '#/adapter/vxe-table';
import type { MenuRowType } from '#/api/system';

import { getMenuListApi } from '#/api/system';
import { $t } from '@vben/locales';

export { type MenuRowType };
export const formOptions: VbenFormProps = {
  // 默认展开
  collapsed: false,
  submitOnEnter: true,
  schema: [
    {
      component: 'Input',
      fieldName: 'name',
      label: $t('system.user.username'),
      componentProps: { allowClear: true },
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: [
          {
            label: 'Color1',
            value: '1',
          },
          {
            label: 'Color2',
            value: '2',
          },
        ],
        placeholder: $t('system.project.pleaseInput'),
      },
      fieldName: 'user_type',
      label: $t('system.menu.type'),
    },
  ],
  // 控制表单是否显示折叠按钮
  showCollapseButton: true,
  // 按下回车时是否提交表单
  wrapperClass: 'grid-cols-4',
};
export const gridOptions: VxeGridProps<MenuRowType> = {
  columns: [
    { fixed: 'left', title: '', type: 'checkbox', width: 50 },
    { fixed: 'left', title: $t('component.table.index'), type: 'seq', width: 50 },
    {
      field: 'name',
      title: $t('system.user.realName'),
      titlePrefix: { content: 'name' },
      // slots: { default: 'name' },
    },
    { field: 'type', title: $t('system.menu.type'), cellRender: { name: 'formatMenuType' } },
    { field: 'icon', title: 'Icon', slots: { default: 'icon' } },

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
      width: 160,
    },
  ],
  height: 'auto',
  exportConfig: {},
  importConfig: {},
  keepSource: true,
  round: false,
  pagerConfig: {
    pageSize: 10,
  },
  proxyConfig: {
    ajax: {
      query: async ({ page }) => {
        return await getMenuListApi({
          page: page.currentPage,
          size: page.pageSize,
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
    // buttons: [
    //   { name: $t('system.dict.add'), code: 'add', status: 'primary' },
    //   { name: $t('system.dict.delete'), code: 'del', status: 'error' },
    //   { name: $t('component.upload.save'), code: 'save', status: 'success' },
    // ],
    // buttons: [{ name: '删除11', type: 'button', status: 'info', code: 'eee' }],
    // tools: [
    //   { name: '删除1', type: 'button', status: 'info', code: 'open_import' },
    // ],
    // slots: {
    //   tools: 'toolbar_buttons',
    // },
  },
};
