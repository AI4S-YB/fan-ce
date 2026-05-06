<script setup lang="ts">
import { ref, computed } from 'vue';

const props = defineProps<{
  placeholder?: string;
}>();

const emit = defineEmits<{
  search: [payload: { type: 'gene' | 'region' | 'variant_id'; value: string }];
}>();

const input = ref('');

const detectedType = computed<'gene' | 'region' | 'variant_id' | null>(() => {
  const v = input.value.trim();
  if (!v) return null;
  // Region: chr:start-end or chr:start
  if (/^[a-zA-Z0-9_]+:\d+(-\d+)?$/.test(v)) return 'region';
  // Variant ID: chrom_pos format (underscore with digits on both sides)
  if (/^[a-zA-Z0-9_]+_\d+$/.test(v)) return 'variant_id';
  // Gene ID: alphanumeric, may contain dots, at least 3 chars
  if (/^[a-zA-Z0-9._]+$/.test(v) && v.length >= 3) return 'gene';
  return null;
});

const typeLabel = computed(() => {
  switch (detectedType.value) {
    case 'gene': return 'Gene';
    case 'region': return 'Region';
    case 'variant_id': return 'Variant ID';
    default: return '';
  }
});

function onSubmit() {
  const v = input.value.trim();
  if (!v || !detectedType.value) return;
  emit('search', { type: detectedType.value, value: v });
}

// Exposed so parent can fill search box from example chips
function setInput(value: string) {
  input.value = value;
}

defineExpose({ setInput });
</script>

<template>
  <el-input
    v-model="input"
    :placeholder="placeholder || 'Search genes, regions, or variant IDs...'"
    size="large"
    clearable
    @keyup.enter="onSubmit"
  >
    <template #prepend>
      <el-tag v-if="detectedType" size="small" effect="plain">{{ typeLabel }}</el-tag>
      <span v-else style="color:#bbb;">Type...</span>
    </template>
    <template #append>
      <el-button :disabled="!detectedType" @click="onSubmit">Go</el-button>
    </template>
  </el-input>
</template>
