<script lang="ts" setup>
import { ref, unref, watch } from 'vue';

import { addTeamApi, updateTeamUserRoleApi } from '#/api/system/team';
import { BasicModal, useModalInner } from '#/components/Modal';
import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';

import { PermissionForm, permissionFormApi } from './data';
import UserRoleItem from './Item.vue';

defineOptions({ name: 'RoleModal' });
const emit = defineEmits(['success', 'register']);
const rows = ref([]);
const { createMessage } = useMessage();
const isUpdate = ref(true);

const [registerModal, { setModalProps, closeModal }] = useModalInner(
  async (data) => {
    permissionFormApi.setState((prev) => {
      return { schema: prev?.schema };
    });
    permissionFormApi.resetValidate();
    setModalProps({ confirmLoading: false });
    isUpdate.value = !!data?.isUpdate;
    rows.value = data.row.user_role_list;
    permissionFormApi.setFieldValue('id', data.row.id);
    permissionFormApi.setFieldValue('name', data.row.name);
    permissionFormApi.setFieldValue('user_role_list', data.row.user_role_list);

    if (unref(isUpdate)) {
      // const res = await getTeamInfoApi({ id: data.row.id });
      // permissionFormApi.setValues({ ...res });
    }
  },
);

async function handleSubmit() {
  try {
    const valid = await permissionFormApi.validate();
    if (valid.valid) {
      const values = await permissionFormApi.getValues();
      setModalProps({ confirmLoading: true });
      await (unref(isUpdate)
        ? updateTeamUserRoleApi(values)
        : addTeamApi(values));
      closeModal();
      emit('success');
      createMessage.success(t('common.saveSuccessText'));
    }
  } finally {
    setModalProps({ confirmLoading: false });
  }
}

watch(
  () => rows.value,
  (newValue) => {
    permissionFormApi.setFieldValue('user_role_list', newValue);
  },
  { deep: true, immediate: false },
);
</script>

<template>
  <div>
    <BasicModal
      :min-height="200"
      :title="$t('system.role.userAuth')"
      v-bind="$attrs"
      :width="600"
      show-footer
      @ok="handleSubmit"
      @register="registerModal"
    >
      <!-- <UserRoleItem v-model:value="rows" :one="[111]" /> -->
      <PermissionForm>
        <template #user_role_list>
          <div style="width: 450px">
            <UserRoleItem v-model:value="rows" :one="[111]" />
          </div>
        </template>
      </PermissionForm>
    </BasicModal>
  </div>
</template>
