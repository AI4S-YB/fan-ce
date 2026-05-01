/**
 * 字段级别枚举
 */
export enum FieldLevel {
  /** 自由选填字段 */
  FREE_OPTIONAL = 'freeOptional',
  /** 部分选填字段 */
  PARTIAL_OPTIONAL = 'partialOptional',
  /** 必填字段 */
  REQUIRED = 'required',
}

/**
 * 验证规则接口
 */
export interface ValidationRules {
  /** 自由选填字段列表 */
  freeOptional?: string[];
  /** 部分选填字段组 - 每组至少需要填写一个字段 */
  partialOptional?: string[][];
  /** 必填字段列表 */
  required?: string[];
}

/**
 * 按钮配置接口
 */
export interface ButtonConfig {
  /** 显示添加列按钮 */
  showAddColumn?: boolean;
  /** 显示添加行按钮 */
  showAddRow?: boolean;
  /** 显示清空数据按钮 */
  showClearData?: boolean;
  /** 显示删除选中行按钮 */
  showDeleteRows?: boolean;
  /** 显示验证数据按钮 */
  showValidateData?: boolean;
}

/**
 * 列配置接口
 */
export interface ColumnConfig {
  /** 数据索引 */
  dataIndex: string;
  /** 是否可编辑 */
  editable?: boolean;
  /** 分组标识 */
  group?: string;
  /** 表头样式 */
  headerStyle?: Record<string, any>;
  /** 单元格样式 */
  cellStyle?: Record<string, any>;
  /** 字段级别 */
  level?: FieldLevel;
  /** 选择类型的选项 */
  options?: Array<{ label: string; value: any }>;
  /** 占位符 */
  placeholder?: string;
  /** 列标题 */
  title: string;
  /** 字段类型 */
  type?: 'date' | 'number' | 'select' | 'text';
  /** 列宽度 */
  width?: number;
}

/**
 * 字段配置接口（保持兼容性）
 */
export interface FieldConfig extends ColumnConfig {
  /** 分组标识 */
  group?: string;
  /** 字段级别 */
  level?: FieldLevel;
}

/**
 * 表格数据项接口
 */
export interface TableDataItem {
  /** 动态字段 */
  [key: string]: any;
  /** 唯一标识 */
  id?: number | string;
}

/**
 * 验证结果接口
 */
export interface ValidationResult {
  /** 错误信息 */
  errors: string[];
  /** 缺失的部分选填字段组 */
  missingPartialOptional?: string[][];
  /** 缺失的必填字段 */
  missingRequired?: string[];
  /** 是否验证通过 */
  valid: boolean;
}

/**
 * 编辑状态接口
 */
export interface EditState {
  /** 编辑的列索引 */
  columnIndex?: string;
  /** 是否正在编辑 */
  editing: boolean;
  /** 是否编辑表头 */
  isHeader?: boolean;
  /** 编辑的行索引 */
  rowIndex?: number;
  /** 编辑的值 */
  value?: any;
}

/**
 * DataTable组件Props接口
 */
export interface DataTableProps {
  /** 是否显示边框 */
  bordered?: boolean;
  /** 列配置 */
  columns: ColumnConfig[];
  /** 数据源 */
  dataSource: TableDataItem[];
  /** 是否加载中 */
  loading?: boolean;
  /** 表格最大高度 */
  maxHeight?: number;
  /** 是否可选择行 */
  rowSelection?: boolean;
  /** 选中的行键 */
  selectedRowKeys?: (number | string)[];
  /** 验证规则 */
  validationRules?: ValidationRules;
  /** 是否启用虚拟滚动 */
  virtualScroll?: boolean;
}

/**
 * DataTable组件事件接口
 */
export interface DataTableEmits {
  /** 编辑事件 */
  edit: [rowIndex: number, columnIndex: string, value: any];
  /** 行选择变化 */
  selectionChange: [
    selectedRowKeys: (number | string)[],
    selectedRows: TableDataItem[],
  ];
  /** 数据源更新 */
  'update:dataSource': [value: TableDataItem[]];
  /** 选中行更新 */
  'update:selectedRowKeys': [value: (number | string)[]];
  /** 验证事件 */
  validate: [result: ValidationResult];
}
