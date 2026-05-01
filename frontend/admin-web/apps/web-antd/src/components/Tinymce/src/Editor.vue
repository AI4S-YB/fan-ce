<script lang="ts" setup>
import type { Editor, RawEditorSettings } from '#/utils/antdAll';

import tinymce from 'tinymce/tinymce';
import 'tinymce/models/dom/model';
import 'tinymce/themes/silver';
import 'tinymce/icons/default/icons';
import 'tinymce/skins/ui/oxide/skin.min.css';
import 'tinymce/skins/ui/oxide/content.min.css';
import 'tinymce/plugins/advlist';
import 'tinymce/plugins/anchor';
import 'tinymce/plugins/autolink';
import 'tinymce/plugins/autosave';
import 'tinymce/plugins/code';
import 'tinymce/plugins/codesample';
import 'tinymce/plugins/directionality';
import 'tinymce/plugins/fullscreen';
import 'tinymce/plugins/image';
import 'tinymce/plugins/charmap';
// import 'tinymce/plugins/hr';
import 'tinymce/plugins/insertdatetime';
import 'tinymce/plugins/link';
import 'tinymce/plugins/lists';
import 'tinymce/plugins/media';
import 'tinymce/plugins/nonbreaking';
// import 'tinymce/plugins/noneditable';
import 'tinymce/plugins/pagebreak';
// import 'tinymce/plugins/paste';
import 'tinymce/plugins/preview';
// import 'tinymce/plugins/print';
import 'tinymce/plugins/save';
import 'tinymce/plugins/searchreplace';
// import 'tinymce/plugins/spellchecker'; // 插件不存在
// import 'tinymce/plugins/tabfocus'; // 插件不存在
import 'tinymce/plugins/table';
// import 'tinymce/plugins/template'; // 插件不存在
// import 'tinymce/plugins/textpattern'; // 插件不存在
import 'tinymce/plugins/visualblocks';
import 'tinymce/plugins/visualchars';
import 'tinymce/plugins/wordcount';
import 'tinymce/plugins/help';
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onDeactivated,
  ref,
  unref,
  useAttrs,
  watch,
} from 'vue';

import { onMountedOrActivated } from '#/hooks/core/onMountedOrActivated';
import { isNumber } from '#/utils/is';
import { buildShortUUID } from '#/utils/uuid';
import { useDesign } from '#/utils/vbenModle';

import { bindHandlers } from './helper';
import ImgUpload from './ImgUpload.vue';
import {
  plugins as defaultPlugins,
  toolbar as defaultToolbar,
} from './tinymce';

defineOptions({ name: 'Tinymce', inheritAttrs: false });

const props = defineProps({
  options: {
    type: Object as PropType<Partial<RawEditorSettings>>,
    default: () => ({}),
  },
  value: {
    type: String,
  },

  toolbar: {
    type: Array as PropType<string[]>,
    default: defaultToolbar,
  },
  plugins: {
    type: Array as PropType<string[]>,
    default: defaultPlugins,
  },
  modelValue: {
    type: String,
  },
  height: {
    type: [Number, String] as PropType<number | string>,
    required: false,
    default: 400,
  },
  width: {
    type: [Number, String] as PropType<number | string>,
    required: false,
    default: 'auto',
  },
  showImageUpload: {
    type: Boolean,
    default: true,
  },
});
const emit = defineEmits([
  'change',
  'update:modelValue',
  'inited',
  'init-error',
]);
const attrs = useAttrs();
const editorRef = ref<Nullable<Editor>>(null);
const fullscreen = ref(false);
const tinymceId = ref<string>(buildShortUUID('tiny-vue'));
const elRef = ref<Nullable<HTMLElement>>(null);

const { prefixCls } = useDesign('tinymce-container');

const containerWidth = computed(() => {
  const width = props.width;
  if (isNumber(width)) return `${width}px`;

  return width;
});

// 语言与皮肤使用 TinyMCE 默认配置，避免外链静态资源 404 导致加载失败

const initOptions = computed((): RawEditorSettings => {
  const { height, options, toolbar, plugins } = props;
  return {
    selector: `#${unref(tinymceId)}`,
    height,
    toolbar,
    menubar: 'file edit insert view format table',
    plugins,
    language: 'zh_CN',
    branding: false,
    default_link_target: '_blank',
    link_title: false,
    object_resizing: false,
    auto_focus: true,
    ...options,
    setup: (editor: Editor) => {
      editorRef.value = editor;
      editor.on('init', (e) => initSetup(e));
    },
  };
});

