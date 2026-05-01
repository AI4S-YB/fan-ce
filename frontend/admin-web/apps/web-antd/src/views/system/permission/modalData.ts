import type { VbenFormSchema } from '#/adapter/form';

import { getPopupContainer } from '@vben/utils';

import { getPermissionOptionsTreeApi } from '#/api/system/permission';
import { $t } from '#/locales';

export const formSchema: VbenFormSchema[] = [
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
    label: $t('system.permission.belongType'),
    fieldName: 'pid',
    component: 'ApiTreeSelect',
    rules: 'required',
    defaultValue: 0,
    componentProps: {
      allowClear: true,
      api: async () => {
        const data = await getPermissionOptionsTreeApi({});
        return [
          {
            id: 0,
            pid: 0,
            name: $t('system.permission.mainDir'),
            meta: { title: $t('system.permission.mainDir') },
            children: data,
          },
        ];
      },
      filterTreeNode(input: string, node: Recordable<any>) {
        if (!input || input.length === 0) {
          return true;
        }
        const title: string = node.meta?.title ?? '';
        if (!title) return false;
        return title.includes(input) || $t(title).includes(input);
      },
      getPopupContainer,
      showSearch: true,
      class: 'w-full',
      labelField: 'name',
      valueField: 'id',
      childrenField: 'children',
    },
    formItemClass: 'col-span-2 items-baseline',
  },
  {
    component: 'ApiSelect',
    defaultValue: 'system',
    componentProps: {
      allowClear: true,
      autoSelect: 'system',
      options: [
        { value: 'system', label: $t('system.permission.systemService') },
        { value: 'app', label: $t('system.permission.appService') },
      ],
      placeholder: $t('system.project.pleaseInput'),
    },
    fieldName: 'type',
    label: $t('system.permission.serviceType'),
    formItemClass: 'col-span-2 items-baseline',
  },
  {
    label: $t('system.user.realName'),
    fieldName: 'name',
    rules: 'required',
    component: 'Input',
    formItemClass: 'col-span-2 items-baseline',
  },
  {
    label: $t('system.menu.perms'),
    fieldName: 'code',
    rules: 'required',
    component: 'Input',
    formItemClass: 'col-span-2 items-baseline',
  },
  {
    label: $t('system.permission.apiUrl'),
    fieldName: 'uri',
    rules: 'required',
    component: 'Input',
    formItemClass: 'col-span-2 items-baseline',
  },
  {
    label: $t('system.permission.requestMethod'),
    fieldName: 'method',
    component: 'Select',
    defaultValue: 'POST',
    rules: 'required',
    componentProps: {
      options: [
        { label: 'GET', value: 'GET' },
        { label: 'POST', value: 'POST' },
        { label: 'PUT', value: 'PUT' },
        { label: 'DELETE', value: 'DELETE' },
      ],
    },
    formItemClass: 'col-span-2 items-baseline',
  },

  {
    label: $t('system.menu.sortOrder'),
    fieldName: 'sort',
    defaultValue: 0,
    component: 'InputNumber',
    formItemClass: 'col-span-2 items-baseline',
  },
];
