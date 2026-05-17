"""KEGG Pathway Enrichment — uses local func_anno SQLite data, no KEGG API needed."""
import os
from omics.analysis.base import (
    BaseAnalysisTool, FileParam, TextParam, ChoiceParam, FloatParam, IntParam, FileOutput,
)


class KeggEnrichTool(BaseAnalysisTool):
    tool_id = "kegg_enrich"
    tool_version = "1.0.0"
    display_name = "KEGG Pathway Enrichment"
    description = (
        "KEGG pathway enrichment analysis using Fisher's exact test on local "
        "functional annotation data. No external API calls — all pathway "
        "annotations are read from the func_anno SQLite database."
    )
    category = "annotation"

    inputs = [
        FileParam(
            name="func_anno_db",
            label="Functional Annotation DB",
            accepted_asset_types=["functional_annotation"],
            accepted_formats=["db", "sqlite"],
            accepted_file_roles=["functional_annotation_db"],
            description="SQLite functional annotation database with KEGG pathway annotations.",
        ),
    ]

    parameters = [
        TextParam(
            name="gene_list",
            label="Gene ID List",
            default="",
            description="One gene ID per line. Genes not found in the annotation are skipped.",
        ),
        ChoiceParam(
            name="method", label="Correction Method",
            choices=["fdr_bh", "bonferroni"],
            default="fdr_bh",
        ),
        FloatParam(
            name="alpha", label="Significance Level",
            default=0.05, min=0.001, max=1.0,
        ),
        IntParam(
            name="min_genes", label="Min Genes per Pathway",
            default=3, min=1, max=100,
        ),
    ]

    outputs = [
        FileOutput(name="enrichment_table", format="tsv", label="Enrichment Table", display="table"),
        FileOutput(name="enrichment_plot", format="png", label="Dot Plot", display="image"),
    ]

    timeout_seconds = 300
    dependencies = {}

    def build_command(self, file_paths: dict, params: dict, work_dir: str) -> list:
        gene_list = params.get("gene_list", "")
        gene_path = os.path.join(work_dir, "gene_list.txt")
        with open(gene_path, "w") as f:
            f.write(gene_list)
        script = self._generate_script(gene_path, file_paths, params, work_dir)
        script_path = os.path.join(work_dir, "run_enrich.py")
        with open(script_path, "w") as f:
            f.write(script)
        return ["python", script_path]

    def validate_outputs(self, work_dir: str) -> list:
        found = []
        for name in ["enrichment_table.tsv", "enrichment_plot.png"]:
            p = os.path.join(work_dir, name)
            if os.path.exists(p):
                found.append(p)
        return found

    def _generate_script(self, gene_path, file_paths, params, work_dir):
        db_path = file_paths["func_anno_db"]
        method = params.get("method", "fdr_bh")
        alpha = params.get("alpha", 0.05)
        min_genes = params.get("min_genes", 3)
        return f'''
import sqlite3, json, math, os, sys

os.chdir("{work_dir}")

# ── 1. Read gene→pathway mapping from SQLite ──
db_path = "{db_path}"
if not os.path.exists(db_path):
    print(f"ERROR: Database not found: {{db_path}}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

gene_pathways = {{}}  # gene_id → set of pathway map IDs
pathway_info = {{}}    # map_id → description

rows = conn.execute("SELECT transcript_id, KEGG FROM hse_transcripts WHERE KEGG IS NOT NULL AND KEGG != '' AND KEGG != '[]'").fetchall()
for row in rows:
    gene_id = row["transcript_id"]
    try:
        kegg_data = json.loads(row["KEGG"])
    except (json.JSONDecodeError, TypeError):
        continue
    if not kegg_data:
        continue
    for entry in kegg_data:
        pw = entry.get("pathway", "")
        if not pw:
            continue
        desc = entry.get("description", pw)
        if pw not in pathway_info:
            pathway_info[pw] = desc
        if gene_id not in gene_pathways:
            gene_pathways[gene_id] = set()
        gene_pathways[gene_id].add(pw)

conn.close()

pop_genes = list(gene_pathways.keys())
pop_n = len(pop_genes)
print(f"Population: {{pop_n}} genes with KEGG annotations, {{len(pathway_info)}} pathways")

# ── 2. Read study gene list ──
with open("{gene_path}") as f:
    study_input = [line.strip().split()[0] for line in f if line.strip()]

study_genes = [g for g in study_input if g in gene_pathways]
study_n = len(study_genes)
print(f"Study genes (with KEGG): {{study_n}} / {{len(study_input)}} input")

if study_n == 0:
    print("ERROR: No study genes found in the KEGG annotation")
    sys.exit(1)

# ── 3. Fisher's exact test for each pathway ──
def fisher_exact(a, b, c, d):
    """Two-tailed Fisher's exact test p-value for 2x2 table [[a,b],[c,d]]."""
    # Hypergeometric probability: P(X=k) = C(a+b,a) * C(c+d,c) / C(N,a+c)
    from math import comb
    n = a + b + c + d
    k = a
    K = a + c
    N = n
    n_row = a + b

    p_obs = comb(K, k) * comb(N - K, n_row - k) / comb(N, n_row)

    p_val = 0.0
    for i in range(max(0, n_row + K - N), min(n_row, K) + 1):
        p_i = comb(K, i) * comb(N - K, n_row - i) / comb(N, n_row)
        if p_i <= p_obs + 1e-15:
            p_val += p_i

    return min(p_val, 1.0)

def bh_fdr(pvalues):
    """Benjamini-Hochberg FDR correction. Returns adjusted p-values."""
    n = len(pvalues)
    indexed = sorted(enumerate(pvalues), key=lambda x: x[1])
    adjusted = [0.0] * n
    for rank, (idx, p) in enumerate(indexed):
        adjusted[idx] = min(p * n / (rank + 1), 1.0)
    # Ensure monotonicity
    for i in range(n - 2, -1, -1):
        adjusted[indexed[i][0]] = min(adjusted[indexed[i][0]], adjusted[indexed[i+1][0]])
    return adjusted

rows = []
for pw_id, pw_desc in pathway_info.items():
    pw_genes = {{g for g, pws in gene_pathways.items() if pw_id in pws}}
    pop_with = len(pw_genes)
    if pop_with < {min_genes}:
        continue

    study_with = len([g for g in study_genes if pw_id in gene_pathways.get(g, set())])
    if study_with < {min_genes}:
        continue

    # 2x2 table:
    #                 In pathway    Not in pathway
    # Study genes        a               b
    # Not in study       c               d
    a = study_with
    b = study_n - study_with
    c = pop_with - study_with
    d = pop_n - study_n - c

    p_val = fisher_exact(a, b, c, d)

    if pop_n > 0 and pop_with > 0:
        enrichment = (a / study_n) / (pop_with / pop_n) if study_n > 0 else 0
    else:
        enrichment = 0

    rows.append((pw_id, pw_desc, enrichment, p_val, study_with, pop_with))

if not rows:
    print("No pathways passed the min_genes filter")
    # Write empty table
    with open("{work_dir}/enrichment_table.tsv", "w") as out:
        out.write("Pathway\\tDescription\\tEnrichment\\tP_value\\tP_corrected\\tStudyCount\\tPopCount\\n")
    sys.exit(0)

# ── 4. Multiple testing correction ──
pvals = [r[3] for r in rows]
method = "{method}"

if method == "fdr_bh":
    p_corr = bh_fdr(pvals)
elif method == "bonferroni":
    p_corr = [min(p * len(pvals), 1.0) for p in pvals]
else:
    p_corr = pvals

# Merge correction
rows_corr = []
for i, r in enumerate(rows):
    rows_corr.append((*r, p_corr[i]))
rows_corr.sort(key=lambda x: x[6])  # sort by corrected p-value

# ── 5. Write enrichment table ──
with open("{work_dir}/enrichment_table.tsv", "w") as out:
    out.write("Pathway\\tDescription\\tEnrichment\\tP_value\\tP_corrected\\tStudyCount\\tPopCount\\n")
    for r in rows_corr:
        out.write(f"{{r[0]}}\\t{{r[1]}}\\t{{r[2]:.4f}}\\t{{r[3]:.4e}}\\t{{r[6]:.4e}}\\t{{r[4]}}\\t{{r[5]}}\\n")

sig = [r for r in rows_corr if r[6] < {alpha}]
print(f"Enriched pathways: {{len(sig)}} / {{len(rows_corr)}} (alpha={alpha})")

# ── 6. Dot plot ──
if sig:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    top = sig[:20]
    h = max(3, 0.35 * len(top) + 1.5)
    fig, ax = plt.subplots(figsize=(12, h))
    y_pos = list(range(len(top)))
    enrich_vals = [r[2] for r in top]
    sizes = [max(20, r[4] * 10) for r in top]
    colors = [-math.log10(max(r[6], 1e-100)) for r in top]
    sc = ax.scatter(enrich_vals, y_pos, s=sizes, c=colors, cmap='Reds', alpha=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([r[1][:50] for r in top], fontsize=9)
    ax.set_xlabel('Fold Enrichment')
    ax.set_title('KEGG Pathway Enrichment')
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label('-log10(P_corrected)')
    plt.tight_layout()
    plt.savefig("{work_dir}/enrichment_plot.png", dpi=150)
    print("Dot plot saved")
else:
    # Generate empty plot
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.text(0.5, 0.5, 'No significant pathways', ha='center', va='center', fontsize=14, color='gray')
    ax.set_axis_off()
    plt.savefig("{work_dir}/enrichment_plot.png", dpi=150)

print("KEGG enrichment complete")
'''
