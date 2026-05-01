<script lang="ts">
import { defineComponent, ref } from 'vue';

import { BasicForm, useForm } from '#/components/Form';
import { BasicModal, useModalInner } from '#/components/Modal';
import { ActionEnum } from '#/enums/commonEnum';
import { $t as t } from '#/locales';

import { editMetaFormSchema } from './metadata';

export default defineComponent({
  name: 'DefResourceMetaEdit',
  components: { BasicModal, BasicForm },
  emits: ['success', 'register'],
  setup(_, { emit }) {
    const type = ref(ActionEnum.ADD);

    const [registerForm, { setFieldsValue, resetFields, validate }] = useForm({
      labelWidth: 100,
      schemas: editMetaFormSchema(),
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
        type.value = data?.type;

        const { record = {} } = data;
        await setFieldsValue({
          ...record,
        });
      },
    );

    async function handleSubmit() {
      try {
        const params = await validate();
        setModalProps({ confirmLoading: true });

        closeModal();
        emit('success', params);
      } finally {
        setModalProps({ confirmLoading: false });
      }
    }

    return { t, type, registerModal, registerForm, handleSubmit };
  },
});
</script>
<template>
  <BasicModal
    v-bind="$attrs"
    @register="registerModal"
    :title="t(`common.title.${type}`)"
    :mask-closable="false"
    @ok="handleSubmit"
  >
    <BasicForm @register="registerForm" />
  </BasicModal>
</template>
