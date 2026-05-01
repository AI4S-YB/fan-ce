<script lang="ts" setup>
import type { AuthKeyInfo } from '#/api/system/user';

import { computed, ref } from 'vue';

import { Button, Input, Tag } from 'ant-design-vue';

import {
  deleteUserAuthKeyApi,
  generateUserAuthKeyApi,
  getUserAuthKeyApi,
  regenerateUserAuthKeyApi,
  updateUserAuthKeyStatusApi,
} from '#/api/system/user';
import { BasicModal, useModalInner } from '#/components/Modal';
import { useMessage } from '#/hooks/web/useMessage';
import { $t } from '@vben/locales';

defineOptions({ name: 'AuthKeyModal' });

const emit = defineEmits(['success', 'register']);
const { createMessage, createConfirm } = useMessage();

// 用户信息和认证密钥状态
const currentUser = ref<any>(null);
const authKeyInfo = ref<AuthKeyInfo | null>(null);
const loading = ref(false);
const regenerating = ref(false);

// 计算属性
const hasAuthKey = computed(() => authKeyInfo.value?.has_key === true);
const authKeyStatus = computed(() => authKeyInfo.value?.status);
const isKeyActive = computed(() => authKeyStatus.value === 'active');

const [registerModal, { setModalProps, closeModal }] = useModalInner(
  async (data) => {
    setModalProps({ confirmLoading: false });
    currentUser.value = data.row;
    await loadAuthKeyInfo();
  },
);

// 加载认证密钥信息
async function loadAuthKeyInfo() {
  if (!currentUser.value?.id) return;

  loading.value = true;
  try {
    const response = await getUserAuthKeyApi(currentUser.value.id);
    authKeyInfo.value = response;
  } catch {
    // 如果用户没有密钥，后端可能返回404或空数据
    authKeyInfo.value = null;
  } finally {
    loading.value = false;
  }
}

// 生成认证密钥
async function generateAuthKey() {
  if (!currentUser.value?.id) return;

  loading.value = true;
  try {
    const response = await generateUserAuthKeyApi(currentUser.value.id);
    authKeyInfo.value = {
      auth_key: response.auth_key,
      status: response.status,
      user_id: response.user_id,
      team_id: response.team_id,
      has_key: true,
    };
    createMessage.success($t('system.user.authKeyGenerated'));
    emit('success');
  } catch (error: any) {
    createMessage.error(error?.message || $t('system.user.authKeyGenerateFailed'));
  } finally {
    loading.value = false;
  }
}

// 重新生成认证密钥
async function regenerateAuthKey() {
  if (!currentUser.value?.id) return;

  createConfirm({
    iconType: 'warning',
    content: $t('system.user.regenerateKeyConfirm'),
    centered: false,
    title: $t('system.user.regenerateKey'),
    onOk: async () => {
      regenerating.value = true;
      try {
        const response = await regenerateUserAuthKeyApi(currentUser.value.id);
        authKeyInfo.value = {
          auth_key: response.auth_key,
          status: response.status,
          user_id: response.user_id,
          team_id: response.team_id,
          has_key: true,
        };
        createMessage.success($t('system.user.authKeyRegenerated'));
        emit('success');
      } catch (error: any) {
        createMessage.error(error?.message || $t('system.user.authKeyRegenerateFailed'));
      } finally {
        regenerating.value = false;
      }
    },
  });
}

// 更新密钥状态
async function updateKeyStatus(status: 'active' | 'disabled') {
  if (!currentUser.value?.id) return;

  const statusText = status === 'active' ? $t('system.user.enable') : $t('system.user.disable');
  createConfirm({
    iconType: 'warning',
    content: $t('system.user.updateKeyStatusConfirm', { status: statusText }),
    centered: false,
    title: $t('system.user.statusAuthKey', { status: statusText }),
    onOk: async () => {
      loading.value = true;
      try {
        await updateUserAuthKeyStatusApi(currentUser.value.id, { status });
        if (authKeyInfo.value) {
          authKeyInfo.value.status = status;
        }
        createMessage.success($t('system.user.updateKeyStatusSuccess', { status: statusText }));
        emit('success');
      } catch (error: any) {
        createMessage.error(error?.message || $t('system.user.updateKeyStatusFailed', { status: statusText }));
      } finally {
        loading.value = false;
      }
    },
  });
}

// 删除认证密钥
async function deleteAuthKey() {
  if (!currentUser.value?.id) return;

  createConfirm({
    iconType: 'warning',
    content: $t('system.user.deleteKeyConfirm'),
    centered: false,
    title: $t('system.user.deleteAuthKeyTitle'),
    onOk: async () => {
      loading.value = true;
      try {
        await deleteUserAuthKeyApi(currentUser.value.id);
        authKeyInfo.value = null;
        createMessage.success($t('system.user.authKeyDeleted'));
        emit('success');
      } catch (error: any) {
        createMessage.error(error?.message || $t('system.user.authKeyDeleteFailed'));
      } finally {
        loading.value = false;
      }
    },
  });
}

