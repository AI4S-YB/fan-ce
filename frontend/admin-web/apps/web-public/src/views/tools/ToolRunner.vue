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

// ── BLAST-specific state ──
const databases = ref<any[]>([]);
const selectedDbs = ref<string[]>([]);
const method = ref('auto');
const advanced = ref('-evalue 1e-5 -max_target_seqs 50');
const isBlast = computed(() => toolName.value === 'blast');

// Available BLAST methods
const blastMethods = [
  { value: 'auto', label: 'Auto-detect', hint: 'Automatically choose based on query & database type' },
  { value: 'blastn', label: 'blastn', hint: 'Nucleotide query against nucleotide database' },
  { value: 'blastp', label: 'blastp', hint: 'Protein query against protein database' },
  { value: 'blastx', label: 'blastx', hint: 'Translated nucleotide query against protein database' },
  { value: 'tblastn', label: 'tblastn', hint: 'Protein query against translated nucleotide database' },
  { value: 'tblastx', label: 'tblastx', hint: 'Translated nucleotide query against translated nucleotide database' },
];

// ── Job state ──
const jobId = ref<number | null>(null);
const jobStatus = ref('');
const jobError = ref('');
const outputViews = ref<Record<string, any>>({});
const polling = ref<ReturnType<typeof setInterval> | null>(null);

// ── Preview ──
const indexedDbs = computed(() => databases.value.filter((d: any) => d.indexed));
const selectedDbObjs = computed(() => databases.value.filter((d: any) => selectedDbs.value.includes(d.path)));
const dbTypes = computed(() => [...new Set(selectedDbObjs.value.map((d: any) => d.type))]);
const previewSeqType = computed(() => {
  const s = inputSeq.value.replace(/^>[^\n]*\n/g, '').replace(/\s/g, '').toUpperCase();
  if (!s) return '?';
  const dna = new Set('ATCGN');
  const nonDna = [...s].filter(c => c >= 'A' && c <= 'Z' && !dna.has(c)).length;
  return nonDna / s.length > 0.1 ? 'protein' : 'nucleotide';
});

onMounted(async () => {
  if (isBlast.value) {
    try {
      const data: any = await get('/analysis/blast/databases');
      databases.value = data?.databases || data?.data?.databases || [];
      // Auto-select compatible indexed databases
      const indexed = databases.value.filter((d: any) => d.indexed);
      const st = seqType.value === 'protein' ? 'prot' : 'nucl';
      const matches = indexed.filter((d: any) => d.type === st);
      if (matches.length > 0) selectedDbs.value = matches.map((d: any) => d.path);
    } catch { /* ignore */ }
  }

  // Load sequence
  if (prefillSeq.value) { inputSeq.value = prefillSeq.value; return; }
  if (geneIds.value && datasetId.value) {
    const ids = geneIds.value.split(',').map(s => s.trim()).filter(Boolean);
    inputLabel.value = `Sequences from ${ids.length} genes (${seqType.value})`;
    loading.value = true;
    try {
      const r: any = await post('/public/dataset/sequence/batch', {
        dataset_id: datasetId.value, sequence_type: seqType.value, inputs: ids,
      });
      inputSeq.value = r?.sequences?.map((s: any) => `>${s.input}\n${s.sequence || ''}`).join('\n') || '';
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

function toggleDb(path: string) {
  const idx = selectedDbs.value.indexOf(path);
  if (idx >= 0) selectedDbs.value.splice(idx, 1);
  else selectedDbs.value.push(path);
}

async function submitJob() {
  if (!inputSeq.value.trim() || selectedDbs.value.length === 0) return;
  submitting.value = true; jobError.value = ''; jobStatus.value = ''; outputViews.value = {};
  try {
    const params: any = { query_seq: inputSeq.value, database: selectedDbs.value.join(' ') };
    if (method.value !== 'auto') params.seq_type = method.value.startsWith('blast') ? method.value.replace('blast','').replace('n','nucleotide').replace('p','protein').replace('x','protein') : 'auto';
    // Parse advanced params (simple: just pass as-is; the BLAST script can handle them)
    if (advanced.value.trim()) {
      const parts = advanced.value.trim().split(/\s+/);
      for (let i = 0; i < parts.length; i++) {
        if (parts[i] === '-evalue' && parts[i+1]) { params.evalue = parseFloat(parts[i+1]); i++; }
        else if (parts[i] === '-max_target_seqs' && parts[i+1]) { params.max_hits = parseInt(parts[i+1]); i++; }
      }
    }
    const data: any = await post('/analysis/jobs', { tool_id: 'blast', input_bindings: {}, param_overrides: params });
    jobId.value = data?.id || data?.data?.id;
    jobStatus.value = 'pending';
    startPolling();
  } catch (e: any) { jobError.value = e?.message || 'Submit failed'; }
  finally { submitting.value = false; }
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
        if (j.status === 'failed' || j.status === 'timeout') jobError.value = j.error_message || 'Job failed';
        if (j.status === 'success' && j.output_files?.length) {
          for (const f of j.output_files) {
            try {
              const v: any = await get(`/analysis/jobs/${jobId.value}/output/${f.name}/view`);
              outputViews.value[f.name] = v?.data || v;
            } catch { /* ignore */ }
          }
        }
      }
    } catch { /* ignore */ }
  }, 3000);
}
</script>

