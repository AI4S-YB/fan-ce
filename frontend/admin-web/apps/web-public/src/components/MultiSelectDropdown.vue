<script setup lang="ts">
const props = defineProps<{
  modelValue: string[];
  options: { label: string; value: string }[];
  placeholder?: string;
}>();

const emit = defineEmits<{ 'update:modelValue': [val: string[]] }>();

function handleChange(val: string[]) {
  emit('update:modelValue', val);
}

function selectAll() {
  emit(
    'update:modelValue',
    props.options.map((o) => o.value),
  );
}

function clearAll() {
  emit('update:modelValue', []);
}
</script>

<template>
  <div style="display: inline-flex; align-items: center; gap: 4px;">
    <el-select
      :model-value="modelValue"
      multiple
      filterable
      :placeholder="placeholder || 'Select...'"
      style="width: 260px;"
      @change="handleChange"
    >
      <el-option
        v-for="opt in options"
        :key="opt.value"
        :label="opt.label"
        :value="opt.value"
      />
    </el-select>
    <el-button text size="small" @click="selectAll">All</el-button>
    <el-button text size="small" @click="clearAll">Clear</el-button>
  </div>
</template>
