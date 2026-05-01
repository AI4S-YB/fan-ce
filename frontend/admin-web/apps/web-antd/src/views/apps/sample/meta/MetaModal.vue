<script lang="ts" setup>
import { ref, unref } from 'vue';

import { useVbenForm } from '#/adapter/form';
import { addSampleMetaApi, updateSampleMetaApi } from '#/api/apps/sample';
import { BasicModal, useModalInner } from '#/components/Modal';
import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';

import { metaUseFormSchema } from './data';

defineOptions({ name: 'ScanModal' });
const emit = defineEmits(['success', 'register']);

const { createMessage } = useMessage();
const isUpdate = ref(false);
const [Form, formApi] = useVbenForm({
  schema: metaUseFormSchema(),
  showDefaultActions: false,
});
const Row = ref();
const [registerModal, { setModalProps, closeModal }] = useModalInner(
  async (data) => {
    Row.value = data.row;
    isUpdate.value = data?.isUpdate;
    await formApi.resetForm();
    setModalProps({ confirmLoading: false });
    if (unref(isUpdate)) {
      formApi.setValues({ ...data.row });
    }
  },
);
// 提交数据
async function handleSubmit() {
  try {
    const valid = await formApi.validate();
    if (valid.valid) {
      const formData = await formApi.getValues();
      formData.sample_id = Row.value.sample_id;
      if (unref(isUpdate)) {
        formData.id = Row.value.id;
      }
      await (unref(isUpdate)
        ? updateSampleMetaApi(formData)
        : addSampleMetaApi(formData));
      setModalProps({ confirmLoading: false });
      createMessage.success(t('common.saveSuccessText'));
      closeModal();
      emit('success');
    }
  } finally {
    setModalProps({ confirmLoading: false });
  }
}
</script>

<template>
  <div>
    <BasicModal
      v-bind="$attrs"
      @register="registerModal"
      :title="$t('system.sample.metaManagement')"
      :mask-closable="false"
      :width="600"
      :min-height="200"
      :height="500"
      show-footer
      @ok="handleSubmit"
      :show-cancel-btn="true"
    >
      <Form />
    </BasicModal>
  </div>
</template>
<style lang="scss" scoped></style>
