import type { VbenFormProps } from '#/adapter/form';

import { ref } from 'vue';

import { $t } from '@vben/locales';

import { useVbenForm } from '#/adapter/form';
import { getSampleListApi } from '#/api/apps/sample';
import { getBreedingProgramListApi } from '#/api/breeding/program';

const sampleOptions = ref();
const getSampleOptions = async () => {
  const res = await getBreedingProgramListApi({ page: 1, size: 100 });
  sampleOptions.value = (res?.items || []).map((p) => ({ id: p.id, name: p.name }));
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
      fieldName: 'sample_name',
      label: $t('system.sample.sampleName'),
      componentProps: { allowClear: true },
    },
    {
      component: 'Input',
      fieldName: 'sample_code',
      label: $t('system.sample.sampleCode'),
      componentProps: { allowClear: true },
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
        triggerFields: ['name'],
      },
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.project.pleaseInput'),
        if: false,
      },
      fieldName: 'sample_name',
      label: $t('system.sample.sampleName'),
      rules: 'required',
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.project.pleaseInput'),
        if: false,
      },
      fieldName: 'sample_code',
      label: $t('system.sample.sampleCode'),
      rules: 'required',
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Switch',
      componentProps: {
        class: 'w-auto',
      },
      fieldName: 'is_public',
      label: $t('system.sample.isPublic'),
      defaultValue: true,
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        filterOption: true,
        options: sampleOptions,
        placeholder: $t('system.permission.pleaseSelect'),
        showSearch: true,
        fieldNames: {
          value: 'id',
          label: 'name',
        },
      },
      fieldName: 'project_id',
      label: $t('system.sample.project'),
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Textarea',
      fieldName: 'remark',
      formItemClass: 'col-span-3 items-baseline',
      label: $t('system.project.description'),
    },
  ],
  showDefaultActions: false,
  wrapperClass: 'grid-cols-3',
});

// Table 表格列表
export const gridOptions: any = () => {
  return {
    columns: [
      { fixed: 'left', title: '', type: 'checkbox', width: 50 },
      {
        type: 'expand',
        title: $t('dataset.staging.metadata'),
        slots: { default: 'expand_default', content: 'expand_content' },
      },
      { field: 'sample_name', title: $t('system.sample.sampleName') },
      { field: 'sample_code', title: $t('system.sample.sampleCode') },
      {
        field: 'is_public',
        title: $t('system.sample.isPublic'),
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
          props: { dictType: 'sample_status' },
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
    expandConfig: {
      expandAll: false,
    },
    proxyConfig: {
      ajax: {
        query: async ({ page }: any) => {
          return await getSampleListApi({
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
};
