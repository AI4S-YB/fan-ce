<script lang="ts" setup>
import { ref, unref } from 'vue';

import { useVbenForm } from '#/adapter/form';
import {
  addPermissionApi,
  getPermissionInfoApi,
  updatePermissionApi,
} from '#/api/system/permission';
import { BasicModal, useModalInner } from '#/components/Modal';
import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';

import { formSchema } from './modalData';

defineOptions({ name: 'FormModel' });

const emit = defineEmits(['success', 'register']);
const { createMessage } = useMessage();
const isUpdate = ref(true);

// Modal 提交表单
const [Form, formApi] = useVbenForm({
  commonConfig: {
    // 所有表单项
    componentProps: {
      class: 'w-full',
    },
  },
  layout: 'horizontal',
  schema: formSchema,
  showDefaultActions: false,
  wrapperClass: 'grid-cols-3',
});

const [registerModal, { setModalProps, closeModal }] = useModalInner(
  async (data) => {
    formApi.resetForm();
    if (data?.action === 'addOne') {
      formApi.setValues({ pid: data.row.id, type: data.row.type });
    }
    setModalProps({ confirmLoading: false });
    isUpdate.value = !!data?.isUpdate;
    if (unref(isUpdate)) {
      const res = await getPermissionInfoApi({ id: data.row.id });
      formApi.setValues({ ...res });
    }
  },
);

async function handleSubmit() {
  try {
    const { valid } = await formApi.validate();
    if (valid) {
      const values = await formApi.getValues();
      setModalProps({ confirmLoading: true });
      await (unref(isUpdate)
        ? updatePermissionApi(values)
        : addPermissionApi(values));

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
  <BasicModal
    v-bind="$attrs"
    :title="
      isUpdate ? t('component.action.edit') : t('component.action.create')
    "
    show-footer
    :min-height="200"
    :mask-closable="false"
    @register="registerModal"
    @ok="handleSubmit"
  >
    <!-- <BasicForm @register="registerForm" /> -->
    <Form />
  </BasicModal>
</template>
