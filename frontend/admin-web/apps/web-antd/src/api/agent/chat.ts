import type { ChatEndpointConfig } from '#/config/chat-endpoints';

import { preferences } from '@vben/preferences';
import { useAccessStore } from '@vben/stores';

export interface ChatRequest {
  message: string;
  stream: boolean;
  checkpoint_id?: string;
  conversation_id?: string;
  file_upload?: File[];
}

interface SendChatOptions {
  signal?: AbortSignal;
}

export async function sendChatMessage(
  data: ChatRequest,
  config: ChatEndpointConfig,
  options: SendChatOptions = {},
) {
  const accessStore = useAccessStore();
  const headers: Record<string, string> = {
    Accept: 'text/event-stream',
    'Accept-Language': preferences.app.locale,
    'Cache-Control': 'no-cache',
    'Content-Type': 'application/json',
  };

  if (accessStore.accessToken) {
    headers['Authorization'] = `Bearer ${accessStore.accessToken}`;
  }

  // Build JSON payload matching backend PlatformChatCompletionRequest
  const payload = {
    messages: [{ role: 'user', content: data.message }],
  };

  const fullURL = config.url.startsWith('http') ? config.url : config.url;

  return fetch(fullURL, {
    method: 'POST',
    body: JSON.stringify(payload),
    headers,
    signal: options.signal,
  });
}
