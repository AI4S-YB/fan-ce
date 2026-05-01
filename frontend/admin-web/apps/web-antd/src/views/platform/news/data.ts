import type { VbenFormProps } from '#/adapter/form';
import type { VxeGridListeners, VxeGridProps } from '#/adapter/vxe-table';
import type { NewsRowType } from '#/api/platform/news';

import { h, ref } from 'vue';

import { useVbenForm } from '#/adapter/form';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { deleteNewsApi, getNewsListApi } from '#/api/platform/news';
import { useMessage } from '#/hooks/web/useMessage';
import { $t } from '@vben/locales';
import { getDictDatas } from '#/utils/dict/index';

const { createMessage, createConfirm } = useMessage();
export { type NewsRowType };

export const searchOption: VbenFormProps = {
  // 默认展开
  collapsed: false,
  submitOnEnter: true,
  schema: [
    {
      component: 'Input',
      fieldName: 'title',
      label: $t('platform.news.title2'),
      labelWidth: 50,
      componentProps: { allowClear: true },
    },
    {
      component: 'Select',
      fieldName: 'type',
      label: $t('system.menu.type'),
      labelWidth: 50,
      componentProps: {
        allowClear: true,
        placeholder: $t('platform.news.pleaseSelectType'),
        options: getDictDatas('news_type'),
      },
    },
    {
      component: 'Input',
      fieldName: 'author',
      label: $t('platform.news.author'),
      labelWidth: 50,
      componentProps: { allowClear: true },
    },
  ],
  // 控制表单是否显示折叠按钮
  showCollapseButton: true,
  // 按下回车时是否提交表单
  wrapperClass: 'grid-cols-3',
};

export const [Form, formApi] = useVbenForm({
  commonConfig: {
    // 所有表单项
    // componentProps: {
    //   class: 'w-full',
    // },
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
        triggerFields: ['title'],
      },
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('platform.news.pleaseInput', { field: $t('platform.news.title2') }),
      },
      fieldName: 'title',
      label: $t('platform.news.title2'),
      rules: 'required',
      labelWidth: 80,
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Select',
      componentProps: {
        placeholder: $t('platform.news.pleaseSelectType'),
        options: getDictDatas('news_type'),
      },
      fieldName: 'type',
      label: $t('system.menu.type'),
      rules: 'required',
      labelWidth: 80,
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('platform.news.pleaseInputAuthor'),
      },
      fieldName: 'author',
      label: $t('platform.news.author'),
      rules: 'required',
      labelWidth: 80,
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'RadioGroup',
      componentProps: {
        options: [
          { label: $t('dataset.list.visibility_public'), value: true },
          { label: $t('dataset.list.visibility_private'), value: false },
        ],
      },
      fieldName: 'is_public',
      label: $t('platform.news.isPublic'),
      labelWidth: 80,
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Textarea',
      fieldName: 'content',
      formItemClass: 'col-span-3 items-baseline',
      label: $t('platform.news.content'),
      labelWidth: 80,
      componentProps: {
        placeholder: $t('platform.news.pleaseInput', { field: $t('platform.news.content') }),
        rows: 4,
      },
      dependencies: {
        show: false, // 在Modal中使用富文本$t('platform.setting.edit')器替代
        triggerFields: ['title'],
      },
    },
  ],
  showDefaultActions: false,
  wrapperClass: 'grid-cols-3',
});

