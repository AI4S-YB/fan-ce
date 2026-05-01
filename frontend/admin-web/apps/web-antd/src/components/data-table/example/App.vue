<script setup lang="ts">
import type {
  ColumnConfig,
  TableDataItem,
  ValidationRules,
} from '../src/types';

import { ref } from 'vue';

import { DataTable } from '../src';
import { FieldLevel } from '../src/types';

// 示例数据
const columns = ref<ColumnConfig[]>([
  {
    dataIndex: 'name',
    title: '姓名',
    type: 'text',
    level: FieldLevel.REQUIRED,
    width: 120,
  },
  {
    dataIndex: 'age',
    title: '年龄',
    type: 'number',
    level: FieldLevel.REQUIRED,
    width: 100,
  },
  {
    dataIndex: 'email',
    title: '邮箱',
    type: 'text',
    level: FieldLevel.PARTIAL_OPTIONAL,
    width: 200,
  },
  {
    dataIndex: 'phone',
    title: '电话',
    type: 'text',
    level: FieldLevel.PARTIAL_OPTIONAL,
    width: 150,
  },
  {
    dataIndex: 'department',
    title: '部门',
    type: 'select',
    level: FieldLevel.FREE_OPTIONAL,
    width: 120,
    options: [
      { label: '技术部', value: 'tech' },
      { label: '销售部', value: 'sales' },
      { label: '市场部', value: 'marketing' },
    ],
  },
]);

const dataSource = ref<TableDataItem[]>([
  {
    id: 1,
    name: '张三',
    age: 25,
    email: 'zhangsan@example.com',
    department: 'tech',
  },
  {
    id: 2,
    name: '李四',
    age: 30,
    phone: '13800138000',
    department: 'sales',
  },
]);

const selectedRowKeys = ref<(number | string)[]>([]);

const validationRules = ref<ValidationRules>({
  required: ['name', 'age'],
  partialOptional: [['email', 'phone']],
  freeOptional: ['department'],
});

// 事件处理
const handleEdit = (rowIndex: number, columnIndex: string, value: any) => {
  // eslint-disable-next-line no-console
  console.log('编辑:', { rowIndex, columnIndex, value });
};

const handleSelectionChange = (
  selectedKeys: (number | string)[],
  selectedRows: TableDataItem[],
) => {
  // eslint-disable-next-line no-console
  console.log('选择变化:', { selectedKeys, selectedRows });
};

const handleValidate = (result: any) => {
  // eslint-disable-next-line no-console
  console.log('验证结果:', result);
};
</script>

<template>
  <div class="app-container">
    <h1>DataTable 组件示例</h1>

    <DataTable
      v-model:data-source="dataSource"
      v-model:selected-row-keys="selectedRowKeys"
      :columns="columns"
      :validation-rules="validationRules"
      :row-selection="true"
      :bordered="true"
      @edit="handleEdit"
      @selection-change="handleSelectionChange"
      @validate="handleValidate"
    />
  </div>
</template>

<style scoped>
.app-container {
  max-width: 1200px;
  padding: 20px;
  margin: 0 auto;
}

h1 {
  margin-bottom: 20px;
  color: #1f2937;
}
</style>