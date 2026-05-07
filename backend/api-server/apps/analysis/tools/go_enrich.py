"""GO Enrichment analysis — embedded reference implementation."""
import os
import subprocess
from basis.analysis.base import (
    BaseAnalysisTool, FileParam, TextParam, ChoiceParam, FloatParam, IntParam, FileOutput,
)

GO_OBO_URL = "http://purl.obolibrary.org/obo/go/go-basic.obo"
GO_OBO_CACHE = os.path.join(os.path.dirname(__file__), "go-basic.obo")


def _ensure_obo() -> str:
    """Return path to go-basic.obo, downloading if necessary."""
    if not os.path.exists(GO_OBO_CACHE):
        print(f"Downloading GO OBO from {GO_OBO_URL}...")
        import subprocess
        subprocess.run(["curl", "-sL", "-o", GO_OBO_CACHE, GO_OBO_URL], check=True, timeout=120)
        print(f"Cached to {GO_OBO_CACHE}")
    return GO_OBO_CACHE


class GoEnrichTool(BaseAnalysisTool):
    tool_id = "go_enrich"
    tool_version = "1.0.0"
    display_name = "GO Enrichment Analysis"
    description = "Gene Ontology enrichment analysis using Fisher's exact test. "
    "The GO OBO ontology is bundled — only gene list and GO annotation file are needed."
    category = "annotation"

    inputs = [
        FileParam(
            name="go_annotation",
            label="GO Annotation (GAF)",
            accepted_asset_types=["functional_annotation"],
            accepted_formats=["gaf"],
            accepted_file_roles=["functional_annotation_table"],
            description="Gene-to-GO-term mapping in GAF format (go_gene.gaf).",
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
            choices=["fdr_bh", "bonferroni", "sidak", "holm"],
            default="fdr_bh",
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
        obo_path = _ensure_obo()
        # Write gene list from text param to temp file
        gene_list = params.get("gene_list", "")
        gene_path = os.path.join(work_dir, "gene_list.txt")
        with open(gene_path, "w") as f:
            f.write(gene_list)
        script = self._generate_script(gene_path, file_paths, params, work_dir, obo_path)
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

    def _generate_script(self, gene_path, file_paths, params, work_dir, obo_path):
        return f'''
import sys, os
os.chdir("{work_dir}")
sys.path.insert(0, "{work_dir}")

try:
    from goatools.obo_parser import GODag
    from goatools.go_enrichment import GOEnrichmentStudy
except ImportError as e:
    print(f"Missing dependency: {{e}}")
    print("Install: pip install goatools statsmodels")
    sys.exit(1)

print(f"Loading GO DAG from {obo_path}...")
obodag = GODag("{obo_path}", optional_attrs=['relationship'])

print(f"Loading annotations from {file_paths['go_annotation']}...")
# Custom GAF parser — goatools read_gaf is too strict for non-standard dates
geneid2gos = {{}}
with open("{file_paths['go_annotation']}") as f:
    for line in f:
        if line.startswith("!"):
            continue
        fields = line.strip().split("\\t")
        if len(fields) < 6:
            continue
        gene_id = fields[1]  # col 2: DB_Object_ID
        go_id = fields[4]    # col 5: GO ID
        if gene_id not in geneid2gos:
            geneid2gos[gene_id] = set()
        geneid2gos[gene_id].add(go_id)
print(f"Loaded {{len(geneid2gos)}} genes with GO annotations")

print(f"Loading study genes from {gene_path}...")
with open("{gene_path}") as f:
    study_genes = [line.strip().split()[0] for line in f if line.strip()]

pop_genes = list(geneid2gos.keys())
study_genes = [g for g in study_genes if g in geneid2gos]
print(f"Study genes (found): {{len(study_genes)}}, Population: {{len(pop_genes)}}")

goea = GOEnrichmentStudy(
    pop_genes, geneid2gos, obodag,
    methods=['{params.get("method", "fdr_bh")}'],
    alpha={params.get("alpha", 0.05)},
    propagate_counts=False,
)
results = goea.run_study(study_genes)

method_key = 'p_{params.get("method", "fdr_bh")}'

rows = []
for r in results:
    if r.study_count < {params.get("min_genes", 3)}:
        continue
    p_corr = getattr(r, method_key, r.p_uncorrected)
    rows.append((r.GO, r.name, r.enrichment, r.p_uncorrected, p_corr, r.study_count, r.pop_count))

rows.sort(key=lambda x: x[4])

with open("{work_dir}/enrichment_table.tsv", "w") as out:
    out.write("GO_ID\\tTerm\\tEnrichment\\tP_value\\tP_corrected\\tStudyCount\\tPopCount\\n")
    for r in rows:
        out.write(f"{{r[0]}}\\t{{r[1]}}\\t{{r[2]:.2f}}\\t{{r[3]:.4e}}\\t{{r[4]:.4e}}\\t{{r[5]}}\\t{{r[6]}}\\n")
print(f"Wrote {{len(rows)}} enriched terms")

if rows:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import math

    top = rows[:20]
    h = max(3, 0.35 * len(top) + 1.5)
    fig, ax = plt.subplots(figsize=(10, h))
    y_pos = range(len(top))
    enrich_vals = [r[2] for r in top]
    sizes = [max(20, r[5] * 10) for r in top]
    colors = [-math.log10(max(r[4], 1e-100)) for r in top]
    sc = ax.scatter(enrich_vals, y_pos, s=sizes, c=colors, cmap='Reds', alpha=0.8)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels([r[1][:45] for r in top], fontsize=9)
    ax.set_xlabel('Fold Enrichment')
    ax.set_title("GO Enrichment ({params.get('ontology', 'BP')})")
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label('-log10(P_corrected)')
    plt.tight_layout()
    plt.savefig("{work_dir}/enrichment_plot.png", dpi=150)
    print("Dot plot saved")

print("GO enrichment complete")
'''