export const createGridOptions = (handleAction: any, handleDelete: any): VxeGridProps<NewsRowType> => ({
  columns: [
    { field: 'i', fixed: 'left', title: '', type: 'radio', width: 50 },
    { field: 'index', fixed: 'left', title: $t('component.table.index'), type: 'seq', width: 50 },
    { 
      field: 'title', 
      title: $t('platform.news.title2'),
      width: 200,
    },
    { 
      field: 'type', 
      title: $t('system.menu.type'),
      width: 100,
      cellRender: {
        name: 'DictTagStatus',
        props: { dictType: 'news_type' },
      },
    },
    { 
      field: 'content', 
      title: $t('platform.news.content'),
      // width: 300,
      showOverflow: 'tooltip',
      formatter: ({ cellValue }) => {
        // 移除HTML标签并截断显示
        const text = cellValue?.replace(/<[^>]*>/g, '') || '';
        return text.length > 50 ? text.substring(0, 50) + '...' : text;
      },
    },
    { 
      field: 'author', 
      title: $t('platform.news.author'),
      width: 120,
    },
    { 
      field: 'is_public', 
      title: $t('platform.news.isPublic'),
      width: 100,
      cellRender: {
        name: 'DictTagStatus',
        props: { dictType: 'is_public', valueType: 'boolean' },
      },
    },
    {
      field: 'create_time',
      title: $t('system.menu.createTime'),
      width: 160,
      formatter: ({ cellValue }) => {
        if (!cellValue) return '';
        return new Date(cellValue * 1000).toLocaleString();
      },
    },
    {
      align: 'right',
      cellRender: {
        name: 'CellOperation',
        attrs: {
          onClick: ({ code, row }: { code: string; row: any }) => {
            if (code === 'edit') {
              handleAction('edit', row);
            } else if (code === 'delete') {
              handleDelete(row, false);
            }
          },
        },
        options: ['edit', 'delete'],
      },
      field: 'operation',
      fixed: 'right',
      headerAlign: 'center',
      showOverflow: false,
      title: $t('platform.setting.action'),
      width: 150,
    },
  ],
  border: false,
  height: 'auto',
  exportConfig: {},
  importConfig: {},
  keepSource: true,
  pagerConfig: {
    pageSize: 10,
  },
  filterConfig: {
    remote: true,
  },
  radioConfig: {
    checkRowKey: 'id',
    reserve: true,
    highlight: true,
  },
  proxyConfig: {
    seq: true, // $t('platform.setting.enabled')动态序号代理
    sort: true, // $t('platform.setting.enabled')$t('platform.setting.sortOrder')代理
    filter: true, // $t('platform.setting.enabled')筛选代理
    form: true,
    ajax: {
      query: async ({ page, form }) => {
        const params = {
          id: 0,
          page: page.currentPage,
          size: page.pageSize,
          type: '',
          is_public: true,
          ...form,
        };
        return await getNewsListApi(params);
      },
      querySuccess: ({ response }) => {
        if (response.total !== 0) {
          if (Object.keys(selected.value).length > 0) {
            gridApi.grid.setRadioRow(selected.value);
          } else {
            gridApi.grid.setRadioRow(response.dataList[0]);
            selected.value = response.dataList[0];
          }
        }
      },
    },
  },
  rowConfig: {
    isHover: true,
    keyField: 'id',
  },
  stripe: true,
  toolbarConfig: {
    custom: false,
    export: false,
    import: false,
    refresh: true,
    zoom: true,
    loading: false,
  },
});

const clickOption = ref<any>({});
const selected = ref<any>({});

const handleDelete = async (rows: any = null, isBatch: boolean = false) => {
  if (isBatch) {
    const selecteds = gridApi.grid.getRadioRecord();
    if (Object.keys(selecteds).length === 0) {
      createMessage.warn($t('common.chooseSelect'));
    } else {
      createConfirm({
        iconType: 'warning',
        content: $t('common.delMessage'),
        centered: false,
        title: () => h('span', $t('common.warnning')),
        onCancel() {},
        onOk: async () => {
          try {
            await deleteNewsApi({ id: selecteds?.id });
            createMessage.success($t('common.delSuccessText'));
            gridApi.reload();
          } catch {}
        },
      });
    }
  } else {
    await deleteNewsApi({ id: rows.id });
    createMessage.success($t('common.delSuccessText'));
    gridApi.reload();
  }
};

const gridEvents: VxeGridListeners<NewsRowType> = {
  cellClick: ({ row }) => {
    selected.value = row;
    gridApi.grid.setRadioRow(selected.value);
  },
  radioChange: ({ row }) => {
    selected.value = row;
  },
};

// Grid和gridApi将在index.vue中创建
let Grid: any;
let gridApi: any;

export const createGrid = (handleAction: any) => {
  const [GridInstance, gridApiInstance] = useVbenVxeGrid({
    gridEvents,
    gridOptions: createGridOptions(handleAction, handleDelete),
    formOptions: searchOption,
  });
  
  Grid = GridInstance;
  gridApi = gridApiInstance;
  
  return { Grid: GridInstance, gridApi: gridApiInstance };
};

export { clickOption, Grid, gridApi, handleDelete, selected };
