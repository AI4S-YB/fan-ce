<template>
  <Page>
    <div style="padding: 24px;">
      <h2>Analysis Tools</h2>
      <p style="color: #888; margin-bottom: 16px;">
        Registered tools are discovered from installed Python plugins on startup.
        Install via <code>pip install &lt;plugin-package&gt;</code> then restart the backend.
      </p>

      <a-table :columns="columns" :data-source="tools" :loading="loading" row-key="tool_id" size="small" bordered>
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'display_name'">
            <strong>{{ record.display_name }}</strong>
            <br /><span style="font-size: 12px; color: #888;">{{ record.tool_id }}</span>
          </template>
          <template v-else-if="column.key === 'category'">
            <a-tag>{{ record.category }}</a-tag>
          </template>
          <template v-else-if="column.key === 'version'"> v{{ record.version }} </template>
          <template v-else-if="column.key === 'deps'">
            <span v-if="record.dependencies?.conda?.length">{{ record.dependencies.conda.join(', ') }}</span>
            <span v-else style="color: #ccc;">None</span>
          </template>
          <template v-else-if="column.key === 'class'">
            <code style="font-size: 11px;">{{ record.plugin_class }}</code>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-button size="small" @click="showDetail(record)">Detail</a-button>
          </template>
        </template>
      </a-table>

      <a-divider />

      <!-- Inline Plugin Dev Guide -->
      <h3>Plugin Development Guide</h3>
      <div style="background: #fafafa; border: 1px solid #e5e5e5; border-radius: 8px; padding: 20px; font-size: 13px; line-height: 1.8;">
        <h4>1. Create pyproject.toml</h4>
        <pre style="background: #1e1e1e; color: #d4d4d4; padding: 12px; border-radius: 4px; overflow-x: auto;">{{ pyprojectToml }}</pre>

        <h4>2. Write Tool Class (tool.py)</h4>
        <pre style="background: #1e1e1e; color: #d4d4d4; padding: 12px; border-radius: 4px; overflow-x: auto;">{{ toolPy }}</pre>

        <h4>3. Install &amp; Verify</h4>
        <pre style="background: #1e1e1e; color: #d4d4d4; padding: 12px; border-radius: 4px; overflow-x: auto;">pip install /path/to/plugin
# Restart FAN-CE backend
curl http://localhost:8002/api/v1/analysis/tools</pre>

        <h4>4. File Role Codes (for FileParam.accepted_file_roles)</h4>
        <a-table :columns="roleCols" :data-source="fileRoles" size="small" bordered :pagination="false" />

        <p style="margin-top: 16px; color: #888;">
          Full documentation: <code>docs/plugin-development-guide.md</code>
        </p>
      </div>

      <!-- Detail Drawer -->
      <a-drawer :open="drawerVisible" title="Tool Detail" width="640px" @close="drawerVisible = false">
        <template v-if="detail">
          <h3>{{ detail.display_name }}</h3>
          <p>{{ detail.description }}</p>
          <a-descriptions :column="1" size="small" bordered>
            <a-descriptions-item label="Tool ID">{{ detail.tool_id }}</a-descriptions-item>
            <a-descriptions-item label="Version">v{{ detail.version }}</a-descriptions-item>
            <a-descriptions-item label="Category">{{ detail.category }}</a-descriptions-item>
            <a-descriptions-item label="Timeout">{{ detail.timeout_seconds }}s</a-descriptions-item>
            <a-descriptions-item label="Plugin Class"><code>{{ detail.plugin_class }}</code></a-descriptions-item>
            <a-descriptions-item label="Dependencies">
              <pre>{{ JSON.stringify(detail.dependencies, null, 2) }}</pre>
            </a-descriptions-item>
          </a-descriptions>

          <h4 style="margin-top: 16px;">Input Schema</h4>
          <a-table :columns="inputCols" :data-source="detail.input_schema" size="small" bordered :pagination="false" />

          <h4 style="margin-top: 16px;">Parameters</h4>
          <a-table :columns="paramCols" :data-source="detail.parameter_schema" size="small" bordered :pagination="false" />

          <h4 style="margin-top: 16px;">Output Schema</h4>
          <a-table :columns="outputCols" :data-source="detail.output_schema" size="small" bordered :pagination="false" />
        </template>
      </a-drawer>
    </div>
  </Page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Page } from '@vben/common-ui';
