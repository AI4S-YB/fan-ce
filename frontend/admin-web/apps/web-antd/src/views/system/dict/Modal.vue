<script lang="ts" setup>
import { ref, unref } from 'vue';

import { addDictApi, getDictInfoApi, updateDictApi } from '#/api/system/dict';
import { BasicModal, useModalInner } from '#/components/Modal';
import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';

import { Form, formApi } from './data';

defineOptions({ name: 'SystemDictModal' });

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
      const res = await getDictInfoApi({ id: data.row.id });
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
      await (unref(isUpdate) ? updateDictApi(values) : addDictApi(values));
      closeModal();
      emit('success');
      createMessage.success(t('common.saveSuccessText'));
    }
  } catch {
    setModalProps({ confirmLoading: false });
  } finally {
    setModalProps({ confirmLoading: false });
  }
}
</script>

<template>
  <div>
    <BasicModal
      v-bind="$attrs"
      show-footer
      :title="
        isUpdate ? t('component.action.edit') : t('component.action.create')
      "
      :width="600"
      :min-height="200"
      @register="registerModal"
      @ok="handleSubmit"
    >
      <Form />
    </BasicModal>
  </div>
</template>
