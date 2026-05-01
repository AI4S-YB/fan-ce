<script lang="ts" setup>
import { ref, unref } from 'vue';

import {
  addExperimentApi,
  getExperimentInfoApi,
  updateExperimentApi,
} from '#/api/apps/experiment';
import { BasicModal, useModalInner } from '#/components/Modal';
import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';

import { Form, formApi } from './data';

defineOptions({ name: 'UserModal' });

const emit = defineEmits(['success', 'register']);
const { createMessage } = useMessage();
const isUpdate = ref(true);

const [registerModal, { setModalProps, closeModal }] = useModalInner(
  async (data) => {
    formApi.setState((prev) => {
      return { schema: prev?.schema };
    });
    formApi.resetValidate();
    setModalProps({ confirmLoading: false });
    isUpdate.value = !!data?.isUpdate;
    if (unref(isUpdate)) {
      const res = await getExperimentInfoApi({ id: data.row.id });
      formApi.setValues({ ...res });
    }
  },
);

async function handleSubmit() {
  try {
    const valid = await formApi.validate();
    if (valid.valid) {
      const values = await formApi.getValues();
      setModalProps({ confirmLoading: true });
      await (unref(isUpdate)
        ? updateExperimentApi(values)
        : addExperimentApi(values));
      closeModal();
      emit('success');
      createMessage.success(t('common.saveSuccessText'));
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
      :min-height="200"
      :title="
        isUpdate ? t('component.action.edit') : t('component.action.create')
      "
      :width="600"
      show-footer
      @ok="handleSubmit"
      @register="registerModal"
    >
      <Form />
    </BasicModal>
  </div>
</template>
