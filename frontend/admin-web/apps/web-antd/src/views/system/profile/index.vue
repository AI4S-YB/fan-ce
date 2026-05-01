<script lang="ts" setup>
import { ref, unref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Descriptions,
  DescriptionsItem,
  TabPane,
  Tabs,
} from 'ant-design-vue';

import {
  getUserProfileApi,
  updatePwdApi,
  updateUserApi,
} from '#/api/system/user';
import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';
import { formatToDateTime } from '#/utils/dateUtil';

import { Form, Form2, formApi, formApi2 } from './data';

const userInfo = ref<any>({});

const { createMessage } = useMessage();
const activeKey = ref('1');
const getUserInfo = async () => {
  await getUserProfileApi().then((res) => {
    userInfo.value = res;
    formApi.setValues({ ...unref(res) });
  });
};

getUserInfo();

const handleSelect = (key: any) => {
  if (key === '1') {
    formApi.setValues({ ...unref(userInfo) });
  } else {
    formApi2.setValues({ ...unref(userInfo) });
  }
};
const handleSubmit = async () => {
  if (activeKey.value === '1') {
    await updateUserApi(await formApi.getValues()).then(() => {
      getUserInfo();
      createMessage.success(t('common.saveSuccessText'));
    });
  } else {
    const pwd = await formApi2.getValues();
    if (pwd.new_password !== pwd.confirm_password) {
      createMessage.error(t('system.profile.passwordMismatch'));
      return;
    }
    await updatePwdApi(await formApi2.getValues()).then(() => {
      getUserInfo();
      createMessage.success(t('common.saveSuccessText'));
    });
  }
};
</script>

<template>
  <Page auto-content-height>
    <div style="height: 500px">
      <Card :title="$t('system.profile.userCenter')" :bordered="false">
        <Descriptions title="" bordered>
          <DescriptionsItem :label="$t('system.profile.userNameLabel')">
            {{ userInfo.user_name }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('system.profile.emailLabel')">
            {{ userInfo.user_email }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('system.profile.phone')">
            {{ userInfo.user_phone }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('system.menu.createTime')">
            {{ formatToDateTime(userInfo.create_time) }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('system.user.role')">
            {{ userInfo.user_name }}
          </DescriptionsItem>
        </Descriptions>
      </Card>
      <Card :title="$t('system.profile.infoChange')" class="mt-5">
        <Tabs v-model:active-key="activeKey" @change="handleSelect">
          <TabPane key="1" :tab="$t('system.profile.basicInfoEdit')">
            <Form v-if="activeKey === '1'" />
          </TabPane>
          <TabPane key="2" :tab="$t('system.profile.passwordEdit')">
            <Form2 v-if="activeKey === '2'" />
          </TabPane>
        </Tabs>
        <Button type="primary" @click="handleSubmit">{{ $t('system.profile.submit') }}</Button>
      </Card>
    </div>
  </Page>
</template>
