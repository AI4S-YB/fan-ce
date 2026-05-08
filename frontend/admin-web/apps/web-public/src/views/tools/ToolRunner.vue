<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useRequest } from '@/composables/useRequest';

const route = useRoute();
const router = useRouter();
const { get, post } = useRequest();

// ── Tool identification ──
const toolId = computed(() => {
  const p = route.path;
  if (p.includes('/blast')) return 'blast';
  if (p.includes('/primer')) return 'primer';
  if (p.includes('/grna')) return 'grna';
  if (p.includes('/msa')) return 'msa';
  if (p.includes('/motif')) return 'motif';
  return (route.params.toolId as string) || '';
});

const isBlast = computed(() => toolId.value === 'blast');

// ── Gene context ──
const geneId = ref((route.query.gene_id as string) || '');
const geneIds = ref((route.query.gene_ids as string) || '');
const datasetId = ref(Number(route.query.dataset_id) || 0);
const seqType = ref((route.query.type as string) || 'gene');
const prefillSeq = ref((route.query.seq as string) || '');

// ── Tool schema ──
interface ToolSchema { tool_id: string; display_name: string; description: string; category: string; version: string; timeout_seconds: number; input_schema: { name: string; label: string; accepted_asset_types: string[]; accepted_formats: string[]; accepted_file_roles: string[]; required: boolean }[]; parameter_schema: { name: string; label: string; type: string; default?: any; choices?: string[]; min?: number; max?: number; description?: string }[]; output_schema: { name: string; label: string; format: string; display: string }[]; }
const tool = ref<ToolSchema | null>(null);
const toolLoading = ref(false);
const hasFileInput = computed(() => (tool.value?.input_schema?.length || 0) > 0);

// ── File-param tool state (GO/KEGG Enrich) ──
const selectedFiles = ref<Record<string, number | null>>({});
const paramValues = ref<Record<string, any>>({});
const fileOptions = ref<Record<string, { id: number; label: string; format: string }[]>>({});
const exampleLoading = ref(false);

// ── Sequence tool state (Primer, gRNA, MSA) ──
const inputSeq = ref('');
const inputLabel = ref('Sequence Input (FASTA format)');

// ── BLAST-specific state ──
const databases = ref<any[]>([]);
const selectedDbs = ref<string[]>([]);
const method = ref('auto');
const advanced = ref('-evalue 1e-5 -max_target_seqs 50');
const blastMethods = [
  { value: 'auto', label: 'Auto-detect', hint: 'Automatically choose based on query & database type' },
  { value: 'blastn', label: 'blastn', hint: 'Nucleotide query against nucleotide database' },
  { value: 'blastp', label: 'blastp', hint: 'Protein query against protein database' },
  { value: 'blastx', label: 'blastx', hint: 'Translated nucleotide query against protein database' },
  { value: 'tblastn', label: 'tblastn', hint: 'Protein query against translated nucleotide database' },
  { value: 'tblastx', label: 'tblastx', hint: 'Translated nucleotide query against translated nucleotide database' },
];
const indexedDbs = computed(() => databases.value.filter((d: any) => d.indexed));
const selectedDbObjs = computed(() => databases.value.filter((d: any) => selectedDbs.value.includes(d.path)));
const previewSeqType = computed(() => {
  const s = inputSeq.value.replace(/^>[^\n]*\n/g, '').replace(/\s/g, '').toUpperCase();
  if (!s) return '?';
  const dna = new Set('ATCGN');
  const nonDna = [...s].filter(c => c >= 'A' && c <= 'Z' && !dna.has(c)).length;
  return nonDna / s.length > 0.1 ? 'protein' : 'nucleotide';
});

// ── Shared job state ──
const submitting = ref(false);
const jobId = ref<number | null>(null);
const jobStatus = ref('');
const jobError = ref('');
const outputViews = ref<Record<string, any>>({});
const selectedRow = ref<any>(null);
const polling = ref<ReturnType<typeof setInterval> | null>(null);

