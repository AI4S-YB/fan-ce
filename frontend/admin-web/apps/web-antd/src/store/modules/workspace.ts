import { acceptHMRUpdate, defineStore } from 'pinia';

import { store } from '#/store';

// ---- Data Models ----

export interface WorkspaceMessage {
  id: string;
  role: 'assistant' | 'user';
  type: 'text' | 'tool_call' | 'tool_result' | 'code_result';
  content: string;
  timestamp: number;
}

export interface WorkspaceMessageGroup {
  id: string;
  messages: WorkspaceMessage[];
  startTime: number;
  isComplete: boolean;
}

export interface WorkspaceSession {
  id: string;
  title: string;
  messageGroups: WorkspaceMessageGroup[];
  createdAt: number;
  updatedAt: number;
}

export interface WorkspaceChatState {
  sessions: WorkspaceSession[];
  currentSessionId: null | string;
  streaming: boolean;
}

// ---- Helpers ----

function makeId(): string {
  return Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 11);
}

function createEmptyGroup(startTime?: number): WorkspaceMessageGroup {
  return {
    id: makeId(),
    messages: [],
    startTime: startTime ?? Date.now(),
    isComplete: false,
  };
}

// ---- Store ----

export const useWorkspaceStore = defineStore('workspace-chat', {
  state: (): WorkspaceChatState => ({
    sessions: [],
    currentSessionId: null,
    streaming: false,
  }),

  getters: {
    currentSession: (state): WorkspaceSession | null => {
      if (!state.currentSessionId) return null;
      return state.sessions.find((s) => s.id === state.currentSessionId) ?? null;
    },

    sortedSessions: (state): WorkspaceSession[] => {
      return [...state.sessions].sort((a, b) => b.updatedAt - a.updatedAt);
    },
  },

  actions: {
    // ---- Session CRUD ----

    createSession(): WorkspaceSession {
      const now = Date.now();
      const session: WorkspaceSession = {
        id: makeId(),
        title: '新对话',
        messageGroups: [],
        createdAt: now,
        updatedAt: now,
      };
      this.sessions.push(session);
      this.currentSessionId = session.id;
      return session;
    },

    ensureSession(): WorkspaceSession {
      if (this.currentSession) return this.currentSession;
      return this.createSession();
    },

    switchSession(id: string) {
      this.currentSessionId = id;
    },

    renameSession(id: string, title: string) {
      const s = this.sessions.find((x) => x.id === id);
      if (s) {
        s.title = title;
        s.updatedAt = Date.now();
      }
    },

    deleteSession(id: string) {
      const idx = this.sessions.findIndex((s) => s.id === id);
      if (idx === -1) return;
      this.sessions.splice(idx, 1);
      if (this.currentSessionId === id) {
        if (this.sessions.length > 0) {
          this.currentSessionId = this.sessions[0]!.id;
        } else {
          this.createSession();
        }
      }
    },

    // ---- Message management ----

    addMessage(message: WorkspaceMessage) {
      const session = this.ensureSession();
      let group = session.messageGroups[session.messageGroups.length - 1];

      if (!group || group.isComplete) {
        group = createEmptyGroup(message.timestamp);
        session.messageGroups.push(group);
      }

      group.messages.push(message);
      group.isComplete = false;

      // Auto-name session from first user message
      if (session.title === '新对话' && message.role === 'user' && message.content) {
        session.title = message.content.slice(0, 30);
      }

      session.updatedAt = Date.now();
      return group;
    },

    closeCurrentGroup() {
      const session = this.currentSession;
      if (!session) return;
      const group = session.messageGroups[session.messageGroups.length - 1];
      if (group) {
        group.isComplete = true;
      }
    },

    clearCurrentSession() {
      const session = this.currentSession;
      if (!session) return;
      session.messageGroups = [];
      session.updatedAt = Date.now();
    },

    // ---- Streaming ----

    setStreaming(val: boolean) {
      this.streaming = val;
    },
  },

  // ---- localStorage persistence ----
  persist: {
    key: 'workspace-chat',
    storage: localStorage,
  },
});

const hot = import.meta.hot;
if (hot) {
  hot.accept(acceptHMRUpdate(useWorkspaceStore, hot));
}

export function useWorkspaceStoreWithOut() {
  return useWorkspaceStore(store);
}
