<script lang="ts" setup>
import { ref, unref } from 'vue';

import {
  addProjectApi,
  getProjectInfoApi,
  updateProjectApi,
} from '#/api/system/project';
import { BasicModal, useModalInner } from '#/components/Modal';
import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';
import { useProjectStoreWithOut } from '#/store/modules/project';

import { Form, formApi } from './data';

defineOptions({ name: 'ProjectModal' });

const emit = defineEmits(['success', 'register']);
const proStore = useProjectStoreWithOut();
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
    formApi.setValues({ action: data.action });

    if (unref(isUpdate)) {
      const res = await getProjectInfoApi({ id: data.row.id });
      formApi.setValues({ ...res });
    }
  },
);

// 提交
async function handleSubmit() {
  try {
    const valid = await formApi.validate();
    if (valid.valid) {
      const values = await formApi.getValues();
      setModalProps({ confirmLoading: true });
      await (unref(isUpdate)
        ? updateProjectApi(values)
        : addProjectApi(values));
      closeModal();
      emit('success');
      await proStore.updateProjectOptions();
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
