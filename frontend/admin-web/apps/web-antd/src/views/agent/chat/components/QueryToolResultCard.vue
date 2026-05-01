<script setup lang="ts">
import { computed } from 'vue';
import { Table, Tag } from 'ant-design-vue';
import { $t } from '@vben/locales';
import type { ToolResultPayload } from '#/views/agent/chat/types/chat';

defineOptions({ name: 'QueryToolResultCard' });

const props = defineProps<{
  payload: ToolResultPayload;
}>();

const hasError = computed(() => !!props.payload.error);
const hasData = computed(() => !!props.payload.data && !props.payload.error);

const previewRows = computed(() => {
  const data = props.payload.data;
  if (!data) return [];
  // If data has items array, show as table
  if (data.items && Array.isArray(data.items)) {
    return data.items.slice(0, 20);
  }
  // If data has preview (VCF text), show as single row
  if (data.preview && typeof data.preview === 'string') {
    return [{ preview: data.preview.slice(0, 2000) }];
  }
  // If data has count, show summary
  if (typeof data.count === 'number') {
    return [{ count: data.count, preview: data.preview?.slice(0, 1000) || $t('agent.chat.totalRecords', { count: data.count }) }];
  }
  return [data];
});

const columns = computed(() => {
  if (previewRows.value.length === 0) return [];
  return Object.keys(previewRows.value[0]).map((key) => ({
    title: key,
    dataIndex: key,
    key,
    ellipsis: true,
  }));
});
</script>

<template>
  <div class="tool-result-card">
    <div class="tool-result-header">
      <Tag :color="hasError ? 'red' : 'blue'">{{ payload.tool_name }}</Tag>
      <span v-if="payload.message" class="tool-result-msg">{{ payload.message }}</span>
    </div>

    <div v-if="hasError" class="tool-result-error">
      {{ payload.error }}
    </div>

    <div v-else-if="hasData && previewRows.length > 0" class="tool-result-body">
      <Table
        :columns="columns"
        :data-source="previewRows"
        :pagination="false"
        size="small"
        bordered
      />
      <div v-if="payload.data?.total && payload.data.total > 20" class="tool-result-truncated">
        {{ $t('agent.chat.previewTruncated', { previewCount: 20, totalCount: payload.data.total }) }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.tool-result-card {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: 8px;
  padding: 12px;
  margin: 4px 0;
}

.tool-result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.tool-result-msg {
  font-size: 13px;
  color: #666;
}

.tool-result-error {
  color: #ff4d4f;
  background: #fff2f0;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 13px;
}

.tool-result-body {
  overflow: auto;
}

.tool-result-truncated {
  text-align: center;
  color: #999;
  font-size: 12px;
  margin-top: 4px;
  padding: 4px 0;
}
</style>
