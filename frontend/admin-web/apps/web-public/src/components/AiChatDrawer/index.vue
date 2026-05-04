<script setup lang="ts">
import { ref, nextTick, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useRequest } from '@/composables/useRequest';

const props = defineProps<{ visible: boolean }>();
const emit = defineEmits<{ 'update:visible': [boolean] }>();

const route = useRoute();
const { post } = useRequest();

interface Message { role: 'user' | 'assistant'; content: string; }
const messages = ref<Message[]>([]);
const inputText = ref('');
const sending = ref(false);
const chatRef = ref<HTMLElement>();

// Simple localStorage persistence
const STORAGE_KEY = 'public-portal-chat-messages';
try {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) messages.value = JSON.parse(saved);
} catch {}

function saveMessages() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.value.slice(-50))); } catch {}
}

async function send() {
  const text = inputText.value.trim();
  if (!text || sending.value) return;

  messages.value.push({ role: 'user', content: text });
  inputText.value = '';
  sending.value = true;
  saveMessages();

  // Scroll to bottom
  await nextTick();
  if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight;

  try {
    // Call backend LLM endpoint (use existing agent chat endpoint)
    const resp = await post('/agent/chat', {
      message: text,
      session_id: 'public-portal',
    });
    const reply = resp?.reply || resp?.message || resp?.content || JSON.stringify(resp);
    messages.value.push({ role: 'assistant', content: String(reply) });
  } catch (e: any) {
    messages.value.push({ role: 'assistant', content: 'Sorry, AI service is currently unavailable.' });
  } finally {
    sending.value = false;
    saveMessages();
    await nextTick();
    if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight;
  }
}

function clearChat() {
  messages.value = [];
  saveMessages();
}
</script>
<template>
  <el-drawer
    :model-value="visible"
    @update:model-value="emit('update:visible', $event)"
    title="AI Assistant"
    size="420px"
    direction="rtl"
  >
    <div style="display:flex;flex-direction:column;height:100%;">
      <!-- Messages -->
      <div ref="chatRef" style="flex:1;overflow-y:auto;padding:8px 0;">
        <div v-for="(msg, i) in messages" :key="i" style="margin-bottom:12px;">
          <div v-if="msg.role === 'user'" style="text-align:right;">
            <span style="display:inline-block;background:#409eff;color:#fff;padding:8px 14px;border-radius:12px 12px 0 12px;max-width:80%;font-size:13px;text-align:left;">{{ msg.content }}</span>
          </div>
          <div v-else style="text-align:left;">
            <span style="display:inline-block;background:#f0f2f5;color:#303133;padding:8px 14px;border-radius:12px 12px 12px 0;max-width:85%;font-size:13px;white-space:pre-wrap;word-break:break-word;">{{ msg.content }}</span>
          </div>
        </div>
        <div v-if="messages.length === 0" style="text-align:center;color:#bbb;padding:40px 0;">
          Ask me anything about the datasets!
        </div>
        <div v-if="sending" style="text-align:left;color:#999;font-size:12px;">Thinking...</div>
      </div>

      <!-- Input -->
      <div style="display:flex;gap:8px;padding-top:8px;border-top:1px solid #eee;">
        <el-input v-model="inputText" placeholder="Ask about datasets..." @keyup.enter="send" :disabled="sending" />
        <el-button type="primary" @click="send" :loading="sending">Send</el-button>
      </div>
      <el-button text size="small" @click="clearChat" style="margin-top:4px;">Clear chat</el-button>
    </div>
  </el-drawer>
</template>