const disabled = computed(() => {
  const { options } = props;
  const getdDisabled = options && Reflect.get(options, 'readonly');
  const editor = unref(editorRef);
  if (editor) editor.mode.set(getdDisabled ? 'readonly' : 'design');

  return getdDisabled ?? false;
});

watch(
  () => attrs.disabled,
  () => {
    const editor = unref(editorRef);
    if (!editor) return;

    editor.mode.set(attrs.disabled ? 'readonly' : 'design');
  },
);

onMountedOrActivated(() => {
  if (!initOptions.value.inline) tinymceId.value = buildShortUUID('tiny-vue');

  nextTick(() => {
    setTimeout(() => {
      initEditor();
    }, 30);
  });
});

onBeforeUnmount(() => {
  destory();
});

onDeactivated(() => {
  destory();
});

function destory() {
  if (tinymce !== null) {
    const el = unref(elRef);
    if (el) tinymce?.remove?.(el as any);
    else tinymce?.remove?.(unref(initOptions).selector!);
  }
}

function initEditor() {
  const el = unref(elRef);
  if (el) el.style.visibility = '';

  // 使用 target 直接绑定元素，避免选择器与时序导致的挂载失败
  const { selector: _unused, ...rest } = unref(initOptions) as any;
  // 若未提供本地化文件，则退回英文，避免 404
  if (!('language_url' in rest)) {
    (rest as any).language = (rest as any).language === 'zh_CN' ? undefined : (rest as any).language;
  }
  const doInit = () =>
    tinymce
      .init({ ...rest, target: el as any })
      .then((instance) => {
        const editor = Array.isArray(instance) ? instance[0] : instance;
        emit('inited', editor as Editor);
      })
      .catch((error) => {
        emit('init-error', error);
      });

  // 若容器尚未可见（例如 Modal 动画阶段），延迟重试初始化
  if (!el || (el as HTMLElement).offsetParent === null) {
    setTimeout(() => doInit(), 60);
  } else doInit();
}

function initSetup(e: unknown) {
  const editor = unref(editorRef);
  if (!editor) return;

  const value = props.modelValue || '';

  editor.setContent(value);
  bindModelHandlers(editor);
  bindHandlers(e as any, attrs, unref(editorRef));
}

function setValue(editor: Recordable, val?: string, prevVal?: string) {
  if (
    editor &&
    typeof val === 'string' &&
    val !== prevVal &&
    val !== editor.getContent({ format: attrs.outputFormat })
  )
    editor.setContent(val);
}

function bindModelHandlers(editor: any) {
  const modelEvents = attrs.modelEvents ? attrs.modelEvents : null;
  const normalizedEvents = Array.isArray(modelEvents)
    ? modelEvents.join(' ')
    : modelEvents;

  watch(
    () => props.modelValue,
    (val, prevVal) => {
      setValue(editor, val, prevVal);
    },
  );

  watch(
    () => props.value,
    (val, prevVal) => {
      setValue(editor, val, prevVal);
    },
    {
      immediate: true,
    },
  );

  editor.on(normalizedEvents || 'change keyup undo redo', () => {
    const content = editor.getContent({ format: attrs.outputFormat });
    emit('update:modelValue', content);
    emit('change', content);
  });

  editor.on('FullscreenStateChanged', (e: any) => {
    fullscreen.value = (e as any).state;
  });
}

function handleImageUploading(name: string) {
  const editor = unref(editorRef);
  if (!editor) return;

  editor.execCommand('mceInsertContent', false, getUploadingImgName(name));
  const content = editor?.getContent() ?? '';
  setValue(editor, content);
}

function handleDone(name: string, url: string) {
  const editor = unref(editorRef);
  if (!editor) return;

  const content = editor?.getContent() ?? '';
  const val =
    content?.replace(getUploadingImgName(name), `<img src="${url}"/>`) ?? '';
  setValue(editor, val);
}

function getUploadingImgName(name: string) {
  return `[uploading:${name}]`;
}
</script>

<template>
  <div :class="prefixCls" :style="{ width: containerWidth }">
    <ImgUpload
      v-if="showImageUpload"
      v-show="editorRef"
      :fullscreen="fullscreen"
      :disabled="disabled"
      @uploading="handleImageUploading"
      @done="handleDone"
    />
    <textarea
      v-if="!initOptions.inline"
      :id="tinymceId"
      ref="elRef"
      :style="{ visibility: 'hidden' }"
    ></textarea>
    <slot v-else></slot>
  </div>
</template>

<style lang="less">
@namespace: 'vben';
@prefix-cls: ~'@{namespace}-tinymce-container';

.@{prefix-cls} {
  position: relative;
  line-height: normal;

  textarea {
    z-index: -1;
    visibility: hidden;
  }
}
</style>
