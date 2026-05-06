import type {
  DynamicColumnConfig,
  GermplasmFieldSchemaItem,
  GermplasmItem,
} from './types';

import type { VxeGridProps } from '#/adapter/vxe-table';

import { ref } from 'vue';

import { $t } from '@vben/locales';

import {
  getGermplasmImportBatchListApi,
  getGermplasmListApi,
  getGermplasmTaxonomyOptionsApi,
} from './api';

const taxonomyOptions = ref<any[]>([]);
const batchOptions = ref<any[]>([]);

// 固定列配置
const fixedColumns: DynamicColumnConfig[] = [
  {
    dataIndex: 'accession_id',
    title: $t('germplasm.list.id'),
    width: 140,
  },
  {
    dataIndex: 'display_name',
    title: $t('germplasm.list.displayName'),
    width: 160,
  },
  {
    dataIndex: 'english_name',
    title: $t('germplasm.list.englishName'),
    width: 220,
  },
  {
    dataIndex: 'breeding_material_count',
    title: $t('germplasm.list.breedingMaterial'),
    type: 'number',
    width: 100,
  },
  {
    dataIndex: 'breeding_program_count',
    title: $t('germplasm.list.relatedProgram'),
    type: 'number',
    width: 100,
  },
  {
    dataIndex: 'breeding_material_codes_text',
    title: $t('germplasm.list.representativeMaterial'),
    width: 220,
  },
  {
    dataIndex: 'taxonomy_name',
    title: $t('germplasm.list.species'),
    width: 200,
  },
  {
    dataIndex: 'batch_code',
    title: $t('germplasm.list.importBatch'),
    width: 180,
  },
];

// 获取列宽度
const getColumnWidth = (key: string) => {
  const widthMap: Record<string, number> = {
    用途: 160,
    花朵性状: 220,
    植株特征: 220,
    育种历史: 260,
  };

  return widthMap[key] || 120;
};

// 生成动态列配置
export const generateDynamicColumns = (items: GermplasmItem[]) => {
  if (items.length === 0) return [];

  const schemaMap = new Map<string, GermplasmFieldSchemaItem>();
  items.forEach((item) => {
    (item.field_schema || []).forEach((field) => {
      if (!field.is_dynamic) {
        return;
      }
      const schemaKey =
        field.field_label || field.source_header || field.field_key;
      if (!schemaMap.has(schemaKey)) {
        schemaMap.set(schemaKey, field);
      }
    });
  });

  const schemaItems = [...schemaMap.values()].sort(
    (left, right) => (left.display_order || 0) - (right.display_order || 0),
  );
  if (schemaItems.length > 0) {
    return schemaItems.map((field) => {
      const title = field.field_label || field.source_header || field.field_key;
      return {
        field: title,
        title,
        width: getColumnWidth(title),
      };
    });
  }

  const attributeKeys = new Set<string>();
  items.forEach((item) => {
    if (item.attributes) {
      Object.keys(item.attributes).forEach((key) => {
        if (!['created_at'].includes(key)) {
          attributeKeys.add(key);
        }
      });
    }
  });

  return [...attributeKeys].map((key) => ({
    field: key,
    title: key,
    width: getColumnWidth(key),
  }));
};

function buildBaseColumns() {
  const columns: any[] = [
    { fixed: 'left', title: $t('germplasm.list.seq'), type: 'seq', width: 50 },
    ...fixedColumns.map((column) => ({
      field: column.dataIndex,
      title: column.title,
      width: column.width,
    })),
    {
      field: 'is_public',
      title: $t('germplasm.list.public'),
      width: 80,
      slots: { default: 'is_public' },
    },
    {
      field: 'action',
      fixed: 'right',
      slots: { default: 'action' },
      title: $t('germplasm.list.action'),
      minWidth: 120,
    },
  ];
  return columns;
}

function applyGridColumns(gridApi: any, dynamicColumns: any[]) {
  if (!gridApi) {
    return;
  }
  const baseColumns = buildBaseColumns();
  const actionColumn = baseColumns[baseColumns.length - 1];
  gridApi.setGridOptions({
    columns: [...baseColumns.slice(0, -1), ...dynamicColumns, actionColumn],
  });
}

