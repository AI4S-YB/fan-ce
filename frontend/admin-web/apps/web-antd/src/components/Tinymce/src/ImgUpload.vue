<script lang="ts" setup>
import { computed, reactive } from 'vue';

import { Button, Upload } from 'ant-design-vue';

import { $t as t } from '#/locales';
import { getAccessToken, getTenantId } from '#/utils/auth';
import { useDesign } from '#/utils/vbenModle';

defineOptions({ name: 'TinymceImageUpload' });

const props = defineProps({
  fullscreen: {
    type: Boolean,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits(['uploading', 'done', 'error']);
const headers = reactive({
  Authorization: `Bearer ${getAccessToken()}`,
  'tenant-id': getTenantId(),
});
let uploading = false;

const uploadUrl = '';

const { prefixCls } = useDesign('tinymce-img-upload');

const getButtonProps = computed(() => {
  const { disabled } = props;
  return {
    disabled,
  };
});

function handleChange(info: Recordable) {
  const file = info.file;
  const status = file?.status;
  const url = file?.response?.data;
  const name = file?.name;

  switch (status) {
    case 'done': {
      emit('done', name, url);
      uploading = false;

      break;
    }
    case 'error': {
      emit('error');
      uploading = false;

      break;
    }
    case 'uploading': {
      if (!uploading) {
        emit('uploading', name);
        uploading = true;
      }

      break;
    }
    // No default
  }
}
</script>

<template>
  <div :class="[prefixCls, { fullscreen }]">
    <Upload
      name="file"
      :headers="headers"
      multiple
      :action="uploadUrl"
      :show-upload-list="false"
      accept=".jpg,.jpeg,.gif,.png,.webp"
      @change="handleChange"
    >
      <Button type="primary" v-bind="{ ...getButtonProps }">
        {{ t('component.upload.imgUpload') }}
      </Button>
    </Upload>
  </div>
</template>

<style lang="less" scoped>
@namespace: 'vben';
@prefix-cls: ~'@{namespace}-tinymce-img-upload';

.@{prefix-cls} {
  position: absolute;
  top: 4px;
  right: 10px;
  z-index: 20;

  &.fullscreen {
    position: fixed;
    z-index: 10000;
  }
}
</style>
