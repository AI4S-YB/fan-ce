<script setup lang="ts">
import type { BubbleListProps, BubbleListRef } from 'ant-design-x-vue';

import type { MessageGroup } from '#/views/agent/chat/types/chat';

import { computed, nextTick, ref, watch } from 'vue';

import { BubbleList } from 'ant-design-x-vue';

import { useMarkdownRender } from '#/views/agent/chat/composables/useMarkdownRender';

const props = defineProps<{
  isStreaming: boolean;
  messageGroups: MessageGroup[];
}>();

const listRef = ref<BubbleListRef>();
const panelRef = ref<HTMLDivElement>();
const { messageRender } = useMarkdownRender();

const executionMessages = computed(() =>
  props.messageGroups.flatMap((group) =>
    group.messages.filter((message) => message.type === 'execution'),
  ),
);

const lastMessageId = computed(
  () => executionMessages.value.at(-1)?.id ?? null,
);

const rolesConfig = computed<BubbleListProps['roles']>(() => ({
  user: {
    placement: 'end',
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
}));

const bubbleItems = computed(() => {
  const items = executionMessages.value.map((message) => ({
    key: message.id,
    content: message.content,
    placement: 'end' as const,
    role: 'user',
    messageRender,
    typing: props.isStreaming && message.id === lastMessageId.value,
  }));

  if (props.isStreaming && items.length === 0) {
    items.push({
      key: 'execution-typing',
      content: '',
      placement: 'end' as const,
      loading: true,
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
    await nextTick();
    scrollToBottom();
  },
  { deep: true },
);
</script>

<template>
  <div ref="panelRef" class="chat-panel">
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
</style>
