import { useAppConfig } from '@vben/hooks';
import { useAccessStore } from '@vben/stores';
import { requestClient } from '#/api/request';

export interface PlatformSiteSetting {
  id?: number;
  site_name: string;
  site_title: string;
  filing_no: string;
  domain: string;
  ip_address: string;
  port: number;
  extra_json?: string;
  create_time?: number;
  update_time?: number;
  user_id?: number;
}

export interface PlatformModelApiSetting {
  id: number;
  provider_code: string;
  provider_name: string;
  model_name: string;
  api_base_url: string;
  api_key: string;
  api_key_masked?: string;
  is_primary: boolean;
  is_active: boolean;
  sort_order: number;
  remark?: string;
  extra_json?: string;
  create_time?: number;
  update_time?: number;
  user_id?: number;
}

export interface PlatformModelApiPayload {
  provider_code: string;
  provider_name: string;
  model_name: string;
  api_base_url: string;
  api_key: string;
  is_primary?: boolean;
  is_active?: boolean;
  sort_order?: number;
  remark?: string;
  extra_json?: string;
}

export interface ChatMessage {
  role: 'assistant' | 'system' | 'user';
  content: string;
}

export async function getPlatformSiteSettingApi() {
  return requestClient.post<PlatformSiteSetting>('/platform/setting/site/info', {});
}

export async function updatePlatformSiteSettingApi(data: PlatformSiteSetting) {
  return requestClient.post<PlatformSiteSetting>('/platform/setting/site/update', data);
}

export async function getPlatformModelApiListApi() {
  return requestClient.post<{ items: PlatformModelApiSetting[] }>('/platform/setting/model/list', {});
}

export async function createPlatformModelApiApi(data: PlatformModelApiPayload) {
  return requestClient.post<PlatformModelApiSetting>('/platform/setting/model/create', data);
}

export async function updatePlatformModelApiApi(
  data: PlatformModelApiPayload & { id: number },
) {
  return requestClient.post<PlatformModelApiSetting>('/platform/setting/model/update', data);
}

export async function deletePlatformModelApiApi(data: { id: number }) {
  return requestClient.post('/platform/setting/model/delete', data);
}

export async function setPrimaryPlatformModelApiApi(data: { id: number }) {
  return requestClient.post<PlatformModelApiSetting>('/platform/setting/model/set-primary', data);
}

export async function platformChatStreamApi(
  messages: ChatMessage[],
  signal?: AbortSignal,
): Promise<Response> {
  const accessStore = useAccessStore();
  const { apiURL } = useAppConfig(import.meta.env, import.meta.env.PROD);
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
    'Cache-Control': 'no-cache',
  };
  if (accessStore.accessToken) {
    headers['Authorization'] = `Bearer ${accessStore.accessToken}`;
  }

  return fetch(`${apiURL}/platform/chat/completions`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ messages }),
    signal,
  });
}

export interface PlatformChatTestResult {
  ok: boolean;
  status_code: number;
  model?: string;
  reply_preview?: string;
  error?: string;
}

export async function testPlatformModelApi(data: {
  model_name: string;
  api_base_url: string;
  api_key: string;
}): Promise<PlatformChatTestResult> {
  return requestClient.post('/platform/chat/test', data);
}

// ── FRP Tunnel types ──

export interface FrpStatusResult {
  frp_status: 'stopped' | 'running' | 'error';
  pid: number | null;
  public_url: string | null;
  api_url: string | null;
  last_error: string | null;
  uptime_seconds: number | null;
}

export interface FrpConfigPayload {
  frp_server_addr?: string;
  frp_server_port?: number;
  frp_token?: string;
  frp_public_port?: number;
  frp_config_json?: string;
}

// ── FRP API functions ──

export async function updateFrpConfigApi(data: FrpConfigPayload) {
  return requestClient.post('/platform/frp/config/update', data);
}

export async function startFrpTunnelApi() {
  return requestClient.post<FrpStatusResult>('/platform/frp/start');
}

export async function stopFrpTunnelApi() {
  return requestClient.post<FrpStatusResult>('/platform/frp/stop');
}

export async function getFrpStatusApi() {
  return requestClient.post<FrpStatusResult>('/platform/frp/status');
}

export function getFrpInstallScriptUrl() {
  return '/api/v1/platform/frp/install-script';
}
