<script lang="ts" setup>
import type { PreviewFileItem } from './typing';

import { ref, watch } from 'vue';

import { BasicModal, useModalInner } from '#/components/Modal';
import { $t } from '#/locales';
import { downloadByUrl } from '#/utils/antdAll';
import { isArray } from '#/utils/is';

import { createPreviewActionColumn, createPreviewColumns } from './data';
import FileList from './FileList.vue';
import { previewProps } from './props';

const props = defineProps(previewProps);
const emit = defineEmits(['list-change', 'register', 'delete']);

const [register] = useModalInner();
const t = $t;

const columns = createPreviewColumns() as any[];
const actionColumn = createPreviewActionColumn({
  handleRemove,
  handleDownload,
}) as any;

const fileListRef = ref<PreviewFileItem[]>([]);
watch(
  () => props.value,
  (value) => {
    if (!isArray(value)) value = [];
    fileListRef.value = value
      .filter((item) => !!item)
      .map((item: any) => {
        return {
          url: item.url,
          type: item.url.split('.').pop() || '',
          name: item.url.split('/').pop() || '',
        };
      });
  },
  { immediate: true },
);

// 删除
function handleRemove(record: PreviewFileItem) {
  const index = fileListRef.value.findIndex((item) => item.url === record.url);

  if (index !== -1) {
    const removed: any = fileListRef.value.splice(index, 1);
    emit('delete', removed[0].url);
    emit(
      'list-change',
      fileListRef.value.map((item) => item.url),
    );
  }
}

// 下载
function handleDownload(record: PreviewFileItem) {
  const { url = '' } = record;
  downloadByUrl({ url });
}
</script>

<template>
  <BasicModal
    width="800px"
    :title="t('component.upload.preview')"
    class="upload-preview-modal"
    v-bind="$attrs"
    :show-ok-btn="false"
    @register="register"
  >
    <FileList
      :data-source="fileListRef"
      :columns="columns"
      :action-column="actionColumn"
    />
  </BasicModal>
</template>

<style lang="less">
.upload-preview-modal {
  .ant-upload-list {
    display: none;
  }

  .ant-table-wrapper .ant-spin-nested-loading {
    padding: 0;
  }
}
</style>
