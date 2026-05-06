"""GO Enrichment analysis — embedded reference implementation."""
import os
import subprocess
from basis.analysis.base import (
    BaseAnalysisTool, FileParam, ChoiceParam, FloatParam, IntParam, FileOutput,
)


class GoEnrichTool(BaseAnalysisTool):
    tool_id = "go_enrich"
    tool_version = "1.0.0"
    display_name = "GO Enrichment Analysis"
    description = "Gene Ontology enrichment analysis using Fisher's exact test with multiple correction"
    category = "annotation"

    inputs = [
        FileParam(
            name="gene_list",
            label="Gene List File",
            accepted_asset_types=["functional_annotation"],
            accepted_formats=["txt", "tsv"],
            description="One gene ID per line, or two-column TSV (gene_id + optional universe)",
        ),
        FileParam(
            name="go_annotation",
            label="GO Annotation File",
            accepted_asset_types=["functional_annotation"],
            accepted_formats=["gaf", "tsv", "txt"],
            description="Gene-to-GO-terms mapping (GAF format or simple two-column TSV)",
        ),
        FileParam(
            name="go_obo",
            label="GO Ontology (OBO)",
            accepted_asset_types=["functional_annotation"],
            accepted_formats=["obo"],
            description="Gene Ontology OBO file (e.g. go-basic.obo)",
        ),
    ]

    parameters = [
        ChoiceParam(
            name="ontology", label="Ontology",
            choices=["BP", "MF", "CC"], default="BP",
            description="GO sub-ontology to test",
        ),
        ChoiceParam(
            name="method", label="Correction Method",
            choices=["fdr_bh", "bonferroni", "sidak", "holm"],
            default="fdr_bh",
            description="Multiple test correction",
        ),
        FloatParam(
            name="alpha", label="Significance Level",
            default=0.05, min=0.001, max=1.0,
        ),
        IntParam(
            name="min_genes", label="Min Genes per Term",
            default=3, min=1, max=100,
        ),
    ]

    outputs = [
        FileOutput(name="enrichment_table", format="tsv", label="Enrichment Table"),
        FileOutput(name="enrichment_plot", format="png", label="Dot Plot"),
    ]

    timeout_seconds = 600
    dependencies = {"conda": ["goatools"]}

    def build_command(self, file_paths: dict, params: dict, work_dir: str) -> list:
        script = self._generate_script(file_paths, params, work_dir)
        script_path = os.path.join(work_dir, "run_enrich.py")
        with open(script_path, "w") as f:
            f.write(script)
        return ["python", script_path]

    def validate_outputs(self, work_dir: str) -> list:
        table = os.path.join(work_dir, "enrichment_table.tsv")
        plot = os.path.join(work_dir, "enrichment_plot.png")
        found = []
        if os.path.exists(table):
            found.append(table)
        if os.path.exists(plot):
            found.append(plot)
        return found

    def _generate_script(self, file_paths, params, work_dir):
        return f'''
import sys, os
os.chdir("{work_dir}")
sys.path.insert(0, "{work_dir}")

try:
    from goatools.obo_parser import GODag
    from goatools.go_enrichment import GOEnrichmentStudy
    from goatools.associations import read_gaf
    from statsmodels.stats.multitest import multipletests
except ImportError as e:
    print(f"Missing dependency: {{e}}")
    print("Install: pip install goatools statsmodels")
    sys.exit(1)

obodag = GODag("{file_paths['go_obo']}", optional_attrs=['relationship'])

# Load associations
geneid2gos = read_gaf("{file_paths['go_annotation']}")

# Load study genes
with open("{file_paths['gene_list']}") as f:
    study_genes = [line.strip().split()[0] for line in f if line.strip()]

pop_genes = list(geneid2gos.keys())
study_genes = [g for g in study_genes if g in geneid2gos]
print(f"Study genes: {{len(study_genes)}}, Population: {{len(pop_genes)}}")

goea = GOEnrichmentStudy(
    pop_genes, geneid2gos, obodag,
    methods=['{params['method']}'],
    alpha={params['alpha']},
    propagate_counts=False,
)
results = goea.run_study(study_genes)

method_key = 'p_{params['method']}'
min_genes = {params['min_genes']}

# Filter & write table
rows = []
for r in results:
    if r.study_count < min_genes:
        continue
    p_corr = getattr(r, method_key, r.p_uncorrected)
    rows.append((r.GO, r.name, r.enrichment, r.p_uncorrected, p_corr, r.study_count, r.pop_count))

rows.sort(key=lambda x: x[4])  # sort by corrected p-value

with open("{work_dir}/enrichment_table.tsv", "w") as out:
    out.write("GO_ID\\tTerm\\tEnrichment\\tP_value\\tP_corrected\\tStudyCount\\tPopCount\\n")
    for r in rows:
        out.write(f"{{r[0]}}\\t{{r[1]}}\\t{{r[2]:.2f}}\\t{{r[3]:.4e}}\\t{{r[4]:.4e}}\\t{{r[5]}}\\t{{r[6]}}\\n")
print(f"Wrote {{len(rows)}} enriched terms")

# Dot plot
if rows:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import math

    top = rows[:20]
    fig, ax = plt.subplots(figsize=(10, 0.4 * len(top) + 2))
    y = range(len(top))
    enrich_vals = [r[2] for r in top]
    sizes = [max(20, r[5] * 10) for r in top]
    colors = [-math.log10(max(r[4], 1e-100)) for r in top]
    sc = ax.scatter(enrich_vals, y, s=sizes, c=colors, cmap='Reds', alpha=0.8)
    ax.set_yticks(list(y))
    ax.set_yticklabels([r[1][:45] for r in top], fontsize=9)
    ax.set_xlabel('Fold Enrichment')
    ax.set_title("GO Enrichment ({params['ontology']})")
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label('-log10(P_corrected)')
    plt.tight_layout()
    plt.savefig("{work_dir}/enrichment_plot.png", dpi=150)
    print("Dot plot saved")

print("GO enrichment complete")
'''
