import { getGeneSetByGenomeApi } from '#/api/apps/geneset';
import { IconEnum } from '#/enums/appEnum';
import { $t as t } from '#/locales';

// 主表格配置（一级：基因集列表）
export function useMainGridOptions(genomeId: string) {
  return {
    columns: [
      { fixed: 'left', title: '', type: 'checkbox', width: 50 },
      {
        field: 'geneset_id',
        title: t('geneset.list.geneSetId'),
        width: 100,
        sortable: true,
      },
      {
        field: 'geneset_name',
        title: t('geneset.list.geneSetName'),
        width: 200,
        showOverflow: false,
      },
      {
        field: 'description',
        title: t('geneset.list.description'),
        width: 300,
        showOverflow: false,
      },
      {
        field: 'gene_count',
        title: t('geneset.list.geneCount'),
        width: 120,
        sortable: true,
      },
      {
        field: 'create_time',
        title: t('geneset.list.createTime'),
        width: 180,
        formatter: ({ cellValue }: any) => {
          return cellValue ? new Date(cellValue * 1000).toLocaleString() : '-';
        },
      },
      {
        field: 'action',
        title: t('geneset.list.action'),
        width: 180,
        fixed: 'right',
        slots: { default: 'action' },
      },
    ],
    border: false,
    minHeight: 500,
    exportConfig: {},
    importConfig: {},
    keepSource: true,
    pagerConfig: {
      pageSize: 20,
    },
    proxyConfig: {
      autoLoad: !!genomeId, // 只有当 genomeId 存在时才自动加载
      response: {
        result: 'dataList',
        total: 'total',
      },
      ajax: {
        query: async ({ page }: any) => {
          if (!genomeId) {
            return { dataList: [], total: 0 };
          }
          return await getGeneSetByGenomeApi({
            genome_id: genomeId,
            page: page.currentPage,
            size: page.pageSize,
          });
        },
      },
    },
    id: 'main-geneset',
    rowConfig: {
      isHover: true,
    },
    customConfig: {
      storage: true,
    },
    toolbarConfig: {
      custom: true,
      export: true,
      import: false,
    },
  };
}

// 详情表格配置（二级：基因详情）
export function useDetailGridOptions() {
  return {
    columns: [
      {
        field: 'id',
        title: 'ID',
        width: 80,
      },
      {
        field: 'gene_id',
        title: t('geneset.list.headerGeneId'),
        width: 150,
        showOverflow: false,
      },
      {
        field: 'genome_id',
        title: t('geneset.list.headerGenomeId'),
        width: 120,
      },
      {
        field: 'create_time',
        title: t('geneset.list.headerCreateTime'),
        width: 180,
        formatter: ({ cellValue }: any) => {
          return cellValue ? new Date(cellValue * 1000).toLocaleString() : '-';
        },
      },
    ],
    border: true,
    stripe: true,
    showOverflow: true,
    height: 300,
    id: 'detail-genes',
  };
}

// 搜索表单配置
export function useSearchFormSchema(): any[] {
  return [
    {
      component: 'Input',
      componentProps: {
        placeholder: t('geneset.list.placeholderSearch'),
        allowClear: true,
      },
      fieldName: 'search',
      label: t('geneset.list.search'),
      formItemClass: 'col-span-1',
    },
  ];
} 
