import type { VbenFormProps } from '#/adapter/form';
import type { VxeGridProps } from '#/adapter/vxe-table';
import type { ProjectRowType } from '#/api/system/project';

import { ref } from 'vue';

import { useVbenForm } from '#/adapter/form';
import { getDatasetOptionsApi, type DatasetOptionItem } from '#/api/apps/dataset';
import { getSampleOptionsApi } from '#/api/apps/sample';
import { getProjectListApi } from '#/api/system/project';
import { $t } from '@vben/locales';

const databaseOptions = ref<any[]>([]);
const sampleOptions = ref<any[]>([]);
const getDatabaseOptions = () => {
  getDatasetOptionsApi({ page: 1, size: 999 }).then((res: DatasetOptionItem[]) => {
    databaseOptions.value = (res || []).map((item) => ({
      id: item.id,
      name: item.title || item.name || `dataset-${item.id}`,
      title: item.title || item.name || `dataset-${item.id}`,
      dataset_code: item.dataset_code,
      dataset_type: item.dataset_type,
      version: item.version,
      file_path: item.file_path,
    }));
  });
};
const getSampleOptions = () => {
  getSampleOptionsApi({}).then((res) => {
    sampleOptions.value = res;
  });
};
getDatabaseOptions();
getSampleOptions();

export const formOptions: VbenFormProps = {
  // 默认展开
  collapsed: false,
  submitOnEnter: true,
  schema: [
    {
      component: 'Input',
      fieldName: 'name',
      label: $t('system.project.name'),
      componentProps: { allowClear: true },
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: $t('system.project.code'),
    },
    {
      component: 'Select',
      fieldName: 'database_id',
      label: $t('system.project.data'),
      // defaultValue: databaseOptions.value,

      componentProps: () => {
        return {
          options: databaseOptions.value,
          allowClear: true,
          filterOption: (value: any, option: any) => {
            return option.name.toLowerCase().includes(value.toLowerCase());
          },
          placeholder: $t('system.project.pleaseInput'),
          showSearch: true,
          loading: databaseOptions.value.length === 0,
          fieldNames: {
            value: 'id',
            label: 'name',
          },
          if: true,
        };
      },
    },
    {
      component: 'Select',
      fieldName: 'sample_id',
      label: $t('system.project.sample'),
      componentProps: () => {
        return {
          options: sampleOptions.value,
          allowClear: true,
          filterOption: (value: any, option: any) => {
            return option.name.toLowerCase().includes(value.toLowerCase());
          },
          placeholder: $t('system.project.pleaseInput'),
          showSearch: true,
          fieldNames: {
            value: 'id',
            label: 'name',
          },
          if: true,
        };
      },
    },
  ],
  // 控制表单是否显示折叠按钮
  showCollapseButton: true,
  // 按下回车时是否提交表单
  wrapperClass: 'grid-cols-4',
};
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
      fieldName: 'action',
      label: 'action',
      dependencies: {
        show: false,
        triggerFields: ['action'],
      },
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
        if: false,
      },
      dependencies: {
        disabled(values) {
          return values.action === 'link';
        },
        triggerFields: ['database_id'],
      },
      fieldName: 'name',
      label: $t('system.project.name'),
      rules: 'required',
      formItemClass: 'pw-80',
    },

    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
        if: false,
      },
      dependencies: {
        disabled(values) {
          return values.action === 'link';
        },
        triggerFields: ['database_id'],
      },
      fieldName: 'code',
      label: $t('system.project.code'),
      rules: 'required',
      formItemClass: 'pw-80',
    },
    // {
    //   component: 'Select',
    //   fieldName: 'database_id',
    //   label: '数据',
    //   defaultValue: databaseOptions.value,
    //   componentProps: () => {
    //     return {
    //       options: databaseOptions.value,
    //       allowClear: true,
    //       filterOption: (value: any, option: any) => {
    //         return option.name.toLowerCase().includes(value.toLowerCase());
    //       },
    //       placeholder: $t('system.project.pleaseInput'),
    //       showSearch: true,
    //       mode: 'multiple',
    //       fieldNames: {
    //         value: 'id',
    //         label: 'name',
    //       },
    //     };
    //   },
    // },
    // {
    //   component: 'Select',
    //   fieldName: 'sample_id',
    //   label: '样本',
    //   componentProps: () => {
    //     return {
    //       options: sampleOptions.value,
    //       allowClear: true,
    //       filterOption: (value: any, option: any) => {
    //         return option.name.toLowerCase().includes(value.toLowerCase());
    //       },
    //       placeholder: $t('system.project.pleaseInput'),
    //       showSearch: true,
    //       mode: 'multiple',
    //       fieldNames: {
    //         value: 'id',
    //         label: 'name',
    //       },
    //       if: true,
    //     };
    //   },
    // },
    {
      component: 'Switch',
      defaultValue: false,
      fieldName: 'is_public',
      help: $t('system.project.publicHelp'),
      label: $t('system.project.status'),
      componentProps: {
        class: 'w-auto',
      },
    },
    {
      component: 'Textarea',
      fieldName: 'remark',
      label: $t('system.user.remark'),
    },
  ],
  showDefaultActions: false,
  wrapperClass: 'grid-cols-1',
});

export const gridOptions: VxeGridProps<ProjectRowType> = {
  columns: [
    { fixed: 'left', title: '', type: 'checkbox', width: 50 },
    { fixed: 'left', title: $t('component.table.index'), type: 'seq', width: 50 },
    { field: 'name', title: $t('system.project.name'), align: 'left' },
    { field: 'code', title: $t('system.project.code') },
    { field: 'user_name', title: $t('system.project.userName') },
    {
      field: 'is_public',
      title: $t('system.project.status'),
      cellRender: {
        name: 'DictTagStatus',
        props: { dictType: 'is_public', valueType: 'boolean' },
      },
    },
    {
      field: 'status',
      title: $t('system.project.status'),
      cellRender: {
        name: 'DictTagStatus',
        props: { dictType: 'project_status' },
      },
    },
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
      minWidth: 120,
    },
  ],
  height: 'auto',
  align: 'center',
  exportConfig: {},
  importConfig: {},
  keepSource: true,
  pagerConfig: {
    pageSize: 10,
  },
  loadingConfig: {
    text: $t('system.project.pleaseInput'),
  },
  proxyConfig: {
    ajax: {
      query: async ({ page }, formData) => {
        return await getProjectListApi({
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
    buttons: [
      { name: $t('system.dict.add'), code: 'myAdd', status: 'primary' },
      { name: $t('system.dict.delete'), code: 'myDel', status: 'error' },
      { name: $t('component.upload.save'), code: 'mySave', status: 'success' },
    ],
    custom: true,
    export: true,
    import: true,
    refresh: true,
    zoom: true,
    loading: false,
  },
};