<template>
  <div class="blast-page" v-if="isBlast">
    <div class="blast-header">
      <h2>BLAST Search</h2>
      <p v-if="geneId" class="blast-context">Gene: <strong>{{ geneId }}</strong> &middot; Type: <strong>{{ seqType }}</strong></p>
    </div>

    <div class="blast-layout">
      <!-- Left: Form -->
      <div class="blast-form">
        <!-- Method -->
        <div class="form-group">
          <label class="form-label">BLAST Method</label>
          <select v-model="method" class="method-select">
            <option v-for="m in blastMethods" :key="m.value" :value="m.value">
              {{ m.label }} — {{ m.hint }}
            </option>
          </select>
        </div>

        <!-- Database Selection -->
        <div class="form-group">
          <label class="form-label">
            Databases
            <span class="form-hint">{{ selectedDbs.length }} of {{ indexedDbs.length }} indexed selected</span>
          </label>
          <div class="db-list">
            <label v-for="db in databases" :key="db.path"
              class="db-item" :class="{ 'db-disabled': !db.indexed, 'db-selected': selectedDbs.includes(db.path) }">
              <input type="checkbox" :checked="selectedDbs.includes(db.path)"
                :disabled="!db.indexed" @change="toggleDb(db.path)" />
              <span class="db-name">{{ db.dataset }} / {{ db.name }}</span>
              <span class="db-type" :class="'type-' + db.type">{{ db.type }}</span>
              <span v-if="!db.indexed" class="db-badge">not indexed</span>
            </label>
          </div>
          <div v-if="databases.length === 0" style="color:#999;font-size:13px;padding:8px;">
            No BLAST databases available. Use the admin panel to build indexes.
          </div>
        </div>

        <!-- Sequence -->
        <div class="form-group">
          <label class="form-label">{{ inputLabel }}</label>
          <textarea v-model="inputSeq" rows="10" placeholder="Paste query sequence(s) in FASTA format..."
            class="seq-input" v-loading="loading"></textarea>
        </div>

        <!-- Advanced -->
        <div class="form-group">
          <label class="form-label">Advanced Parameters</label>
          <input v-model="advanced" type="text" class="advanced-input"
            placeholder="-evalue 1e-5 -max_target_seqs 50" />
        </div>

        <!-- Submit -->
        <button class="submit-btn" :disabled="submitting || selectedDbs.length === 0 || !inputSeq.trim()"
          @click="submitJob">
          {{ submitting ? 'Submitting...' : 'BLAST' }}
        </button>
        <div v-if="selectedDbs.length === 0 && indexedDbs.length > 0" class="form-warning">
          Select at least one database to search.
        </div>
      </div>

      <!-- Right: Preview -->
      <div class="blast-preview">
        <div class="preview-card">
          <h4>Submission Preview</h4>

          <div class="preview-section">
            <div class="preview-label">Method</div>
            <div class="preview-value">{{ method === 'auto' ? 'Auto-detect' : method }}</div>
            <div class="preview-hint">{{ blastMethods.find(m => m.value === method)?.hint }}</div>
          </div>

          <div class="preview-section">
            <div class="preview-label">Query Type</div>
            <div class="preview-value">{{ previewSeqType }}</div>
          </div>

          <div class="preview-section">
            <div class="preview-label">Databases ({{ selectedDbs.length }})</div>
            <div v-if="selectedDbs.length === 0" class="preview-empty">No databases selected</div>
            <div v-for="db in selectedDbObjs" :key="db.path" class="preview-db">
              <span class="type-badge" :class="'type-' + db.type">{{ db.type }}</span>
              {{ db.dataset }} / {{ db.name }}
            </div>
          </div>

          <!-- Job Result (post-submit) -->
          <div v-if="jobId" class="preview-section job-result">
            <div class="preview-label">Job #{{ jobId }}</div>
            <span class="status-tag" :class="'status-' + jobStatus">{{ jobStatus }}</span>
            <div v-if="outputViews['blast_report']?.type === 'text'" style="margin-top:8px;">
              <pre class="report-preview">{{ outputViews['blast_report'].content?.slice(0, 500) }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Results -->
    <div v-if="jobStatus" class="blast-results">
      <div v-if="jobError" class="result-error">{{ jobError }}</div>
      <div v-if="outputViews['blast_table']?.type === 'table'" class="result-table-wrap">
        <el-table :data="outputViews['blast_table'].rows" border size="small" stripe max-height="600">
          <el-table-column prop="Hit_ID" label="Subject ID" width="180" show-overflow-tooltip />
          <el-table-column prop="Hit_Def" label="Description" min-width="300" show-overflow-tooltip />
          <el-table-column prop="Score" label="Score" width="80" />
          <el-table-column prop="Evalue" label="E-value" width="90" />
          <el-table-column prop="Identity" label="Identity" width="90" />
          <el-table-column label="Link" width="70">
            <template #default="{ row }">
              <a v-if="row.Link" :href="row.Link" target="_blank" class="ext-link">View</a>
            </template>
          </el-table-column>
          <el-table-column label="Alignment" width="80">
            <template #default="{ row }">
              <el-button size="small" @click="outputViews['_selected'] = row">Show</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <!-- Alignment detail -->
      <div v-if="outputViews['_selected']" class="alignment-detail">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <strong>{{ outputViews['_selected'].Hit_ID }}</strong>
          <el-button size="small" text @click="outputViews['_selected'] = null">✕</el-button>
        </div>
        <pre class="alignment-pre">Query:  {{ outputViews['_selected'].QSeq }}
        {{ outputViews['_selected'].Midline }}
Sbjct:  {{ outputViews['_selected'].SSeq }}</pre>
      </div>
    </div>
  </div>

  <!-- Non-BLAST tools: simple form -->
  <div v-else style="padding:24px;max-width:960px;">
    <h2 style="margin-top:0;">{{ toolName }}</h2>
    <p v-if="geneId" style="color:#888;margin-bottom:8px;">
      Gene: <strong>{{ geneId }}</strong> &middot; Type: <strong>{{ seqType }}</strong>
    </p>
    <div style="margin-bottom:4px;font-weight:500;">{{ inputLabel }}</div>
    <el-input v-model="inputSeq" type="textarea" :rows="12"
      placeholder="Paste sequences in FASTA format..."
      style="font-family:monospace;font-size:13px;" v-loading="loading" />
    <el-button type="primary" :loading="submitting" @click="submitJob" style="margin-top:12px;">
      Run {{ toolName }}
    </el-button>
  </div>
</template>

<style scoped>
.blast-page { max-width: 1100px; margin: 0 auto; padding: 24px 16px; }
.blast-header { margin-bottom: 20px; }
.blast-header h2 { margin: 0 0 4px; font-size: 22px; }
.blast-context { color: #888; font-size: 13px; margin: 0; }

.blast-layout { display: grid; grid-template-columns: 1fr 320px; gap: 24px; align-items: start; }
@media (max-width: 860px) { .blast-layout { grid-template-columns: 1fr; } }

/* Form */
.blast-form { display: flex; flex-direction: column; gap: 16px; }
.form-group { display: flex; flex-direction: column; gap: 4px; }
.form-label { font-weight: 600; font-size: 13px; color: #303133; display: flex; align-items: center; gap: 8px; }
.form-hint { font-weight: 400; color: #999; font-size: 11px; }
.form-warning { color: #e6a23c; font-size: 12px; }

.method-select { width: 100%; padding: 8px 10px; border: 1px solid #dcdfe6; border-radius: 6px;
  font-size: 13px; background: #fff; color: #303133; font-family: inherit; }

/* Database list */
.db-list { max-height: 240px; overflow-y: auto; border: 1px solid #e5e5e5; border-radius: 6px; }
.db-item { display: flex; align-items: center; gap: 8px; padding: 6px 10px; cursor: pointer;
  border-bottom: 1px solid #f0f0f0; font-size: 13px; transition: background .15s; }
.db-item:last-child { border-bottom: none; }
.db-item:hover { background: #f5f7fa; }
.db-selected { background: #ecf5ff; }
.db-disabled { opacity: 0.5; cursor: not-allowed; }
.db-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.db-type { padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; text-transform: uppercase; }
.type-nucl, .type-nucleotide { background: #e6f7ff; color: #1890ff; }
.type-prot, .type-protein { background: #f6ffed; color: #52c41a; }
.db-badge { font-size: 10px; color: #faad14; }

/* Sequence input */
.seq-input { width: 100%; padding: 10px; border: 1px solid #dcdfe6; border-radius: 6px;
  font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12px; resize: vertical;
  box-sizing: border-box; }
.advanced-input { width: 100%; padding: 8px 10px; border: 1px solid #dcdfe6; border-radius: 6px;
  font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12px; box-sizing: border-box; }

/* Submit */
.submit-btn { padding: 10px 32px; border: none; border-radius: 999px;
  background: linear-gradient(135deg, #14213d, #335c67); color: #fff;
  font-size: 15px; font-weight: 600; cursor: pointer; align-self: flex-start;
  transition: opacity .2s; font-family: inherit; }
.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.submit-btn:hover:not(:disabled) { opacity: 0.9; }

/* Preview */
.blast-preview { position: sticky; top: 24px; }
.preview-card { background: rgba(255,255,255,0.9); border: 1px solid #e5e5e5; border-radius: 10px;
  padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.preview-card h4 { margin: 0 0 12px; font-size: 14px; color: #303133; }
.preview-section { margin-bottom: 14px; }
.preview-label { font-size: 11px; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2px; }
.preview-value { font-size: 14px; font-weight: 600; color: #303133; }
.preview-hint { font-size: 11px; color: #999; margin-top: 2px; }
.preview-empty { font-size: 12px; color: #ccc; font-style: italic; }
.preview-db { font-size: 12px; padding: 2px 0; display: flex; align-items: center; gap: 6px; }
.type-badge { padding: 1px 5px; border-radius: 3px; font-size: 9px; font-weight: 600; }
.type-badge.type-nucl { background: #e6f7ff; color: #1890ff; }
.type-badge.type-prot { background: #f6ffed; color: #52c41a; }

.job-result { background: #f5f7fa; padding: 10px; border-radius: 6px; }
.status-tag { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; }
.status-pending, .status-running { background: #e6f7ff; color: #1890ff; }
.status-success { background: #f6ffed; color: #52c41a; }
.status-failed, .status-timeout { background: #fff2f0; color: #ff4d4f; }
.report-preview { font-size: 11px; max-height: 200px; overflow: auto; }
.result-error { color: #ff4d4f; background: #fff2f0; padding: 10px; border-radius: 6px; margin-bottom: 12px; }

/* Results */
.blast-results { margin-top: 24px; }
.result-table-wrap { margin-top: 12px; }
.ext-link { color: #409eff; text-decoration: none; }
.alignment-detail { margin-top: 16px; padding: 16px; background: #f5f7fa; border-radius: 8px; }
.alignment-pre { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12px;
  white-space: pre; overflow-x: auto; background: #101828; color: #d4d4d4;
  padding: 12px; border-radius: 6px; }
</style>
