<script lang="ts" setup>
import type { FileItem } from './typing';

import { computed, ref, toRefs, unref } from 'vue';

import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  InboxOutlined,
  SyncOutlined,
} from '@ant-design/icons-vue';
import { Button, Progress, Tag, UploadDragger } from 'ant-design-vue';

import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';
import { isFunction } from '#/utils/is';
import { warn } from '#/utils/log';
import { buildUUID } from '#/utils/uuid';

import { basicProps } from './props';
import { UploadResultStatus } from './typing';
import { useUploadType } from './useUpload';

const props = defineProps({
  ...basicProps,
  previewFileList: {
    type: Array as PropType<string[]>,
    default: () => [],
  },
  dataTypeStr: { type: String, default: '' },
  isShowPreview: { type: Boolean, default: false },
  modelValue: { type: Array, default: () => [] },
});
const emit = defineEmits(['change', 'register', 'delete', 'update:modelValue']);

//   是否正在上传

const isUploadingRef = ref(false);
const fileListRef = ref<FileItem[]>([]);
const { createMessage } = useMessage();
const { accept, helpText, maxNumber, maxSize } = toRefs(props);

// 显示后缀和提示
const { getStringAccept, getHelpText } = useUploadType({
  acceptRef: accept,
  helpTextRef: helpText,
  maxNumberRef: maxNumber,
  maxSizeRef: maxSize,
});

const getIsSelectFile = computed(() => {
  return (
    fileListRef.value.length > 0 &&
    !fileListRef.value.every(
      (item) => item.status === UploadResultStatus.SUCCESS,
    )
  );
});

const getOkButtonProps = computed(() => {
  const someSuccess = fileListRef.value.some(
    (item) => item.status === UploadResultStatus.SUCCESS,
  );
  return {
    disabled:
      isUploadingRef.value || fileListRef.value.length === 0 || !someSuccess,
  };
});

const getUploadBtnText = computed(() => {
  const someError = fileListRef.value.some(
    (item) => item.status === UploadResultStatus.ERROR,
  );
  return isUploadingRef.value
    ? t('component.upload.uploading')
    : someError
      ? t('component.upload.reUploadFailed')
      : t('component.upload.startUpload');
});

// 上传前校验
function beforeUpload(file: File) {
  const { size, name } = file;
  const { maxSize } = props;
  // emit('update:modelValue', file);
  // emit('change', file);
  // 设置最大值，则判断
  if (maxSize && file.size / 1024 / 1024 >= maxSize) {
    createMessage.error(t('component.upload.maxSizeMultiple', [maxSize]));
    return true;
  }
  const commonItem = {
    uuid: buildUUID(),
    file,
    size,
    name,
    percent: 0,
    data_type: '',
    type: name.split('.').pop(),
  };
  fileListRef.value = [...unref(fileListRef), commonItem];
  emit('change', fileListRef.value);
  return false;
}

// 删除
function handleRemove(record: FileItem) {
  const index = fileListRef.value.findIndex(
    (item) => item.uuid === record.uuid,
  );
  index !== -1 && fileListRef.value.splice(index, 1);
  emit('delete', record);
}

// 上传到api后端
async function uploadApiByItem(item: FileItem) {
  const { api } = props;
  if (!api || !isFunction(api))
    return warn('upload api must exist and be a function');

  try {
    item.status = UploadResultStatus.UPLOADING;
    const data = await props.api?.(
      {
        data: {
          ...props.uploadParams,
          uid: item.uuid,
          data_type: item.data_type || '',
        },

        file: item.file,
        name: props.name,
        filename: props.filename,
      },
      (progressEvent: ProgressEvent) => {
        const complete =
          ((progressEvent.loaded / progressEvent.total) * 100) | 0;
        item.percent = complete;
      },
    );
    item.status = UploadResultStatus.SUCCESS;
    item.responseData = data;
    return {
      success: true,
      error: null,
    };
  } catch (error) {
    item.status = UploadResultStatus.ERROR;
    return {
      success: false,
      error,
    };
  }
}

