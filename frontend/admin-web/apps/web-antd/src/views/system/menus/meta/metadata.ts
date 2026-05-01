import type { BasicColumn, FormSchema } from '#/components/Table';
import { $t } from '@vben/locales';

// 元数据 表格
export const metaJsonColumns: BasicColumn[] = [
  {
    title: 'key',
    dataIndex: 'key',
    maxWidth: 100,
  },
  {
    title: 'value',
    dataIndex: 'value',
    maxWidth: 100,
    format: (text: boolean | number | string) => {
      if (text === true) {
        return 'true';
      } else if (text === false) {
        return 'false';
      } else {
        return text;
      }
    },
  },
];

// 元数据 编辑表单
export const editMetaFormSchema = (): FormSchema[] => {
  return [
    {
      label: 'key',
      field: 'key',
      component: 'Select',
      required: true,
      helpMessage: [
        $t('system.menu.metaKeyHelp'),
      ],
      componentProps: {
        allowClear: true,
        getPopupContainer: () => document.body,
        filterOption: (input: string, option: any) => {
          return option.value.toUpperCase().includes(input.toUpperCase());
        },
        options: [
          { value: 'title', label: $t('system.menu.title') },
          { value: 'ignoreKeepAlive', label: $t('system.menu.ignoreKeepAlive') },
          { value: 'affix', label: $t('system.menu.affix') },
          { value: 'activePath', label: $t('system.menu.activePath') },
          { value: 'transitionName', label: $t('system.menu.transitionName') },
          { value: 'hideBreadcrumb', label: $t('system.menu.hideBreadcrumb') },
          { value: 'carryParam', label: $t('system.menu.carryParam') },
          { value: 'hideChildrenInMenu', label: $t('system.menu.hideChildrenInMenu') },
          { value: 'currentActiveMenu', label: $t('system.menu.currentActiveMenu') },
          { value: 'hideTab', label: $t('system.menu.hideTab') },
          { value: 'hideMenu', label: $t('system.menu.hideMenu') },
          { value: 'ignoreRoute', label: $t('system.menu.ignoreRoute') },
          { value: 'content', label: $t('platform.news.content') },
          { value: 'dot', label: $t('system.menu.dot') },
          { value: 'type', label: $t('system.menu.type') },
          { value: 'iframeSrc', label: $t('system.menu.iframeSrc') },
          { value: 'noBasicLayout', label: $t('system.menu.noBasicLayout') },
        ],
      },
    },
    {
      label: 'value',
      field: 'value',
      component: 'Input',
      required: true,
    },
  ];
};