import { requestClient } from '#/api/request';

interface ToolInfo {
  tool_id: string; display_name: string; description: string;
  category: string; version: string; timeout_seconds: number;
  plugin_class: string; dependencies: Record<string, string[]>;
  input_schema: any[]; parameter_schema: any[]; output_schema: any[];
}

const tools = ref<ToolInfo[]>([]);
const loading = ref(false);
const drawerVisible = ref(false);
const detail = ref<ToolInfo | null>(null);

const columns = [
  { title: 'Tool', key: 'display_name', width: 220 },
  { title: 'Category', key: 'category', width: 100 },
  { title: 'Version', key: 'version', width: 80 },
  { title: 'Deps', key: 'deps', width: 200 },
  { title: 'Class', key: 'class' },
  { title: '', key: 'action', width: 80 },
];
const inputCols = [
  { title: 'Name', dataIndex: 'name', width: 120 },
  { title: 'Label', dataIndex: 'label', width: 120 },
  { title: 'Asset Types', dataIndex: 'accepted_asset_types', width: 160 },
  { title: 'Formats', dataIndex: 'accepted_formats', width: 100 },
  { title: 'Roles', dataIndex: 'accepted_file_roles', width: 160 },
  { title: 'Req', dataIndex: 'required', width: 60 },
];
const paramCols = [
  { title: 'Name', dataIndex: 'name', width: 120 },
  { title: 'Label', dataIndex: 'label', width: 120 },
  { title: 'Type', dataIndex: 'type', width: 100 },
  { title: 'Default', dataIndex: 'default', width: 100 },
];
const outputCols = [
  { title: 'Name', dataIndex: 'name', width: 120 },
  { title: 'Label', dataIndex: 'label', width: 120 },
  { title: 'Format', dataIndex: 'format', width: 100 },
];
const roleCols = [
  { title: 'Role Code', dataIndex: 'code', width: 250 },
  { title: 'Used For', dataIndex: 'usage', width: 350 },
];
const fileRoles = [
  { code: 'functional_annotation_table', usage: 'GO, KEGG, eggNOG, AHRD tables' },
  { code: 'functional_annotation_db', usage: 'SQLite annotation databases' },
  { code: 'gene_models', usage: 'GFF3/GTF gene structure' },
  { code: 'transcript_sequence', usage: 'mRNA, CDS FASTA' },
  { code: 'protein_sequence', usage: 'Protein FASTA' },
  { code: 'genome_sequence', usage: 'Reference FASTA' },
];

const pyprojectToml = `[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "fance-plugin-my-analysis"
version = "1.0.0"
requires-python = ">=3.10"

[project.entry-points."fance.analysis_tools"]
my_tool = "my_plugin.tool:MyAnalysisTool"`;

const toolPy = `from basis.analysis.base import (
    BaseAnalysisTool, FileParam, ChoiceParam,
    FloatParam, FileOutput,
)

class MyAnalysisTool(BaseAnalysisTool):
    tool_id = "my_analysis"
    display_name = "My Analysis"
    category = "annotation"

    inputs = [
        FileParam(
            name="gene_list", label="Gene List",
            accepted_asset_types=["functional_annotation"],
            accepted_formats=["txt", "tsv"],
            accepted_file_roles=["functional_annotation_table"],
        ),
    ]
    parameters = [
        ChoiceParam(name="method", label="Method",
                    choices=["a","b"], default="a"),
        FloatParam(name="pvalue", label="P-value",
                   default=0.05, min=0.001, max=1.0),
    ]
    outputs = [
        FileOutput(name="result", format="tsv", label="Result"),
    ]

    def build_command(self, file_paths, params, work_dir):
        return ["my_tool", "--in", file_paths["gene_list"],
                "--pval", str(params["pvalue"]),
                "--out", f"{work_dir}/result.tsv"]

    def validate_outputs(self, work_dir):
        p = f"{work_dir}/result.tsv"
        return [p] if os.path.exists(p) else []`;

function showDetail(record: ToolInfo) {
  detail.value = record;
  drawerVisible.value = true;
}

async function loadTools() {
  loading.value = true;
  try {
    const resp: any = await requestClient.get('/analysis/admin/tools');
    tools.value = resp?.data || resp || [];
  } finally {
    loading.value = false;
  }
}

onMounted(loadTools);
</script>
