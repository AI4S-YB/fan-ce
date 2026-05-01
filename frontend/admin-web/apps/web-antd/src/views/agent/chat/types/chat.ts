/**
 * Core stream message types emitted by the backend SSE channel.
 */
export type StreamMessageType =
  | 'start'
  | 'output_msg'
  | 'execution_msg'
  | 'break'
  | 'interrupt'
  | 'tool_call'
  | 'tool_result'
  | 'complete'

/**
 * Raw SSE payload coming from the backend.
 */
export interface SSEMessage {
  type: StreamMessageType
  message?: string
  content?: string
  node_name?: string
  conversation_id?: string
  checkpoint_id?: string
  next?: string  // 🔧 [STAGE_WORKFLOW] 新增：下一阶段标识，用于多阶段工作流
}

export interface ToolResultPayload {
  tool_name: string
  data?: Record<string, any>
  error?: string
  message?: string
}

/**
 * Normalised chat message stored on the frontend.
 */
export interface ChatMessage {
  id: string
  type: 'output' | 'execution' | 'user' | 'tool_call' | 'tool_result'
  content: string
  nodeName?: string
  timestamp: number
  conversationId?: string
  toolPayload?: ToolResultPayload
}

export const ChatMessageValidation = {
  id: { required: true, pattern: /^\d+-[a-f0-9-]{36}$/ },
  type: { required: true, enum: ['output', 'execution', 'user', 'tool_call', 'tool_result'] as const },
  content: { required: true, minLength: 1 },
  timestamp: { required: true, type: 'number', min: 0 },
} as const

/**
 * Message grouping entity used to aggregate streaming chunks.
 */
export interface MessageGroup {
  id: string
  messages: ChatMessage[]
  type: 'output' | 'execution' | 'mixed'
  startTime: number
  endTime?: number
  isComplete: boolean
}

export const MessageGroupStates = {
  ACCUMULATING: 'accumulating',
  COMPLETED: 'completed',
  INTERRUPTED: 'interrupted',
} as const

/**
 * Conversation level metadata for an agent session.
 */
export enum SessionStatus {
  ACTIVE = 'active',
  WAITING_STREAM = 'waiting_stream',
  INTERRUPTED = 'interrupted',
  COMPLETED = 'completed',
  ERROR = 'error',
}

export interface ConversationSession {
  id: string
  title: string
  messageGroups: MessageGroup[]
  checkpointId?: string
  createdAt: number
  updatedAt: number
  status: SessionStatus
  userInput?: string
}

/**
 * Interrupt workflow types.
 */
export interface InterruptRequest {
  id: string
  content: string
  checkpointId: string
  conversationId: string
  options: InterruptOption[]
  timestamp: number
  currentStage?: string // 🔧 [STAGE_WORKFLOW] 新增：当前阶段信息
}

export interface InterruptOption {
  label: string
  value: string | number
  description?: string
}

export interface InterruptResponse {
  checkpointId: string
  conversationId: string
  choice: string | number
  timestamp: number
}

export type InterruptMessage = SSEMessage & {
  type: 'interrupt'
  content: string
  checkpoint_id: string
  conversation_id: string
}

/**
 * Stream level telemetry for UI feedback.
 */
export enum ConnectionStatus {
  IDLE = 'idle',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  STREAMING = 'streaming',
  DISCONNECTED = 'disconnected',
}

export interface StreamError {
  code: string
  message: string
  details?: unknown
  timestamp: number
  isRecoverable: boolean
}

export interface StreamState {
  isStreaming: boolean
  connectionStatus: ConnectionStatus
  error: StreamError | null
  lastUpdateTime: number
  retryCount: number
}

export interface MessageIndex {
  byId: Map<string, ChatMessage>
  byTimestamp: ChatMessage[]
  byType: {
    output: ChatMessage[]
    execution: ChatMessage[]
  }
}

export const MessageContentRules = {
  maxLength: 50000,
  minLength: 1,
  sanitize: true,
  trimWhitespace: true,
  validateMarkdown: false,
} as const

export const SessionValidationRules = {
  conversationIdPattern: /^[a-f0-9]{32}$/,
  maxDurationMs: 3_600_000,
  maxMessageGroups: 1000,
  maxMessagesPerGroup: 100,
} as const

export const MemoryLimits = {
  maxMessagesPerSession: 1000,
  cleanupThreshold: 800,
  keepRecentCount: 500,
  cleanupStrategy: 'LRU',
} as const

export const PersistenceConfig = {
  key: 'agent-chat-sessions',
  version: 1,
  maxSessions: 10,
  filter(session: ConversationSession) {
    return session.status === SessionStatus.COMPLETED
  },
} as const

/**
 * Type guards
 */
export function isSSEMessage(value: unknown): value is SSEMessage {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  const candidate = value as Record<string, unknown>
  if (typeof candidate.type !== 'string') {
    return false
  }

  return (
    ['start', 'output_msg', 'execution_msg', 'break', 'interrupt', 'tool_call', 'tool_result', 'complete'] as const
  ).includes(candidate.type as StreamMessageType)
}

export function isChatMessage(value: unknown): value is ChatMessage {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  const candidate = value as Record<string, unknown>
  return (
    typeof candidate.id === 'string' &&
    (candidate.type === 'output' || candidate.type === 'execution' || candidate.type === 'user'
      || candidate.type === 'tool_call' || candidate.type === 'tool_result') &&
    typeof candidate.content === 'string' &&
    typeof candidate.timestamp === 'number'
  )
}

export function isMessageGroup(value: unknown): value is MessageGroup {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  const candidate = value as Record<string, unknown>
  const validType =
    candidate.type === 'output' || candidate.type === 'execution' || candidate.type === 'mixed'
  const messages = candidate.messages

  return (
    typeof candidate.id === 'string' &&
    Array.isArray(messages) &&
    messages.every(isChatMessage) &&
    validType &&
    typeof candidate.startTime === 'number' &&
    typeof candidate.isComplete === 'boolean'
  )
}

export function isInterruptMessage(value: unknown): value is InterruptMessage {
  if (!isSSEMessage(value)) {
    return false
  }

  const candidate = value as SSEMessage
  return (
    candidate.type === 'interrupt' &&
    typeof candidate.content === 'string' &&
    typeof candidate.checkpoint_id === 'string' &&
    typeof candidate.conversation_id === 'string'
  )
}
