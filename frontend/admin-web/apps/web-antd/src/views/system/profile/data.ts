import { useVbenForm } from '#/adapter/form';
import { $t } from '@vben/locales';

export const [Form, formApi] = useVbenForm({
  commonConfig: {
    // 所有表单项
    componentProps: {
      class: 'w-full',
    },
  },
  // handleSubmit: handleSubmit,
  layout: 'horizontal',
  schema: [
    {
      component: 'Input',
      fieldName: 'id',
      label: 'id',
      dependencies: {
        show: false,
        if: true,
        triggerFields: ['user_name'],
      },
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
        if: false,
      },
      dependencies: {
        disabled: true,
        triggerFields: ['user_name'],
      },
      fieldName: 'user_name',
      label: $t('system.user.realName'),
      rules: 'required',
      // labelWidth: 80,
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'InputPassword',
      componentProps: {
        placeholder: $t('system.user.passwordTip'),
        autocomplete: 'off',
      },
      dependencies: {
        if(values) {
          return !values.id;
        },
        triggerFields: ['id'],
      },
      fieldName: 'user_password',
      label: $t('system.user.password'),
      rules: 'required',
      formItemClass: 'col-span-2 items-baseline',
      // labelWidth: 50,
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
      },
      fieldName: 'user_phone',
      label: $t('system.user.phone'),
      formItemClass: 'col-span-2 items-baseline',
    },

    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
      },
      fieldName: 'user_email',
      label: $t('system.user.email'),
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'Textarea',
      fieldName: 'remark',
      formItemClass: 'col-span-3 items-baseline',
      label: $t('system.user.remark'),
    },
  ],
  showDefaultActions: false,
  wrapperClass: 'grid-cols-3',
});

export const [Form2, formApi2] = useVbenForm({
  commonConfig: {
    // 所有表单项
    componentProps: {
      class: 'w-full',
    },
  },
  // handleSubmit: handleSubmit,
  layout: 'horizontal',
  schema: [
    {
      component: 'Input',
      fieldName: 'id',
      label: 'id',
      dependencies: {
        show: false,
        if: true,
        triggerFields: ['user_name'],
      },
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('system.user.pleaseInput'),
        if: false,
      },
      dependencies: {
        disabled: true,
        triggerFields: ['user_name'],
      },
      fieldName: 'user_name',
      label: $t('system.user.realName'),
      rules: 'required',
      // labelWidth: 80,
      formItemClass: 'col-span-2 items-baseline',
    },
    {
      component: 'InputPassword',
      componentProps: {
        placeholder: $t('system.user.passwordTip'),
        autocomplete: 'off',
      },
      fieldName: 'new_password',
      label: $t('system.user.password'),
      rules: 'required',
      formItemClass: 'col-span-2 items-baseline',
      // labelWidth: 50,
    },
    {
      component: 'InputPassword',
      componentProps: {
        placeholder: $t('system.user.passwordTip'),
        autocomplete: 'off',
      },
      fieldName: 'confirm_password',
      label: $t('system.user.confirmPassword'),
      rules: 'required',
      formItemClass: 'col-span-2 items-baseline',
      // labelWidth: 50,
    },
  ],
  showDefaultActions: false,
  wrapperClass: 'grid-cols-3',
});

export { type UserRowType } from '#/api/system';
