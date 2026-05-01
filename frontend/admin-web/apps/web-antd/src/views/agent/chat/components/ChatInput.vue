<template>
  <div class="chat-input-container">
    <!-- File list display -->
    <div v-if="uploadedFiles.length > 0" class="uploaded-files">
      <Tag
        v-for="(file, index) in uploadedFiles"
        :key="index"
        closable
        @close="removeFile(index)"
      >
        {{ file.name }}
      </Tag>
    </div>

    <!-- Input box -->
    <Sender
      ref="senderRef"
      v-model:value="innerValue"
      class="chat-input"
      :placeholder="placeholder"
      :loading="loading"
      :disabled="disabled"
      :submit-type="'enter'"
      @submit="handleSubmit"
      @cancel="handleCancel"
    >
      <template v-if="supportsFileUpload" #prefix>
        <Upload
          :show-upload-list="false"
          :before-upload="() => false"
          :multiple="true"
          :accept="acceptedFileTypes?.join(',')"
          @change="handleFileChange"
        >
          <Button type="text" :icon="h(UploadOutlined)" />
        </Upload>
      </template>
    </Sender>
  </div>
</template>

<script setup lang="ts">
import { h, computed, ref, watch } from 'vue'

import { Button, message, Tag, Upload } from 'ant-design-vue'
import { UploadOutlined } from '@ant-design/icons-vue'
import { Sender } from 'ant-design-x-vue'
import { $t } from '@vben/locales';

const props = defineProps<{
  modelValue?: string
  loading?: boolean
  disabled?: boolean
  placeholder?: string
  supportsFileUpload?: boolean
  maxFileSize?: number
  acceptedFileTypes?: string[]
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
  (event: 'submit', value: { message: string; file_upload?: File[] }): void
  (event: 'cancel'): void
}>()

const innerValue = ref(props.modelValue ?? '')
const uploadedFiles = ref<File[]>([])
const senderRef = ref()

watch(
  () => props.modelValue,
  (value) => {
    if (value !== undefined && value !== innerValue.value) {
      innerValue.value = value
    }
  },
)

watch(innerValue, (value) => {
  emit('update:modelValue', value)
})

const loading = computed(() => props.loading ?? false)
const disabled = computed(() => props.disabled ?? false)
const placeholder = computed(
  () => props.placeholder ?? $t('agent.chat.alternativePlaceholder'),
)

function handleFileChange(info: any) {
  if (!info.fileList) return

  const files = info.fileList.map((item: any) => item.originFileObj).filter(Boolean)

  // Validate file size
  const maxSize = (props.maxFileSize || 10) * 1024 * 1024
  const validFiles = files.filter((file: File) => {
    if (file.size > maxSize) {
      message.error(`File ${file.name} exceeds ${props.maxFileSize}MB limit`)
      return false
    }
    return true
  })

  uploadedFiles.value = validFiles
}

function removeFile(index: number) {
  uploadedFiles.value.splice(index, 1)
}

function handleSubmit(msg: string) {
  const trimmed = msg.trim()
  if (!trimmed && uploadedFiles.value.length === 0) {
    return
  }

  emit('submit', {
    message: trimmed,
    file_upload: uploadedFiles.value.length > 0 ? uploadedFiles.value : undefined,
  })

  innerValue.value = ''
  uploadedFiles.value = []

  // Reset textarea height after clearing content
  if (senderRef.value?.$el) {
    const textarea = senderRef.value.$el.querySelector('textarea')
    if (textarea) {
      textarea.style.height = 'auto'
    }
  }
}

function handleCancel() {
  emit('cancel')
}
</script>

<style scoped>
.chat-input-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.uploaded-files {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chat-input {
  width: 100%;
}
</style>
