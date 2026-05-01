<script lang="ts" setup>
import type { NewsRowType } from '#/api/platform/news';

import { computed, ref, unref } from 'vue';

import { BasicModal, useModalInner } from '#/components/Modal';
import MarkdownEditor from '#/components/MarkdownEditor/MarkdownEditor.vue';
import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';

import { addNewsApi, updateNewsApi } from '#/api/platform/news';
import MarkdownIt from 'markdown-it';
import TurndownService from 'turndown';
import { Form, formApi } from './data';

defineOptions({ name: 'NewsModal' });

const emit = defineEmits(['success', 'register']);

const isUpdate = ref(true);
const rowId = ref<number>();
const content = ref<string>('');
const md = new MarkdownIt();
const turndown = new TurndownService();

const { createMessage } = useMessage();

const [registerModal, { setModalProps, closeModal }] = useModalInner(
  async (data) => {
    setModalProps({ confirmLoading: false });
    isUpdate.value = !!data?.isUpdate;

    if (unref(isUpdate)) {
      rowId.value = data.record.id;
      formApi.setValues(data.record);
      // B 方案：后端存 HTML，这里转为 Markdown 展示
      const html = data.record.content || '';
      content.value = html ? turndown.turndown(html) : '';
    } else {
      formApi.resetValidate();
      formApi.setValues({});
      content.value = '';
    }
  },
);

const getTitle = computed(() =>
  !unref(isUpdate) ? t('component.action.create') : t('component.action.edit'),
);

async function handleSubmit() {
  try {
    const valid = await formApi.validate();
    if (!valid.valid) return;
    
    const values = await formApi.getValues();
    setModalProps({ confirmLoading: true });

    // 添加content$t('platform.news.content')（B 方案：提交前将 Markdown 转 HTML）
    const htmlContent = md.render(content.value || '');
    if (unref(isUpdate)) {
      const submitData = {
        ...values,
        content: htmlContent,
        id: unref(rowId)!,
      } as any; // 使用any类型避免类型检查问题
      await updateNewsApi(submitData);
    } else {
      const submitData = {
        ...values,
        content: htmlContent,
      } as any; // 使用any类型避免类型检查问题
      await addNewsApi(submitData);
    }

    closeModal();
    emit('success', { isUpdate: unref(isUpdate), values });
    createMessage.success(t('common.saveSuccessText'));
  } finally {
    setModalProps({ confirmLoading: false });
  }
}

function handleContentChange(value: string) {
  content.value = value;
}
</script>

<template>
  <BasicModal
    v-bind="$attrs"
    @register="registerModal"
    :title="getTitle"
    @ok="handleSubmit"
    :width="800"
  >
    <div class="pt-3px pr-3px">
      <Form />
      
      <div class="mt-4">
        <label class="block text-sm font-medium mb-2">{{ $t('platform.news.content') }} <span class="text-red-500">*</span></label>
        <MarkdownEditor
          :modelValue="content"
          :height="300"
          @update:modelValue="handleContentChange"
        />
      </div>
    </div>
  </BasicModal>
</template>

<style lang="less" scoped>
:deep(.ant-form-item) {
  margin-bottom: 16px;
}

:deep(.tinymce-container) {
  border: 1px solid #d9d9d9;
  border-radius: 6px;
}
</style>