// ── Load tool and setup ──
onMounted(async () => {
  // Load tools
  toolLoading.value = true;
  try {
    const tools: any = await get('/analysis/tools');
    const match = (tools || []).find((t: any) => t.tool_id === toolId.value);
    if (match) {
      tool.value = match;
      setupTool(match);
    }
  } finally { toolLoading.value = false; }

  // Load sequence from gene context
  if (prefillSeq.value) { inputSeq.value = prefillSeq.value; return; }
  if (geneId.value && datasetId.value) {
    try {
      const r: any = await post('/public/dataset/sequence/batch', {
        dataset_id: datasetId.value, sequence_type: seqType.value, inputs: [geneId.value],
      });
      const seq = r?.sequences?.[0]?.sequence || '';
      inputSeq.value = `>${geneId.value}\n${seq}`;
      inputLabel.value = `${seqType.value} sequence for ${geneId.value}`;
    } catch { /* ignore */ }
  }
  if (geneIds.value && datasetId.value) {
    const ids = geneIds.value.split(',').map(s => s.trim()).filter(Boolean);
    try {
      const r: any = await post('/public/dataset/sequence/batch', {
        dataset_id: datasetId.value, sequence_type: seqType.value, inputs: ids,
      });
      inputSeq.value = r?.sequences?.map((s: any) => `>${s.input}\n${s.sequence || ''}`).join('\n') || '';
      inputLabel.value = `Sequences from ${ids.length} genes (${seqType.value})`;
    } catch { /* ignore */ }
  }
});

onUnmounted(() => { if (polling.value) clearInterval(polling.value); });

// Watch route change for tool switching
watch(() => route.path, () => {
  if (polling.value) clearInterval(polling.value);
  jobId.value = null; jobStatus.value = ''; jobError.value = ''; outputViews.value = {};
});

// ── Tool setup ──
async function setupTool(t: ToolSchema) {
  if (t.tool_id === 'blast') {
    try {
      const data: any = await get('/analysis/blast/databases');
      databases.value = data?.databases || data?.data?.databases || [];
      const indexed = databases.value.filter((d: any) => d.indexed);
      const st = seqType.value === 'protein' ? 'prot' : 'nucl';
      const matches = indexed.filter((d: any) => d.type === st);
      if (matches.length > 0) selectedDbs.value = matches.map((d: any) => d.path);
    } catch { /* ignore */ }
    return;
  }

  // Generic tool: set defaults
  selectedFiles.value = {};
  paramValues.value = {};
  for (const p of t.parameter_schema) {
    paramValues.value[p.name] = p.default ?? '';
  }
  // Load file options for file inputs
  for (const inp of t.input_schema) {
    selectedFiles.value[inp.name] = null;
    fileOptions.value[inp.name] = [];
    try {
      const result: any = await post('/analysis/files/search', {
        asset_types: inp.accepted_asset_types,
        file_formats: inp.accepted_formats,
        file_roles: inp.accepted_file_roles || [],
      });
      fileOptions.value[inp.name] = result?.items || [];
    } catch { /* ignore */ }
  }
}

// ── Generic tool: example genes ──
async function loadExampleGenes() {
  if (!tool.value) return;
  exampleLoading.value = true;
  try {
    const data: any = await post(`/analysis/tools/${tool.value.tool_id}/example-genes`, {});
    const ids = data?.gene_ids || data?.data?.gene_ids || [];
    if (ids.length > 0) paramValues.value['gene_list'] = ids.join('\n');
  } finally { exampleLoading.value = false; }
}

// ── BLAST: toggle DB ──
function toggleDb(path: string) {
  const idx = selectedDbs.value.indexOf(path);
  if (idx >= 0) selectedDbs.value.splice(idx, 1);
  else selectedDbs.value.push(path);
}

