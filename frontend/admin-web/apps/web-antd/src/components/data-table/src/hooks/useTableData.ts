import type { Ref } from 'vue';
import { computed, ref } from 'vue';

import type { TableDataItem } from '../types';

/**
 * 表格数据管理Hook
 * @param initialData 初始数据
 * @returns 表格数据管理方法
 */
export function useTableData(initialData: Ref<TableDataItem[]>) {
  // 选中的行键
  const selectedRowKeys = ref<(number | string)[]>([]);

  // 选中的行数据
  const selectedRows = computed(() => {
    return initialData.value.filter((item) => {
      const id = item.id || initialData.value.indexOf(item);
      return selectedRowKeys.value.includes(id);
    });
  });

  /**
   * 添加新行
   * @param rowData 行数据，如果不提供则创建空行
   */
  const addRow = (rowData?: Partial<TableDataItem>) => {
    const newRow: TableDataItem = {
      id: Date.now() + Math.random(),
      ...rowData,
    };
    initialData.value.push(newRow);
  };

  /**
   * 删除指定行
   * @param rowIndex 行索引
   */
  const deleteRow = (rowIndex: number) => {
    if (rowIndex >= 0 && rowIndex < initialData.value.length) {
      initialData.value.splice(rowIndex, 1);
    }
  };

  /**
   * 删除选中的行
   */
  const deleteSelectedRows = () => {
    const idsToDelete = new Set(selectedRowKeys.value);
    initialData.value = initialData.value.filter((item) => {
      const id = item.id || initialData.value.indexOf(item);
      return !idsToDelete.has(id);
    });
    selectedRowKeys.value = [];
  };

  /**
   * 清空所有数据
   */
  const clearData = () => {
    initialData.value.length = 0;
    selectedRowKeys.value = [];
  };

  /**
   * 更新单元格数据
   * @param rowIndex 行索引
   * @param columnIndex 列索引
   * @param value 新值
   */
  const updateCellData = (
    rowIndex: number,
    columnIndex: string,
    value: any,
  ) => {
    if (rowIndex >= 0 && rowIndex < initialData.value.length) {
      const row = initialData.value[rowIndex];
      if (row) {
        row[columnIndex] = value;
      }
    }
  };

  /**
   * 处理行选择变化
   * @param keys 选中的行键
   */
  const handleSelectionChange = (keys: (number | string)[]) => {
    selectedRowKeys.value = keys;
  };

  /**
   * 获取行的唯一标识
   * @param item 行数据
   * @param index 行索引
   * @returns 唯一标识
   */
  const getRowKey = (item: TableDataItem, index: number): number | string => {
    return item.id ?? index;
  };

  return {
    // 响应式数据
    selectedRowKeys,
    selectedRows,

    // 方法
    addRow,
    clearData,
    deleteRow,
    deleteSelectedRows,
    getRowKey,
    handleSelectionChange,
    updateCellData,
  };
}