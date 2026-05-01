from fastapi import APIRouter

from basis.api.m_genome import genome_router
from basis.api.biofile import biofile_router

from basis.api.d_ngs import ngs_router
from basis.api.d_sequences import sequence_router
from basis.api.d_features import feature_router
from basis.api.d_expression import rnaseq_router
from basis.api.d_variant import variant_router
from basis.api.d_peaks import peaks_router
from basis.api.d_phenome import phenome_router
from basis.api.d_grn import grn_router

from basis.api.g_sequences import g_sequence_router
from basis.api.g_genes import g_gene_router
from basis.api.g_features import g_feature_router 

basis_router = APIRouter()

# routers for genomes
basis_router.include_router(genome_router)

# routers for biofile detection and analysis
basis_router.include_router(biofile_router)

# routers for omics data 
basis_router.include_router(ngs_router)
basis_router.include_router(sequence_router)
basis_router.include_router(feature_router)
basis_router.include_router(rnaseq_router)
basis_router.include_router(variant_router)
basis_router.include_router(peaks_router)
basis_router.include_router(phenome_router)
basis_router.include_router(grn_router)

# basis_router.include_router(publication_router)

# routers for gene/feature/sequence/...
basis_router.include_router(g_sequence_router)
basis_router.include_router(g_gene_router)
basis_router.include_router(g_feature_router)
