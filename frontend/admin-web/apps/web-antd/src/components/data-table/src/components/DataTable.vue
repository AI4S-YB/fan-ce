<script setup lang="ts">
import type {
  DataTableEmits,
  DataTableProps,
  TableDataItem,
  ValidationResult,
} from '../types';

import { computed, ref, watch } from 'vue';

import {
  Alert,
  DatePicker,
  Input,
  InputNumber,
  Select,
  Table,
} from 'ant-design-vue';

import { $t } from '@vben/locales';

import {
  useTableColumns,
  useTableData,
  useTableEdit,
  useTableValidation,
} from '../hooks';

// Props定义
const props = withDefaults(defineProps<DataTableProps>(), {
  bordered: true,
  defaultInlineEdit: true,
  loading: false,
  rowSelection: false,
  selectedRowKeys: () => [],
  virtualScroll: false,
});

// Events定义
const emit = defineEmits<DataTableEmits>();

// 响应式数据
const internalDataSource = ref<TableDataItem[]>([...props.dataSource]);
const internalSelectedRowKeys = ref<(number | string)[]>([
  ...props.selectedRowKeys,
]);
const validationResult = ref<null | ValidationResult>(null);

// 监听props变化
watch(
  () => props.dataSource,
  (newData) => {
    internalDataSource.value = [...newData];
  },
  { deep: true },
);

watch(
  () => props.selectedRowKeys,
  (newKeys) => {
    internalSelectedRowKeys.value = [...newKeys];
  },
);
const currentColumns = ref(props.columns)
watch(
  () => props.columns,
  () => {
    currentColumns.value = props.columns
  },
  { deep: true },
);

// 使用Hooks
const { addRow, clearData, updateCellData } = useTableData(internalDataSource);

const { visibleColumns } = useTableColumns(currentColumns);

const { isEditingCell } = useTableEdit(props.defaultInlineEdit);

const { getCellBackgroundClass, validateData } = useTableValidation(
  internalDataSource,
  ref(props.columns),
  ref(props.validationRules),
);

// 计算属性
// const buttonConfig = computed<ButtonConfig>(() => ({
//   showAddRow: true,
//   showClearData: true,
//   showDeleteRows: true,
//   showValidateData: true,
// }));

// const showToolbar = computed(() => {
//   return Object.values(buttonConfig.value).some(Boolean);
// });

const editableColumns = computed(() => {
  return visibleColumns.value.filter((col) => col.editable !== false);
});

const tableColumns = computed(() => {
  return visibleColumns.value.map((col) => ({
    key: col.dataIndex,
    dataIndex: col.dataIndex,
    title: col.title || '',
    width: col.width || 180,
    customHeaderCell: (column: any) => {
      return {
        onDblclick: () => handleHeaderDoubleClick(column.dataIndex, column),
      };
    },
  }));
});
const rowSelectionConfig = computed(() => {
  if (!props.rowSelection) return undefined;

  return {
    selectedRowKeys: internalSelectedRowKeys.value,
    onChange: (
      selectedKeys: (number | string)[],
      selectedRows: TableDataItem[],
    ) => {
      internalSelectedRowKeys.value = selectedKeys;
      emit('update:selectedRowKeys', selectedKeys);
      emit('selectionChange', selectedKeys, selectedRows);
    },
  };
});

const scrollConfig = computed(() => {
  const config: any = {};

  if (props.maxHeight) {
    config.y = props.maxHeight;
  }

  if (props.virtualScroll) {
    config.scrollToFirstRowOnChange = true;
  }

  return Object.keys(config).length > 0 ? config : undefined;
});

// 方法
const handleAddRow = () => {
  const newRow = addRow();
  emit('update:dataSource', internalDataSource.value);
  return newRow;
};

const handleDeleteRows = () => {
  // 删除选中的行
  const keysToDelete = new Set(internalSelectedRowKeys.value);
  internalDataSource.value = internalDataSource.value.filter(
    (_, index) => !keysToDelete.has(index),
  );
  internalSelectedRowKeys.value = [];
  emit('update:dataSource', internalDataSource.value);
  emit('update:selectedRowKeys', []);
};

const handleClearData = () => {
  clearData();
  internalSelectedRowKeys.value = [];
  emit('update:dataSource', internalDataSource.value);
  emit('update:selectedRowKeys', []);
};

const handleValidateData = () => {
  const result = validateData();
  validationResult.value = result;
  emit('validate', result);
  return result;
};

// 移除未使用的编辑相关函数，因为现在始终按照defaultInlineEdit: true处理

const handleCellDoubleClick = (
  rowIndex: number,
  columnIndex: string,
  record: TableDataItem,
) => {
  emit('cellDoubleClick', rowIndex, columnIndex, record);
};

const handleHeaderDoubleClick = (columnIndex: string, column: any) => {
  emit('headerDoubleClick', columnIndex, column);
};

const handleTableChange = (pagination: any, filters: any, sorter: any) => {
  // 处理表格变化事件
  // eslint-disable-next-line no-console
  console.log('Table changed:', { pagination, filters, sorter });
};

const formatCellValue = (value: any, type?: string) => {
  if (value === null || value === undefined) return '';

  switch (type) {
    case 'date': {
      return value instanceof Date ? value.toLocaleDateString() : value;
    }
    case 'number': {
      return typeof value === 'number' ? value.toString() : value;
    }
    default: {
      return value.toString();
    }
  }
};

