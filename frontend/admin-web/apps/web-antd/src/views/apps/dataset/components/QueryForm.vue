<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import {
  Button, Select, Input, Tag, Space,
} from 'ant-design-vue';
import type { DatasetVersionQueryCapabilitiesResult } from '#/api/apps/dataset';
import { $t } from '@vben/locales';

const props = defineProps<{
  capabilities: DatasetVersionQueryCapabilitiesResult | null;
  loading: boolean;
}>();

const emit = defineEmits<{
  execute: [operation: string, params: Record<string, any>];
}>();

const operation = ref('');
const paramsText = ref('{}');
const executing = ref(false);

const operationOptions = computed(() =>
  (props.capabilities?.query_adapter?.supported_operations || []).map(op => ({
    label: op,
    value: op,
  })),
);

const defaultParams: Record<string, Record<string, any>> = {
  fetch: { seq_id: '', start: 1, end: 100 },
  genes_list: { max_records: 100 },
  samples_list: { max_records: 100 },
  matrix_slice: { data_type: 'count', genes: [], samples: [] },
  query: { regions: [] },
  region_features: { region: '', feature_type: 'gene', limit: 100 },
  gene_search: { keyword: '', page: 1, page_size: 20 },
  gene_list: { page: 1, page_size: 20 },
  gene_info: { gene_id: '' },
  transcript_list: { page: 1, page_size: 20 },
  term_lookup: { term_source: 'go', keyword: '', limit: 20 },
  term_gene_list: { term_source: 'go', term_id: '', page: 1, size: 20 },
  batch_fetch: { regions: [{ seq_id: '', start: 1, end: 100 }] },
  dataset_summary: {},
  trait_list: { limit: 20 },
  trait_search: { keyword: '', limit: 20 },
  trait_values: { trait: '', timepoint: '', limit: 20 },
  subject_list: { limit: 20 },
  subject_detail: { subject_id: '' },
  trial_list: { limit: 20 },
  trial_detail: { trial_id: '' },
  plot_list: { trial_id: '', limit: 20 },
  plot_detail: { plot_id: '' },
  multi_trait_query: { trait_codes: [], plot_ids: [] },
};

function loadExample() {
  if (!operation.value) return;
  // Prefer backend-provided examples from the adapter
  const backendExamples = props.capabilities?.query_adapter?.examples;
  const backendExample = backendExamples?.[operation.value];
  if (backendExample?.params) {
    paramsText.value = JSON.stringify(backendExample.params, null, 2);
    return;
  }
  const example = defaultParams[operation.value];
  paramsText.value = example ? JSON.stringify(example, null, 2) : '{}';
}

watch(operation, () => {
  loadExample();
});

async function handleExecute() {
  let params: Record<string, any>;
  try {
    params = JSON.parse(paramsText.value);
  } catch {
    params = {};
  }
  executing.value = true;
  try {
    emit('execute', operation.value, params);
  } finally {
    executing.value = false;
  }
}
</script>

<template>
  <div>
    <div v-if="!capabilities?.query_adapter?.supported_operations?.length" style="color: #888; padding: 20px; text-align: center;">
      {{ $t('dataset.query.noQueryActionForVersion') }}
    </div>

    <template v-else>
      <div style="margin-bottom: 8px; font-size: 12px; color: #888;">{{ $t('dataset.query.fileAccessible') }}</div>
      <Tag :color="capabilities?.file_access?.exists_on_server ? 'success' : 'warning'" style="margin-bottom: 12px;">
        {{ capabilities?.file_access?.exists_on_server ? $t('grn.relationship.yes') : $t('grn.relationship.no') }}
      </Tag>

      <div style="display: flex; flex-direction: column; gap: 8px;">
        <label>
          <span style="font-size: 12px;">{{ $t('dataset.query.selectAction') }}</span>
          <Select
            v-model:value="operation"
            :options="operationOptions"
            :placeholder="$t('dataset.query.selectAction')"
            style="width: 100%;"
          />
        </label>

        <label>
          <span style="font-size: 12px;">{{ $t('dataset.query.paramJson') }}</span>
          <Input.TextArea
            v-model:value="paramsText"
            :rows="12"
            :placeholder="$t('dataset.query.paramJsonPlaceholder')"
          />
        </label>

        <Space>
          <Button type="primary" :loading="executing" @click="handleExecute">{{ $t('dataset.query.execQuery') }}</Button>
          <Button :disabled="!operation" @click="loadExample">{{ $t('dataset.query.loadExampleParams') }}</Button>
        </Space>
      </div>
    </template>
  </div>
</template>
