<script lang="ts" setup>
import { ref, unref } from 'vue';

import { Card, CardMeta, Col, Row, Tag } from 'ant-design-vue';
import { split, uniqueId } from 'lodash-es';

import { getPermissionOptionsTreeApi } from '#/api/system/permission';
import { BasicForm, useForm } from '#/components/Form';
import { BasicModal, useModalInner } from '#/components/Modal';
import { HTTP_TAG_MAP } from '#/enums/httpEnum';

import { selectResourceApiFormSchema } from './data';
import { $t } from '@vben/locales';

defineOptions({ name: 'ApiSelect' });
const emit = defineEmits(['success', 'register']);
const currentService = ref<string>('system'); // 当前的服务
const currentController = ref<string>(''); // 当前的控制器类

const serviceControllerListMap = ref<Recordable>({}); // 服务 对应的控制器类
const currentControllerData = ref<any[]>([]); // 服务 控制类 数据
const apiMap = ref<Recordable>({}); // 后端返回集合
const selectedData = ref<Recordable[]>([]);
// 选择服务
async function handleServiceChange(value: string) {
  currentService.value = value;
  const controllerOptions: Recordable[] = [];
  apiMap.value = await getPermissionOptionsTreeApi({ type: value });

  apiMap.value.forEach((k: any) => {
    controllerOptions.push({
      value: k.id,
      key: k.id,
      label: k.name,
    });
  });

  serviceControllerListMap.value[value] = apiMap.value;

  updateSchema([
    {
      field: 'controller',
      componentProps: {
        options: controllerOptions,
      },
    },
    {
      field: 'uri',
      componentProps: {
        options: undefined,
        'option-label-prop': 'label',
      },
    },
  ]);

  setFieldsValue({ controller: '', uri: [] });
}
// 选择控制器
async function handleControllerChange(value: string) {
  const uriOptions: Recordable[] = [];
  currentController.value = value;
  if (value) {
    apiMap.value.forEach((item: any) => {
      if (item.id === value) {
        uriOptions.push({
          value: `${item.id}#${item.uri}#${item.method}#${item.name}#${item.code}`,
          key: item.id,
          label: `${item.uri} 【 ${item.method}】${item.name}`,
          ...item,
        });
        item.children.forEach((uri: any) => {
          uriOptions.push({
            value: `${uri.id}#${uri.uri}#${uri.method}#${uri.name}#${uri.code}`,
            key: uri.id,
            label: `${uri.uri} 【 ${uri.method}】${uri.name}`,
            ...item,
          });
        });
      }
    });
  }
  currentControllerData.value = uriOptions;
  const selectedOptions = getSelectedOptions(value);
  updateSchema({
    field: 'uri',
    componentProps: {
      options: uriOptions,
    },
  });
  setFieldsValue({ uri: selectedOptions });
}

// 获取已经选中的uri
function getSelectedOptions(controller: string) {
  const selectedOptions: string[] = [];
  if (!controller) {
    return selectedOptions;
  }
  // 已选列表
  for (const selected of unref(selectedData)) {
    currentControllerData.value.forEach((item: any) => {
      if (selected.id === item.id) {
        selectedOptions.push(
          `${item.id}#${item.uri}#${item.method}#${item.name}#${item.code}`,
        );
      }
    });
  }
  return selectedOptions;
}
// 添加
function addSelectedData(obj: any) {
  let flag = false;
  for (const selected of unref(selectedData)) {
    if (
      selected.name === obj.name &&
      selected.uri === obj.uri &&
      selected.method === obj.method
    ) {
      flag = true;
      break;
    }
  }
  if (!flag) {
    selectedData.value.push(obj);
  }
}

async function delSelectedDataByCard(obj: any) {
  const model = await getFieldsValue();
  const uris = model?.uri;
  if (uris) {
    const index = uris.findIndex((uri: any) => {
      const selected = split(uri, '#');
      return (
        selected[1] === obj.uri &&
        selected[2] === obj.method &&
        selected[3] === obj.name
      );
    });
    if (index !== -1) {
      uris.splice(index, 1);
    }

    if (uris && uris.length > 0) {
      await setFieldsValue({ uri: undefined });
      await setFieldsValue({ uri: uris });
    } else {
      setFieldsValue({ uri: undefined });
    }
  }
  delSelectedData(obj);
}

