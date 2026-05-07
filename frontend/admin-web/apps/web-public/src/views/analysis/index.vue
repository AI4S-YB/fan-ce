<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRequest } from '@/composables/useRequest';

const { get, post } = useRequest();

interface ToolSchema {
  tool_id: string; display_name: string; description: string; category: string;
  version: string; timeout_seconds: number;
  input_schema: { name: string; label: string; accepted_asset_types: string[]; accepted_formats: string[]; accepted_file_roles: string[]; required: boolean }[];
  parameter_schema: { name: string; label: string; type: string; default?: any; choices?: string[]; min?: number; max?: number }[];
  output_schema: { name: string; label: string; format: string }[];
}

interface JobInfo {
  id: number; tool_id: string; status: string;
  output_files?: { name: string; path: string; size: number }[] | null;
  error_message?: string | null;
  created_at?: number; finished_at?: number;
}

const tools = ref<ToolSchema[]>([]);
const selectedTool = ref<ToolSchema | null>(null);
const selectedFiles = ref<Record<string, number | null>>({});
const paramValues = ref<Record<string, any>>({});
const submitting = ref(false);
const submittedJob = ref<JobInfo | null>(null);
const jobStatus = ref<JobInfo | null>(null);
const polling = ref<ReturnType<typeof setInterval> | null>(null);

// Available asset files for file params
const fileOptions = ref<Record<string, { id: number; label: string; format: string }[]>>({});

async function loadTools() {
  const data: any = await get('/analysis/tools');
  tools.value = data || [];
  // Auto-select the first tool — skip card list when there's only one
  if (tools.value.length === 1) {
    selectTool(tools.value[0]);
  }
}

async function selectTool(tool: ToolSchema) {
  selectedTool.value = tool;
  selectedFiles.value = {};
  paramValues.value = {};
  submittedJob.value = null;
  jobStatus.value = null;
  if (polling.value) clearInterval(polling.value);

  // Set defaults for params
  for (const p of tool.parameter_schema) {
    paramValues.value[p.name] = p.default ?? '';
  }

  // For each file input, fetch matching asset files
  for (const inp of tool.input_schema) {
    selectedFiles.value[inp.name] = null;
    fileOptions.value[inp.name] = [];
    try {
      const result: any = await post('/analysis/files/search', {
        asset_types: inp.accepted_asset_types,
        file_formats: inp.accepted_formats,
        file_roles: inp.accepted_file_roles || [],
      });
      fileOptions.value[inp.name] = result?.items || [];
    } catch (e) {
      console.warn(`Failed to load options for ${inp.name}:`, e);
    }
  }
}

async function submitJob() {
  if (!selectedTool.value) return;
  submitting.value = true;
  try {
    const bindings: Record<string, number> = {};
    for (const inp of selectedTool.value.input_schema) {
      const fid = selectedFiles.value[inp.name];
      if (inp.required && !fid) {
        alert(`Please select a file for "${inp.label}"`);
        submitting.value = false;
        return;
      }
      if (fid) bindings[inp.name] = fid;
    }
    const data: any = await post('/analysis/jobs', {
      tool_id: selectedTool.value.tool_id,
      input_bindings: bindings,
      param_overrides: paramValues.value,
    });
    submittedJob.value = data;
    startPolling();
  } catch (e: any) {
    alert('Failed to submit: ' + (e?.message || 'Unknown error'));
  } finally {
    submitting.value = false;
  }
}

function startPolling() {
  if (polling.value) clearInterval(polling.value);
  polling.value = setInterval(async () => {
    if (!submittedJob.value) return;
    try {
      const data: any = await get(`/analysis/jobs/${submittedJob.value.id}`);
      jobStatus.value = data;
      if (data.status === 'success' || data.status === 'failed' || data.status === 'timeout') {
        if (polling.value) clearInterval(polling.value);
      }
    } catch { /* ignore */ }
  }, 2000);
}

function downloadOutput(jobId: number, fileName: string) {
  window.open(`/api/v1/analysis/jobs/${jobId}/output/${fileName}`, '_blank');
}

function formatTime(ts?: number): string {
  if (!ts) return '-';
  return new Date(ts * 1000).toLocaleString();
}

onMounted(loadTools);
</script>

