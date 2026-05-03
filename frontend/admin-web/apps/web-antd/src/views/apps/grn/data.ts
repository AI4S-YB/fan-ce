import type { VxeGridListeners, VxeGridProps } from '#/adapter/vxe-table';
import { ref } from 'vue';

import { $t } from '@vben/locales';

import type { GrnItem, DynamicColumnConfig } from './types';

import { getGrnListApi } from './api';
import { getDatasetOptionsApi } from '#/api/apps/dataset';
import { ACTION_COLUMN_FLAG } from '#/components/Table/src/const';

// 固定列配置 - 调控关系表格
const fixedColumns: DynamicColumnConfig[] = [
  {
    dataIndex: 'target_gene',
    title: $t('grn.list.targetGene'),
    width: 150,
  },
  {
    dataIndex: 'target_gene_name',
    title: $t('grn.list.targetGeneName'),
    width: 120,
  },
  {
    dataIndex: 'tf_gene',
    title: $t('grn.list.transcriptionFactor'),
    width: 150,
  },
  {
    dataIndex: 'tf_name',
    title: $t('grn.list.tfName'),
    width: 100,
  },
  {
    dataIndex: 'tf_family',
    title: $t('grn.list.tfFamily'),
    width: 100,
  },
  {
    dataIndex: 'peak_fold_change',
    title: $t('grn.list.regulationStrength'),
    type: 'number',
    width: 110,
  },
  {
    dataIndex: 'c_score',
    title: $t('grn.list.confidence'),
    type: 'number',
    width: 80,
  },
  {
    dataIndex: 'weight',
    title: $t('grn.list.weight'),
    type: 'number',
    width: 80,
  },
];

// 获取列宽度（每列增加50px）
const getColumnWidth = (key: string) => {
  const widthMap: Record<string, number> = {
    gene_symbol: 200,
    gene_name: 250,
    gene_type: 170,
    chromosome: 150,
    start_position: 170,
    end_position: 170,
    expression_level: 170,
    regulation_type: 170,
    interaction_type: 170,
    confidence_level: 170,
    regulation_direction: 170,
    binding_site: 170,
    evidence_score: 170,
  };
  
  return widthMap[key] || 170;  // 默认宽度也增加50px
};

// 生成动态列配置 - 只处理edge_attributes的额外属性
export const generateDynamicColumns = (items: any[]) => {
  if (items.length === 0) return [];
  
  // 收集edge_attributes的额外属性键
  const attributeKeys = new Set<string>();
  
  items.forEach(item => {
    // 只收集edge_attributes的额外属性（排除已经在固定列中显示的）
    if (item.edge_attributes) {
      Object.keys(item.edge_attributes).forEach(key => {
        if (!['peak_fold-change', 'c_score', 'weight', 'created_at'].includes(key)) {
          attributeKeys.add(key);
        }
      });
    }
  });
  
  // 生成列配置
  return Array.from(attributeKeys).map(key => {
    const labelMap: Record<string, string> = {
      interaction_type: $t('grn.list.interactionType'),
      confidence_level: $t('grn.list.confidenceLevel'),
      regulation_direction: $t('grn.list.regulationDirection'),
      binding_site: $t('grn.list.bindingSite'),
      evidence_score: $t('grn.list.evidenceScore'),
    };

    return {
      field: `edge_${key}`, // 添加前缀以避免冲突
      title: labelMap[key] || key,
      width: getColumnWidth(key),
    };
  });
};

