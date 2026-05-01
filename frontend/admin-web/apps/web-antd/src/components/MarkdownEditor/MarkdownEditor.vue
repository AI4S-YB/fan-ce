<script setup lang="ts">
import { computed } from 'vue';
import { MdEditor } from 'md-editor-v3';
import 'md-editor-v3/lib/style.css';

type Props = {
  modelValue: string;
  height?: number | string;
  disabled?: boolean;
  toolbars?: string[];
};

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  height: 300,
  disabled: false,
  toolbars: undefined,
});

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void;
  (e: 'change', v: string): void;
}>();

const editorHeight = computed(() =>
  typeof props.height === 'number' ? `${props.height}px` : props.height,
);

const defaultToolbars = [
  'bold',
  'underline',
  'italic',
  'strikeThrough',
  'title',
  'quote',
  'unorderedList',
  'orderedList',
  'codeRow',
  'code',
  'link',
  'table',
  'sub',
  'sup',
  'toc',
  'save',
  'preview',
  'htmlPreview',
  'fullscreen',
];

const toolbars = computed(() => props.toolbars ?? defaultToolbars);

const handleChange = (v: string) => {
  emit('update:modelValue', v);
  emit('change', v);
};
</script>

<template>
  <MdEditor
    :modelValue="modelValue"
    :language="'zh-CN'"
    :toolbars="toolbars"
    :previewOnly="disabled"
    :readOnly="disabled"
    :style="{ height: editorHeight }"
    @update:modelValue="handleChange"
  />
  
</template>

<style scoped>
</style>


