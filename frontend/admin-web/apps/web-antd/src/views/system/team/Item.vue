<script setup>
import { computed, onMounted, ref, watch } from 'vue';

import { Button, Select } from 'ant-design-vue';

import { getRoleOptionApi } from '#/api/system/role';
import { getUserOptionsApi } from '#/api/system/user';
import { $t } from '@vben/locales';

const props = defineProps({
  value: {
    type: Array,
    default: () => [{ user_id: undefined, role_ids: [] }],
  },
  one: {
    type: Object,
    required: true,
  },
});
const emit = defineEmits(['update:value']);
const rows = computed(() => props.value);

const UserOptions = ref();
const RoleOptions = ref();
const getUserOptions = async () => {
  const res = await getUserOptionsApi({});
  UserOptions.value = res;
};
const getRoleOptions = async () => {
  const res = await getRoleOptionApi({});
  RoleOptions.value = res;
};
const addRow = () => {
  rows.value.push({ user_id: undefined, role_ids: [] });
};
const removeRow = (index) => {
  rows.value.splice(index, 1);
};
onMounted(async () => {
  await getUserOptions();
  await getRoleOptions();
});
watch(
  () => rows.value,
  (newValue) => {
    console.error('newValue', newValue);
    emit('update:value', newValue);
  },
  { deep: true },
);

defineExpose({});
</script>

<template>
  <div>
    <Button @click="addRow">{{ $t('system.team.addRow') }}</Button>
    <div
      v-for="(row, index) in rows"
      :key="index"
      class="mb-2 mt-2 flex flex-row items-center"
    >
      <Select
        v-model:value="row.user_id"
        :placeholder="$t('system.team.selectUser')"
        :allow-clear="true"
        class="mr-2 w-1/2"
        :options="UserOptions"
      />
      <Select
        v-model:value="row.role_ids"
        :placeholder="$t('system.team.selectRole')"
        :allow-clear="true"
        mode="multiple"
        class="mr-2 w-1/2"
        :options="RoleOptions"
      />
      <Button @click="removeRow(index)" class="ml-2">{{ $t('common.title.delete') }}</Button>
    </div>
  </div>
</template>
