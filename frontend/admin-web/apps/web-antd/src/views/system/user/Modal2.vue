<script lang="ts" setup>
import { useVbenModal } from '@vben/common-ui';

import { message } from 'ant-design-vue';

import { useVbenForm } from '#/adapter/form';
import { $t } from '@vben/locales';

defineOptions({
  name: 'FormModelDemo',
});

function onSubmit(values: Record<string, any>) {
  message.info(JSON.stringify(values)); // 只会执行一次
}

const [Form, formApi] = useVbenForm({
  handleSubmit: onSubmit,
  schema: [
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
      },
      fieldName: 'field1',
      label: $t('system.user.field1'),
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
      },
      fieldName: 'field2',
      label: $t('system.user.field2'),
      rules: 'required',
    },
    {
      component: 'Select',
      componentProps: {
        options: [
          { label: $t('system.user.option1'), value: '1' },
          { label: $t('system.user.option2'), value: '2' },
        ],
        placeholder: $t('system.user.pleaseInput'),
      },
      fieldName: 'field3',
      label: $t('system.user.field3'),
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
    await formApi.submitForm();
    modalApi.close();
  },
  onOpenChange(isOpen: boolean) {
    if (isOpen) {
      const { values } = modalApi.getData<Record<string, any>>();
      if (values) {
        formApi.setValues(values);
      }
    }
  },
  title: $t('system.user.inlineFormExample'),
});
</script>
<template>
  <Modal>
    <Form />
  </Modal>
</template>
