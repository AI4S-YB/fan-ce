<script lang="ts" setup>
import { computed, unref } from 'vue';

import { Icon } from '#/components/Icon';
import { $t } from '@vben/locales';
import { useMessage } from '#/hooks/web/useMessage';

const props = defineProps({
  element: { type: HTMLElement, required: true },
  fileList: { type: Object, required: true },
  mover: { type: Boolean, required: true },
  download: { type: Boolean, required: true },
  emitValue: { type: Function, required: true },
});

const { createMessage } = useMessage();

const list = computed(() => unref(props.fileList));

// 向前移动图片
function onMoveForward() {
  const index = getIndexByUrl();
  if (index === -1) {
    createMessage.warn($t('component.uploadExtra.moveFailed', { index }));
    return;
  }
  if (index === 0) {
    doSwap(index, unref(list).length - 1);
    return;
  }
  doSwap(index, index - 1);
}

// 向后移动图片
function onMoveBack() {
  const index = getIndexByUrl();
  if (index === -1) {
    createMessage.warn($t('component.uploadExtra.moveFailed', { index }));
    return;
  }
  if (index === unref(list).length - 1) {
    doSwap(index, 0);
    return;
  }
  doSwap(index, index + 1);
}

function doSwap(oldIndex, newIndex) {
  if (oldIndex !== newIndex) {
    const array: any[] = [...(unref(list) as Array<any>)];
    const temp = array[oldIndex];
    array[oldIndex] = array[newIndex];
    array[newIndex] = temp;
    props.emitValue(array.map((i) => i.url).join(','));
  }
}

function getIndexByUrl() {
  const url = props.element?.getElementsByTagName('img')[0]?.src;
  if (url) {
    const fileList: any = unref(list);
    for (const [i, element] of fileList.entries()) {
      const current = element.url;
      const replace = url.replace(window.location.origin, '');
      if (current === replace || encodeURI(current) === replace) return i;
    }
  }
  return -1;
}

function onDownload() {
  const url = props.element?.getElementsByTagName('img')[0]?.src;
  window.open(url);
}
</script>

<template>
  <div v-show="download" class="upload-download-handler">
    <a class="download" :title="$t('component.upload.download')" @click="onDownload">
      <Icon icon="ant-design:download" />
    </a>
  </div>
  <div v-show="mover && list.length > 1" class="upload-mover-handler">
    <a :title="$t('component.uploadExtra.moveForward')" @click="onMoveForward">
      <Icon icon="ant-design:arrow-left" />
    </a>
    <a :title="$t('component.uploadExtra.moveBackward')" @click="onMoveBack">
      <Icon icon="ant-design:arrow-right" />
    </a>
  </div>
</template>
