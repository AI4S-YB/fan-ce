<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue';
import {
  Card, Button, Input, InputNumber, Space, Tag, message, Alert, Spin,
} from 'ant-design-vue';
import {
  startFrpTunnelApi, stopFrpTunnelApi, getFrpStatusApi,
  updateFrpConfigApi, getFrpInstallScriptUrl,
  type FrpStatusResult,
} from '#/api/platform/setting';
import { $t } from '@vben/locales';

interface FrpConfig {
  frp_server_addr: string;
  frp_server_port: number;
  frp_token: string;
  frp_public_port: number;
  frp_config_json: string;
}

const props = defineProps<{
  siteSetting: Record<string, any>;
}>();

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

const statusLoading = ref(false);
const actionLoading = ref(false);
const configSaving = ref(false);
const status = ref<FrpStatusResult | null>(null);
let pollTimer: ReturnType<typeof setInterval> | null = null;

const config = ref<FrpConfig>({
  frp_server_addr: '',
  frp_server_port: 7000,
  frp_token: '',
  frp_public_port: 80,
  frp_config_json: '',
});

function initFromProps() {
  config.value.frp_server_addr = props.siteSetting?.frp_server_addr || '';
  config.value.frp_server_port = props.siteSetting?.frp_server_port || 7000;
  config.value.frp_token = props.siteSetting?.frp_token || '';
  config.value.frp_public_port = props.siteSetting?.frp_public_port || 80;
  config.value.frp_config_json = props.siteSetting?.frp_config_json || '';
}

const frpStatus = computed(() => status.value?.frp_status || 'stopped');

const statusColor = computed(() => {
  switch (frpStatus.value) {
    case 'running': return 'green';
    case 'error': return 'red';
    default: return 'default';
  }
});

const statusText = computed(() => $t(`platform.frpStatus.${frpStatus.value}`));

async function fetchStatus() {
  statusLoading.value = true;
  try {
    const res = await getFrpStatusApi();
    status.value = res;
  } catch {
    status.value = null;
  } finally {
    statusLoading.value = false;
  }
}

async function saveConfig() {
  configSaving.value = true;
  try {
    await updateFrpConfigApi(config.value);
    message.success($t('platform.frpConfigSaved'));
    emit('refresh');
  } catch {
    message.error($t('platform.frpConfigSaveFailed'));
  } finally {
    configSaving.value = false;
  }
}

async function handleStart() {
  actionLoading.value = true;
  try {
    const res = await startFrpTunnelApi();
    status.value = res;
    if (res.frp_status === 'running') {
      message.success($t('platform.frpTunnelStarted'));
      startPolling();
    } else {
      message.error(res.last_error || $t('platform.frpTunnelStartFailed'));
    }
    emit('refresh');
  } catch {
    message.error($t('platform.frpTunnelStartFailed'));
  } finally {
    actionLoading.value = false;
  }
}

async function handleStop() {
  actionLoading.value = true;
  try {
    await stopFrpTunnelApi();
    status.value = { frp_status: 'stopped', pid: null, public_url: null, api_url: null, last_error: null, uptime_seconds: null };
    message.success($t('platform.frpTunnelStopped'));
    stopPolling();
    emit('refresh');
  } catch {
    message.error($t('platform.frpTunnelStopFailed'));
  } finally {
    actionLoading.value = false;
  }
}

function generateToken() {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let token = '';
  for (let i = 0; i < 32; i++) {
    token += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  config.value.frp_token = token;
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(fetchStatus, 10000);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

onMounted(() => {
  initFromProps();
  fetchStatus();
  if (props.siteSetting?.frp_status === 'running') {
    startPolling();
  }
});

onUnmounted(() => stopPolling());
</script>

<template>
  <Card :title="$t('platform.frpTunnelCard')" style="margin-top: 16px;">
    <!-- Config Form -->
    <div style="display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 16px;">
      <div style="flex: 1; min-width: 200px;">
        <label style="display: block; margin-bottom: 4px; font-weight: 500;">
          {{ $t('platform.frpServerAddr') }} *
        </label>
        <Input v-model:value="config.frp_server_addr" :placeholder="$t('platform.frpServerAddrPlaceholder')" />
      </div>
      <div style="flex: 1; min-width: 120px;">
        <label style="display: block; margin-bottom: 4px; font-weight: 500;">
          {{ $t('platform.frpServerPort') }}
        </label>
        <InputNumber v-model:value="config.frp_server_port" :min="1" :max="65535" style="width: 100%;" />
      </div>
      <div style="flex: 1; min-width: 120px;">
        <label style="display: block; margin-bottom: 4px; font-weight: 500;">
          {{ $t('platform.frpPublicPort') }}
        </label>
        <InputNumber v-model:value="config.frp_public_port" :min="1" :max="65535" style="width: 100%;" />
      </div>
      <div style="flex: 2; min-width: 280px;">
        <label style="display: block; margin-bottom: 4px; font-weight: 500;">
          {{ $t('platform.frpToken') }} *
        </label>
        <Space style="width: 100%;">
          <Input v-model:value="config.frp_token" :placeholder="$t('platform.frpTokenPlaceholder')" style="flex: 1;" />
          <Button size="small" @click="generateToken">{{ $t('platform.frpGenerateToken') }}</Button>
        </Space>
      </div>
    </div>

    <Space style="margin-bottom: 16px;">
      <Button type="primary" ghost :loading="configSaving" @click="saveConfig">
        {{ $t('platform.frpSaveConfig') }}
      </Button>
      <Button @click="() => window.open(getFrpInstallScriptUrl(), '_blank')">
        {{ $t('platform.frpDownloadScript') }}
      </Button>
    </Space>

    <!-- Status & Controls -->
    <div style="display: flex; align-items: center; gap: 12px; padding: 12px; background: #fafafa; border-radius: 6px;">
      <span style="font-weight: 500;">{{ $t('platform.frpCurrentStatus') }}:</span>
      <Spin v-if="statusLoading" size="small" />
      <Tag v-else :color="statusColor">{{ statusText }}</Tag>

      <template v-if="status?.public_url && frpStatus === 'running'">
        <span style="color: #888; margin-left: 8px;">
          {{ $t('platform.frpPublicUrl') }}:
          <a :href="status.public_url" target="_blank">{{ status.public_url }}</a>
        </span>
      </template>

      <div style="flex: 1;" />

      <Button
        v-if="frpStatus !== 'running'"
        type="primary"
        :loading="actionLoading"
        @click="handleStart"
      >
        {{ $t('platform.frpStartSharing') }}
      </Button>
      <Button
        v-else
        danger
        :loading="actionLoading"
        @click="handleStop"
      >
        {{ $t('platform.frpStopSharing') }}
      </Button>
    </div>

    <!-- Error display -->
    <Alert
      v-if="frpStatus === 'error' && status?.last_error"
      type="error"
      :message="$t('platform.frpErrorTitle')"
      :description="status.last_error"
      show-icon
      style="margin-top: 12px;"
    />

    <!-- Notice for first-time users -->
    <Alert
      type="info"
      :message="$t('platform.frpFirstTimeTitle')"
      :description="$t('platform.frpFirstTimeDesc')"
      show-icon
      style="margin-top: 12px;"
    />
  </Card>
</template>
