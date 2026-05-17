from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Optional


class GeneSearchRequest(BaseModel):
    # 必需参数：基因组标识
    genome_id: Optional[str] = Field(None, title="Genome ID", description="Unique ID for the genome")
    genome_path: Optional[str] = Field(None, title="Genome Path", description="Path to genome file")
    
    # 分页参数
    page: Optional[int] = Field(1, ge=1, description="Page number")
    page_size: Optional[int] = Field(20, ge=1, le=1000, description="Number of results per page")
    
    # 查询参数：所有字段可选，支持多字段组合查询
    keyword: Optional[str] = Field(None, description="Search in description field (fuzzy match)")
    gene_id: Optional[str] = Field(None, description="Exact match gene ID")  
    chrom: Optional[str] = Field(None, description="Chromosome name")
    start: Optional[int] = Field(None, ge=0, description="Region start position (genes must start >= this)")
    end: Optional[int] = Field(None, ge=0, description="Region end position (genes must end <= this)")
    strand: Optional[str] = Field(None, description="Strand information (+ or -)")
    family: Optional[str] = Field(None, description="Gene family")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "genome_id": "96",
                "genome_path": "",
                "keyword": "ethylene",
                "gene_id": "AT1G14685",
                "chrom": "chr1",
                "start": 10000,
                "end": 50000,
                "strand": "+",
                "family": "AP2",
                "page": 1,
                "page_size": 20
            }
        }
    )
class GeneListRequest(BaseModel):
    genome_id: Optional[str] = Field(None, title="Genome ID", description="Unique ID for the genome")
    genome_path: Optional[str] = Field(None, title="Genome Path", description="Path to genome file")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=1000, description="Number of results per page")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "genome_id": "82",
                "genome_path": "",
                "page": 1,
                "page_size": 20
            }
        }
        
        
    )
class GeneInfoRequest(BaseModel):
    genome_id: Optional[str] = Field(None, title="Genome ID", description="Unique ID for the genome")
    genome_path: Optional[str] = Field(None, title="Genome Path", description="Path to genome file")
    gene_id: str = Field(..., title="Gene ID", description="Unique ID for the gene")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "genome_id": "82",
                "genome_path": "",
                "gene_id": "AT1G14685"
            }
        }
    )
class GeneInfoResponse(BaseModel):
    genome: Dict = Field({}, title="GenomeData", description="Details about the organism's genome")
    gene: Dict = Field({}, title="GeneData", description="Details about the gene")
    transcript: Dict = Field({}, title="TranscriptData", description="Details about the transcript")
    fa_blast: List | None = Field(None, title="List of BLAST hits", description="List of BLAST search results")
    fa_ipr: List | None = Field(None, title="List of Interpro domains", description="List of Interpro domain annotations")
    fa_go: List | None = Field(None, title="List of GO terms", description="List of Gene Ontology terms")
    fa_kegg: List | None = Field(None, title="List of KEGG pathways", description="List of KEGG pathway annotations")
    fa_family: List | None = Field(None, title="List of gene families", description="List of associated gene families")
    paralogs: List | None = Field(None, title="List of paralogs", description="List of paralogous genes")
    orthologs: List | None = Field(None, title="List of orthologs", description="List of orthologous genes")
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "genome": {"id": 1, "name": "Arabidopsis thaliana"},
                "gene": {"id": "AT1G14685", "name": "Gene A"},
                "transcript": {"id": "AT1G14685.1", "name": "Transcript A"},
                "fa_blast": ["BLAST hit 1", "BLAST hit 2"],
                "fa_ipr": ["Interpro domain 1", "Interpro domain 2"],
                "fa_go": ["GO term 1", "GO term 2"],
                "fa_family": ["Gene family 1", "Gene family 2"],
                "paralogs": ["Paralog 1", "Paralog 2"],
                "orthologs": ["Ortholog 1", "Ortholog 2"]
            }
        }
        
    )
class TranscriptInfoRequest(BaseModel):
    genome_id: Optional[str] = Field(None, title="Genome ID", description="Unique ID for the genome")
    genome_path: Optional[str] = Field(None, title="Genome Path", description="Path to genome file")
    transcript_id: str = Field(..., title="Transcript ID", description="Unique ID for the transcript")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "genome_id": "82",
                "genome_path": "",
                "transcript_id": "AT1G14685.1"
            }
        }
        
    )
class TranscriptInfoResponse(BaseModel):
    genome: Dict = Field({}, title="GenomeData", description="Details about the organism's genome")
    gene: Dict = Field({}, title="GeneData", description="Details about the gene")
    transcript: Dict = Field({}, title="TranscriptData", description="Details about the transcript")
    fa_blast: List | None = Field(None, title="List of BLAST hits", description="List of BLAST search results")
    fa_ipr: List | None = Field(None, title="List of Interpro domains", description="List of Interpro domain annotations")
    fa_go: List | None = Field(None, title="List of GO terms", description="List of Gene Ontology terms")
    fa_kegg: List | None = Field(None, title="List of KEGG pathways", description="List of KEGG pathway annotations")
    fa_family: List | None = Field(None, title="List of gene families", description="List of associated gene families")
    paralogs: List | None = Field(None, title="List of paralogs", description="List of paralogous genes")
    orthologs: List | None = Field(None, title="List of orthologs", description="List of orthologous genes")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "genome": {"id": 1, "name": "Arabidopsis thaliana"},
                "gene": {"id": "AT1G14685", "name": "Gene A"},
                "transcript": {"id": "AT1G14685.1", "name": "Transcript A"},
                "fa_blast": ["BLAST hit 1", "BLAST hit 2"],
                "fa_ipr": ["Interpro domain 1", "Interpro domain 2"],
                "fa_go": ["GO term 1", "GO term 2"],
                "fa_family": ["Gene family 1", "Gene family 2"],
                "paralogs": ["Paralog 1", "Paralog 2"],
                "orthologs": ["Ortholog 1", "Ortholog 2"]
            }
        }
    )