function delSelectedData(obj: any) {
  const index = unref(selectedData).findIndex(
    (selected) =>
      selected.name === obj.name &&
      selected.uri === obj.uri &&
      selected.method === obj.method,
  );

  if (index !== -1) {
    selectedData.value.splice(index, 1);
  }
}

// 选择 uri
const handleUriChange = async (values: string[]) => {
  // 当前选中的值
  if (values && values.length > 0) {
    for (const value of values) {
      const valueList = split(value, '#');
      // const ids = parseInt(valueList?.[0], 10);
      // console.log(ids);

      addSelectedData({
        id: valueList[0] ? Number.parseInt(valueList[0], 10) : valueList[0],
        uri: valueList[1],
        method: valueList[2],
        name: valueList[3],
        code: valueList[4],
        isInput: false,
        tempId: uniqueId(),
      });
    }
  } else {
    currentControllerData.value.forEach((api: any) => {
      delSelectedData(api);
    });
  }
};
// 取消 uri
const handleUriDeselect = async (value: any) => {
  // 取消的数据
  const valueList = split(value, '#');
  delSelectedData({
    id: valueList[0],
    uri: valueList[1],
    method: valueList[2],
    name: valueList[3],
    code: valueList[4],
  });
};

const [
  registerForm,
  { setFieldsValue, getFieldsValue, resetFields, updateSchema },
] = useForm({
  // labelWidth: 80,
  layout: 'vertical',
  schemas: selectResourceApiFormSchema(
    handleServiceChange,
    handleControllerChange,
    handleUriChange,
    handleUriDeselect,
  ),
  baseColProps: { span: 24 },
  showActionButtonGroup: false,
  actionColOptions: {
    span: 23,
  },
});

const [registerModal, { setModalProps, closeModal }] = useModalInner(
  async (data) => {
    await resetFields();
    await updateSchema([
      {
        field: 'controller',
        componentProps: {
          options: undefined,
        },
      },
      {
        field: 'uri',
        componentProps: {
          options: undefined,
        },
      },
    ]);
    handleServiceChange('system');
    setModalProps({ confirmLoading: false, minHeight: 300 });
    selectedData.value = data?.selectedData;
  },
);

async function handleSubmit() {
  try {
    setModalProps({ confirmLoading: true });
    closeModal();
    emit('success', unref(selectedData));
  } finally {
    setModalProps({ confirmLoading: false });
  }
}
</script>
<template>
  <BasicModal
    v-bind="$attrs"
    @register="registerModal"
    :title="$t('system.menu.selectApi')"
    :mask-closable="false"
    @ok="handleSubmit"
    width="60%"
  >
    <Row>
      <Col :span="14">
        <div class="ml-4 mr-4">
          <BasicForm @register="registerForm" />
        </div>
      </Col>
      <Col :span="10">
        <div class="ml-4 mr-4">
          <h4>{{ $t('system.menu.selectedApis', { count: selectedData.length }) }}</h4>
          <Card
            style="margin-bottom: 0.5rem"
            hoverable
            size="small"
            v-for="api in selectedData"
            :key="api.name + api.uri + api.method"
            :title="api.name"
          >
            <template #extra>
              <a
                href="javascript:void(0);"
                @click="delSelectedDataByCard(api)"
                class="text-red-500"
                >{{ $t('common.title.delete') }}
              </a>
            </template>
            <CardMeta>
              <template #title>
                {{ $t('system.menu.apiNameLabel') }}： {{ api.name }} <br />
                {{ $t('system.menu.apiPermission') }}：{{ api.code }}
              </template>
              <template #description>
                <div
                  class="cardDesc"
                  :title="`(${api.method}) ${api.uri} (${api.controller})`"
                >
                  <Tag :color="HTTP_TAG_MAP.get(api.method)">
                    {{ api.method }}
                  </Tag>
                  {{ api.uri }}
                </div>
              </template>
            </CardMeta>
          </Card>
        </div>
      </Col>
    </Row>
  </BasicModal>
</template>
<style lang="scss" scoped>
.cardDesc {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  font-weight: bold;
  white-space: nowrap;
  background: rgb(97 175 254 / 10%);
}
</style>
