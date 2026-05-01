<script lang="ts" setup>
import type { NotificationItem } from '@vben/layouts';

import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import { AuthenticationLoginExpiredModal } from '@vben/common-ui';
import { useRefresh, useWatermark } from '@vben/hooks';
import {
  BasicLayout,
  LockScreen,
  Notification,
  UserDropdown,
} from '@vben/layouts';
import { preferences, usePreferences } from '@vben/preferences';
import { useAccessStore, useUserStore } from '@vben/stores';
import { Button, Dropdown, Menu } from 'ant-design-vue';

import { $t } from '#/locales';
import { useAuthStore } from '#/store';
import { useProjectStoreWithOut } from '#/store/modules/project';
import LoginForm from '#/views/_core/authentication/login.vue';

const notifications = ref<NotificationItem[]>([
  {
    avatar: 'https://avatar.vercel.sh/vercel.svg?text=VB',
    date: '3小时前',
    isRead: true,
    message: '描述信息描述信息描述信息',
    title: '收到了 14 份新周报',
  },
]);
const { refresh } = useRefresh();
const userStore = useUserStore();
const authStore = useAuthStore();
const accessStore = useAccessStore();
const proStore = useProjectStoreWithOut();
const { destroyWatermark, updateWatermark } = useWatermark();
const showDot = computed(() =>
  notifications.value.some((item) => !item.isRead),
);
const router = useRouter();
const menus: any = computed(() => [
  {
    handler: () => {
      router.push('/system/user/profile');
    },
    icon: 'ant-design:user-outlined',
    text: $t('page.profile'),
  },
]);
const { isDark } = usePreferences();
const headerColor = computed(() => {
  const dark = isDark.value || preferences.theme.semiDarkHeader;
  return dark;
});
const avatar = computed(() => {
  return userStore.userInfo?.avatar ?? preferences.app.defaultAvatar;
});
async function handleLogout() {
  await authStore.logout(false);
}

function handleNoticeClear() {
  notifications.value = [];
}

function handleMakeAll() {
  notifications.value.forEach((item) => (item.isRead = true));
}
watch(
  () => preferences.app.watermark,
  async (enable) => {
    if (enable) {
      await updateWatermark({
        content: `${userStore.userInfo?.username} - ${userStore.userInfo?.realName}`,
      });
    } else {
      destroyWatermark();
    }
  },
  {
    immediate: true,
  },
);
</script>

<template>
  <BasicLayout @clear-preferences-and-logout="handleLogout">
    <template #user-dropdown>
      <UserDropdown
        :avatar
        :menus
        :text="userStore.userInfo?.userinfo.user_name"
        :description="''"
        tag-text=""
        @logout="handleLogout"
      />
      <div></div>
    </template>
    <template #notification>
      <Notification
        :dot="showDot"
        :notifications="notifications"
        @clear="handleNoticeClear"
        @make-all="handleMakeAll"
      />
    </template>
    <template #extra>
      <AuthenticationLoginExpiredModal
        v-model:open="accessStore.loginExpired"
        :avatar
      >
        <LoginForm />
      </AuthenticationLoginExpiredModal>
    </template>
    <template #lock-screen>
      <LockScreen :avatar @to-login="handleLogout" />
    </template>
  </BasicLayout>
</template>
