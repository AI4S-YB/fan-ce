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
const team_list = computed(() => {
  return userStore.userInfo?.team_list;
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
const handleTeamSelect = (item: any) => {
  // 执行团队选择逻辑
  proStore.setTeamInfo(item);
  proStore.updateProjectOptions();
  refresh();
};
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
const placement = computed(() => proStore.getTeamInfo?.team_name);
</script>

<template>
  <BasicLayout @clear-preferences-and-logout="handleLogout">
    <template #user-dropdown>
      <Dropdown placement="bottom">
        <Button
          :style="{
            'background-color': 'hsl(var(--header))',
            border: '0',
            color: headerColor.value ? '#000' : '#fff',
          }"
        >
          {{ placement }}
        </Button>
        <template #overlay>
          <Menu>
            <Menu.Item
              v-for="item in team_list"
              :key="item.id"
              :style="{
                'background-color':
                  placement === item.team_name
                    ? 'hsl(var(--primary) / 30%)'
                    : '',
              }"
            >
              <a @click="handleTeamSelect(item)"> {{ item.team_name }} </a>
            </Menu.Item>
          </Menu>
        </template>
      </Dropdown>
      <UserDropdown
        :avatar
        :menus
        :text="userStore.userInfo?.userinfo.user_name"
        :description="placement"
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
