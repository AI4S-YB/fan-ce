import type { Ref } from 'vue';
import { computed } from 'vue';

import type {
  ColumnConfig,
  TableDataItem,
  ValidationResult,
  ValidationRules,
} from '../types';

/**
 * 表格验证Hook
 * @param dataSource 数据源
 * @param columns 列配置
 * @param validationRules 验证规则
 * @returns 验证相关方法和状态
 */
export function useTableValidation(
  dataSource: Ref<TableDataItem[]>,
  columns: Ref<ColumnConfig[]>,
  validationRules?: Ref<undefined | ValidationRules>,
) {
  /**
   * 验证数据
   * @returns 验证结果
   */
  const validateData = (): ValidationResult => {
    const result: ValidationResult = {
      errors: [],
      missingPartialOptional: [],
      missingRequired: [],
      valid: true,
    };

    if (!validationRules?.value || dataSource.value.length === 0) {
      return result;
    }

    const rules = validationRules.value;
    const data = dataSource.value;

    // 验证必填字段
    if (rules.required && rules.required.length > 0) {
      for (const field of rules.required) {
        const hasEmptyValue = data.some((row) => {
          const value = row[field];
          return value === undefined || value === null || value === '';
        });

        if (hasEmptyValue) {
          result.missingRequired?.push(field);
          result.errors.push(`必填字段 "${field}" 存在空值`);
        }
      }
    }

    // 验证部分选填字段组
    if (rules.partialOptional && rules.partialOptional.length > 0) {
      for (const group of rules.partialOptional) {
        const hasIncompleteRow = data.some((row) => {
          const filledCount = group.filter((field) => {
            const value = row[field];
            return value !== undefined && value !== null && value !== '';
          }).length;
          return filledCount > 0 && filledCount < group.length;
        });

        if (hasIncompleteRow) {
          result.missingPartialOptional?.push(group);
          result.errors.push(
            `部分选填字段组 [${group.join(', ')}] 存在不完整的行`,
          );
        }
      }
    }

    result.valid = result.errors.length === 0;
    return result;
  };

  /**
   * 获取字段的验证状态
   * @param field 字段名
   * @returns 验证状态
   */
  const getFieldValidationStatus = (field: string) => {
    if (!validationRules?.value) {
      return 'normal';
    }

    const rules = validationRules.value;

    if (rules.required?.includes(field)) {
      return 'required';
    }

    if (rules.partialOptional?.some((group) => group.includes(field))) {
      return 'partial-optional';
    }

    if (rules.freeOptional?.includes(field)) {
      return 'free-optional';
    }

    return 'normal';
  };

  /**
   * 获取单元格的背景色类名
   * @param field 字段名
   * @returns CSS类名
   */
  const getCellBackgroundClass = (field: string) => {
    const status = getFieldValidationStatus(field);
    switch (status) {
      case 'free-optional': {
        return 'bg-green-50';
      }
      case 'partial-optional': {
        return 'bg-yellow-50';
      }
      case 'required': {
        return 'bg-red-50';
      }
      default: {
        return '';
      }
    }
  };

  // 计算验证结果
  const validationResult = computed(() => validateData());

  return {
    // 计算属性
    validationResult,

    // 方法
    getCellBackgroundClass,
    getFieldValidationStatus,
    validateData,
  };
}