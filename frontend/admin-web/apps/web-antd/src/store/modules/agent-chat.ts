import { acceptHMRUpdate, defineStore } from 'pinia'

import type {
  ChatMessage,
  ConversationSession,
  InterruptRequest,
  MessageGroup,
  StreamError,
  StreamState,
} from '#/views/agent/chat/types/chat'
import { ConnectionStatus, SessionStatus } from '#/views/agent/chat/types/chat'
import { createTimestampedId } from '#/views/agent/chat/services/id'
import { store } from '#/store'

interface StartSessionPayload {
  conversationId?: string
  title?: string
  userInput?: string
  checkpointId?: string
  createdAt?: number
  status?: SessionStatus
}

interface NewGroupOptions {
  type?: MessageGroup['type']
  startTime?: number
  markPreviousComplete?: boolean
}

interface AgentChatState {
  currentSession: ConversationSession | null
  messageGroups: MessageGroup[]
  streamState: StreamState
  currentInterrupt: InterruptRequest | null
  needsUserCommand: boolean
  pendingContinuation: {
    conversationId: string
    checkpointId: string
  } | null
  // 🔧 [STAGE_WORKFLOW] 新增：阶段工作流状态
  currentStage: string | null
  pendingNextStage: {
    nextStage: string
    conversationId: string
    checkpointId: string
  } | null
}

const INITIAL_STREAM_STATE: StreamState = {
  isStreaming: false,
  connectionStatus: ConnectionStatus.IDLE,
  error: null,
  lastUpdateTime: 0,
  retryCount: 0,
}

function createEmptyGroup(startTime: number, type: MessageGroup['type'] = 'mixed'): MessageGroup {
  return {
    id: createTimestampedId(),
    messages: [],
    type,
    startTime,
    isComplete: false,
  }
}

