# Dataset Metadata System Redesign

> **Date:** 2026-05-02
> **Scope:** Dataset / Breeding metadata layer only
> **Status:** Approved

## Goal

Redesign the metadata system for datasets and breeding entities to support three LLM-powered scenarios:
1. **Dataset-level metadata** — describe what's inside a dataset so LLM can discover it
2. **Metadata-based search** — find datasets by structured fields + full-text search on description
3. **Content query with relationship traversal** — LLM follows dataset→sample→assay chains and cross-dataset lineage edges to expand query context

## Architecture: Three-Layer Model

```
Layer 1: Dataset Metadata  (dataset_registry)
Layer 2: Sample / Assay     (brd_biosample, brd_assay, + link tables)
Layer 3: Relationships      (dataset_lineage_edge — no changes)
```

LLM traversal path: metadata search → locate dataset → follow lineage edges to related datasets → follow breeding link tables to sample/assay context.

## Layer 1: Dataset Metadata

### Model Changes: `dataset_registry`

Add one column:

| Column | Type | Purpose |
|--------|------|---------|
| `description_md` | Text | Human-curated Markdown description of dataset content and context |

### Full-Text Index

PostgreSQL trigram index (`pg_trgm`) on `description_md` for full-text search. Trigram is preferred over `tsvector` because the content is Chinese + English mixed, and trigram handles substring matching well for gene names and mixed-language keywords.

### LLM Context Injection

When a dataset is located (via structured search or full-text match), its `description_md` content is auto-injected into the LLM conversation context. This enables the LLM to understand the dataset's contents without requiring complex metadata schemas.

### Existing Columns (No Changes)

- `organism` — species filter (typed, already exists)
- `assembly` — assembly version (typed, already exists)
- `dataset_type` — data type: sequence/expression/variant/phenome/annotation/interaction/signal
- `extra_json` — extensible JSON metadata (unstructured catch-all)

## Layer 2: Sample / Assay Metadata

### BreedingBioSample — Add 1 Column

| Column | Type | Purpose |
|--------|------|---------|
| `organism` | String(128) | Species name for LLM sample-level queries |

Existing columns (unchanged): sample_code, material_id, plot_id, sample_type, tissue_type, timepoint, treatment_label, collection_date, collector, storage_location, meta_json.

### BreedingAssay — Add 6 Columns

Core SRA fields as typed columns:

| Column | Type | Purpose |
|--------|------|---------|
| `library_strategy` | String(64) | WGS, RNA-Seq, ChIP-Seq, etc. |
| `library_source` | String(64) | GENOMIC, TRANSCRIPTOMIC, etc. |
| `library_selection` | String(64) | PolyA, RANDOM, ChIP, etc. |
| `library_layout` | String(32) | SINGLE, PAIRED |
| `instrument_model` | String(128) | HiSeq 4000, NovaSeq 6000, etc. |
| `read_length` | Integer | Read length in bp (e.g., 150 for PE150) |

Existing columns (unchanged): assay_code, biosample_id, assay_type, platform, vendor, run_date, meta_json.

### Fields in meta_json (Not Typed)

The following SRA-level fields remain in `meta_json` as user-extensible JSON:
design_description, library_construction_protocol, gc_content, quality_score, adapter_sequence, primer_sequence, target_gene, target_region, enrichment_method, amplification_method, insert_size, total_reads, total_bases, sequencing_center.

### Link Tables (No Changes)

- `brd_dataset_subject_link` — connects dataset → material/biosample/trial/plot
- `brd_dataset_assay_link` — connects dataset → assay
- `brd_variant_sample_map` — maps VCF sample names to materials/biosamples
- `brd_phenotype_subject_map` — maps phenotype rows to trials/plots/materials

## Layer 3: Dataset Relationships (No Changes)

Existing `dataset_lineage_edge` table with relation types:
- `derived_from` — expression matrix derived from raw FASTQ
- `cites` — dataset based on / uses data from another
- `complements` — variant dataset + annotation that explains it
- `references` — expression data references the reference genome
- `supersedes` — v2 replaces v1

Existing LLM tool `get_related_datasets` handles traversal.

## Out of Scope

- **Databases module** — dead code, no frontend consumers. Not being enhanced.
- **Sample/Experiment modules** — active but will migrate to breeding later. Not in this phase.
- **Basis app (BioSample/Experiment models)** — left as-is. Will be fully deprecated when breeding is complete.
- **Content adapters** — expression, variant, sequence, etc. adapters are unchanged.
- **BreedingBioSample.description_md** — explicitly excluded. User wants to keep sample/assay metadata simple for now.

## Query Patterns

### Pattern A: Metadata-First Discovery
```
User: "find rose leaf transcriptome datasets with drought treatment"
→ WHERE dataset_registry.organism = 'Rosa' AND dataset_type = 'expression'
  + full-text search description_md for 'drought'
→ Found dataset(s)
→ Inject description_md into LLM context
→ LLM summarizes findings with human-readable context
```

### Pattern B: Dataset → Sample Context
```
User: "what samples were used in dataset-042?"
→ Locate dataset-042
→ Follow brd_dataset_subject_link → BreedingBioSample records
→ Return sample list with tissue_type, treatment_label, timepoint, organism
```

### Pattern C: Cross-Dataset Traversal
```
User: "what gene is highly expressed in dataset-042?"
→ Query expression adapter on dataset-042 → top DE genes
→ get_related_datasets(dataset-042, relation='references')
→ Returns reference genome dataset
→ Query gene annotation on reference genome dataset
→ Return gene details with full annotation context
```

### Pattern D: Sample-Condition Query
```
User: "find RNA-seq datasets from HiSeq where samples were drought-treated leaf"
→ Search BreedingAssay: library_strategy='RNA-Seq', instrument_model='HiSeq 4000'
→ Linked biosamples: treatment_label='drought', tissue_type='leaf'
→ Follow brd_dataset_assay_link back to dataset
→ Return matching datasets with sample context
```

## Database Changes Summary

| Table | New Columns | Index Needed |
|-------|-------------|--------------|
| `dataset_registry` | `description_md TEXT` | Full-text (GIN or trigram) |
| `brd_biosample` | `organism VARCHAR(128)` | — |
| `brd_assay` | `library_strategy VARCHAR(64)` | Recommended |
| `brd_assay` | `library_source VARCHAR(64)` | — |
| `brd_assay` | `library_selection VARCHAR(64)` | — |
| `brd_assay` | `library_layout VARCHAR(32)` | — |
| `brd_assay` | `instrument_model VARCHAR(128)` | — |
| `brd_assay` | `read_length INTEGER` | — |

Total: 8 new columns, 1 full-text index, 1 recommended index.
