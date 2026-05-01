import type { ColumnConfig, FieldConfig, FieldLevel } from '../types';

import type { Ref } from 'vue';
import { computed } from 'vue';

/**
 * 表格列配置Hook
 * @param columns 列配置
 * @param fields 字段配置
 * @returns 列相关方法和计算属性
 */
export function useTableColumns(
  columns: Ref<ColumnConfig[]>,
  fields?: Ref<FieldConfig[]>,
) {
  /**
   * 获取可见列
   */
  const visibleColumns = computed(() => {
    return columns.value;
  });

  /**
   * 获取固定列
   */
  const fixedColumns = computed(() => {
    return columns.value;
  });

  /**
   * 获取可排序列
   */
  const sortableColumns = computed(() => {
    return columns.value;
  });

  /**
   * 根据字段级别获取列
   * @param level 字段级别
   */
  const getColumnsByLevel = (level: FieldLevel) => {
    if (!fields?.value) return [];

    const fieldKeys = new Set(
      fields.value
        .filter((field) => field.level === level)
        .map((field) => field.dataIndex),
    );

    return columns.value.filter((col) => fieldKeys.has(col.dataIndex));
  };

  /**
   * 获取列的字段配置
   * @param columnKey 列键
   */
  const getFieldConfig = (columnKey: string) => {
    return fields?.value?.find((field) => field.dataIndex === columnKey);
  };

  /**
   * 更新列配置
   * @param columnKey 列键
   * @param updates 更新内容
   */
  const updateColumn = (columnKey: string, updates: Partial<ColumnConfig>) => {
    const index = columns.value.findIndex((col) => col.dataIndex === columnKey);
    if (index !== -1) {
      Object.assign(columns.value[index], updates);
    }
  };

  /**
   * 切换列可见性
   * @param columnKey 列键
   */
  const toggleColumnVisibility = (columnKey: string) => {
    // 由于ColumnConfig没有visible属性，这里暂时保留接口但不实现
    console.warn('toggleColumnVisibility not implemented: ColumnConfig does not have visible property');
  };

  /**
   * 重置列配置
   */
  const resetColumns = () => {
    // 重置列配置到初始状态
    columns.value.forEach((col, index) => {
      columns.value[index] = { ...col };
    });
  };

  /**
   * 获取列宽度
   * @param columnKey 列键
   */
  const getColumnWidth = (columnKey: string) => {
    const column = columns.value.find((col) => col.dataIndex === columnKey);
    return column?.width;
  };

  /**
   * 设置列宽度
   * @param columnKey 列键
   * @param width 宽度
   */
  const setColumnWidth = (columnKey: string, width: number) => {
    updateColumn(columnKey, { width });
  };

  return {
    // 计算属性
    fixedColumns,
    sortableColumns,
    visibleColumns,

    // 方法
    getColumnWidth,
    getColumnsByLevel,
    getFieldConfig,
    resetColumns,
    setColumnWidth,
    toggleColumnVisibility,
    updateColumn,
  };
}
