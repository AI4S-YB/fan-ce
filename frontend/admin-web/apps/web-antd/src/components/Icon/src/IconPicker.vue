<script lang="ts" setup>
import { ref, watch, watchEffect } from 'vue';

import { useDebounceFn } from '@vueuse/core';
import { Empty, Input, Pagination, Popover } from 'ant-design-vue';

import { usePagination } from '#/hooks/web/usePagination';
// import { useI18n } from '@/hooks/web/useI18n';
import { copyText } from '#/utils/copyTextToClipboard';
import { useNamespace } from '#/utils/vbenModle';

import { ScrollContainer } from '../../Container';
import iconsData, { iconData } from '../data/icons.data';
import Icon from './Icon.vue';

export interface Props {
  value?: string;
  width?: string;
  pageSize?: number;
  copy?: boolean;
  mode?: 'iconify' | 'svg';
}

const props = withDefaults(defineProps<Props>(), {
  value: '',
  width: '100%',
  pageSize: 140,
  copy: false,
  mode: 'iconify',
});

const emit = defineEmits(['change', 'update:value']);

function getIcons() {
  const data = iconsData as any;
  const prefix: string = data?.prefix ?? '';
  let result: string[] = [];
  if (prefix) {
    result = (data?.icons ?? []).map((item: any) => `${prefix}:${item}`);
    result = [...iconData, ...result];
  } else if (Array.isArray(iconsData)) result = iconsData as string[];

  return result;
}

function getSvgIcons() {
  // return svgIcons.map((icon: string) => icon.replace('icon-', ''));
}

const isSvgMode = props.mode === 'svg';
const icons: any = isSvgMode ? getSvgIcons() : getIcons();

const currentSelect = ref('');
const open = ref(false);
const currentList = ref(icons);

// const { t } = useI18n();
const { b } = useNamespace('icon-picker');
const prefixCls = b();

const debounceHandleSearchChange = useDebounceFn(handleSearchChange, 100);

const { getPaginationList, getTotal, setCurrentPage } = usePagination(
  currentList,
  props.pageSize,
);

watchEffect(() => {
  currentSelect.value = props.value;
});

watch(
  () => currentSelect.value,
  (v) => {
    emit('update:value', v);
    return emit('change', v);
  },
);

function handlePageChange(page: number) {
  setCurrentPage(page);
}

function handleClick(icon: string) {
  currentSelect.value = icon;
  console.log('cccccc', currentSelect.value);

  if (props.copy) copyText(icon, 'copy');
}

function handleSearchChange(e: ChangeEvent) {
  const value = e.target.value;
  if (!value) {
    setCurrentPage(1);
    currentList.value = icons;
    return;
  }
  currentList.value = icons.filter((item: string | string[]) =>
    item.includes(value),
  );
}
</script>

<template>
  <Input
    v-model:value="currentSelect"
    disabled
    :style="{ width }"
    placeholder="placeholder"
    :class="prefixCls"
  >
    <template #addonAfter>
      <Popover
        v-model="open"
        placement="bottomRight"
        trigger="click"
        :overlay-class-name="`${prefixCls}-popover`"
      >
        <template #title>
          <div class="flex justify-between">
            <Input
              placeholder="search"
              allow-clear
              @change="debounceHandleSearchChange"
            />
          </div>
        </template>

        <template #content>
          <div v-if="getPaginationList.length > 0">
            <ScrollContainer class="border border-t-0 border-solid">
              <ul class="flex flex-wrap px-2">
                <li
                  v-for="icon in getPaginationList"
                  :key="icon"
                  :class="currentSelect === icon ? 'border-primary border' : ''"
                  class="w-1/8 hover:border-primary mr-1 mt-1 flex cursor-pointer items-center justify-center border border-solid p-2"
                  :title="icon"
                  @click="handleClick(icon)"
                >
                  <Icon :icon="icon" />
                </li>
              </ul>
            </ScrollContainer>
            <div
              v-if="getTotal >= pageSize"
              class="flex items-center justify-center py-2"
            >
              <Pagination
                show-less-items
                size="small"
                :page-size="pageSize"
                :total="getTotal"
                @change="handlePageChange"
              />
            </div>
          </div>
          <template v-else>
            <div class="p-5">
              <Empty />
            </div>
          </template>
        </template>

        <span
          v-if="isSvgMode && currentSelect"
          class="flex cursor-pointer items-center px-2 py-1"
        >
          <!-- <SvgIcon :name="currentSelect" /> -->
        </span>
        <Icon
          v-else
          :icon="currentSelect || 'material-symbols:database'"
          class="cursor-pointer px-2 py-1"
        />
      </Popover>
    </template>
  </Input>
</template>

<style lang="scss"></style>