// ── Submit job ──
async function submitJob() {
  submitting.value = true; jobError.value = ''; jobStatus.value = ''; outputViews.value = {};

  let params: any = {};
  let bindings: any = {};

  if (isBlast.value) {
    if (!inputSeq.value.trim() || selectedDbs.value.length === 0) { submitting.value = false; return; }
    params = { query_seq: inputSeq.value, database: selectedDbs.value.join(' ') };
    const adv = advanced.value.trim().split(/\s+/);
    for (let i = 0; i < adv.length; i++) {
      if (adv[i] === '-evalue' && adv[i+1]) { params.evalue = parseFloat(adv[i+1]); i++; }
      else if (adv[i] === '-max_target_seqs' && adv[i+1]) { params.max_hits = parseInt(adv[i+1]); i++; }
    }
  } else if (hasFileInput.value) {
    for (const inp of tool.value!.input_schema) {
      const fid = selectedFiles.value[inp.name];
      if (inp.required && !fid) { jobError.value = `Please select a file for "${inp.label}"`; submitting.value = false; return; }
      if (fid) bindings[inp.name] = fid;
    }
    params = { ...paramValues.value };
  } else {
    if (!inputSeq.value.trim()) { submitting.value = false; return; }
    params = Object.fromEntries(
      tool.value?.parameter_schema.map(p => [p.name, paramValues.value[p.name] ?? p.default ?? '']) || []
    );
  }

  try {
    const data: any = await post('/analysis/jobs', {
      tool_id: toolId.value, input_bindings: bindings, param_overrides: params,
    });
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
      if (['success','failed','timeout'].includes(j.status)) {
        if (polling.value) clearInterval(polling.value);
        if (['failed','timeout'].includes(j.status)) jobError.value = j.error_message || 'Job failed';
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

// ── Helpers ──
function formatTime(ts?: number): string { return ts ? new Date(ts * 1000).toLocaleString() : '-'; }
function formatLocation(loc: any): string {
  if (!loc) return '-';
  if (typeof loc === 'string') return loc;
  if (Array.isArray(loc)) return loc.map((l: any) => `${l.start || ''}-${l.end || ''}`).join('; ');
  if (typeof loc === 'object') return `${loc.start || ''}-${loc.end || ''}`;
  return String(loc);
}
function formatKO(o: any): string { return Array.isArray(o) ? o.join(', ') : String(o || ''); }
function getBlastLink(acc: string, db: string): string {
  const d = db.toLowerCase();
  if (d.includes('nr')) return `https://www.ncbi.nlm.nih.gov/protein/${acc}`;
  if (d.includes('swiss') || d.includes('trembl')) return `https://www.uniprot.org/uniprot/${acc}`;
  return '#';
}
</script>

<template>
  <div style="max-width:1100px;margin:0 auto;padding:24px 16px;">
    <!-- Loading -->
    <div v-if="toolLoading" style="text-align:center;padding:60px;color:#999;">Loading tool...</div>

    <!-- BLAST UI -->
    <template v-else-if="isBlast && tool">
      <div class="blast-header">
        <h2>{{ tool.display_name }}</h2>
        <p v-if="geneId" class="blast-context">Gene: <strong>{{ geneId }}</strong> &middot; Type: <strong>{{ seqType }}</strong></p>
      </div>
      <div class="blast-layout">
        <div class="blast-form">
          <div class="form-group">
            <label class="form-label">BLAST Method</label>
            <select v-model="method" class="method-select">
              <option v-for="m in blastMethods" :key="m.value" :value="m.value">{{ m.label }} — {{ m.hint }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Databases <span class="form-hint">{{ selectedDbs.length }} of {{ indexedDbs.length }} indexed selected</span></label>
            <div class="db-list">
              <label v-for="db in databases" :key="db.path" class="db-item" :class="{ 'db-disabled': !db.indexed, 'db-selected': selectedDbs.includes(db.path) }">
                <input type="checkbox" :checked="selectedDbs.includes(db.path)" :disabled="!db.indexed" @change="toggleDb(db.path)" />
                <span class="db-name">{{ db.name }}</span>
                <span class="db-type" :class="'type-' + db.type">{{ db.type }}</span>
                <span v-if="!db.indexed" class="db-badge">not indexed</span>
              </label>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">{{ inputLabel }}</label>
            <textarea v-model="inputSeq" rows="10" placeholder="Paste query sequence(s) in FASTA format..." class="seq-input"></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">Advanced Parameters</label>
            <input v-model="advanced" type="text" class="advanced-input" placeholder="-evalue 1e-5 -max_target_seqs 50" />
          </div>
          <button class="submit-btn" :disabled="submitting || selectedDbs.length === 0 || !inputSeq.trim()" @click="submitJob">{{ submitting ? 'Submitting...' : 'BLAST' }}</button>
        </div>
        <div class="blast-preview">
          <div class="preview-card">
            <h4>Submission Preview</h4>
            <div class="preview-section"><div class="preview-label">Method</div><div class="preview-value">{{ method === 'auto' ? 'Auto-detect' : method }}</div></div>
            <div class="preview-section"><div class="preview-label">Query Type</div><div class="preview-value">{{ previewSeqType }}</div></div>
            <div class="preview-section"><div class="preview-label">Databases ({{ selectedDbs.length }})</div>
              <div v-for="db in selectedDbObjs" :key="db.path" class="preview-db"><span class="type-badge" :class="'type-' + db.type">{{ db.type }}</span>{{ db.name }}</div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Generic file-input tool (GO/KEGG Enrich) -->
    <template v-else-if="hasFileInput && tool">
      <h2>{{ tool.display_name }}</h2>
      <p style="color:#666;">{{ tool.description }}</p>
      <div style="background:#fafafa;border:1px solid #e5e5e5;border-radius:8px;padding:20px;margin-top:12px;">
        <div v-for="inp in tool.input_schema" :key="inp.name" style="margin-bottom:16px;">
          <div style="font-weight:500;margin-bottom:4px;">{{ inp.label }}<span v-if="inp.required" style="color:red;">*</span></div>
          <el-select v-model="selectedFiles[inp.name]" placeholder="Select a file..." style="width:100%;">
            <el-option v-for="opt in fileOptions[inp.name]" :key="opt.id" :label="opt.label" :value="opt.id" />
          </el-select>
          <div style="font-size:11px;color:#bbb;margin-top:2px;">Accepted: {{ inp.accepted_formats.join(', ') }}</div>
        </div>
        <div v-for="p in tool.parameter_schema" :key="p.name" style="margin-bottom:12px;">
          <div style="font-weight:500;margin-bottom:4px;">{{ p.label }}</div>
          <div v-if="p.name === 'gene_list'" style="margin-bottom:4px;">
            <el-button type="primary" plain size="small" :loading="exampleLoading" @click="loadExampleGenes">Try Example</el-button>
          </div>
          <template v-if="p.type === 'ChoiceParam'">
            <el-select v-model="paramValues[p.name]" style="width:200px;">
              <el-option v-for="c in p.choices" :key="c" :label="c" :value="c" />
            </el-select>
          </template>
          <el-input-number v-else-if="p.type === 'IntParam'" v-model="paramValues[p.name]" :min="p.min" :max="p.max" style="width:160px;" />
          <el-input-number v-else-if="p.type === 'FloatParam'" v-model="paramValues[p.name]" :min="p.min" :max="p.max" :precision="3" :step="0.01" style="width:160px;" />
          <el-input v-else-if="p.type === 'TextParam'" v-model="paramValues[p.name]" type="textarea" :rows="6" placeholder="Enter gene IDs, one per line..." style="width:100%;font-family:monospace;font-size:12px;" />
          <el-input v-else v-model="paramValues[p.name]" style="width:100%;" />
        </div>
        <el-button type="primary" :loading="submitting" @click="submitJob">Run Analysis</el-button>
      </div>
    </template>

    <!-- Generic text-input tool (Primer, gRNA, MSA) -->
    <template v-else-if="tool">
      <h2>{{ tool.display_name }}</h2>
      <p v-if="geneId" style="color:#888;margin-bottom:8px;">Gene: <strong>{{ geneId }}</strong> &middot; Type: <strong>{{ seqType }}</strong></p>
      <p style="color:#666;">{{ tool.description }}</p>
      <div style="margin-bottom:4px;font-weight:500;">{{ inputLabel }}</div>
      <el-input v-model="inputSeq" type="textarea" :rows="12" placeholder="Paste sequences in FASTA format..." style="font-family:monospace;font-size:13px;" />
      <el-button type="primary" :loading="submitting" @click="submitJob" style="margin-top:12px;">Run {{ tool.display_name }}</el-button>
    </template>

    <el-empty v-else description="Tool not found" />

    <!-- ── Job Result (shared) ── -->
    <div v-if="jobStatus" style="margin-top:20px;padding:16px;background:#f5f7fa;border-radius:8px;">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
        <span style="font-weight:600;">Job #{{ jobId }}</span>
        <el-tag :type="jobStatus === 'success' ? 'success' : ['failed','timeout'].includes(jobStatus) ? 'danger' : 'warning'" size="small">{{ jobStatus }}</el-tag>
      </div>
      <div v-if="jobError" style="color:#f56c6c;font-size:13px;white-space:pre-wrap;margin-bottom:8px;">{{ jobError }}</div>

      <!-- BLAST table -->
      <div v-if="outputViews['blast_table']?.type === 'table'" style="max-height:600px;overflow:auto;">
        <el-table :data="outputViews['blast_table'].rows" border size="small" stripe>
          <el-table-column prop="Hit_ID" label="Subject ID" width="180" show-overflow-tooltip />
          <el-table-column prop="Hit_Def" label="Description" min-width="300" show-overflow-tooltip />
          <el-table-column prop="Score" label="Score" width="80" />
          <el-table-column prop="Evalue" label="E-value" width="90" />
          <el-table-column prop="Identity" label="Identity" width="90" />
          <el-table-column label="Link" width="70"><template #default="{ row }"><a v-if="row.Link" :href="row.Link" target="_blank" class="ext-link">View</a></template></el-table-column>
          <el-table-column label="Alignment" width="80"><template #default="{ row }"><el-button size="small" @click="selectedRow = row">Show</el-button></template></el-table-column>
        </el-table>
      </div>

      <!-- Alignment -->
      <div v-if="selectedRow" class="alignment-detail">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;"><strong>{{ selectedRow.Hit_ID }}</strong><el-button size="small" text @click="selectedRow = null">✕</el-button></div>
        <pre class="alignment-pre">Query:  {{ selectedRow.QSeq }}
        {{ selectedRow.Midline }}
Sbjct:  {{ selectedRow.SSeq }}</pre>
      </div>

      <!-- Generic table output -->
      <div v-for="(view, name) in outputViews" :key="name" style="margin-top:8px;">
        <template v-if="view.type === 'table' && name !== 'blast_table'">
          <el-table :data="view.rows" border size="small" stripe max-height="500">
            <el-table-column v-for="col in view.columns" :key="col" :prop="col" :label="col" min-width="120" show-overflow-tooltip />
          </el-table>
        </template>
        <img v-else-if="view.type === 'image'" :src="view.url" style="max-width:100%;border-radius:4px;" />
        <pre v-else-if="view.type === 'text'" style="font-size:12px;max-height:400px;overflow:auto;white-space:pre-wrap;">{{ view.content }}</pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* BLAST styles */
.blast-header { margin-bottom: 20px; }
.blast-header h2 { margin: 0 0 4px; font-size: 22px; }
.blast-context { color: #888; font-size: 13px; margin: 0; }
.blast-layout { display: grid; grid-template-columns: 1fr 320px; gap: 24px; align-items: start; }
@media (max-width: 860px) { .blast-layout { grid-template-columns: 1fr; } }
.blast-form { display: flex; flex-direction: column; gap: 16px; }
.blast-preview { position: sticky; top: 24px; }
.form-group { display: flex; flex-direction: column; gap: 4px; }
.form-label { font-weight: 600; font-size: 13px; color: #303133; display: flex; align-items: center; gap: 8px; }
.form-hint { font-weight: 400; color: #999; font-size: 11px; }
.method-select { width: 100%; padding: 8px 10px; border: 1px solid #dcdfe6; border-radius: 6px; font-size: 13px; background: #fff; color: #303133; font-family: inherit; }
.db-list { max-height: 240px; overflow-y: auto; border: 1px solid #e5e5e5; border-radius: 6px; }
.db-item { display: flex; align-items: center; gap: 8px; padding: 6px 10px; cursor: pointer; border-bottom: 1px solid #f0f0f0; font-size: 13px; transition: background .15s; }
.db-item:last-child { border-bottom: none; }
.db-item:hover { background: #f5f7fa; }
.db-selected { background: #ecf5ff; }
.db-disabled { opacity: 0.5; cursor: not-allowed; }
.db-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.db-type { padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; text-transform: uppercase; }
.type-nucl { background: #e6f7ff; color: #1890ff; }
.type-prot { background: #f6ffed; color: #52c41a; }
.db-badge { font-size: 10px; color: #faad14; }
.seq-input { width: 100%; padding: 10px; border: 1px solid #dcdfe6; border-radius: 6px; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12px; resize: vertical; box-sizing: border-box; }
.advanced-input { width: 100%; padding: 8px 10px; border: 1px solid #dcdfe6; border-radius: 6px; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12px; box-sizing: border-box; }
.submit-btn { padding: 10px 32px; border: none; border-radius: 999px; background: linear-gradient(135deg, #14213d, #335c67); color: #fff; font-size: 15px; font-weight: 600; cursor: pointer; align-self: flex-start; transition: opacity .2s; font-family: inherit; }
.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.preview-card { background: rgba(255,255,255,0.9); border: 1px solid #e5e5e5; border-radius: 10px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.preview-card h4 { margin: 0 0 12px; font-size: 14px; }
.preview-section { margin-bottom: 14px; }
.preview-label { font-size: 11px; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2px; }
.preview-value { font-size: 14px; font-weight: 600; }
.preview-db { font-size: 12px; padding: 2px 0; display: flex; align-items: center; gap: 6px; }
.type-badge { padding: 1px 5px; border-radius: 3px; font-size: 9px; font-weight: 600; }
.type-badge.type-nucl { background: #e6f7ff; color: #1890ff; }
.type-badge.type-prot { background: #f6ffed; color: #52c41a; }

/* Shared */
.ext-link { color: #409eff; text-decoration: none; }
.alignment-detail { margin-top: 16px; padding: 16px; background: #f5f7fa; border-radius: 8px; }
.alignment-pre { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12px; white-space: pre; overflow-x: auto; background: #101828; color: #d4d4d4; padding: 12px; border-radius: 6px; }
</style>
