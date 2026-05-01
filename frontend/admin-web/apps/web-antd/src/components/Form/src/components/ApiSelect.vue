<script lang="ts" setup>
import type { SelectValue } from 'ant-design-vue/es/select';

import type { PropType } from 'vue';

import { computed, ref, unref, watch } from 'vue';

import { LoadingOutlined } from '@ant-design/icons-vue';
import { Select, Spin } from 'ant-design-vue';
import { get, omit } from 'lodash-es';

import { useRuleFormItem } from '#/hooks/component/useFormItem';
import { $t as t } from '#/locales';
import { isFunction } from '#/utils/is';
import { propTypes } from '#/utils/propTypes';

interface OptionsItem {
  label: string;
  value: string;
  disabled?: boolean;
}

defineOptions({ name: 'ApiSelect', inheritAttrs: false });

const props = defineProps({
  value: { type: [Array, Object, String, Number] as PropType<SelectValue> },
  numberToString: propTypes.bool,
  api: {
    type: Function as PropType<(arg?: any) => Promise<OptionsItem[]>>,
    default: null,
  },
  // api params
  params: propTypes.any.def({}),
  // support xxx.xxx.xx
  resultField: propTypes.string.def(''),
  labelField: propTypes.string.def('label'),
  valueField: propTypes.string.def('value'),
  immediate: propTypes.bool.def(true),
  alwaysLoad: propTypes.bool.def(false),
  options: {
    type: Array<OptionsItem>,
    default: [],
  },
  // 全选功能相关属性
  showSelectAll: propTypes.bool.def(false),
  enableSearch: propTypes.bool.def(false),
  showCount: propTypes.bool.def(false),
  maxTagCount: propTypes.number.def(2),
});
const emit = defineEmits(['options-change', 'change', 'update:value']);
const options = ref<OptionsItem[]>([]);
const loading = ref(false);
// 首次是否加载过了
const isFirstLoaded = ref(false);
const emitData = ref<OptionsItem[]>([]);
// 搜索关键词
const keyword = ref('');

// Embedded in the form, just use the hook binding to perform form verification
const [state] = useRuleFormItem(props, 'value', 'change', emitData);

const getOptions = computed(() => {
  const { labelField, valueField, numberToString } = props;

  const data = unref(options).reduce((prev, next: any) => {
    if (next) {
      const value = get(next, valueField);
      prev.push({
        ...omit(next, [labelField, valueField]),
        label: get(next, labelField),
        value: numberToString ? `${value}` : value,
      });
    }
    return prev;
  }, [] as OptionsItem[]);
  return data.length > 0 ? data : props.options;
});

// 过滤后的选项
const filteredOptions = computed(() => {
  if (!props.enableSearch || !keyword.value) return getOptions.value;
  const kw = keyword.value.toLowerCase();
  return getOptions.value.filter((o) => o.label.toLowerCase().includes(kw));
});

watch(
  () => state.value,
  (v) => {
    emit('update:value', v);
  },
);

watch(
  () => props.params,
  () => {
    !unref(isFirstLoaded) && fetch();
  },
  { deep: true, immediate: props.immediate },
);

async function fetch() {
  const api = props.api;
  if (!api || !isFunction(api) || loading.value) return;
  options.value = [];
  try {
    loading.value = true;
    const res = await api(props.params);
    isFirstLoaded.value = true;
    if (Array.isArray(res)) {
      options.value = res;
      emitChange();
      return;
    }
    if (props.resultField) options.value = get(res, props.resultField) || [];

    emitChange();
  } catch (error) {
    console.warn(error);
  } finally {
    loading.value = false;
    // reset status
    isFirstLoaded.value = false;
  }
}

async function handleFetch(open: boolean) {
  if (open) {
    if (props.alwaysLoad) await fetch();
    else if (!props.immediate && !unref(isFirstLoaded)) await fetch();
  }
}

function emitChange() {
  emit('options-change', unref(getOptions));
}

function handleChange(_: any, ...args: any[]) {
  emitData.value = args;
}

// 全选功能
function handleSelectAll() {
  const all = filteredOptions.value.map((o) => o.value);
  state.value = all;
  emit('update:value', all);
  emit('change', all);
}

function handleUnselectAll() {
  state.value = [];
  emit('update:value', []);
  emit('change', []);
}

function onSearch(val: string) {
  keyword.value = val;
}
</script>

<template>
  <Select
    v-bind="$attrs"
    v-model:value="state"
    :options="filteredOptions"
    :show-search="enableSearch"
    :filter-option="false"
    :max-tag-count="showSelectAll ? maxTagCount : undefined"
    @dropdown-visible-change="handleFetch"
    @change="handleChange"
    @search="onSearch"
  >
    <template v-for="item in Object.keys($slots)" #[item]="data">
      <slot :name="item" v-bind="data || {}"></slot>
    </template>
    <template v-if="loading" #suffixIcon>
      <LoadingOutlined spin />
    </template>
    <template v-if="loading" #notFoundContent>
      <span>
        <LoadingOutlined spin class="mr-1" />
        {{ t('component.form.apiSelectNotFound') }}
      </span>
    </template>
    <!-- 全选功能的下拉面板 -->
    <template v-if="showSelectAll && $attrs.mode === 'multiple'" #dropdownRender="{ menuNode }">
      <div>
        <div
          style="display:flex; gap:8px; align-items:center; padding:8px; border-bottom:1px solid var(--color-border,#f0f0f0)"
        >
          <a @click.stop.prevent="handleSelectAll">{{ $t('component.select.selectAll') }}</a>
          <a @click.stop.prevent="handleUnselectAll">{{ $t('component.select.deselectAll') }}</a>
          <span v-if="showCount" style="margin-left:auto; color:#999">
            {{ filteredOptions.length }}/{{ getOptions.length }}
          </span>
        </div>
        <Spin :spinning="loading">
          <div style="max-height:300px; overflow:auto">
            <component :is="menuNode" />
          </div>
        </Spin>
      </div>
    </template>
  </Select>
</template>