<template>
  <div>
    <h2>Analysis Tools</h2>

    <!-- Tool list -->
    <div v-if="!selectedTool" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;">
      <el-card v-for="t in tools" :key="t.tool_id" shadow="hover" style="cursor:pointer;" @click="selectTool(t)">
        <h3 style="margin:0 0 4px;">{{ t.display_name }}</h3>
        <el-tag size="small">{{ t.category }}</el-tag>
        <span style="color:#888;font-size:12px;margin-left:8px;">v{{ t.version }}</span>
        <p style="color:#666;font-size:13px;margin:8px 0 0;">{{ t.description }}</p>
      </el-card>
      <el-empty v-if="tools.length === 0" description="No analysis tools available" />
    </div>

    <!-- Tool form -->
    <div v-if="selectedTool">
      <el-button text @click="selectedTool = null">← Back to tools</el-button>
      <h3 style="margin:8px 0;">{{ selectedTool.display_name }}</h3>
      <p style="color:#666;">{{ selectedTool.description }}</p>

      <div style="background:#fafafa;border:1px solid #e5e5e5;border-radius:8px;padding:20px;margin-top:12px;">
        <!-- File inputs -->
        <div v-for="inp in selectedTool.input_schema" :key="inp.name" style="margin-bottom:16px;">
          <div style="font-weight:500;margin-bottom:4px;">
            {{ inp.label }}
            <span v-if="inp.required" style="color:red;">*</span>
          </div>
          <el-select v-model="selectedFiles[inp.name]" placeholder="Select a file..." style="width:100%;">
            <el-option v-for="opt in fileOptions[inp.name]" :key="opt.id"
              :label="opt.label" :value="opt.id" />
          </el-select>
          <div style="font-size:11px;color:#bbb;margin-top:2px;">
            Accepted: {{ inp.accepted_formats.join(', ') }} ({{ inp.accepted_asset_types.join(', ') }})
          </div>
        </div>

        <!-- Parameter inputs -->
        <div v-for="p in selectedTool.parameter_schema" :key="p.name" style="margin-bottom:12px;">
          <div style="font-weight:500;margin-bottom:4px;">{{ p.label }}</div>
          <el-select v-if="p.type === 'ChoiceParam'" v-model="paramValues[p.name]" style="width:100%;">
            <el-option v-for="c in p.choices" :key="c" :label="c" :value="c" />
          </el-select>
          <el-input-number v-else-if="p.type === 'IntParam'" v-model="paramValues[p.name]"
            :min="p.min" :max="p.max" style="width:100%;" />
          <el-input-number v-else-if="p.type === 'FloatParam'" v-model="paramValues[p.name]"
            :min="p.min" :max="p.max" :precision="3" :step="0.01" style="width:100%;" />
          <el-input v-else v-model="paramValues[p.name]" style="width:100%;" />
        </div>

        <el-button type="primary" :loading="submitting" @click="submitJob"
          style="margin-top:8px;">Run Analysis</el-button>
      </div>

      <!-- Job result -->
      <div v-if="submittedJob" style="margin-top:16px;padding:16px;background:#f0f9ff;border-radius:8px;">
        <h4 style="margin:0 0 8px;">Job #{{ submittedJob.id }}</h4>
        <div>Status: <el-tag :type="jobStatus?.status === 'success' ? 'success' : jobStatus?.status === 'failed' ? 'danger' : 'warning'" size="small">{{ jobStatus?.status || 'pending' }}</el-tag></div>
        <div v-if="jobStatus?.error_message" style="color:red;margin-top:8px;font-size:13px;white-space:pre-wrap;">{{ jobStatus.error_message }}</div>
        <div v-if="jobStatus?.output_files?.length" style="margin-top:8px;">
          <div style="font-weight:500;margin-bottom:4px;">Output Files:</div>
          <div v-for="f in jobStatus.output_files" :key="f.name" style="display:flex;align-items:center;gap:8px;margin:4px 0;">
            <span style="font-size:13px;">{{ f.name }} ({{ (f.size / 1024).toFixed(1) }} KB)</span>
            <el-button size="small" @click="downloadOutput(submittedJob!.id, f.name)">Download</el-button>
          </div>
        </div>
        <div style="font-size:11px;color:#999;margin-top:8px;">
          Submitted: {{ formatTime(submittedJob.created_at) }}
          <span v-if="jobStatus?.finished_at"> | Finished: {{ formatTime(jobStatus.finished_at) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
