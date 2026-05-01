<script lang="ts" setup>
import { BasicForm, useForm } from '#/components/Form';
import { BasicModal, useModalInner } from '#/components/Modal';

import { editResourceApiFormSchema } from './data';
import { $t } from '@vben/locales';

defineOptions({ name: 'ApiEdit' });
const emit = defineEmits(['success', 'register']);
const [registerForm, { setFieldsValue, resetFields, validate }] = useForm({
  labelWidth: 100,
  schemas: editResourceApiFormSchema(),
  showActionButtonGroup: false,
  baseColProps: { span: 24 },
  actionColOptions: {
    span: 23,
  },
});
const [registerModal, { setModalProps, closeModal }] = useModalInner(
  async (data) => {
    await resetFields();
    setModalProps({ confirmLoading: false, minHeight: 300 });
    await setFieldsValue({
      ...data.record,
    });
  },
);
async function handleSubmit() {
  try {
    const params = await validate();
    setModalProps({ confirmLoading: true });
    params.isInput = params.isInput === undefined ? false : params.isInput;
    closeModal();
    emit('success', params);
  } finally {
    setModalProps({ confirmLoading: false });
  }
}
</script>
<template>
  <BasicModal
    v-bind="$attrs"
    @register="registerModal"
    :title="$t('system.menu.enterApi')"
    :mask-closable="false"
    @ok="handleSubmit"
  >
    <BasicForm @register="registerForm" />
  </BasicModal>
</template>
