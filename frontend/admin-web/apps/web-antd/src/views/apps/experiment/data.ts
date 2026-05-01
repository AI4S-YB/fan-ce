import type { VbenFormProps } from '#/adapter/form';
import type { VxeGridProps } from '#/adapter/vxe-table';

import { ref } from 'vue';

import { $t } from '@vben/locales';
import { useVbenForm } from '#/adapter/form';
import { getExperimentListApi } from '#/api/apps/experiment';
import { getSampleOptionsApi } from '#/api/apps/sample';

export const sampleOptions = ref<any[]>([]);
const getSampleOptions = () => {
  getSampleOptionsApi({}).then((res) => {
    sampleOptions.value = res;
  });
};
getSampleOptions();
// Table 搜索表单
export const formOptions: VbenFormProps = {
  // 默认展开
  collapsed: false,
  submitOnEnter: true,
  schema: [
    {
      component: 'Input',
      fieldName: 'title',
      label: $t('system.dict.name'),
      componentProps: { allowClear: true },
    },
    {
      component: 'Input',
      fieldName: 'accession',
      label: $t('system.project.code'),
      componentProps: { allowClear: true },
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
          placeholder: $t('system.permission.pleaseSelect'),
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
  wrapperClass: 'grid-cols-3',
};
// Modal 提交表单
export const [Form, formApi] = useVbenForm({
  commonConfig: {
    // 所有表单项
    componentProps: {
      class: 'w-full',
    },
  },
  layout: 'horizontal',
  schema: [
    {
      component: 'Input',
      fieldName: 'id',
      label: 'id',
      dependencies: {
        show: false,
        triggerFields: ['title'],
      },
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.project.pleaseInput'),
        if: false,
      },
      fieldName: 'title',
      label: $t('system.experiment.experimentName'),
      rules: 'required',
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.project.pleaseInput'),
        if: false,
      },
      fieldName: 'accession',
      label: $t('system.experiment.experimentCode'),
      rules: 'required',
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Select',
      fieldName: 'sample_id',
      label: $t('system.project.sample'),
      formItemClass: 'col-span-2 items-baseline',
      componentProps: () => {
        return {
          options: sampleOptions.value,
          allowClear: true,
          filterOption: (value: any, option: any) => {
            return option.name.toLowerCase().includes(value.toLowerCase());
          },
          placeholder: $t('system.permission.pleaseSelect'),
          showSearch: true,
          fieldNames: {
            value: 'id',
            label: 'name',
          },
          if: true,
        };
      },
    },
    {
      component: 'Switch',
      componentProps: {
        class: 'w-auto',
      },
      fieldName: 'is_public',
      label: $t('system.experiment.isPublic'),
      defaultValue: true,
    },
    {
      component: 'Textarea',
      fieldName: 'description',
      formItemClass: 'col-span-3 items-baseline',
      label: $t('system.project.description'),
    },
  ],
  showDefaultActions: false,
  wrapperClass: 'grid-cols-3',
});

// Table 表格列表
export function gridOptions(): VxeGridProps<any> {
  return {
    columns: [
      { fixed: 'left', title: '', type: 'checkbox', width: 50 },
      { fixed: 'left', title: $t('component.table.index'), type: 'seq', width: 50 },
      {
        type: 'expand',
        title: $t('dataset.staging.metadata'),
        width: 60,
        slots: { content: 'expand_content' },
      },
      { field: 'title', title: $t('system.experiment.experimentName') },
      { field: 'accession', title: $t('system.experiment.experimentCode') },
      {
        field: 'is_public',
        title: $t('system.experiment.isPublic'),
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
          props: { dictType: 'experiment_status' },
        },
      },
      { field: 'description', title: $t('system.project.description') },
      {
        field: 'create_time',
        formatter: 'formatDateTime10',
        title: $t('system.menu.createTime'),
      },
      {
        field: 'action',
        fixed: 'right',
        slots: { default: 'action' },
        title: $t('system.dict.action'),
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
        query: async ({ page }: any) => {
          return await getExperimentListApi({
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
    },
  };
}
