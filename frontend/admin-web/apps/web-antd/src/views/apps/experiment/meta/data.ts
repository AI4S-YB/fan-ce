import type { VbenFormSchema } from '#/adapter/form';

import { $t } from '@vben/locales';

// meta Form 表单
export function metaUseFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'experiment_id',
      label: $t('system.dict.name'),
      rules: 'required',
      dependencies: {
        show: false,
        triggerFields: ['key'],
      },
    },
    {
      component: 'Input',
      fieldName: 'key',
      label: $t('system.dict.name'),
      rules: 'required',
    },
    {
      component: 'Input',
      fieldName: 'value',
      label: $t('system.dict.value'),
      rules: 'required',
    },
    {
      component: 'Textarea',
      fieldName: 'description',
      label: $t('system.project.description'),
    },
  ];
}
