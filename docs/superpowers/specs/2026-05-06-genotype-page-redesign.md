# Genotype Page Redesign

> **Date:** 2026-05-06 | **Status:** Design Approved

## References

- SnpHub (GigaScience 2020): smart single-input search, collapsible advanced filters
- CuGenDBv2: per-sample genotype table display (Sample | Accession | Group | Allele)

## Current State

`public-web/src/views/genotype/index.vue`: dataset dropdown + 3 raw inputs (chrom/start/end) + Query button → DataVisualization. Only single-region query, no gene lookup, no sample filtering.

## Goal

A unified, intelligent genotype query interface — simpler than CuGenDBv2 (no multiple input modes) and more visual than SnpHub (better result display).

---

## Architecture

### One Search Box, Three Input Types

```
User types anything → frontend classifies → routes to correct backend path
```

| Input Example | Type | Parse Rule | Backend Path |
|---|---|---|---|
| `Cla97C04G070940` | Gene ID | Matches gene ID pattern (alphanumeric, no colon/underscore with digits) | annotation adapter `search_genes` → get chrom/start/stop → variant adapter `query` |
| `Chr04:15442000-15443000` | Region | Matches `chr:start-end` or `chr:start` | variant adapter `query` directly |
| `Cla97Chr04_15442323` | Variant ID | Variant ID from VCF (query via bcftools) | variant adapter `query_by_id` |

Input type auto-detection on frontend. If ambiguous, try variant adapter first; fall back to annotation adapter.

### Backend Changes Needed

**variant adapter** — new operation `query_by_id`:
- Accepts `variant_ids: string[]`
- Uses bcftools to query specific variant IDs directly from VCF/BCF
- Returns same format as `query` operation

### Page Layout

```
┌─────────────────────────────────────────────────────────┐
│  Genotype Query                                         │
│                                                         │
│  [Dataset: Rose Variome ▾]                              │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 🔍 Search genes, regions, or variant IDs...  [Go]  ││
│  └─────────────────────────────────────────────────────┘│
│  ↳ Parsed as: Gene Cla97C04G070940 → Chr04:15442000..  │
│                                                         │
│  [▼ Samples (233)]              [▼ Advanced Filters]    │
│   multi-select + search          MAF / missing rate     │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Results: 127 variants across 3 regions                 │
│  [Table] [Density Plot] [Heatmap]          [Export CSV]│
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Chrom │ Pos  │ Ref │ Alt │ Qual │ Genotypes │       ││
│  │ Chr04 │ 15.4M│ G   │ T   │ 999  │ 45/120/68 │  ▸   ││
│  │ Chr04 │ 15.4M│ A   │ C   │ 850  │ 67/98/68  │  ▸   ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  [Click row expands per-sample genotype ↓]              │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Sample ID  │ Accession │ Group      │ Allele        ││
│  │ XG0350     │ PI247398  │ landrace   │ G/T           ││
│  │ XG0351     │ PI490377  │ landrace   │ T/T           ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### Components

1. **SmartSearchBar.vue** — Single input with auto-type detection and type badge
2. **VariantTable.vue** — Main variant list with expandable rows (per-sample genotype)
3. **VariantDensityPlot.vue** — ECharts density chart along chromosome
4. **SampleFilter.vue** — Multi-select with search, loads from `samples_list`
5. **genotype/index.vue** — Page shell, orchestrates state

### Data Flow

```
[SmartSearchBar]
  │ input string
  ▼
[type detection]
  ├─ gene ID → useAnnotationAdapter.searchGenes(id) → {chrom, start, stop}
  │            → useVariantAdapter.query({regions: [`chrom:start-stop`]})
  ├─ region  → useVariantAdapter.query({regions: [input]})
  └─ variant ID → useVariantAdapter.queryById({variant_ids: [input]})
  │
  ▼
[VariantTable] ← queryResult.rows
  │ click row
  ▼
[PerSampleTable] ← variant.sampleGenotypes
```

### Sample Genotypes Data

variant adapter `query` response already includes VCF preview text. Frontend parses the VCF rows into:
- Per-variant rows: chrom, pos, ref, alt, qual
- Per-sample genotypes: extracted from GT column → ref/ref, ref/alt, alt/alt counts + allele string

### Edge Cases

- **Empty search**: Show placeholder with example queries
- **Gene not found**: Show "No genes matched, searching as region..."
- **Region out of bounds**: bcftools returns empty, show "No variants in this region"
- **Large result (>10K variants)**: Paginate, warn with "Showing first N results"
- **Dataset not ready**: Use existing draft warning alert pattern
