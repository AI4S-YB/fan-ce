<script lang="ts" setup>
import type { DataNode } from 'ant-design-vue/es/tree';

import { ref, unref } from 'vue';

import { VbenTree } from '@vben/common-ui';

import { Spin } from 'ant-design-vue';

import { getMenuPermissonTreeApi } from '#/api/system/menu';
import { addRoleApi, getRoleInfoApi, updateRoleApi } from '#/api/system/role';
import { Icon } from '#/components/Icon2';
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
      const res = await getRoleInfoApi({ id: data.row.id });
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
      await (unref(isUpdate) ? updateRoleApi(values) : addRoleApi(values));
      closeModal();
      emit('success');
      createMessage.success(t('common.saveSuccessText'));
    }
  } finally {
    setModalProps({ confirmLoading: false });
  }
}
function getNodeClass(node: Recordable<any>) {
  const classes: string[] = [];
  if (node.value?.type === 3) {
    delete node.value.children;
    classes.push('inline-flex');
    if (node.index % 3 >= 1) {
      classes.push('!pl-0');
    }
  }
  if (node.value.children?.length === 0) {
    delete node.value.children;
  }

  return classes.join(' ');
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
      <Form>
        <template #permissions="slotProps">
          <Spin :spinning="loadingPermissions" wrapper-class-name="w-full">
            <VbenTree
              :tree-data="permissions"
              multiple
              bordered
              :default-expanded-level="0"
              :get-node-class="getNodeClass"
              v-bind="slotProps"
              value-field="id"
              min-height="100"
              label-field="meta.title"
              icon-field="meta.icon"
            >
              <template #node="{ value }">
                <Icon v-if="value.meta.icon" :icon="value.meta.icon" />
                {{ $t(value.meta.title) }}
              </template>
            </VbenTree>
          </Spin>
        </template>
      </Form>
    </BasicModal>
  </div>
</template>