// 点击开始上传
async function handleStartUpload(file: any) {
  fileListRef.value = file;
  const { maxNumber } = props;
  if (fileListRef.value.length + props.previewFileList?.length > maxNumber)
    return createMessage.warning(t('component.upload.maxNumber', [maxNumber]));

  try {
    isUploadingRef.value = true;
    // 只上传不是成功状态的
    const uploadFileList =
      fileListRef.value.filter(
        (item) => item.status !== UploadResultStatus.SUCCESS,
      ) || [];
    const data = await Promise.all(
      uploadFileList.map((item) => {
        return uploadApiByItem(item);
      }),
    );
    isUploadingRef.value = false;
    // 生产环境:抛出错误
    const errorList = data.filter((item: any) => !item.success);
    if (errorList.length > 0) throw errorList;
  } catch (error) {
    isUploadingRef.value = false;
    throw error;
  }
}

//   点击保存
function handleOk() {
  if (fileListRef.value.length > props.maxNumber)
    return createMessage.warning(
      t('component.upload.maxNumber', [props.maxNumber]),
    );

  if (isUploadingRef.value)
    return createMessage.warning(t('component.upload.saveWarn'));

  const fileList: Object[] = [];
  for (const item of fileListRef.value) {
    const { status, responseData } = item;
    if (status === UploadResultStatus.SUCCESS && responseData)
      fileList.push({
        url: responseData.url,
        name: item.name,
        type: item.type,
        size: item.size,
      });
  }
  // 存在一个上传成功的即可保存
  if (fileList.length <= 0)
    return createMessage.warning(t('component.upload.saveError'));
  fileListRef.value = [];
  emit('change', fileList);
}

defineExpose({
  handleOk,
  handleRemove,
  handleStartUpload,
  fileListRef,
});
</script>

<template>
  <div class="upload-modal-toolbar">
    <UploadDragger
      :accept="getStringAccept"
      :multiple="multiple"
      :before-upload="beforeUpload"
      :show-upload-list="false"
      class="upload-div"
    >
      <p class="ant-upload-drag-icon">
        <InboxOutlined />
      </p>
      <p>{{ dataTypeStr }}，{{ getHelpText }}</p>
    </UploadDragger>
  </div>
  <slot name="fileListShow" :item="fileListRef.values">
    <div v-if="isShowPreview">
      <div v-for="file in fileListRef" class="progress-div">
        <div class="progress-name mr-3">
          {{ file.name }}
        </div>
        <div class="progress-content">
          <Progress
            v-if="file.status == 'error'"
            :stroke-color="{
              '0%': '#108ee9',
              '100%': '#87d068',
            }"
            :percent="file.percent"
            size="small"
            status="exception"
          />
          <Progress
            v-else
            :stroke-color="{
              '0%': '#108ee9',
              '100%': '#87d068',
            }"
            :percent="file.percent"
            size="small"
            status="active"
          />
        </div>
        <div class="progress-action">
          <Tag v-if="file.status == 'uploading'" color="processing">
            <template #icon>
              <SyncOutlined :spin="true" />
            </template>
            {{ $t('component.upload.uploading') }}
          </Tag>
          <Tag v-else-if="file.status == 'success'" color="success">
            <template #icon>
              <CheckCircleOutlined />
            </template>
            {{ $t('component.upload.uploadSuccess') }}
          </Tag>
          <Tag v-else-if="file.status == 'error'" color="error">
            <template #icon> <CloseCircleOutlined /> </template>{{ $t('component.upload.uploadError') }}
          </Tag>
          <Tag v-else color="warning">
            <template #icon> <ExclamationCircleOutlined /> </template>{{ $t('component.upload.pending') }}
          </Tag>
        </div>
        <div class="progress-action">
          <Button size="small" type="link" block @click="handleRemove(file)">
            <template #icon>
              <DeleteOutlined />
            </template>
          </Button>
        </div>
      </div>
    </div>
  </slot>
</template>

<style lang="less">
.upload-modal {
  .ant-upload-list {
    display: none;
  }

  .ant-table-wrapper .ant-spin-nested-loading {
    padding: 0;
  }

  &-toolbar {
    display: flex;
    align-items: center;
    margin-bottom: 8px;

    &__btn {
      flex: 1;
      margin-left: 8px;
      text-align: right;
    }
  }
}
</style>
<style lang="scss" scoped>
.upload-div {
  width: 550px;
}

.progress-div {
  display: flex;
  align-items: center;
  justify-content: center;

  // width: 440px;
  .progress-select {
    width: 100px;
  }

  .progress-name {
    justify-content: flex-start;
    // width: calc(100% - 250px);
  }

  .progress-content {
    flex: 1;
    padding-right: 10px;
    margin-top: 5px;
    // width: 200px;
  }

  .progress-action {
    justify-content: flex-end;
  }
}
</style>
