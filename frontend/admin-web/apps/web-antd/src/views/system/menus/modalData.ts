import type { BasicColumn, FormSchema } from '#/components/Table';

import { getAllMenusApi } from '#/api/system';
// import { DICT_TYPE, getDictOptions } from '#/utils/dict'
import { SystemMenuTypeEnum } from '#/enums/systemEnum';
import { useRender } from '#/hooks/web/useRender';
import { $t } from '@vben/locales';

export const columns: BasicColumn[] = [
  {
    title: $t('system.menu.menuName'),
    dataIndex: 'name',
    width: 250,
    align: 'left',
  },
  {
    title: $t('system.menu.menuType'),
    dataIndex: 'type',
    width: 80,
    customRender: ({ text }) => {
      return useRender.renderDict(text, '');
    },
  },
  {
    title: $t('system.menu.icon'),
    dataIndex: 'icon',
    width: 60,
    customRender: ({ record }) => {
      return useRender.renderIcon(record.icon);
    },
  },
  {
    title: $t('system.role.sortOrder'),
    dataIndex: 'sort',
    width: 60,
  },

  {
    title: $t('system.menu.componentPath'),
    dataIndex: 'component',
    width: 140,
  },
  {
    title: $t('system.project.status'),
    dataIndex: 'status',
    width: 80,
    customRender: ({ text }) => {
      return useRender.renderDict(text, '');
    },
  },
];

export const searchFormSchema: FormSchema[] = [
  {
    label: $t('system.menu.menuName'),
    field: 'name',
    component: 'Input',
    colProps: { span: 8 },
  },
  {
    label: $t('system.project.status'),
    field: 'status',
    component: 'Select',
    componentProps: {
      options: [],
    },
    colProps: { span: 8 },
  },
];

export const formSchema: FormSchema[] = [
  {
    label: $t('system.project.code'),
    field: 'id',
    show: false,
    component: 'InputNumber',
  },
  {
    label: $t('system.menu.parentMenu'),
    field: 'pid',
    required: true,
    component: 'ApiTreeSelect',
    componentProps: {
      api: () => getAllMenusApi({}),
      parentLabel: $t('system.menu.mainDir'),
      parentValue: 0,
      handleTree: 'id',
      parentFiled: 'pid',
      labelField: 'title',
    },
    colProps: { span: 12 },
  },
  {
    label: $t('system.menu.menuTypeLabel'),
    field: 'type',
    required: true,
    defaultValue: 1,
    component: 'RadioButtonGroup',
    componentProps: {
      options: [
        { label: $t('system.menu.dirType'), value: 1 },
        { label: $t('system.menu.menuType'), value: 2 },
        { label: $t('system.menu.buttonType'), value: 3 },
      ],
    },
    colProps: { span: 12 },
  },
  {
    label: $t('system.menu.menuTitle'),
    field: 'title',
    helpMessage: $t('system.menu.displayName'),
    required: true,
    component: 'Input',
    colProps: { span: 12 },
  },
  {
    label: $t('system.menu.menuName'),
    field: 'name',
    helpMessage: $t('system.menu.nameUnique'),
    required: true,
    component: 'Input',
    colProps: { span: 12 },
  },
  {
    label: $t('system.menu.menuIcon'),
    field: 'icon',
    component: 'IconPicker',
    ifShow: ({ values }) => values.type !== SystemMenuTypeEnum.BUTTON,
    colProps: { span: 12 },
  },

  {
    label: $t('system.menu.accessPath'),
    field: 'path',
    required: true,
    component: 'Input',
    helpMessage: $t('system.menu.accessPathHelp'),
    ifShow: ({ values }) =>
      values.type === SystemMenuTypeEnum.MENU ||
      values.type === SystemMenuTypeEnum.DIR,
    colProps: { span: 12 },
  },
  {
    label: $t('system.menu.redirect'),
    field: 'redirect',
    component: 'Input',
    helpMessage: $t('system.menu.redirectHelp'),
    ifShow: ({ values }) => values.type === SystemMenuTypeEnum.DIR,
    colProps: { span: 12 },
  },

  {
    label: $t('system.menu.componentPath'),
    field: 'component',
    component: 'Input',
    helpMessage: $t('system.menu.componentPathHelp'),
    ifShow: ({ values }) =>
      values.type === SystemMenuTypeEnum.MENU ||
      values.type === SystemMenuTypeEnum.DIR,
    colProps: { span: 12 },
  },
  {
    label: $t('system.menu.sortOrder'),
    field: 'sort',
    required: true,
    component: 'InputNumber',
    defaultValue: 0,
    componentProps: { with: '100px' },
    colProps: { span: 12 },
  },
  {
    label: $t('system.menu.displayStatus'),
    field: 'is_visible',
    component: 'Switch',
    defaultValue: true,
    componentProps: {
      checkedChildren: $t('system.menu.show'),
      unCheckedChildren: $t('system.menu.hide'),
    },
    helpMessage: $t('system.menu.hideHelp'),
    ifShow: ({ values }) => values.type !== SystemMenuTypeEnum.BUTTON,
    colProps: { span: 12 },
  },

  {
    label: $t('system.menu.isCache'),
    field: 'is_cache',
    component: 'Switch',
    componentProps: {
      checkedChildren: $t('system.menu.cache'),
      unCheckedChildren: $t('system.menu.noCache'),
    },
    colProps: { span: 12 },
    helpMessage: $t('system.menu.cacheHelp'),
    ifShow: ({ values }) => values.type === SystemMenuTypeEnum.MENU,
  },
  {
    field: 'divider-selects3',
    component: 'Divider',
    label: $t('system.menu.extendedInfo'),
    colProps: {
      span: 24,
    },
  },
  {
    label: $t('system.menu.apiInterface'),
    field: 'permission_list',
    component: 'Select',
    slot: 'resourceApiList',
    defaultValue: [],
    colProps: { span: 24 },
  },

  {
    label: $t('dataset.staging.metadata'),
    field: 'meta',
    component: 'Input',
    slot: 'metaJson',
    helpMessage: [
      $t('system.menu.metaHelpLine1'),
      $t('system.menu.metaHelpLine2'),
    ],
    colProps: { span: 24 },
  },
];
