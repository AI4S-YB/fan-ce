<script setup lang="ts">
import { ref, nextTick } from 'vue';
import { renderMarkdown } from '@/composables/useMarkdown';

interface Message { role: 'user' | 'assistant' | 'tool'; content: string; tool?: string; }
interface Session { id: string; title: string; messages: Message[]; createdAt: number; }

const SESSIONS_KEY = 'public-chat-sessions';
const ACTIVE_KEY = 'public-chat-active';

// Generate anonymous session ID
function genId(): string {
  return 'sess_' + Math.random().toString(36).slice(2, 10);
}

// Load sessions from localStorage
function loadSessions(): Session[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function saveSessions(sessions: Session[]) {
  try {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions.slice(-20)));
  } catch {}
}

const sessions = ref<Session[]>(loadSessions());
const activeId = ref<string>(localStorage.getItem(ACTIVE_KEY) || '');

// Init: ensure at least one session
if (sessions.value.length === 0) {
  const id = genId();
  sessions.value.push({ id, title: 'New Chat', messages: [], createdAt: Date.now() });
  activeId.value = id;
}
if (!sessions.value.find(s => s.id === activeId.value)) {
  activeId.value = sessions.value[0].id;
}

const activeSession = ref<Session>(sessions.value.find(s => s.id === activeId.value)!);

const inputText = ref('');
const sending = ref(false);
const chatRef = ref<HTMLElement>();

function switchSession(id: string) {
  activeId.value = id;
  localStorage.setItem(ACTIVE_KEY, id);
  activeSession.value = sessions.value.find(s => s.id === id)!;
  nextTick(() => { if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight; });
}

function newSession() {
  const id = genId();
  const s: Session = { id, title: 'New Chat', messages: [], createdAt: Date.now() };
  sessions.value.unshift(s);
  saveSessions(sessions.value);
  switchSession(id);
}

function deleteSession(id: string) {
  const idx = sessions.value.findIndex(s => s.id === id);
  if (idx === -1) return;
  sessions.value.splice(idx, 1);
  saveSessions(sessions.value);
  if (activeId.value === id) {
    if (sessions.value.length === 0) {
      const newId = genId();
      sessions.value.push({ id: newId, title: 'New Chat', messages: [], createdAt: Date.now() });
    }
    switchSession(sessions.value[0].id);
  }
}

function persistActive() {
  const s = activeSession.value;
  if (s.messages.length === 1 && s.title === 'New Chat') {
    s.title = s.messages[0].content.slice(0, 30);
  }
  saveSessions(sessions.value);
}