// Grid配置
export function gridOptions(gridApi?: any): VxeGridProps<GrnItem & Record<string, any>> {
  return {
    columns: [
      { fixed: 'left', title: '', type: 'checkbox', width: 50 },
      { fixed: 'left', title: $t('component.table.index'), type: 'seq', width: 50 },
      // 固定列 - 调控关系相关（每列增加50px）
      { field: 'target_gene', title: $t('grn.list.targetGene'), width: 200 },
      { field: 'target_gene_name', title: $t('grn.list.targetGeneName'), width: 170 },
      { field: 'tf_gene', title: $t('grn.list.transcriptionFactor'), width: 200 },
      { field: 'tf_name', title: $t('grn.list.tfName'), width: 150 },
      { field: 'tf_family', title: $t('grn.list.tfFamily'), width: 150 },
      { field: 'peak_fold_change', title: $t('grn.list.regulationStrength'), width: 160 },
      { field: 'c_score', title: $t('grn.list.confidence'), width: 130 },
      { field: 'weight', title: $t('grn.list.weight'), width: 130 },
      // 动态列将在运行时添加
      {
        field: 'action',
        fixed: 'right',
        slots: { default: 'action' },
        title: $t('system.dict.action'),
        width: 120,  // 固定宽度
        align: 'left',  // 左对齐
        flag: ACTION_COLUMN_FLAG,  // 添加操作列标记
      },
    ],
    border: false,
    height: 'auto',
    exportConfig: {},
    importConfig: {},
    keepSource: true,
    checkboxConfig: {
      // checkMethod: ({ row }: any) => {
      //   // 当已选择两个时，只允许取消已选，不允许再选新的
      //   try {
      //     const selected: (GrnItem & Record<string, any>)[] = gridApi?.grid?.getCheckboxRecords?.() || [];
      //     if (selected.length >= 2) {
      //       return selected.some((r) => r.id === row.id);
      //     }
      //     return true;
      //   } catch {
      //     return true;
      //   }
      // },
    },
    pagerConfig: {
      pageSize: 10,
    },
    proxyConfig: {
      ajax: {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        query: async ({ page }: any, formValues: any) => {
          // 先决条件：必须选择调控网络数据（来自 /database/options, type: 9）
          if (!formValues?.database_id) {
            return { dataList: [] };
          }

          const filePath = formValues?.database_id?.option?.file_path;
          if (!filePath) {
            return { dataList: [] };
          }

          const response = await getGrnListApi({
            page: page.currentPage,
            page_size: page.pageSize,
            file_path: filePath,
            keyword: formValues?.keyword,
          });

          const items = (response as any)?.items ?? (response as any)?.data?.items ?? [];
          const processedItems = items.map((item: GrnItem, index: number) => ({
            // 为每个调控关系生成唯一ID
            id: `${item.node1.name}_${item.node2.name}_${index}`,
            
            // 展平基本信息到顶层，便于表格显示
            target_gene: item.node1.name,
            target_gene_name: item.node1.attributes?.target_gene_name || '',
            target_gene_description: item.node1.attributes?.target_gene_description || '',
            
            tf_gene: item.node2.name,
            tf_name: item.node2.attributes?.tf_name || '',
            tf_family: item.node2.attributes?.tf_family || '',
            
            peak_fold_change: item.edge_attributes['peak_fold-change'],
            c_score: item.edge_attributes.c_score,
            weight: item.edge_attributes.weight,
            created_at: item.edge_attributes.created_at,
            
            // 保留原始结构供详情使用
            node1: item.node1,
            node2: item.node2,
            edge_attributes: item.edge_attributes,
            
            // 只展平edge_attributes的额外属性
            ...Object.keys(item.edge_attributes || {}).reduce((acc, key) => {
              if (!['peak_fold-change', 'c_score', 'weight', 'created_at'].includes(key)) {
                acc[`edge_${key}`] = item.edge_attributes[key];
              }
              return acc;
            }, {} as Record<string, any>),
          }));

          // 数据加载完成后，更新动态列
          if (gridApi && processedItems.length > 0) {
            const dynamicColumns = generateDynamicColumns(processedItems);
              
              // 获取基础列（排除action列）
              const columns = gridApi.state?.gridOptions?.columns;
              if (columns) {
                const baseColumns = columns.slice(0, -1);
                const actionColumn = columns[columns.length - 1];
                
                // 更新列配置
                const newColumns = [
                  ...baseColumns,
                  ...dynamicColumns,
                  actionColumn,
                ];
                
                // 更新表格列配置
                gridApi.setGridOptions({
                  columns: newColumns,
                });
              }
          }

          // 返回正确的分页信息格式
          return { 
            dataList: processedItems,
            total: (response as any)?.total ?? 0,
            page: (response as any)?.page ?? 1,
            pageSize: (response as any)?.page_size ?? 10,
            totalPages: (response as any)?.total_pages ?? 0
          };
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

// 表单配置（如果需要搜索功能）
export function formOptions(onFilePathChange?: (filePath: string) => void) {
  // 下拉选项：/database/options, type: 9
  const databaseOptions = ref<any[]>([]);
  const getDatabaseOptions = () => {
    getDatasetOptionsApi({ dataset_type: 'interaction' }).then((res: any) => {
      databaseOptions.value = res;
      return res;
    });
  };
  getDatabaseOptions();

  return {
    collapsed: false,
    submitOnEnter: true,
    submitOnChange: true,
    showCollapseButton: true,
    wrapperClass: 'grid-cols-4',
    schema: [
      {
        component: 'Select',
        fieldName: 'database_id',
        label: $t('grn.list.networkData'),
        rules: 'required',
        formItemClass: 'col-span-2',
        componentProps: (): any => {
          return {
            options: databaseOptions.value,
            allowClear: true,
            placeholder: $t('system.permission.pleaseSelect'),
            showSearch: true,
            filterOption: (value: any, option: any) => {
              return option.name?.toLowerCase?.().includes?.(value.toLowerCase());
            },
            fieldNames: {
              value: 'id',
              label: 'name',
            },
            labelInValue: true,
            onChange: (value: any) => {
              const filePath = value?.option?.file_path || '';
              onFilePathChange?.(filePath);
            },
          };
        },
      },
      {
        component: 'Input',
        fieldName: 'keyword',
        label: $t('grn.list.keyword'),
        formItemClass: 'col-span-2',
        componentProps: () => ({
          allowClear: true,
          placeholder: $t('grn.list.inputGeneId'),
        }),
      },
    ],
  };
}
