import type { ColumnConfig, EditState } from '../types';

import { ref } from 'vue';

/**
 * 表格编辑Hook
 * @returns 编辑相关方法和状态
 */
export function useTableEdit() {
  // 编辑状态
  const editState = ref<EditState>({
    columnIndex: undefined,
    editing: false,
    isHeader: false,
    rowIndex: undefined,
    value: undefined,
  });

  // 表头编辑状态
  const headerEditState = ref<{
    column?: ColumnConfig;
    editing: boolean;
    originalColumn?: ColumnConfig;
  }>({
    editing: false,
  });

  /**
   * 开始编辑单元格
   * @param rowIndex 行索引
   * @param columnIndex 列索引
   * @param currentValue 当前值
   */
  const startCellEdit = (
    rowIndex: number,
    columnIndex: string,
    currentValue: any,
  ) => {
    editState.value = {
      columnIndex,
      editing: true,
      isHeader: false,
      rowIndex,
      value: currentValue,
    };
  };

  /**
   * 开始编辑表头
   * @param column 列配置
   */
  const startHeaderEdit = (column: ColumnConfig) => {
    headerEditState.value = {
      column: { ...column },
      editing: true,
      originalColumn: { ...column },
    };
  };

  /**
   * 取消编辑
   */
  const cancelEdit = () => {
    editState.value = {
      columnIndex: undefined,
      editing: false,
      isHeader: false,
      rowIndex: undefined,
      value: undefined,
    };
  };

  /**
   * 取消表头编辑
   */
  const cancelHeaderEdit = () => {
    headerEditState.value = {
      editing: false,
    };
  };

  /**
   * 确认编辑
   * @param newValue 新值
   * @returns 编辑结果
   */
  const confirmEdit = (newValue: any) => {
    if (
      editState.value.columnIndex === undefined ||
      editState.value.rowIndex === undefined
    ) {
      return null;
    }
    const result = {
      columnIndex: editState.value.columnIndex,
      rowIndex: editState.value.rowIndex,
      value: newValue,
    };
    cancelEdit();
    return result;
  };

  /**
   * 确认表头编辑
   * @returns 编辑后的列配置
   */
  const confirmHeaderEdit = () => {
    const result = headerEditState.value.column;
    cancelHeaderEdit();
    return result;
  };

  /**
   * 检查是否正在编辑指定单元格
   * @param rowIndex 行索引
   * @param columnIndex 列索引
   * @returns 是否正在编辑
   */
  const isEditingCell = (rowIndex: number, columnIndex: string) => {
    return (
      editState.value.editing &&
      !editState.value.isHeader &&
      editState.value.rowIndex === rowIndex &&
      editState.value.columnIndex === columnIndex
    );
  };

  return {
    // 响应式状态
    editState,
    headerEditState,

    // 方法
    cancelEdit,
    cancelHeaderEdit,
    confirmEdit,
    confirmHeaderEdit,
    isEditingCell,
    startCellEdit,
    startHeaderEdit,
  };
}