// 获取列类型的辅助方法
const getColumnType = (dataIndex: string) => {
  const column = visibleColumns.value.find(
    (col) => col.dataIndex === dataIndex,
  );
  return column?.type;
};

// 获取列选项的辅助方法
const getColumnOptions = (dataIndex: string) => {
  const column = visibleColumns.value.find(
    (col) => col.dataIndex === dataIndex,
  );
  return column?.options || [];
};

// 获取列占位符的辅助方法
const getColumnPlaceholder = (dataIndex: string) => {
  const column = visibleColumns.value.find(
    (col) => col.dataIndex === dataIndex,
  );
  return column?.placeholder;
};

// 暴露给父组件的方法
defineExpose({
  addRow: handleAddRow,
  clearData: handleClearData,
  deleteRows: handleDeleteRows,
  validateData: handleValidateData,
});
</script>

<template>
  <div class="data-table-container">
    <!-- 主表格 -->
    <Table
      :columns="tableColumns"
      :data-source="internalDataSource"
      :loading="loading"
      :bordered="bordered"
      :row-selection="rowSelectionConfig"
      :scroll="scrollConfig"
      :pagination="false"
      row-key="id"
      @change="handleTableChange"
    >
      <!-- 自定义列渲染 -->
      <template #bodyCell="{ record, index, column }">
        <template
          v-if="
            column.dataIndex &&
            editableColumns.some((col) => col.dataIndex === column.dataIndex)
          "
        >
          <div
            class="table-cell"
            :class="[
              getCellBackgroundClass(column.dataIndex as string),
              { editing: isEditingCell(index, column.dataIndex as string) },
            ]"
            @click="
              () => {
                // 始终按照defaultInlineEdit: true处理，不需要点击启动编辑
              }
            "
            @dblclick="
              handleCellDoubleClick(index, column.dataIndex as string, record)
            "
          >
            <!-- 编辑状态 -->
            <template v-if="isEditingCell(index, String(column.dataIndex))">
              <Input
                v-if="
                  getColumnType(String(column.dataIndex)) === 'text' ||
                  !getColumnType(String(column.dataIndex))
                "
                :value="record[String(column.dataIndex)]"
                @input="
                  (e) => {
                    // 始终按照defaultInlineEdit: true处理
                    const value = e?.target?.value || '';
                    updateCellData(index, String(column.dataIndex), value);
                    emit('edit', index, String(column.dataIndex), value);
                    emit('update:dataSource', internalDataSource);
                  }
                "
                :auto-focus="false"
              />
              <InputNumber
                v-else-if="getColumnType(String(column.dataIndex)) === 'number'"
                :value="record[String(column.dataIndex)]"
                @update:value="
                  (val) => {
                    // 始终按照defaultInlineEdit: true处理
                    updateCellData(index, String(column.dataIndex), val);
                    emit('edit', index, String(column.dataIndex), val);
                    emit('update:dataSource', internalDataSource);
                  }
                "
                :auto-focus="false"
              />
              <Select
                v-else-if="getColumnType(String(column.dataIndex)) === 'select'"
                :value="record[String(column.dataIndex)]"
                :options="getColumnOptions(String(column.dataIndex))"
                @update:value="
                  (val) => {
                    // 始终按照defaultInlineEdit: true处理
                    updateCellData(index, String(column.dataIndex), val);
                    emit('edit', index, String(column.dataIndex), val);
                    emit('update:dataSource', internalDataSource);
                  }
                "
                :auto-focus="false"
              />
              <DatePicker
                v-else-if="getColumnType(String(column.dataIndex)) === 'date'"
                value-format="yyyy-MM-dd"
                :value="record[String(column.dataIndex)]"
                @update:value="
                  (val) => {
                    // 始终按照defaultInlineEdit: true处理
                    updateCellData(index, String(column.dataIndex), val);
                    emit('edit', index, String(column.dataIndex), val);
                    emit('update:dataSource', internalDataSource);
                  }
                "
                :auto-focus="false"
              />
            </template>

            <!-- 显示状态 -->
            <template v-else>
              <span v-if="record?.[String(column?.dataIndex)]">
                {{
                  formatCellValue(
                    record[String(column.dataIndex)],
                    getColumnType(String(column.dataIndex)),
                  )
                }}
              </span>
              <span v-else class="text-gray-400">
                {{
                  getColumnPlaceholder(String(column.dataIndex)) || $t('component.dataTable.clickToEdit')
                }}
              </span>
            </template>
          </div>
        </template>
      </template>
    </Table>

    <!-- 验证结果显示 -->
    <div
      v-if="validationResult && !validationResult.valid"
      class="validation-errors mt-4"
    >
      <Alert
        type="error"
        :message="$t('component.dataTable.validationFailed', { count: validationResult.errors.length })"
        show-icon
      >
        <template #description>
          <ul>
            <li v-for="error in validationResult.errors" :key="error">
              {{ error }}
            </li>
          </ul>
        </template>
      </Alert>
    </div>
  </div>
</template>

<style scoped>
.data-table-container {
  width: 100%;
}

.data-table-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding: 12px 0;
}

.table-cell {
  display: flex;
  align-items: center;
  min-height: 32px;
  padding: 16px;
  margin: -16px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.table-cell:hover {
  background-color: #f5f5f5;
}

.validation-errors {
  margin-top: 16px;
}

.validation-errors ul {
  padding-left: 20px;
  margin: 0;
}

.validation-errors li {
  margin: 4px 0;
}

.text-gray-400 {
  color: #9ca3af;
}
</style>