// 复制密钥到剪贴板
async function copyAuthKey() {
  if (!authKeyInfo.value?.auth_key) return;

  try {
    await navigator.clipboard.writeText(authKeyInfo.value.auth_key);
    createMessage.success($t('system.user.authKeyCopied'));
  } catch (error) {
    console.error('复制认证密钥失败:', error);
    createMessage.error($t('system.user.copyFailed'));
  }
}

// 脱敏显示密钥
function maskAuthKey(key: string): string {
  if (!key || key.length < 16) return key;
  return `${key.slice(0, 12)}****${key.slice(Math.max(0, key.length - 4))}`;
}
</script>

<template>
  <div>
    <BasicModal
      v-bind="$attrs"
      :min-height="400"
      :title="$t('system.user.authKeyManagement', { name: currentUser?.user_name || '' })"
      :width="700"
      show-footer
      :ok-text="$t('component.modal.close')"
      :cancel-text="undefined"
      @ok="closeModal"
      @register="registerModal"
    >
      <div v-loading="loading" class="p-4">
        <!-- 用户信息 -->
        <div class="mb-6 rounded-lg bg-gray-50 p-4">
          <h3 class="mb-2 text-lg font-medium">{{ $t('system.user.userInfo') }}</h3>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span class="font-medium">{{ $t('system.user.usernameLabel') }}</span>
              <span>{{ currentUser?.user_name }}</span>
            </div>
            <div>
              <span class="font-medium">{{ $t('system.user.emailLabel') }}</span>
              <span>{{ currentUser?.user_email || $t('system.user.notSet') }}</span>
            </div>
            <div>
              <span class="font-medium">{{ $t('system.user.userIdLabel') }}</span>
              <span>{{ currentUser?.id }}</span>
            </div>
            <div v-if="authKeyInfo?.team_id">
              <span class="font-medium">{{ $t('system.user.teamIdLabel') }}</span>
              <span>{{ authKeyInfo.team_id }}</span>
            </div>
          </div>
        </div>

        <!-- 认证密钥信息 -->
        <div class="mb-6">
          <h3 class="mb-4 text-lg font-medium">{{ $t('system.user.authKeyInfo') }}</h3>

          <!-- 没有密钥的情况 -->
          <div v-if="!hasAuthKey" class="py-8 text-center">
            <div class="mb-4">
              <i class="text-4xl text-gray-400">🔑</i>
            </div>
            <p class="mb-4 text-gray-600">{{ $t('system.user.noAuthKeyGenerated') }}</p>
            <Button type="primary" :loading="loading" @click="generateAuthKey">
              {{ $t('system.user.generateAuthKey') }}
            </Button>
          </div>

          <!-- 有密钥的情况 -->
          <div v-else class="space-y-4">
            <!-- 密钥显示区域 -->
            <div class="rounded-lg border p-4">
              <div class="mb-2 flex items-center justify-between">
                <span class="font-medium">{{ $t('system.user.authKey') }}</span>
                <Tag :color="isKeyActive ? 'green' : 'red'">
                  {{ isKeyActive ? $t('system.user.enable') : $t('system.user.disable') }}
                </Tag>
              </div>
              <div class="flex items-center space-x-2">
                <Input
                  :value="authKeyInfo?.auth_key || ''"
                  readonly
                  class="font-mono text-sm"
                />
                <Button type="primary" ghost @click="copyAuthKey">
                  {{ $t('system.user.copy') }}
                </Button>
              </div>
              <!-- <p class="mt-2 text-xs text-gray-500">
                为安全起见，密钥部分内容已隐藏。点击复制可获取完整密钥。
              </p> -->
            </div>

            <!-- 操作按钮 -->
            <div class="flex flex-wrap gap-2">
              <Button
                type="primary"
                :loading="regenerating"
                @click="regenerateAuthKey"
              >
                {{ $t('system.user.regenerate') }}
              </Button>

              <Button
                v-if="isKeyActive"
                type="default"
                :loading="loading"
                @click="updateKeyStatus('disabled')"
              >
                {{ $t('system.user.disableKey') }}
              </Button>

              <Button
                v-else
                type="primary"
                ghost
                :loading="loading"
                @click="updateKeyStatus('active')"
              >
                {{ $t('system.user.enableKey') }}
              </Button>

              <Button danger :loading="loading" @click="deleteAuthKey">
                {{ $t('system.user.deleteKey') }}
              </Button>
            </div>

            <!-- 使用说明 -->
            <div class="rounded-lg bg-blue-50 p-4">
              <h4 class="mb-2 font-medium text-blue-800">{{ $t('system.user.usageGuide') }}</h4>
              <ul class="space-y-1 text-sm text-blue-700">
                <li>• {{ $t('system.user.usageTip1') }}</li>
                <li>• {{ $t('system.user.usageTip2') }}</li>
                <li>• {{ $t('system.user.usageTip3') }}</li>
                <li>• {{ $t('system.user.usageTip4') }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </BasicModal>
  </div>
</template>

<style scoped>
.ant-input[readonly] {
  cursor: default;
  background-color: #f5f5f5;
}
</style>
