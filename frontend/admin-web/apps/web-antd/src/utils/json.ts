/**
 * JSON 处理工具类
 * 提供 JSON 校验、格式化、实时检测等功能
 */

export interface JsonDetectionResult {
  isJson: boolean;
  isComplete: boolean;
  formatted?: string;
  error?: string;
}

/**
 * 检测字符串是否为有效的 JSON 格式
 * @param str 要检测的字符串
 * @returns 是否为有效 JSON
 */
export const isValidJSON = (str: string): boolean => {
  try {
    const trimmed = str.trim();
    if (!trimmed) return false;

    // 检查是否以 { 或 [ 开头，以 } 或 ] 结尾
    if (
      !(
        (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
        (trimmed.startsWith('[') && trimmed.endsWith(']'))
      )
    ) {
      return false;
    }

    JSON.parse(trimmed);
    return true;
  } catch {
    return false;
  }
};

/**
 * 格式化 JSON 字符串
 * @param str 要格式化的 JSON 字符串
 * @param indent 缩进空格数，默认为 2
 * @returns 格式化后的 JSON 字符串
 */
export const formatJSON = (str: string, indent: number = 2): string => {
  try {
    const parsed = JSON.parse(str.trim());
    return JSON.stringify(parsed, null, indent);
  } catch {
    return str;
  }
};

/**
 * 检测字符串是否可能是正在构建中的 JSON
 * 用于流式输出过程中的实时检测
 * @param str 要检测的字符串
 * @returns 检测结果
 */
export const detectStreamingJSON = (str: string): JsonDetectionResult => {
  const trimmed = str.trim();

  if (!trimmed) {
    return { isJson: false, isComplete: false };
  }

  // 检查是否以 JSON 开始符号开头
  const startsWithJson = trimmed.startsWith('{') || trimmed.startsWith('[');

  if (!startsWithJson) {
    return { isJson: false, isComplete: false };
  }

  // 尝试解析完整的 JSON
  try {
    const parsed = JSON.parse(trimmed);
    const formatted = JSON.stringify(parsed, null, 2);
    return {
      isJson: true,
      isComplete: true,
      formatted,
    };
  } catch (error) {
    // 如果解析失败，检查是否是不完整的 JSON
    const isIncompleteJson = checkIncompleteJSON(trimmed);

    return {
      isJson: isIncompleteJson,
      isComplete: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
};

/**
 * 检查是否为不完整的 JSON（正在构建中）
 * @param str 要检测的字符串
 * @returns 是否为不完整的 JSON
 */
const checkIncompleteJSON = (str: string): boolean => {
  // 基本的 JSON 开始检查
  if (!str.startsWith('{') && !str.startsWith('[')) {
    return false;
  }

  // 计算括号匹配情况
  let braceCount = 0;
  let bracketCount = 0;
  let inString = false;
  let escaped = false;

  for (const char of str) {
    if (escaped) {
      escaped = false;
      continue;
    }

    if (char === '\\') {
      escaped = true;
      continue;
    }

    if (char === '"' && !escaped) {
      inString = !inString;
      continue;
    }

    if (!inString) {
      if (char === '{') {
        braceCount++;
      } else if (char === '}') {
        braceCount--;
      } else if (char === '[') {
        bracketCount++;
      } else if (char === ']') {
        bracketCount--;
      }
    }
  }

  // 如果括号没有完全匹配，可能是不完整的 JSON
  return braceCount > 0 || bracketCount > 0;
};

/**
 * 尝试修复不完整的 JSON 字符串（用于预览）
 * @param str 不完整的 JSON 字符串
 * @returns 修复后的 JSON 字符串或原字符串
 */
export const tryFixIncompleteJSON = (str: string): string => {
  const trimmed = str.trim();

  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
    return str;
  }

  try {
    // 尝试直接解析
    JSON.parse(trimmed);
    return trimmed;
  } catch {
    // 尝试添加缺失的结束符号
    let fixed = trimmed;

    // 计算需要的结束符号
    let braceCount = 0;
    let bracketCount = 0;
    let inString = false;
    let escaped = false;

    for (const char of fixed) {
      if (escaped) {
        escaped = false;
        continue;
      }

      if (char === '\\') {
        escaped = true;
        continue;
      }

      if (char === '"' && !escaped) {
        inString = !inString;
        continue;
      }

      if (!inString) {
        if (char === '{') {
          braceCount++;
        } else if (char === '}') {
          braceCount--;
        } else if (char === '[') {
          bracketCount++;
        } else if (char === ']') {
          bracketCount--;
        }
      }
    }

    // 如果在字符串中结束，添加结束引号
    if (inString) {
      fixed += '"';
    }

    // 添加缺失的结束括号
    while (braceCount > 0) {
      fixed += '}';
      braceCount--;
    }

    while (bracketCount > 0) {
      fixed += ']';
      bracketCount--;
    }

    try {
      JSON.parse(fixed);
      return fixed;
    } catch {
      return str; // 如果修复失败，返回原字符串
    }
  }
};