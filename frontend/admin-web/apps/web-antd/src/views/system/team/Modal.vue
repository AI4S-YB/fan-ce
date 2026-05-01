<script lang="ts" setup>
import type { DataNode } from 'ant-design-vue/es/tree';

import { ref, unref } from 'vue';

import { getMenuPermissonTreeApi } from '#/api/system/menu';
import { addTeamApi, getTeamInfoApi, updateTeamApi } from '#/api/system/team';
import { BasicModal, useModalInner } from '#/components/Modal';
import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';

import { Form, formApi } from './data';

defineOptions({ name: 'RoleModal' });

const emit = defineEmits(['success', 'register']);
const { createMessage } = useMessage();
const isUpdate = ref(true);
const permissions = ref<DataNode[]>([]);
const loadingPermissions = ref(false);

const [registerModal, { setModalProps, closeModal }] = useModalInner(
  async (data) => {
    formApi.setState((prev) => {
      return { schema: prev?.schema };
    });
    formApi.resetValidate();
    setModalProps({ confirmLoading: false });
    isUpdate.value = !!data?.isUpdate;
    if (permissions.value.length === 0) {
      loadPermissions();
    }
    if (unref(isUpdate)) {
      const res = await getTeamInfoApi({ id: data.row.id });
      formApi.setValues({ ...res });
    }
  },
);

async function handleSubmit() {
  try {
    const valid = await formApi.validate();
    if (valid.valid) {
      const values = await formApi.getValues();
      setModalProps({ confirmLoading: true });
      await (unref(isUpdate) ? updateTeamApi(values) : addTeamApi(values));
      closeModal();
      emit('success');
      createMessage.success(t('common.saveSuccessText'));
    }
  } finally {
    setModalProps({ confirmLoading: false });
  }
}

async function loadPermissions() {
  loadingPermissions.value = true;
  try {
    const res = await getMenuPermissonTreeApi({});

    console.error(res);
    permissions.value = res as unknown as DataNode[];
  } finally {
    loadingPermissions.value = false;
  }
}
</script>

<template>
  <div>
    <BasicModal
      v-bind="$attrs"
      :min-height="200"
      :title="
        isUpdate ? t('component.action.edit') : t('component.action.create')
      "
      :width="600"
      show-footer
      @ok="handleSubmit"
      @register="registerModal"
    >
      <Form />
    </BasicModal>
  </div>
</template>
