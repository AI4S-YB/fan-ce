# FAN-CE Analysis Plugin Development Guide

## Quick Start

Create a minimal GO Enrichment plugin in 5 minutes.

### 1. Project Structure

```
my-fance-plugin/
├── pyproject.toml
└── my_plugin/
    ├── __init__.py
    └── tool.py
```

### 2. pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "fance-plugin-my-analysis"
version = "1.0.0"
requires-python = ">=3.10"

[project.entry-points."fance.analysis_tools"]
my_tool = "my_plugin.tool:MyAnalysisTool"
```

### 3. Tool Implementation (tool.py)

```python
from basis.analysis.base import (
    BaseAnalysisTool, FileParam, ChoiceParam,
    FloatParam, IntParam, TextParam, FileOutput,
)

class MyAnalysisTool(BaseAnalysisTool):
    tool_id = "my_analysis"           # unique, lowercase, underscores only
    tool_version = "1.0.0"
    display_name = "My Analysis"
    description = "What this tool does"
    category = "annotation"           # annotation|sequence|variant|expression|utility

    # ── Input files (system-registered asset_files) ──
    inputs = [
        FileParam(
            name="gene_list",
            label="Gene List File",
            accepted_asset_types=["functional_annotation"],
            accepted_formats=["txt", "tsv"],
            accepted_file_roles=["functional_annotation_table"],
            description="One gene ID per line.",
        ),
    ]

    # ── Parameters (user-adjustable) ──
    parameters = [
        ChoiceParam(
            name="method", label="Method",
            choices=["method_a", "method_b"],
            default="method_a",
        ),
        FloatParam(
            name="pvalue", label="P-value Cutoff",
            default=0.05, min=0.001, max=1.0,
        ),
        IntParam(
            name="top_n", label="Top N Results",
            default=20, min=1, max=100,
        ),
        TextParam(
            name="extra_args", label="Extra Arguments",
            default="",
        ),
    ]

    # ── Outputs ──
    outputs = [
        FileOutput(name="result_table", format="tsv", label="Result Table"),
        FileOutput(name="result_plot", format="png", label="Result Plot"),
    ]

    timeout_seconds = 600                     # 10 min hard limit
    dependencies = {"conda": ["my-tool>=1.0"]}  # software deps

    def build_command(self, file_paths: dict, params: dict, work_dir: str) -> list:
        """Build the shell command to execute."""
        return [
            "my_tool",
            "--input", file_paths["gene_list"],
            "--method", params["method"],
            "--pvalue", str(params["pvalue"]),
            "--top", str(params["top_n"]),
            "--out", f"{work_dir}/result_table.tsv",
            "--plot", f"{work_dir}/result_plot.png",
        ]

    def validate_outputs(self, work_dir: str) -> list:
        """Verify outputs exist. Return absolute paths."""
        import os
        results = []
        for out in self.outputs:
            path = os.path.join(work_dir, f"{out.name}.{out.format}")
            if os.path.exists(path):
                results.append(path)
        return results
```

### 4. Install & Verify

```bash
# Install the plugin
pip install /path/to/my-fance-plugin

# Restart FAN-CE backend
bash scripts/dev/start-backend.sh

# Check tool is registered
curl http://localhost:8002/api/v1/analysis/tools
```

### 5. Run a Job

```bash
curl -X POST http://localhost:8002/api/v1/analysis/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "my_analysis",
    "input_bindings": {"gene_list": 82},
    "param_overrides": {"pvalue": 0.01}
  }'
```

---

## Reference

### FileParam Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Internal param name (used in input_bindings) |
| `label` | str | Display name in UI |
| `accepted_asset_types` | list | e.g. `["functional_annotation", "gene_annotation"]` |
| `accepted_formats` | list | e.g. `["gaf", "txt", "fa.gz"]` |
| `accepted_file_roles` | list | e.g. `["functional_annotation_table", "transcript_sequence"]` |
| `accepted_dataset_types` | list | e.g. `["genome", "transcriptome"]` |
| `required` | bool | Is this input mandatory? |
| `description` | str | Help text |

### Parameter Types

| Type | Key Fields |
|------|-----------|
| `TextParam` | `name`, `label`, `default` |
| `ChoiceParam` | `name`, `label`, `choices`, `default` |
| `IntParam` | `name`, `label`, `default`, `min`, `max` |
| `FloatParam` | `name`, `label`, `default`, `min`, `max` |

### File Role Codes (asset_file_type_registry)

| Role Code | Used For |
|-----------|----------|
| `functional_annotation_table` | GO, KEGG, eggNOG, AHRD tables |
| `functional_annotation_db` | SQLite annotation databases |
| `gene_models` | GFF3/GTF gene structure |
| `gene_models_index` | GFF/GTF tabix index |
| `transcript_sequence` | mRNA, CDS FASTA |
| `transcript_sequence_index` | mRNA/CDS FASTA index |
| `protein_sequence` | Protein FASTA |
| `protein_sequence_index` | Protein FASTA index |
| `genome_sequence` | Reference FASTA |
| `genome_sequence_index` | FASTA index (.fai) |

### Output File Formats

| Format | File Extension |
|--------|---------------|
| `tsv` | .tsv |
| `csv` | .csv |
| `txt` | .txt |
| `png` | .png |
| `pdf` | .pdf |
| `vcf` | .vcf / .vcf.gz |
| `fa` | .fa / .fa.gz |

### Security

- `build_command` **must** return a list (not a shell string) to prevent injection
- Each job runs in an isolated `work_dir` (`/tmp/fance-jobs/<job_id>/`)
- Hard timeout enforced via `timeout_seconds` (default: 3600)
- Output files are validated via `validate_outputs()` before marking success

### LLM Integration (Automatic)

When your tool is registered, it's automatically exposed as an LLM tool.
Users can say "Run my analysis with p=0.01" and the LLM will call your tool.
No extra code needed.
