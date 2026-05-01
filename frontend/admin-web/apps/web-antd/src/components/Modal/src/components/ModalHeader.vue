<script lang="ts" setup>
import { BasicTitle } from '#/components/Basic';

defineOptions({ name: 'BasicModalHeader' });

defineProps({
  helpMessage: {
    type: [String, Array] as PropType<string | string[]>,
  },
  title: { type: String },
  hr: { type: Boolean, default: true },
});
const emit = defineEmits(['dblclick']);
</script>

<template>
  <BasicTitle :help-message="helpMessage">
    {{ title }}
  </BasicTitle>
  <hr v-if="hr" style="margin-top: 10px" />
</template>
