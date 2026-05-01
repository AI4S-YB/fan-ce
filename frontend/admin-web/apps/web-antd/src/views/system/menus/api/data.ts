// 资源接口 表格
// 资源接口 表格
import type { BasicColumn, FormSchema } from '#/components/Table';

import { getPermissionControllerApi } from '#/api/system/permission';
import { $t } from '@vben/locales';

export const getAPiTreeList = () => {
  return {
    api: () => getPermissionControllerApi({}),
    params: {},
    showSearch: true,
    labelField: 'name',
    valueField: 'id',
  };
};

export const resourceApiColumns: BasicColumn[] = [
  {
    title: 'resourceId',
    dataIndex: 'resourceId',
    ifShow: false,
  },

  {
    title: $t('platform.api.apiName'),
    dataIndex: 'name',
    align: 'center',
    width: 100,
  },
  {
    title: $t('system.menu.permissionCode'),
    dataIndex: 'code',
    align: 'center',
    width: 130,
  },
  {
    title: $t('system.menu.urlAddress'),
    dataIndex: 'uri',
    // ellipsis: true,
    align: 'left',
    minWidth: 10,
  },
];

// 资源接口 编辑表单
export const editResourceApiFormSchema = (): FormSchema[] => {
  return [
    {
      label: $t('system.menu.isManualEntry'),
      field: 'isInput',
      component: 'RadioGroup',
      show: false,
    },
    {
      label: 'id',
      field: 'id',
      component: 'InputNumber',
      show: false,
    },
    {
      label: $t('system.menu.tempId'),
      field: 'tempId',
      component: 'Input',
      show: false,
    },
    {
      component: 'ApiSelect',
      label: $t('system.menu.belongNode'),
      field: 'pid',
      colProps: { span: 24 },
      componentProps: {
        ...getAPiTreeList(),
      },
    },
    {
      label: $t('system.permission.serviceType'),
      field: 'type',
      component: 'ApiSelect',
      defaultValue: 'system',
      componentProps: () => {
        return {
          getPopupContainer: () => document.body,
          showSearch: true,
          autoSelect: 'first',
          labelField: 'name',
          valueField: 'id',
          options: [
            { value: 'system', label: $t('system.permission.systemService') },
            { value: 'app', label: $t('system.permission.appService') },
          ],
        };
      },
    },
    {
      label: $t('platform.api.apiName'),
      field: 'name',
      component: 'Input',
      required: true,
    },
    {
      label: $t('system.menu.uniqueCode'),
      field: 'code',
      component: 'Input',
      required: true,
    },
    {
      label: $t('system.menu.urlAddress'),
      field: 'uri',
      component: 'Input',
      required: true,
    },
    {
      label: $t('system.menu.requestType'),
      field: 'method',
      component: 'ApiSelect',
      required: true,
      defaultValue: 'POST',
      componentProps: () => {
        return {
          getPopupContainer: () => document.body,
          // ...enumComponentProps(EnumEnum.HttpMethod),
          options: [
            { value: 'ALL', label: $t('system.menu.all') },
            { value: 'GET', label: 'GET' },
            { value: 'POST', label: 'POST' },
            { value: 'PUT', label: 'PUT' },
            { value: 'DELETE', label: 'DELETE' },
          ],
        };
      },
    },
  ];
};

// 资源接口 选择表单
export const selectResourceApiFormSchema = (
  handleServiceChange: Fn,
  handleControllerChange: Fn,
  handleUriChange: Fn,
  handleUriDeselect: Fn,
): FormSchema[] => {
  return [
    {
      label: $t('system.permission.serviceType'),
      field: 'type',
      component: 'ApiSelect',
      helpMessage: [''],
      defaultValue: 'system',
      componentProps: () => {
        return {
          getPopupContainer: () => document.body,
          onChange: handleServiceChange,
          showSearch: true,
          autoSelect: 'first',
          // api: getPermissionOptionsTreeApi,
          labelField: 'name',
          valueField: 'id',
          options: [
            // 后端有几个服务，就写几个
            { value: 'system', label: $t('system.permission.systemService') },
            { value: 'app', label: $t('system.permission.appService') },
          ],
        };
      },
    },
    {
      label: $t('system.permission.category'),
      field: 'controller',
      component: 'Select',
      componentProps: {
        getPopupContainer: () => document.body,
        onChange: handleControllerChange,
        showSearch: true,
      },
    },
    {
      label: $t('system.permission.apiUrl'),
      field: 'uri',
      component: 'Select',
      colProps: { span: 24 },
      componentProps: {
        // fieldNames: { label: 'name', value: 'id' },
        onChange: handleUriChange,
        onDeselect: handleUriDeselect,
        mode: 'multiple',
        'option-label-prop': 'value',
        // getPopupContainer: () => document.body,
      },
    },
  ];
};
