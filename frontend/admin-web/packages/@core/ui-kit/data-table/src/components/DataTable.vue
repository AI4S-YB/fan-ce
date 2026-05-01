<script setup lang="ts">
import type {
  ButtonConfig,
  DataTableEmits,
  DataTableProps,
  TableDataItem,
  ValidationResult,
} from '../types';

import { computed, ref, watch } from 'vue';

// Note: ant-design-vue components should be imported based on your project setup
// This is a placeholder - adjust imports according to your ant-design-vue configuration
const AAlert = 'a-alert';
const AButton = 'a-button';
const ADatePicker = 'a-date-picker';
const AInput = 'a-input';
const AInputNumber = 'a-input-number';
const ASelect = 'a-select';
const ASpace = 'a-space';
const ATable = 'a-table';

import {
  useTableColumns,
  useTableData,
  useTableEdit,
  useTableValidation,
} from '../hooks';

// Props定义
const props = withDefaults(defineProps<DataTableProps>(), {
  bordered: true,
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

// 使用Hooks
const { addRow, clearData, updateCellData } = useTableData(internalDataSource);

const { visibleColumns } = useTableColumns(ref(props.columns));

const {
  cancelEdit,
  confirmEdit: confirmEditHook,
  editState,
  isEditingCell,
  startCellEdit,
} = useTableEdit();

const { getCellBackgroundClass, validateData } = useTableValidation(
  internalDataSource,
  ref(props.columns),
  ref(props.validationRules),
);

// 计算属性
const buttonConfig = computed<ButtonConfig>(() => ({
  showAddRow: true,
  showClearData: true,
  showDeleteRows: true,
  showValidateData: true,
}));

const showToolbar = computed(() => {
  return Object.values(buttonConfig.value).some(Boolean);
});

const editableColumns = computed(() => {
  return visibleColumns.value.filter((col) => col.editable !== false);
});

const tableColumns = computed(() => {
  return visibleColumns.value.map((col) => ({
    ...col,
    customRender: col.editable === false ? undefined : { name: col.dataIndex },
    customHeaderCell: col.headerStyle ? () => ({ style: col.headerStyle }) : undefined,
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

const startEdit = (
  rowIndex: number,
  columnIndex: string,
  currentValue: any,
) => {
  startCellEdit(rowIndex, columnIndex, currentValue);
};

const confirmEdit = () => {
  const result = confirmEditHook(editState.value.value);
  if (result) {
    updateCellData(result.rowIndex, result.columnIndex, result.value);
    emit('edit', result.rowIndex, result.columnIndex, result.value);
    emit('update:dataSource', internalDataSource.value);
  }
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
    <!-- 表格工具栏 -->
    <div v-if="showToolbar" class="data-table-toolbar mb-4">
      <ASpace>
        <AButton
          v-if="buttonConfig?.showAddRow"
          type="primary"
          @click="handleAddRow"
        >
          添加行
        </AButton>
        <AButton
          v-if="buttonConfig?.showDeleteRows && selectedRowKeys.length > 0"
          danger
          @click="handleDeleteRows"
        >
          删除选中行 ({{ selectedRowKeys.length }})
        </AButton>
        <AButton v-if="buttonConfig?.showClearData" @click="handleClearData">
          清空数据
        </AButton>
        <AButton
          v-if="buttonConfig?.showValidateData"
          type="default"
          @click="handleValidateData"
        >
          验证数据
        </AButton>
      </ASpace>
    </div>

    <!-- 主表格 -->
    <ATable
      :columns="tableColumns"
      :data-source="dataSource"
      :loading="loading"
      :bordered="bordered"
      :row-selection="rowSelectionConfig"
      :scroll="scrollConfig"
      :pagination="false"
      row-key="id"
      @change="handleTableChange"
    >
      <!-- 自定义列渲染 -->
      <template
        v-for="column in editableColumns"
        :key="column.dataIndex"
        #[column.dataIndex]="{ record, index }"
      >
        <div
          class="table-cell"
          :class="[
            getCellBackgroundClass(column.dataIndex),
            { editing: isEditingCell(index, column.dataIndex) },
          ]"
          :style="column.cellStyle"
          @click="startEdit(index, column.dataIndex, record[column.dataIndex])"
        >
          <!-- 编辑状态 -->
          <template v-if="isEditingCell(index, column.dataIndex)">
            <AInput
              v-if="column.type === 'text' || !column.type"
              v-model:value="editState.value"
              @blur="confirmEdit"
              @keyup.enter="confirmEdit"
              @keyup.esc="cancelEdit"
              auto-focus
            />
            <AInputNumber
              v-else-if="column.type === 'number'"
              v-model:value="editState.value"
              @blur="confirmEdit"
              @keyup.enter="confirmEdit"
              @keyup.esc="cancelEdit"
              auto-focus
            />
            <ASelect
              v-else-if="column.type === 'select'"
              v-model:value="editState.value"
              :options="column.options"
              @blur="confirmEdit"
              @keyup.esc="cancelEdit"
              auto-focus
            />
            <ADatePicker
              v-else-if="column.type === 'date'"
              v-model:value="editState.value"
              @blur="confirmEdit"
              @keyup.esc="cancelEdit"
              auto-focus
            />
          </template>

          <!-- 显示状态 -->
          <template v-else>
            <span v-if="record[column.dataIndex]">
              {{ formatCellValue(record[column.dataIndex], column.type) }}
            </span>
            <span v-else class="text-gray-400">
              {{ column.placeholder || '点击编辑' }}
            </span>
          </template>
        </div>
      </template>
    </ATable>

    <!-- 验证结果显示 -->
    <div
      v-if="validationResult && !validationResult.valid"
      class="validation-errors mt-4"
    >
      <AAlert
        type="error"
        :message="`数据验证失败 (${validationResult.errors.length} 个错误)`"
        show-icon
      >
        <template #description>
          <ul>
            <li v-for="error in validationResult.errors" :key="error">
              {{ error }}
            </li>
          </ul>
        </template>
      </AAlert>
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
  min-height: 32px;
  padding: 4px 8px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.table-cell:hover {
  background-color: #f5f5f5;
}

.table-cell.editing {
  background-color: #e6f7ff;
  border: 1px solid #1890ff;
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