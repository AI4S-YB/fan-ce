import type { Recordable, UserInfo } from '@vben/types';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { LOGIN_PATH } from '@vben/constants';
import { preferences } from '@vben/preferences';
import { resetAllStores, useAccessStore, useUserStore } from '@vben/stores';

import { notification } from 'ant-design-vue';
import { defineStore } from 'pinia';

import { getUserAuthApi, loginApi, logoutApi } from '#/api';
import { getDictMapApi } from '#/api/system/';
import { $t } from '#/locales';
import { useDictStoreWithOut } from '#/store/modules/dict';
import { useProjectStoreWithOut } from '#/store/modules/project';

export const useAuthStore = defineStore('auth', () => {
  const accessStore = useAccessStore();
  const userStore = useUserStore();
  const router = useRouter();
  const dictStore = useDictStoreWithOut();
  const proStore = useProjectStoreWithOut();
  const loginLoading = ref(false);
  // const options1: any = inject('projectOptions');
  /**
   * 异步处理登录操作
   * Asynchronously handle the login process
   * @param params 登录表单数据
   */
  async function authLogin(
    params: Recordable<any>,
    onSuccess?: () => Promise<void> | void,
  ) {
    // 异步处理用户登录操作并获取 accessToken
    let userInfo: null | UserInfo = null;
    try {
      loginLoading.value = true;
      const { access_token, team, project } = await loginApi(params);
      proStore.setTeamInfo(team || {});
      proStore.setProjectInfo(project || {});
      // 如果成功获取到 accessToken
      if (access_token) {
        accessStore.setAccessToken(access_token);

        // 获取用户信息并存储到 accessStore 中
        const [fetchUserInfoResult, fetchDictMapResult] = await Promise.all([
          fetchUserInfo(),
          fetchDictMap(),
        ]);

        userInfo = fetchUserInfoResult;

        userStore.setUserInfo(userInfo);
        fetchDictMapResult;
        if (accessStore.loginExpired) {
          accessStore.setLoginExpired(false);
        } else {
          onSuccess
            ? await onSuccess?.()
            : await router.push(preferences.app.defaultHomePath);
        }

        if (userInfo?.realName) {
          notification.success({
            description: `${$t('authentication.loginSuccessDesc')}:${userInfo?.realName}`,
            duration: 3,
            message: $t('authentication.loginSuccess'),
          });
        }
      }
    } finally {
      loginLoading.value = false;
    }

    return {
      userInfo,
    };
  }

  async function logout(redirect: boolean = true) {
    try {
      await logoutApi();
    } catch {
      // 不做任何处理
    }
    resetAllStores();
    accessStore.setLoginExpired(false);

    // 回登录页带上当前路由地址
    await router.replace({
      path: LOGIN_PATH,
      query: redirect
        ? {
            redirect: encodeURIComponent(router.currentRoute.value.fullPath),
          }
        : {},
    });
  }

  async function fetchUserInfo() {
    let userInfo: any | UserInfo = null;
    userInfo = await getUserAuthApi();
    userStore.setUserInfo(userInfo);
    // 初始化数据团队、项目
    accessStore.setAccessCodes(userInfo?.permissions || []);
    if (!proStore.getTeamInfo.team_id) {
      proStore.setTeamInfo(userInfo?.team_list?.[0] || {});
    }
    if (!proStore.getProjectInfo.id) {
      proStore.setProjectInfo(userInfo?.project_list?.[0] || {});
    }
    proStore.fetchProjectOptions();
    return userInfo;
  }
  async function fetchDictMap() {
    const dictData = await getDictMapApi({});
    dictStore.setDictMap(dictData);
    return dictData;
  }

  function $reset() {
    loginLoading.value = false;
  }

  return {
    $reset,
    authLogin,
    fetchDictMap,
    fetchUserInfo,
    loginLoading,
    logout,
  };
});
