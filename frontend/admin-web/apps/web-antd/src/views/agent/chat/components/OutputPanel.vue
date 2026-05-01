<script setup lang="ts">
import type { BubbleListProps, BubbleListRef } from 'ant-design-x-vue';

import type { MessageGroup } from '#/views/agent/chat/types/chat';

import { computed, h, nextTick, ref, watch } from 'vue';

import { Button, Flex } from 'ant-design-vue';
import { BubbleList } from 'ant-design-x-vue';

import { useAgentChatStore } from '#/store/modules/agent-chat';
import { useMarkdownRender } from '#/views/agent/chat/composables/useMarkdownRender';
import { isPrimaryOption } from '#/views/agent/chat/utils/parseInterruptOptions';
import QueryToolResultCard from './QueryToolResultCard.vue';

const props = defineProps<{
  isStreaming: boolean;
  messageGroups: MessageGroup[];
}>();

const emit = defineEmits<{
  interruptSelect: [value: string];
}>();

const store = useAgentChatStore();
const listRef = ref<BubbleListRef>();
const panelRef = ref<HTMLDivElement>();
const { messageRender } = useMarkdownRender();

const outputMessages = computed(() => {
  return props.messageGroups.flatMap((group) =>
    group.messages.filter((message) => message.type === 'output' || message.type === 'user'),
  );
});

const toolMessages = computed(() => {
  return props.messageGroups.flatMap((group) =>
    group.messages.filter(
      (message) => message.type === 'tool_result' || message.type === 'tool_call',
    ),
  );
});

const lastMessageId = computed(() => outputMessages.value.at(-1)?.id ?? null);

const rolesConfig = computed<BubbleListProps['roles']>(() => ({
  ai: {
    placement: 'start',
    variant: 'filled',
    shape: 'round',
    styles: {
      content: {
        maxWidth: '85%',
        borderRadius: '12px',
        padding: '12px 16px',
      },
    },
  },
  interrupt: {
    placement: 'start',
    variant: 'outlined',
    shape: 'round',
    styles: {
      content: {
        maxWidth: '85%',
        borderRadius: '12px',
        padding: '12px 16px',
      },
    },
    footer: (content) => {
      if (!store.currentInterrupt) {
        return null;
      }

      const options = store.currentInterrupt.options;
      if (!options || options.length === 0) {
        return null;
      }

      return h(Flex, { gap: 'small', wrap: 'wrap' }, () =>
        options.map((opt) =>
          h(
            Button,
            {
              type: isPrimaryOption(opt.label) ? 'primary' : 'default',
              onClick: () => emit('interruptSelect', opt.value),
            },
            () => opt.label,
          ),
        ),
      );
    },
  },
  user: {
    placement: 'end',
    variant: 'filled',
    shape: 'round',
    styles: {
      content: {
        maxWidth: '85%',
        borderRadius: '12px',
        padding: '12px 16px',
        backgroundColor: '#1890ff',
        color: '#ffffff',
      },
    },
  },
}));

const bubbleItems = computed(() => {
  const items = outputMessages.value.map((message) => {
    const isUserMessage = message.type === 'user';

    const item: any = {
      key: message.id,
      content: message.content,
      placement: isUserMessage ? ('end' as const) : ('start' as const),
      role: isUserMessage ? 'user' : 'ai',
      typing: !isUserMessage && props.isStreaming && message.id === lastMessageId.value,
    };

    // 只为 AI 消息添加 markdown 渲染器
    if (!isUserMessage) {
      item.messageRender = messageRender;
    }

    return item;
  });

  if (props.isStreaming && items.length === 0) {
    items.push({
      key: 'output-typing',
      content: '',
      placement: 'start' as const,
      loading: true,
    });
  }

  if (store.currentInterrupt) {
    items.push({
      key: store.currentInterrupt.id,
      content: store.currentInterrupt.content,
      placement: 'start' as const,
      role: 'interrupt',
      messageRender,
    });
  }

  return items;
});

function scrollToBottom() {
  if (!panelRef.value) {
    return
  }

  // 查找真正的滚动容器 - BubbleList 内部的 .ant-bubble-list 元素
  const bubbleListElement = panelRef.value.querySelector('.ant-bubble-list') as HTMLElement | null

  if (bubbleListElement) {
    bubbleListElement.scrollTop = bubbleListElement.scrollHeight
  }
}

watch(
  bubbleItems,
  async () => {
    await nextTick()
    scrollToBottom()
  },
  { deep: true },
)

// Also watch for interrupt state changes
watch(
  () => store.currentInterrupt,
  async () => {
    await nextTick()
    scrollToBottom()
  },
)
</script>

<template>
  <div ref="panelRef" class="chat-panel">
    <div class="chat-panel__tools">
      <template v-for="msg in toolMessages" :key="msg.id">
        <QueryToolResultCard
          v-if="msg.type === 'tool_result' && msg.toolPayload"
          :payload="msg.toolPayload"
        />
        <div v-else-if="msg.type === 'tool_call'" class="tool-call-status">
          {{ $t('agent.chat.callingTool', { toolName: msg.toolPayload?.tool_name || 'tool' }) }}
        </div>
      </template>
    </div>
    <BubbleList
      ref="listRef"
      class="chat-panel__list"
      :items="bubbleItems"
      :roles="rolesConfig"
      :auto-scroll="false"
      :style="{ flex: '1 1 0%', minHeight: '0' }"
    />
  </div>
</template>

<style scoped>
.chat-panel {
  display: flex;
  flex: 1;
  padding: 16px;
  overflow: hidden auto;
}

.chat-panel__list {
  flex: 1;
  padding: 16px;
}

.chat-panel__tools {
  padding: 4px 16px 0;
}

.tool-call-status {
  color: #1677ff;
  font-style: italic;
  padding: 4px 8px;
  font-size: 13px;
}
</style>
