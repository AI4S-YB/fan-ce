<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import { useRequest } from '@/composables/useRequest';

const route = useRoute();
const { get, post } = useRequest();

const toolName = computed(() => route.params.name as string);
const geneId = ref((route.query.gene_id as string) || '');
const geneIds = ref((route.query.gene_ids as string) || '');
const datasetId = ref(Number(route.query.dataset_id) || 0);
const seqType = ref((route.query.type as string) || 'gene');
const prefillSeq = ref((route.query.seq as string) || '');

const inputSeq = ref('');
const inputLabel = ref('Sequence Input (FASTA format)');
const loading = ref(false);
const submitting = ref(false);

// Tool-specific state
const databases = ref<any[]>([]);
const selectedDb = ref<string[]>([]);
const evalue = ref(0.001);
const maxHits = ref(50);
const showDbSelect = computed(() => toolName.value === 'blast');

// Job state
const jobId = ref<number | null>(null);
const jobStatus = ref('');
const jobError = ref('');
const outputViews = ref<Record<string, any>>({});
const polling = ref<ReturnType<typeof setInterval> | null>(null);

onMounted(async () => {
  // Load databases for BLAST
  if (toolName.value === 'blast') {
    try {
      const data: any = await get('/analysis/blast/databases');
      databases.value = data?.databases || data?.data?.databases || [];
      // Auto-select indexed protein DB for protein queries, first indexed otherwise
      const indexed = databases.value.filter((d: any) => d.indexed);
      const match = indexed.find((d: any) => d.type === seqType.value);
      if (match) selectedDb.value = [match.path];
    } catch { /* ignore */ }
  }

  // Load sequence from gene context
  if (prefillSeq.value) {
    inputSeq.value = prefillSeq.value;
    return;
  }
  if (geneIds.value && datasetId.value) {
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

onUnmounted(() => { if (polling.value) clearInterval(polling.value); });

async function submitJob() {
  if (!inputSeq.value.trim()) return;
  submitting.value = true;
  jobError.value = '';
  jobStatus.value = '';
  outputViews.value = {};
  try {
    const params: any = {
      query_seq: inputSeq.value,
      evalue: evalue.value,
      max_hits: maxHits.value,
    };
    if (selectedDb.value.length > 0) params.database = selectedDb.value.join(' ');

    const data: any = await post('/analysis/jobs', {
      tool_id: toolName.value,
      input_bindings: {},
      param_overrides: params,
    });
    jobId.value = data?.id || data?.data?.id;
    jobStatus.value = 'pending';
    startPolling();
  } catch (e: any) {
    jobError.value = e?.message || 'Submit failed';
  } finally {
    submitting.value = false;
  }
}

function startPolling() {
  if (polling.value) clearInterval(polling.value);
  polling.value = setInterval(async () => {
    if (!jobId.value) return;
    try {
      const data: any = await get(`/analysis/jobs/${jobId.value}`);
      const j = data?.data || data;
      jobStatus.value = j.status;
      if (j.status === 'success' || j.status === 'failed' || j.status === 'timeout') {
        if (polling.value) clearInterval(polling.value);
        if (j.status === 'failed' || j.status === 'timeout') {
          jobError.value = j.error_message || 'Job failed';
        }
        // Load output views on success
        if (j.status === 'success' && j.output_files?.length) {
          for (const f of j.output_files) {
            try {
              const v: any = await get(`/analysis/jobs/${jobId.value}/output/${f.name}/view`);
              outputViews.value[f.name] = v?.data || v;
            } catch { /* view not available */ }
          }
        }
      }
    } catch { /* ignore */ }
  }, 3000);
}

function formatSize(bytes: number): string {
  if (!bytes) return '-';
  return (bytes / 1024 / 1024).toFixed(1) + ' MB';
}
</script>

<template>
  <div style="padding:24px;max-width:1000px;">
    <h2 style="margin-top:0;">{{ toolName }}</h2>
    <p v-if="geneId" style="color:#888;margin-bottom:8px;">
      Gene: <strong>{{ geneId }}</strong>
      <span v-if="geneIds">&middot; Batch: {{ geneIds.split(',').length }} genes</span>
      &middot; Type: <strong>{{ seqType }}</strong>
    </p>

    <!-- Database selector (BLAST only) -->
    <div v-if="showDbSelect" style="margin-bottom:16px;">
      <div style="font-weight:500;margin-bottom:4px;">BLAST Database</div>
      <el-select v-model="selectedDb" placeholder="Select databases..." style="width:100%;max-width:600px;" filterable multiple>
        <el-option v-for="db in databases" :key="db.id" :label="`${db.dataset} / ${db.name} (${db.type}) ${db.indexed ? '' : '[not indexed]'}`" :value="db.path" :disabled="!db.indexed" />
      </el-select>
    </div>

    <!-- Parameters -->
    <div style="display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap;">
      <div>
        <div style="font-weight:500;font-size:13px;">E-value</div>
        <el-input-number v-model="evalue" :min="1e-100" :max="1000" :precision="3" :step="0.1" size="small" style="width:160px;" />
      </div>
      <div>
        <div style="font-weight:500;font-size:13px;">Max Hits</div>
        <el-input-number v-model="maxHits" :min="1" :max="500" size="small" style="width:120px;" />
      </div>
    </div>

    <div style="margin-bottom:4px;font-weight:500;">{{ inputLabel }}</div>
    <el-input
      v-model="inputSeq"
      type="textarea"
      :rows="12"
      placeholder="Paste sequences in FASTA format..."
      style="font-family:monospace;font-size:13px;"
      v-loading="loading"
    />
    <el-button type="primary" :loading="submitting" @click="submitJob" style="margin-top:12px;">
      Run {{ toolName }}
    </el-button>

    <!-- Job Status -->
    <div v-if="jobStatus" style="margin-top:16px;padding:16px;background:#f5f7fa;border-radius:8px;">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
        <span style="font-weight:600;">Job #{{ jobId }}</span>
        <el-tag :type="jobStatus === 'success' ? 'success' : jobStatus === 'failed' || jobStatus === 'timeout' ? 'danger' : 'warning'" size="small">{{ jobStatus }}</el-tag>
      </div>
      <div v-if="jobError" style="color:#f56c6c;font-size:13px;white-space:pre-wrap;margin-bottom:8px;">{{ jobError }}</div>

      <!-- BLAST table output -->
      <div v-if="outputViews['blast_table']?.type === 'table'" style="max-height:600px;overflow:auto;">
        <el-table :data="outputViews['blast_table'].rows" border size="small" stripe>
          <el-table-column prop="Hit_ID" label="Subject ID" width="200" show-overflow-tooltip />
          <el-table-column prop="Hit_Def" label="Description" min-width="300" show-overflow-tooltip />
          <el-table-column prop="Score" label="Score" width="90" />
          <el-table-column prop="Evalue" label="E-value" width="90" />
          <el-table-column prop="Identity" label="Identity" width="90" />
          <el-table-column label="Link" width="80">
            <template #default="{ row }">
              <a v-if="row.Link" :href="row.Link" target="_blank" style="color:#409eff;">View</a>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Text report -->
      <div v-if="outputViews['blast_report']?.type === 'text'" style="margin-top:8px;">
        <pre style="font-size:12px;max-height:400px;overflow:auto;background:#1e1e1e;color:#d4d4d4;padding:8px;border-radius:4px;white-space:pre-wrap;">{{ outputViews['blast_report'].content }}</pre>
      </div>

      <!-- Generic table output -->
      <div v-for="(view, name) in outputViews" :key="name" style="margin-top:8px;">
        <div v-if="view.type === 'table' && name !== 'blast_table'" style="max-height:400px;overflow:auto;">
          <el-table :data="view.rows" border size="small" stripe>
            <el-table-column v-for="col in view.columns" :key="col" :prop="col" :label="col" min-width="120" show-overflow-tooltip />
          </el-table>
        </div>
      </div>
    </div>
  </div>
</template>
