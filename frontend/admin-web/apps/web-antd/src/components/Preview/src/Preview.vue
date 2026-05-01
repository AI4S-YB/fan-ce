<script lang="ts" setup>
import { computed } from 'vue';

import { Image, ImagePreviewGroup } from 'ant-design-vue';

import { isString } from '#/utils/is';
import { propTypes } from '#/utils/propTypes';
import { useDesign } from '#/utils/vbenModle';

interface ImageProps {
  alt?: string;
  fallback?: string;
  src: string;
  width: number | string;
  height?: number | string;
  placeholder?: boolean | string;
  preview?:
    | boolean
    | {
        getContainer: (() => HTMLElement) | HTMLElement | string;
        onOpenChange?: (open: boolean, prevOpen: boolean) => void;
        open?: boolean;
      };
}

type ImageItem = ImageProps | string;

defineOptions({ name: 'ImagePreview' });

const props = defineProps({
  functional: propTypes.bool,
  imageList: {
    type: Array as PropType<ImageItem[]>,
  },
});

const { prefixCls } = useDesign('image-preview');

const getImageList = computed((): any[] => {
  const { imageList } = props;
  if (!imageList) return [];

  return imageList.map((item) => {
    if (isString(item)) {
      return {
        src: item,
        placeholder: false,
      };
    }
    return item;
  });
});
</script>

<template>
  <div :class="prefixCls">
    <ImagePreviewGroup>
      <slot v-if="!imageList || $slots.default"></slot>
      <template v-else>
        <template v-for="item in getImageList" :key="item.src">
          <Image v-bind="item">
            <template v-if="item.placeholder" #placeholder>
              <Image v-bind="item" :src="item.placeholder" :preview="false" />
            </template>
          </Image>
        </template>
      </template>
    </ImagePreviewGroup>
  </div>
</template>

<style lang="less">
@namespace: 'vben';
@prefix-cls: ~'@{namespace}-image-preview';

.@{prefix-cls} {
  .ant-image {
    margin-right: 10px;
  }

  .ant-image-preview-operations {
    background-color: rgb(0 0 0 / 40%);
  }
}
</style>
