<script lang="ts" setup>
import { ref, unref } from 'vue';

import { createMenuApi, getMenuInfoApi, updateMenuApi } from '#/api/system';
import { BasicForm, useForm } from '#/components/Form';
import { BasicModal, useModalInner } from '#/components/Modal';
import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';

import { formSchema } from './modalData';

defineOptions({ name: 'SystemMenuModal' });

const emit = defineEmits(['success', 'register']);
const { createMessage } = useMessage();
const isUpdate = ref(true);

const [registerForm, { setFieldsValue, resetFields, validate }] = useForm({
  labelWidth: 120,
  baseColProps: { span: 24 },
  schemas: formSchema,
  showActionButtonGroup: false,
  actionColOptions: { span: 23 },
});

const [registerModal, { setModalProps, closeModal }] = useModalInner(
  async (data) => {
    resetFields();
    setModalProps({ confirmLoading: false });
    isUpdate.value = !!data?.isUpdate;
    if (unref(isUpdate)) {
      console.log(data);

      const res = await getMenuInfoApi({ id: data.row.id });
      setFieldsValue({ ...res });
    }
  },
);

async function handleSubmit() {
  try {
    const values = await validate();
    setModalProps({ confirmLoading: true });
    await (unref(isUpdate) ? updateMenuApi(values) : createMenuApi(values));

    closeModal();
    emit('success');
    createMessage.success(t('common.saveSuccessText'));
  } finally {
    setModalProps({ confirmLoading: false });
  }
}
</script>

<template>
  <BasicModal
    v-bind="$attrs"
    :title="
      isUpdate ? t('component.action.edit') : t('component.action.create')
    "
    @register="registerModal"
    @ok="handleSubmit"
  >
    <BasicForm @register="registerForm" />
  </BasicModal>
</template>
