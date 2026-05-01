# DataTable 组件

一个功能强大的Vue 3数据表格组件，支持内联编辑、数据验证、行选择等功能。

## 功能特性

- ✅ 内联编辑：支持文本、数字、选择、日期等多种字段类型的内联编辑
- ✅ 数据验证：支持必填字段、部分选填字段组、自由选填字段的验证
- ✅ 行选择：支持单选和多选行功能
- ✅ 工具栏：提供添加行、删除行、清空数据、验证数据等操作按钮
- ✅ 响应式设计：支持自适应布局和虚拟滚动
- ✅ TypeScript支持：完整的类型定义

## 组件结构

```
src/
├── components/
│   └── DataTable.vue          # 主组件
├── hooks/
│   ├── useTableColumns.ts     # 列管理Hook
│   ├── useTableData.ts        # 数据管理Hook
│   ├── useTableEdit.ts        # 编辑管理Hook
│   ├── useTableValidation.ts  # 验证管理Hook
│   └── index.ts               # Hook导出
├── types.ts                   # 类型定义
└── index.ts                   # 组件导出
```

## 基本使用

```vue
<template>
  <DataTable
    v-model:data-source="dataSource"
    v-model:selected-row-keys="selectedRowKeys"
    :columns="columns"
    :validation-rules="validationRules"
    :row-selection="true"
    @edit="handleEdit"
    @selection-change="handleSelectionChange"
    @validate="handleValidate"
  />
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { DataTable, FieldLevel } from '@core/ui-kit/data-table';
import type { ColumnConfig, TableDataItem, ValidationRules } from '@core/ui-kit/data-table';

const columns = ref<ColumnConfig[]>([
  {
    dataIndex: 'name',
    title: '姓名',
    type: 'text',
    level: FieldLevel.REQUIRED,
  },
  {
    dataIndex: 'age',
    title: '年龄',
    type: 'number',
    level: FieldLevel.REQUIRED,
  },
]);

const dataSource = ref<TableDataItem[]>([]);
const selectedRowKeys = ref<(number | string)[]>([]);

const validationRules = ref<ValidationRules>({
  required: ['name', 'age'],
});
</script>
```

## API

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| columns | `ColumnConfig[]` | - | 列配置 |
| dataSource | `TableDataItem[]` | - | 数据源 |
| selectedRowKeys | `(number \| string)[]` | `[]` | 选中的行键 |
| validationRules | `ValidationRules` | - | 验证规则 |
| rowSelection | `boolean` | `false` | 是否可选择行 |
| bordered | `boolean` | `true` | 是否显示边框 |
| loading | `boolean` | `false` | 是否加载中 |
| maxHeight | `number` | - | 表格最大高度 |
| virtualScroll | `boolean` | `false` | 是否启用虚拟滚动 |

### Events

| 事件名 | 参数 | 说明 |
|--------|------|------|
| edit | `(rowIndex: number, columnIndex: string, value: any)` | 编辑事件 |
| selectionChange | `(selectedKeys: (number \| string)[], selectedRows: TableDataItem[])` | 行选择变化 |
| validate | `(result: ValidationResult)` | 验证事件 |
| update:dataSource | `(value: TableDataItem[])` | 数据源更新 |
| update:selectedRowKeys | `(value: (number \| string)[])` | 选中行更新 |

### 字段类型

- `text`: 文本输入
- `number`: 数字输入
- `select`: 下拉选择
- `date`: 日期选择

### 字段级别

- `FieldLevel.REQUIRED`: 必填字段
- `FieldLevel.PARTIAL_OPTIONAL`: 部分选填字段（组内至少填写一个）
- `FieldLevel.FREE_OPTIONAL`: 自由选填字段

## 开发

本组件使用Vue 3 + TypeScript + Ant Design Vue开发，采用Composition API和Hook模式设计。