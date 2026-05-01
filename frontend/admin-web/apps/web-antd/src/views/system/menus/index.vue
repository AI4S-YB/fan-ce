<script lang="ts" setup>
import { h, reactive, ref } from 'vue';

import { ColPage, Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { Tooltip } from 'ant-design-vue';

import {
  createMenuApi,
  deleteMenuApi,
  getMenuInfoApi,
  updateMenuApi,
} from '#/api/system/menu';
import { Button } from '#/components/Button';
import { BasicForm, useForm } from '#/components/Form';
import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';

import ResourceApi from './api/ResourceApi.vue';
import MetaJson from './meta/MetaJson.vue';
import { formSchema } from './modalData';
import MenuTree from './tree/index.vue';

const { createMessage, createConfirm } = useMessage();
const menuInfo = ref<any>({});
const isUpdate = ref(true);
const action = ref('');
const treeRef = ref<any>(null);
const metaRef = ref<any>(null);
const handleDelete = async (rows: any = null, isBatch: Boolean = false) => {
  if (isBatch) {
    console.warn('批量删除');
  } else {
    createConfirm({
      iconType: 'warning',
      content: `${t('common.delMessage')}【${rows.title}】`,
      centered: false,
      title: () => h('span', t('common.warnning')),
      onCancel() {},
      onOk: async () => {
        try {
          await deleteMenuApi({ id: rows.id });
          createMessage.success(t('common.delSuccessText'));
          treeRef.value.fetch();
        } catch {}
      },
    });
  }
};

const getMenuInfo = async (id: any) => {
  const res: any = await getMenuInfoApi({ id });
  menuInfo.value = res;
  return res;
};
const handleAdd = (row: any) => {
  isUpdate.value = false;
  action.value = 'add';
  resetFields();
  setFieldsValue({ pid: row.id });
  setProps({ disabled: false });
  // openModal(true, { row, isUpdate: false, action: 'add' });
};
const handleEdit = async (_parent: any, node: any) => {
  isUpdate.value = true;
  action.value = 'edit';
  const res: any = await getMenuInfo(node.id);
  setFieldsValue({ ...res });
  setProps({ disabled: false });
  // openModal(true, { row: current, isUpdate: true, action: 'edit' });
};
const handleSelect = async (nodeId: any) => {
  if (nodeId) {
    setProps({ disabled: true });
    action.value = 'view';
    isUpdate.value = true;
    const res: any = await getMenuInfo(nodeId);
    setFieldsValue({ ...res });
  }
};
async function handleSubmit() {
  try {
    const values = await validate();
    if (values.permission_list === undefined) {
      values.permission_list = [];
    }
    await (action.value === 'edit'
      ? updateMenuApi(values)
      : createMenuApi(values));
    createMessage.success(t('common.saveSuccessText'));
  } finally {
    treeRef.value.fetch();
  }
}
const [registerForm, { setFieldsValue, resetFields, validate, setProps }] =
  useForm({
    labelWidth: 120,
    baseColProps: { span: 24 },
    schemas: formSchema,
    showActionButtonGroup: false,
    actionColOptions: { span: 23 },
    disabled: true,
  });
const props = reactive({
  leftCollapsedWidth: 5,
  leftCollapsible: true,
  leftMaxWidth: 50,
  leftMinWidth: 20,
  leftWidth: 30,
  resizable: true,
  rightWidth: 70,
  splitHandle: true,
  splitLine: true,
});
</script>

<template>
  <ColPage auto-content-height v-bind="props">
    <!-- <template #title>
      <span class="mr-2 text-2xl font-bold">ColPage 双列布局组件</span>
      <Tag color="hsl(var(--destructive))">Alpha</Tag>
    </template> -->
    <template #left="{ isCollapsed, expand }">
      <div v-if="isCollapsed" @click="expand">
        <Tooltip :title="$t('system.menu.clickToExpandLeft')">
          <Button shape="circle" type="primary">
            <template #icon>
              <IconifyIcon class="text-2xl" icon="bi:arrow-right" />
            </template>
          </Button>
        </Tooltip>
      </div>
      <div
        v-else
        :style="{ minWidth: '200px' }"
        class="bg-card mr-3 rounded-[var(--radius)] p-2"
      >
        <Page auto-content-height style="height: 100%">
          <MenuTree
            ref="treeRef"
            @add="handleAdd"
            @edit="handleEdit"
            @select="handleSelect"
            @delete="handleDelete"
          />
        </Page>
      </div>
    </template>
    <!-- <Card class="ml-2" title="基本使用"> -->
    <Page auto-content-height content-class="p-1 ml-3 bg-white ">
      <div class="menu-form" style="height: 100%">
        <div class="active-title">
          <div class="ml-5 mr-10" v-if="menuInfo.id">
            {{ $t('system.menu.selectedMenu', { title: menuInfo.title }) }}
          </div>
          <div class="ml-5 mr-10" v-else>{{ $t('system.menu.pleaseSelectMenu') }}</div>
          <Button
            @click="resetFields()"
            v-if="action === 'edit' || action === 'add'"
            class="mr-5"
          >
            {{ $t('system.menu.reset') }}
          </Button>
          <Button
            type="primary"
            @click="handleSubmit"
            v-if="action === 'edit' || action === 'add'"
          >
            {{ $t('system.menu.submit') }}
          </Button>
        </div>
        <hr />
        <BasicForm @register="registerForm" class="ml-5 mr-10 mt-10">
          <template #resourceApiList="{ model, field }">
            <ResourceApi
              class="itme"
              v-model:value="model[field]"
              :type="action"
            />
          </template>
          <template #metaJson="{ model, field }">
            <MetaJson
              class="itme"
              ref="metaRef"
              v-model:value="model[field]"
              :type="action"
            />
          </template>
        </BasicForm>
      </div>
    </Page>
    <!-- </Card> -->
  </ColPage>
</template>
<style lang="scss" scoped>
.menu-form {
  position: relative;
  width: 100%;
  background-color: #fff;

  .menu-form-content {
    padding: 10px;
  }
}

.active-title {
  display: flex;
  align-items: center;
  margin-top: 10px;
  margin-bottom: 5px;
}

.itme {
  display: grid;
}
</style>