// Grid配置
export function gridOptions(gridApi?: any): VxeGridProps<GermplasmItem> {
  return {
    columns: buildBaseColumns(),
    border: false,
    height: 'auto',
    exportConfig: {},
    importConfig: {},
    keepSource: true,
    pagerConfig: {
      pageSize: 10,
    },
    proxyConfig: {
      ajax: {
        query: async ({ page }: any, formValues: any) => {
          const taxonomyTaxId =
            formValues?.taxonomy_tax_id ??
            (taxonomyOptions.value.length === 1
              ? taxonomyOptions.value[0].value
              : undefined);
          const batchId =
            formValues?.batch_id ??
            (batchOptions.value.length === 1
              ? batchOptions.value[0].value
              : undefined);

          if (!taxonomyTaxId) {
            applyGridColumns(gridApi, []);
            return { dataList: [], total: 0 };
          }

          const response = await getGermplasmListApi({
            page: page.currentPage,
            size: page.pageSize,
            taxonomy_tax_id: Number(taxonomyTaxId),
            batch_id: batchId ? Number(batchId) : undefined,
            keyword: formValues?.keyword,
            status: 'active',
          });

          const items =
            (response as any)?.items ?? (response as any)?.data?.items ?? [];
          const processedItems = items.map((item: GermplasmItem) => ({
            ...item,
            ...item.attributes,
            accession_id: item.accession_id || item.id,
            breeding_material_count:
              item.breeding_summary?.breeding_material_count ?? 0,
            breeding_program_count:
              item.breeding_summary?.breeding_program_count ?? 0,
            breeding_material_codes_text:
              item.breeding_summary?.breeding_material_codes?.join(', ') || '-',
            taxonomy_name:
              item.taxonomy?.scientific_name ||
              item.taxonomy?.common_name ||
              '-',
          }));

          // 数据加载完成后，更新动态列
          applyGridColumns(gridApi, generateDynamicColumns(processedItems));

          return {
            dataList: processedItems,
            total: (response as any)?.total ?? 0,
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
export function formOptions(
  initialTaxonomyTaxId?: number,
  initialBatchId?: number,
  onTaxonomyChange?: (taxonomyTaxId?: number) => void,
  onBatchChange?: (batchId?: number) => void,
  onAutoSelectBatch?: (batchId?: number) => void,
) {
  const loadTaxonomyOptions = async (keyword?: string) => {
    const response = await getGermplasmTaxonomyOptionsApi({
      keyword,
      limit: 100,
      active_only: 1,
      with_germplasm_only: 1,
    });
    const items =
      (response as any)?.items ?? (response as any)?.data?.items ?? [];
    taxonomyOptions.value = items.map((item: any) => ({
      label: item.common_name
        ? `${item.scientific_name} (${item.common_name})`
        : item.scientific_name,
      value: item.tax_id,
      raw: item,
    }));
    return taxonomyOptions.value;
  };

  const loadBatchOptions = async (taxonomyTaxId?: number) => {
    if (!taxonomyTaxId) {
      batchOptions.value = [];
      return [];
    }
    const response = await getGermplasmImportBatchListApi({
      page: 1,
      size: 100,
      taxonomy_tax_id: taxonomyTaxId,
      status: 'imported',
    });
    const records = (response as any)?.items ?? [];
    batchOptions.value = records.map((item: any) => ({
      label: `${item.batch_code}${item.source_filename ? ` / ${item.source_filename}` : ''}`,
      value: item.id,
      raw: item,
    }));
    return batchOptions.value;
  };

  void loadTaxonomyOptions();
  if (initialTaxonomyTaxId) {
    void loadBatchOptions(initialTaxonomyTaxId).then((items) => {
      const selectedBatchId =
        initialBatchId ??
        (items.length > 0 ? Number(items[0].value) : undefined);
      onAutoSelectBatch?.(selectedBatchId);
    });
  }

  return {
    collapsed: false,
    submitOnEnter: true,
    submitOnChange: true,
    showCollapseButton: true,
    wrapperClass: 'grid-cols-4',
    schema: [
      {
        component: 'Select',
        fieldName: 'taxonomy_tax_id',
        label: $t('germplasm.list.species'),
        formItemClass: 'col-span-2',
        componentProps: (): any => {
          return {
            options: taxonomyOptions.value,
            allowClear: true,
            placeholder: $t('germplasm.list.placeholderTaxonomy'),
            showSearch: true,
            filterOption: false,
            onChange: (value: number | undefined) => {
              const nextTaxonomyTaxId =
                value !== undefined && value !== null
                  ? Number(value)
                  : undefined;
              onTaxonomyChange?.(nextTaxonomyTaxId);
              void loadBatchOptions(nextTaxonomyTaxId).then((items) => {
                const nextBatchId =
                  items.length > 0 ? Number(items[0].value) : undefined;
                onAutoSelectBatch?.(nextBatchId);
              });
            },
            onSearch: (value: string) => {
              void loadTaxonomyOptions(value);
            },
          };
        },
      },
      {
        component: 'Select',
        fieldName: 'batch_id',
        label: $t('germplasm.list.importBatch'),
        formItemClass: 'col-span-2',
        componentProps: (): any => ({
          options: batchOptions.value,
          allowClear: false,
          placeholder:
            batchOptions.value.length > 0
              ? $t('germplasm.list.placeholderBatch')
              : $t('germplasm.list.noBatchAvailable'),
          showSearch: true,
          onChange: (value: number | undefined) => {
            onBatchChange?.(
              value !== undefined && value !== null ? Number(value) : undefined,
            );
          },
        }),
      },
      {
        component: 'Input',
        fieldName: 'keyword',
        label: $t('germplasm.list.keyword'),
        formItemClass: 'col-span-4',
        componentProps: () => ({
          allowClear: true,
          placeholder: $t('germplasm.list.placeholderKeyword'),
        }),
      },
    ],
    defaultValues: {
      keyword: '',
      taxonomy_tax_id: initialTaxonomyTaxId,
      batch_id: initialBatchId,
    },
  };
}