async function send() {
  const text = inputText.value.trim();
  if (!text || sending.value) return;

  const s = activeSession.value;
  s.messages.push({ role: 'user', content: text });
  inputText.value = '';
  sending.value = true;
  persistActive();

  await nextTick();
  if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight;

  try {
    const apiBase = import.meta.env.VITE_API_BASE_URL || '/api/v1';

    const resp = await fetch(`${apiBase}/public/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: s.messages.map(m => ({ role: m.role, content: m.content })),
      }),
    });

    if (!resp.ok) {
      const errText = resp.status === 429
        ? 'Too many requests. Please wait a moment and try again.'
        : resp.status === 403
          ? 'AI chat is currently disabled.'
          : `Server error (${resp.status})`;
      s.messages.push({ role: 'assistant', content: errText });
      sending.value = false;
      persistActive();
      return;
    }

    const reader = resp.body?.getReader();
    if (!reader) {
      s.messages.push({ role: 'assistant', content: 'No response stream available.' });
      sending.value = false;
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';
    let assistantContent = '';
    let toolInfo: string[] = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const event = JSON.parse(line.slice(6));
          if (event.type === 'output_msg') {
            assistantContent += event.content || '';
            // Update the last assistant message in-place
            const last = s.messages[s.messages.length - 1];
            if (last && last.role === 'assistant') {
              last.content = assistantContent + (toolInfo.length ? '\n\n' + toolInfo.join('\n') : '');
            } else {
              s.messages.push({ role: 'assistant', content: assistantContent });
            }
          } else if (event.type === 'tool_call') {
            toolInfo.push(`🔧 Calling ${event.tool_name}...`);
          } else if (event.type === 'tool_result') {
            const idx = toolInfo.findIndex(t => t.includes(event.tool_name));
            if (idx >= 0) toolInfo[idx] = `✅ ${event.tool_name} done`;
          } else if (event.type === 'error') {
            s.messages.push({ role: 'assistant', content: `❌ ${event.message}` });
          }
          await nextTick();
          if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight;
        } catch {}
      }
    }
  } catch (e: any) {
    s.messages.push({ role: 'assistant', content: 'Network error. Please check your connection.' });
  } finally {
    sending.value = false;
    persistActive();
    await nextTick();
    if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight;
  }
}
</script>

<template>
  <div style="display:flex;height:calc(100vh - 52px - 48px - 48px);">
    <!-- Sidebar -->
    <div style="width:240px;border-right:1px solid #e5e5e5;padding:12px;overflow-y:auto;flex-shrink:0;">
      <el-button size="small" type="primary" style="width:100%;margin-bottom:12px;"
        @click="newSession">+ New Chat</el-button>
      <div v-for="s in sessions" :key="s.id"
        style="padding:8px;margin-bottom:4px;border-radius:6px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;"
        :style="{ background: activeId === s.id ? '#ecf5ff' : 'transparent' }"
        @click="switchSession(s.id)">
        <span style="font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;">
          {{ s.title }}
        </span>
        <el-button v-if="sessions.length > 1" text size="small" type="danger"
          @click.stop="deleteSession(s.id)" style="margin-left:4px;">✕</el-button>
      </div>
    </div>

    <!-- Chat Area -->
    <div style="flex:1;display:flex;flex-direction:column;padding:0 20px;">
      <div ref="chatRef" style="flex:1;overflow-y:auto;padding:12px 0;">
        <div v-if="activeSession.messages.length === 0" style="text-align:center;color:#bbb;padding:60px 0;">
          <p style="font-size:16px;">Ask me anything about public datasets</p>
          <p style="font-size:13px;">e.g. "What datasets are available?" or "Search for rose genes"</p>
        </div>
        <div v-for="(msg, i) in activeSession.messages" :key="i" style="margin-bottom:14px;">
          <div v-if="msg.role === 'user'" style="text-align:right;">
            <span style="display:inline-block;background:#409eff;color:#fff;padding:8px 14px;border-radius:12px 12px 0 12px;max-width:75%;font-size:13px;text-align:left;">{{ msg.content }}</span>
          </div>
          <div v-else style="text-align:left;">
            <span class="chat-bubble" style="display:inline-block;background:#f0f2f5;color:#303133;padding:8px 14px;border-radius:12px 12px 12px 0;max-width:85%;font-size:13px;white-space:pre-wrap;word-break:break-word;line-height:1.6;"
              v-html="renderMarkdown(msg.content)"></span>
          </div>
        </div>
        <div v-if="sending" style="text-align:left;color:#999;font-size:12px;padding:4px 0;">Thinking...</div>
      </div>

      <!-- Input -->
      <div style="display:flex;gap:8px;padding:12px 0;border-top:1px solid #eee;">
        <el-input v-model="inputText" placeholder="Ask about public datasets..."
          @keyup.enter="send" :disabled="sending" size="large" />
        <el-button type="primary" @click="send" :loading="sending" size="large">Send</el-button>
      </div>
    </div>
  </div>
</template>

<style>
/* Markdown content inside chat bubbles */
.chat-bubble h1 { font-size: 18px; margin: 8px 0 4px; }
.chat-bubble h2 { font-size: 16px; margin: 8px 0 4px; }
.chat-bubble h3 { font-size: 14px; margin: 6px 0 3px; }
.chat-bubble h4 { font-size: 13px; margin: 4px 0 2px; }
.chat-bubble p { margin: 4px 0; }
.chat-bubble ul, .chat-bubble ol { margin: 4px 0; padding-left: 18px; }
.chat-bubble li { margin: 2px 0; }
.chat-bubble code { background: #e8e8e8; padding: 1px 4px; border-radius: 3px; font-size: 12px; }
.chat-bubble pre { background: #1e1e1e; color: #d4d4d4; padding: 8px 12px; border-radius: 6px; overflow-x: auto; font-size: 12px; margin: 6px 0; }
.chat-bubble pre code { background: none; padding: 0; color: inherit; }
.chat-bubble blockquote { border-left: 3px solid #409eff; padding-left: 8px; margin: 6px 0; color: #666; }
.chat-bubble table { border-collapse: collapse; margin: 6px 0; width: 100%; font-size: 12px; }
.chat-bubble th, .chat-bubble td { border: 1px solid #ddd; padding: 4px 8px; text-align: left; }
.chat-bubble th { background: #f5f7fa; font-weight: 600; }
.chat-bubble a { color: #409eff; }
.chat-bubble hr { border: none; border-top: 1px solid #e5e5e5; margin: 8px 0; }
.chat-bubble strong { font-weight: 600; }
</style>
