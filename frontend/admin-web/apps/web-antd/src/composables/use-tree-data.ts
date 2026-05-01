import { computed, ref } from 'vue';

export interface TreeNodeItem {
  key: string;
  label: string;
  value?: any;
  children?: TreeNodeItem[];
  isArray?: boolean;
}

export interface FlatTreeNode extends TreeNodeItem {
  level: number;
}

/**
 * 递归构建树形结构数据
 * @param obj 要转换的对象
 * @param parentKey 父级键名
 * @returns 树形结构数组
 */
export function buildTreeData(
  obj: Record<string, any>,
  parentKey = '',
): TreeNodeItem[] {
  const result: TreeNodeItem[] = [];

  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      const value = obj[key];
      const currentKey = parentKey ? `${parentKey}.${key}` : key;

      if (
        typeof value === 'object' &&
        value !== null &&
        !Array.isArray(value)
      ) {
        // 对象类型，递归处理
        const children = buildTreeData(value, currentKey);
        result.push({
          key: currentKey,
          label: key,
          children,
        });
      } else if (Array.isArray(value)) {
        // 数组类型
        const children = value.map((item, idx) => {
          const arrayKey = `${currentKey}[${idx}]`;
          return typeof item === 'object' && item !== null
            ? {
                key: arrayKey,
                label: `[${idx}]`,
                children: buildTreeData(item, arrayKey),
              }
            : {
                key: arrayKey,
                label: `[${idx}]`,
                value: item,
              };
        });
        result.push({
          key: currentKey,
          label: key,
          children,
          isArray: true, // 标记为数组类型
        });
      } else {
        // 基本类型
        result.push({
          key: currentKey,
          label: key,
          value,
        });
      }
    }
  }

  return result;
}

/**
 * 将树形数据重建为原始对象结构
 * @param treeItems 树形数据项
 * @returns 重建的原始对象
 */
export function rebuildOriginalData(
  treeItems: TreeNodeItem[],
): Record<string, any> {
  const result: Record<string, any> = {};

  function processItems(items: TreeNodeItem[], target: Record<string, any>) {
    for (const item of items) {
      if (item.value !== undefined) {
        // 叶子节点，设置值
        setNestedValue(target, item.key, item.value);
      } else if (item.children) {
        if (item.isArray) {
          // 数组类型
          const arrayData: any[] = [];
          for (const child of item.children) {
            if (child.children) {
              // 数组元素是对象
              const childObj = {};
              processItems(child.children, childObj);
              arrayData.push(childObj);
            } else {
              // 数组元素是基本类型
              arrayData.push(child.value);
            }
          }
          setNestedValue(target, item.key, arrayData);
        } else {
          // 对象类型
          if (!getNestedValue(target, item.key)) {
            setNestedValue(target, item.key, {});
          }
          const nestedObj = getNestedValue(target, item.key);
          processItems(item.children, nestedObj);
        }
      }
    }
  }

  processItems(treeItems, result);
  return result;
}

/**
 * 设置嵌套对象的值
 * @param obj 目标对象
 * @param path 路径字符串，如 'a.b.c' 或 'a.b[0].c'
 * @param value 要设置的值
 */
function setNestedValue(obj: any, path: string, value: any) {
  const keys = path.split(/[.[\]]/).filter(Boolean);
  let current = obj;

  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];
    const nextKey = keys[i + 1];

    if (key && !(key in current)) {
      // 判断下一个键是否为数组索引
      current[key] = nextKey && /^\d+$/.test(nextKey) ? [] : {};
    }
    if (key) {
      current = current[key];
    }
  }

  const lastKey = keys[keys.length - 1];
  if (lastKey) {
    current[lastKey] = value;
  }
}

/**
 * 获取嵌套对象的值
 * @param obj 源对象
 * @param path 路径字符串
 * @returns 获取到的值
 */
function getNestedValue(obj: any, path: string): any {
  const keys = path.split(/[.[\]]/).filter(Boolean);
  let current = obj;

  for (const key of keys) {
    if (current && typeof current === 'object' && key in current) {
      current = current[key];
    } else {
      return undefined;
    }
  }

  return current;
}

/**
 * 使用树形数据的 Hook
 * @param dataLoader 数据加载函数
 * @param onDataChange 数据变化回调函数（可选）
 * @returns 树形数据状态和更新函数
 */
export function useTreeData(
  dataLoader: () => Promise<any>,
  onDataChange?: (data: any) => void,
) {
  const loading = ref(true);
  const treeData = ref<TreeNodeItem[]>([]);
  const collapsedStates = ref<Record<string, boolean>>({});
  const originalData = ref<any>(null);

  const toggleCollapse = (key: string) => {
    collapsedStates.value[key] = !collapsedStates.value[key];
  };

  const flattenedVisibleTree = computed(() => {
    const result: FlatTreeNode[] = [];
    function flatten(items: TreeNodeItem[], level: number) {
      for (const item of items) {
        result.push({ ...item, level });
        if (
          item.children &&
          (!item.isArray || !collapsedStates.value[item.key])
        ) {
          flatten(item.children, level + 1);
        }
      }
    }
    flatten(treeData.value, 0);
    return result;
  });

  const loadData = async () => {
    loading.value = true;
    try {
      const data = await dataLoader();
      originalData.value = data;
      treeData.value = buildTreeData(data);
      collapsedStates.value = {};
    } catch (error) {
      console.error('Failed to load tree data:', error);
    } finally {
      loading.value = false;
    }
  };

  const updateValue = (key: string, newValue: string) => {
    function updateValueRecursive(
      items: TreeNodeItem[],
      targetKey: string,
      value: string,
    ): boolean {
      for (const item of items) {
        if (item.key === targetKey) {
          item.value = value;
          return true;
        }
        if (
          item.children &&
          updateValueRecursive(item.children, targetKey, value)
        ) {
          return true;
        }
      }
      return false;
    }

    updateValueRecursive(treeData.value, key, newValue);

    // 同步数据变化
    syncDataChange();
  };

  /**
   * 同步树形数据变化到原始数据结构
   */
  const syncDataChange = () => {
    if (onDataChange) {
      const rebuiltData = rebuildOriginalData(treeData.value);
      onDataChange(rebuiltData);
    }
  };

  /**
   * 手动重新加载数据（用于外部数据变化时）
   */
  const reloadFromExternal = (externalData: any) => {
    originalData.value = externalData;
    treeData.value = buildTreeData(externalData);
  };

  return {
    loading,
    treeData: flattenedVisibleTree,
    loadData,
    updateValue,
    toggleCollapse,
    syncDataChange,
    reloadFromExternal,
  };
}