export const useAgentChatStore = defineStore('agent-chat', {
  state: (): AgentChatState => ({
    currentSession: null,
    messageGroups: [],
    streamState: { ...INITIAL_STREAM_STATE },
    currentInterrupt: null,
    needsUserCommand: false,
    pendingContinuation: null,
    currentStage: null,  // 🔧 [STAGE_WORKFLOW] 新增
    pendingNextStage: null,  // 🔧 [STAGE_WORKFLOW] 新增
  }),

  getters: {
    sessionStatus: (state) => state.currentSession?.status ?? null,
    isActiveSession: (state) => state.currentSession?.status === SessionStatus.ACTIVE,
    messageGroupCount: (state) => state.messageGroups.length,
    totalMessageCount: (state) =>
      state.messageGroups.reduce((count, group) => count + group.messages.length, 0),
  },

  actions: {
    startNewSession(payload: StartSessionPayload = {}) {
      const now = payload.createdAt ?? Date.now()
      const groups: MessageGroup[] = []
      const session: ConversationSession = {
        id: payload.conversationId ?? createTimestampedId(),
        title: payload.title ?? 'New Conversation',
        messageGroups: groups,
        checkpointId: payload.checkpointId,
        createdAt: now,
        updatedAt: now,
        status: payload.status ?? SessionStatus.WAITING_STREAM,
        userInput: payload.userInput,
      }

      this.currentSession = session
      this.messageGroups = groups
      this.streamState = {
        ...INITIAL_STREAM_STATE,
        connectionStatus: ConnectionStatus.CONNECTING,
        lastUpdateTime: now,
      }
    },

    addMessageToCurrentGroup(message: ChatMessage) {
      if (!this.currentSession) {
        this.startNewSession({ conversationId: message.conversationId, userInput: message.content })
      }

      if (!this.currentSession) {
        return
      }

      let group = this.messageGroups[this.messageGroups.length - 1]

      if (!group || group.isComplete) {
        group = this.startNewGroup({ type: message.type, startTime: message.timestamp })
      }

      if (!group) {
        return
      }

      group.messages.push(message)

      if (group.messages.length === 1) {
        group.type = message.type
        group.startTime = message.timestamp
      } else if (group.type !== message.type) {
        group.type = 'mixed'
      }

      group.endTime = message.timestamp
      group.isComplete = false

      // 强制触发响应式更新：创建新数组引用
      this.messageGroups = [...this.messageGroups]
      this.currentSession.messageGroups = this.messageGroups
      this.currentSession.updatedAt = Date.now()
    },

    startNewGroup(options: NewGroupOptions = {}) {
      if (!this.currentSession) {
        return undefined
      }

      const now = options.startTime ?? Date.now()
      const previous = this.messageGroups[this.messageGroups.length - 1]

      if (previous && !previous.isComplete && options.markPreviousComplete !== false) {
        previous.isComplete = true
        previous.endTime = now
      }

      const nextGroup = createEmptyGroup(now, options.type ?? 'mixed')
      this.messageGroups.push(nextGroup)
      this.currentSession.messageGroups = this.messageGroups
      this.currentSession.updatedAt = now

      return nextGroup
    },

    updateStreamState(patch: Partial<StreamState>) {
      const now = patch.lastUpdateTime ?? Date.now()

      this.streamState = {
        ...this.streamState,
        ...patch,
        lastUpdateTime: now,
      }

      if (!this.currentSession) {
        return
      }

      if (patch.error) {
        this.currentSession.status = SessionStatus.ERROR
      } else if (patch.connectionStatus === ConnectionStatus.CONNECTING) {
        this.currentSession.status = SessionStatus.WAITING_STREAM
      } else if (patch.connectionStatus === ConnectionStatus.STREAMING) {
        this.currentSession.status = SessionStatus.ACTIVE
      } else if (patch.connectionStatus === ConnectionStatus.DISCONNECTED && !this.streamState.isStreaming) {
        this.currentSession.status = SessionStatus.COMPLETED
      }

      this.currentSession.updatedAt = now
    },

    registerStreamError(error: StreamError) {
      this.updateStreamState({
        error,
        isStreaming: false,
        connectionStatus: ConnectionStatus.DISCONNECTED,
        lastUpdateTime: error.timestamp,
      })
    },

    setInterrupt(interrupt: InterruptRequest) {
      this.currentInterrupt = interrupt
      if (this.currentSession) {
        this.currentSession.status = SessionStatus.INTERRUPTED
        this.currentSession.checkpointId = interrupt.checkpointId
        this.currentSession.updatedAt = Date.now()
      }
    },

    clearInterrupt() {
      this.currentInterrupt = null
      if (this.currentSession && this.currentSession.status === SessionStatus.INTERRUPTED) {
        this.currentSession.status = SessionStatus.ACTIVE
        this.currentSession.updatedAt = Date.now()
      }
    },

    setNeedsUserCommand(needs: boolean) {
      this.needsUserCommand = needs
    },

    setPendingContinuation(conversationId: string, checkpointId: string) {
      this.pendingContinuation = { conversationId, checkpointId }
    },

    clearPendingContinuation() {
      this.pendingContinuation = null
    },

    continueSession(conversationId: string, checkpointId: string) {
      if (!this.currentSession) {
        return
      }

      this.currentSession.id = conversationId
      this.currentSession.checkpointId = checkpointId
      this.currentSession.status = SessionStatus.ACTIVE
      this.currentSession.updatedAt = Date.now()

      this.streamState = {
        ...this.streamState,
        connectionStatus: ConnectionStatus.CONNECTING,
        lastUpdateTime: Date.now(),
      }
    },

    // 🔧 [STAGE_WORKFLOW] 新增：设置当前阶段
    setCurrentStage(stage: string | null) {
      this.currentStage = stage
    },

    // 🔧 [STAGE_WORKFLOW] 新增：保存待执行的下一阶段
    setPendingNextStage(nextStage: string, conversationId: string, checkpointId: string) {
      this.pendingNextStage = { nextStage, conversationId, checkpointId }
    },

    // 🔧 [STAGE_WORKFLOW] 新增：清除待执行的下一阶段
    clearPendingNextStage() {
      this.pendingNextStage = null
    },

    resetState() {
      this.currentSession = null
      this.messageGroups = []
      this.streamState = { ...INITIAL_STREAM_STATE }
      this.currentInterrupt = null
      this.needsUserCommand = false
      this.pendingContinuation = null
      this.currentStage = null  // 🔧 [STAGE_WORKFLOW] 新增
      this.pendingNextStage = null  // 🔧 [STAGE_WORKFLOW] 新增
    },
  },
})

const hot = import.meta.hot
if (hot) {
  hot.accept(acceptHMRUpdate(useAgentChatStore, hot))
}

export function useAgentChatStoreWithOut() {
  return useAgentChatStore(store)
}
