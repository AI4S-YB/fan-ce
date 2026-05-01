export interface ChatEndpointConfig {
  url: string;
  inputType: 'file' | 'text';
  supportsFileUpload: boolean;
  fileFieldName?: string;
  maxFileSize?: number;
  acceptedFileTypes?: string[];
  timeoutMs?: number;
}

export const CHAT_ENDPOINTS: Record<string, ChatEndpointConfig> = {
  default: {
    url: '/api/v1/platform/chat/completions',
    inputType: 'text',
    supportsFileUpload: false,
    timeoutMs: 10800000, // 3-hour timeout
  },
};

export function getChatEndpointConfig(_path: string): ChatEndpointConfig {
  return CHAT_ENDPOINTS.default;
}
