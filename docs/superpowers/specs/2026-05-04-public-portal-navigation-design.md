# Public Portal — Navigation & Genome Detail Design

> **Date:** 2026-05-04
> **Status:** Approved
> **Builds on:** `2026-05-04-public-database-frontend-design.md`

## Navigation Structure

### Header (global, always visible)

```
Rose Database  │  Genomes ▼  │  Germplasm  │  Genotype  │  Phenotype  │  Expression  │  Tools ▼
```

- **Genomes ▼** — dropdown list of all genome-type datasets. Select one → navigate to `/genome/:id`. Also includes "View all genomes..." link to catalog filtered by type=genome.
- **Germplasm / Genotype / Phenotype / Expression** — direct links to existing query pages.
- **Tools ▼** — global tools menu (see below).

### Genome Internal Page (`/genome/:id`)

After selecting a genome, the page has its own tab bar:

```
Overview  │  Gene Search ▾  │  Tools ▾
```

| Tab | Content |
|-----|---------|
| **Overview** | Genome stats cards (size, N50, gene count, BUSCO), description_md, extra_json attributes table, chromosome/assembly table, publication citation |
| **Gene Search ▾ → Search Genes** | Three search modes (Keyword / Gene ID / Chromosome Range), results table with gene_id/chrom/start/end/strand/description, click to expand gene detail |
| **Gene Search ▾ → Transcription Factors** | Left panel: TF family list (bHLH, MYB, WRKY, NAC, bZIP, ERF...). Right panel: member table filtered by selected family. Data from functional_annotation asset |
| **Tools ▾** | Same tools as global Tools menu, but auto-scoped to the current genome |

## Global Tools Menu

Header `Tools ▾` dropdown:

| Item | Status | Notes |
|------|--------|-------|
| Batch Sequence Retrieval | v1 | Requires genome selection |
| BLAST | v1 | Requires genome selection |
| Genome Downloads | v1 | Requires genome selection |
| Primer Design | future | Grayed out |
| GO Enrichment | future | Grayed out |
| Sequence Converter | future | Grayed out |

**Behavior:** Genome-dependent tools prompt for genome selection if none is active. If coming from a genome page, the current genome is auto-selected.

## Router Changes

```
/                          → home/index.vue (dataset catalog)
/dataset/:id               → dataset/Detail.vue
/genome/:id                → genome/Overview.vue
  /genome/:id               → redirect to home tab
  /genome/:id/home           → genome/Home.vue (Overview)
  /genome/:id/search         → genome/GeneSearch.vue
  /genome/:id/tf             → genome/TranscriptionFactors.vue
  /genome/:id/tools/:tool    → genome/Tools.vue (batch/blast/download)
/expression                → expression/index.vue
/genotype                  → genotype/index.vue
/germplasm                 → germplasm/index.vue
/phenotype                 → phenotype/index.vue
/tools/:tool               → tools/ToolPage.vue (standalone tools)
```

## Genome Tab Bar Logic

- `Overview` → `/genome/:id/home`
- `Gene Search ▾` → dropdown with two items:
  - "Search Genes" → `/genome/:id/search`
  - "Transcription Factors" → `/genome/:id/tf`
- `Tools ▾` → dropdown with items:
  - "Batch Query" → `/genome/:id/tools/batch`
  - "BLAST" → `/genome/:id/tools/blast`
  - "Download" → `/genome/:id/tools/download`

Tab bar is rendered inside `genome/Overview.vue` using `el-tabs` or custom tab component. The active tab is determined from the current route path.
