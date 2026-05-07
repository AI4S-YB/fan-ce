<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useRequest } from '@/composables/useRequest';

const route = useRoute();
const { post } = useRequest();

const toolName = computed(() => route.params.name as string);
const geneId = ref((route.query.gene_id as string) || '');
const geneIds = ref((route.query.gene_ids as string) || '');
const datasetId = ref(Number(route.query.dataset_id) || 0);
const seqType = ref((route.query.type as string) || 'gene');
const prefillSeq = ref((route.query.seq as string) || '');

const inputSeq = ref('');
const inputLabel = ref('Sequence Input (FASTA format)');
const loading = ref(false);

onMounted(async () => {
  if (prefillSeq.value) {
    inputSeq.value = prefillSeq.value;
    return;
  }
  if (geneIds.value && datasetId.value) {
    // Multi-gene mode
    const ids = geneIds.value.split(',').map(s => s.trim()).filter(Boolean);
    inputLabel.value = `Sequences from ${ids.length} genes (${seqType.value})`;
    loading.value = true;
    try {
      const r: any = await post('/public/dataset/sequence/batch', {
        dataset_id: datasetId.value, sequence_type: seqType.value, inputs: ids,
      });
      inputSeq.value = r?.sequences
        ?.map((s: any) => `>${s.input}\n${s.sequence || ''}`)
        .join('\n') || '';
    } finally { loading.value = false; }
    return;
  }
  if (geneId.value && datasetId.value) {
    // Single gene mode
    inputLabel.value = `${seqType.value} sequence for ${geneId.value}`;
    loading.value = true;
    try {
      const r: any = await post('/public/dataset/sequence/batch', {
        dataset_id: datasetId.value, sequence_type: seqType.value, inputs: [geneId.value],
      });
      const seq = r?.sequences?.[0]?.sequence || '';
      inputSeq.value = `>${geneId.value}\n${seq}`;
    } finally { loading.value = false; }
  }
});
</script>

<template>
  <div style="padding:24px;max-width:960px;">
    <h2 style="margin-top:0;">{{ toolName }}</h2>
    <p v-if="geneId" style="color:#888;margin-bottom:8px;">
      Gene: <strong>{{ geneId }}</strong>
      <span v-if="geneIds">&middot; Batch: {{ geneIds.split(',').length }} genes</span>
      &middot; Type: <strong>{{ seqType }}</strong>
    </p>
    <div style="margin-bottom:4px;font-weight:500;">{{ inputLabel }}</div>
    <el-input
      v-model="inputSeq"
      type="textarea"
      :rows="14"
      placeholder="Paste sequences in FASTA format, or use the Try Example button..."
      style="font-family:monospace;font-size:13px;"
      v-loading="loading"
    />
    <el-button type="primary" style="margin-top:12px;">Run {{ toolName }}</el-button>
  </div>
</template>
