# Expression Query Tool — Improvement Plan

> **Date:** 2026-05-06 | **Status:** Planning

## Current State

Expression adapter supports only 3 operations:
- `genes_list` — return all gene names from H5 file
- `samples_list` — return all sample names
- `matrix_slice` — return expression matrix for selected genes × samples

Frontend: multi-select dropdowns for genes/samples, table/heatmap toggle for results.

## P0: Gene Search & Sample Grouping (BLOCKED — needs backend first)

### Gene Autocomplete

**Problem**: Multi-select from 10K+ genes is unusable. Need search-as-you-type.

**Backend requirement**: New API endpoint that accepts `?q=SAM1A` and returns matching gene IDs.

**PostgreSQL considerations**:
- The gene list comes from HDF5 file (via `load_gene_sample_names`), NOT from PostgreSQL
- Adding autocomplete would require: (a) caching gene list in PG, or (b) querying H5 file per keystroke
- Option (a): Create a materialized view or cache table populated during dataset registration. Minimal read load (simple LIKE query with index). Recommended.
- Option (b): Load full gene list into memory on first request, serve from Python cache. Simpler, but per-worker memory.

**Recommendation**: Option (b) for initial implementation — cache in adapter instance as a Python set, filter with simple substring match. No PG changes needed.

**Frontend**: Replace MultiSelectDropdown with `<el-autocomplete>` component.

### Sample Metadata Grouping

**Problem**: Need to group samples by tissue, treatment, timepoint, etc.

**Backend requirement**: Sample metadata must be available through the API.

**Current state**: Sample metadata exists as a JSON file (`*.h5.json`) next to the H5 file, containing per-sample attributes. The adapter does NOT currently expose this.

**Implementation**: New operation `sample_metadata` that reads the JSON and returns `[{sample_id, tissue, treatment, timepoint, ...}]`. The frontend can then group by these fields.

**Status**: ⚠️ BLOCKED — needs backend work first. Estimated effort: 1-2 days.

## P1: Result Visualization (ACHIEVABLE NOW ✅)

These improvements only consume the existing `matrix_slice` response — no backend changes needed.

### 1. Add Bar Chart / Line Graph views

Add to DataVisualization component alongside Table and Heatmap:

- **Bar Chart**: Best for comparing expression of multiple genes in ONE sample
- **Line Graph**: Best for time-series expression (multiple timepoints for one gene)
- Use ECharts (already available)

### 2. Clustered Heatmap

- Add row (gene) and column (sample) clustering using simple hierarchical clustering
- Can be done client-side with a lightweight TS library or basic implementation
- Color scale controls (min/max, color palette selector)

### 3. Data Export

- **CSV download**: One button, generates CSV from current query result
- **PNG/SVG export**: For heatmap/chart views (ECharts has built-in `getDataURL`)

### 4. Data Normalization Toggle

- Raw count / FPKM / log2(FPKM+1) / Z-score
- All transformation done client-side on the matrix data
- No backend changes needed

## P2: Advanced Analysis (FUTURE — needs new backend services)

### Co-expression Network
- Compute pairwise correlation (Pearson/Spearman) between genes across samples
- Needs: statistical computation in backend or pre-computed correlation matrices
- Technology: scipy/numpy in Python backend, or pre-compute during data registration
- Frontend: Cytoscape.js or ECharts graph

### Gene Expression Similarity Search ("Gene Fishing")
- Given a gene, find genes with similar expression patterns
- Needs: correlation computation on-demand (computationally expensive for 10K+ genes)
- Could use: pre-computed similarity index (annoy/faiss) or PG vector search

### Differential Expression
- Compare two groups of samples (e.g., treatment vs control)
- Needs: statistical testing in backend (scipy.stats)
- Display: volcano plot, MA plot

## Recommended Execution Order

| Phase | Content | Depends On |
|-------|---------|------------|
| **Phase 1** | Bar/Line chart, CSV export, normalization toggle | Nothing — ready now |
| **Phase 2** | Gene autocomplete (Python cache) | 1-2 days backend |
| **Phase 3** | Sample metadata API + grouping | 2-3 days backend + frontend |
| **Phase 4** | Clustered heatmap, export images | Phase 1 |
| **Phase 5** | Co-expression, gene fishing, DE analysis | New backend services (weeks) |

**Recommendation**: Start Phase 1 immediately (visualization + export). Phase 2-3 need backend work and should be planned separately. Phase 5 is a separate project.
