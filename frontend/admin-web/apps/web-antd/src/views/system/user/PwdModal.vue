<script lang="ts" setup>
import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { message } from 'ant-design-vue';

import { useVbenForm, z } from '#/adapter/form';
import { resetPwdApi } from '#/api/system/user';

defineOptions({
  name: 'PwdModal',
});

function onSubmit(values: Record<string, any>) {
  if (values.new_password !== values.confirm_password) {
    message.error($t('system.user.passwordMismatch'));
    return;
  }
  resetPwdApi({
    id: values.id,
    new_password: values.new_password,
    confirm_password: values.confirm_password,
  }).then(() => {
    message.success($t('system.user.resetPasswordSuccess'));
    formApi.resetForm();
  });
}

const [Form, formApi] = useVbenForm({
  handleSubmit: onSubmit,
  schema: [
    {
      component: 'Input',
      dependencies: {
        show: false,
        triggerFields: ['id'],
      },
      fieldName: 'id',
      label: 'id',
    },
    {
      component: 'InputPassword',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
      },
      fieldName: 'new_password',
      label: $t('system.user.newPassword'),
      rules: 'required',
    },
    {
      component: 'InputPassword',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
      },
      dependencies: {
        rules(values) {
          const { new_password } = values;
          return z
            .string({ required_error: $t('authentication.passwordTip') })
            .min(1, { message: $t('authentication.passwordTip') })
            .refine((value) => value === new_password, {
              message: $t('authentication.confirmPasswordTip'),
            });
        },
        triggerFields: ['new_password'],
      },
      fieldName: 'confirm_password',
      label: $t('system.user.confirmPassword'),
      rules: 'required',
    },
  ],
  showDefaultActions: false,
});

const [Modal, modalApi] = useVbenModal({
  fullscreenButton: false,
  onCancel() {
    modalApi.close();
  },
  onConfirm: async () => {
    const { valid } = await formApi.validate();
    if (valid) {
      await formApi.submitForm();
      modalApi.close();
    }
  },

  onOpenChange: (isOpen: boolean) => {
    if (isOpen) {
      const values = modalApi.getData();
      formApi.resetForm();
      if (values) {
        formApi.setValues(values);
      }
    }
  },
  title: $t('system.user.resetPassword'),
});
</script>
<template>
  <Modal>
    <Form />
  </Modal>
</template>
