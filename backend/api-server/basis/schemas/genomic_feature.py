from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal, List
from pydantic import validator


class GenomicFeatureRequest(BaseModel):
    genome_id: Optional[str] = Field(None, description="Genome ID")     
    genome_path: Optional[str] = Field(None, description="Genome file path")     # file path for file-based extraction
    chrom: Optional[str] = Field(None, description="Chromosome ID")
    start: Optional[int] = Field(None, ge=1, description="Start position (1-based)")
    end: Optional[int] = Field(None, description="End position (inclusive)")
    feature_type: Literal["gene", "mRNA"] = Field("gene", description="Feature type")

    #@validator('genome_id', 'genome_path')
    #def validate_genome_source(cls, v, values):
    #    if 'genome_id' not in values and 'genome_path' not in values:
    #        raise ValueError('Either genome_id or genome_path must be provided')
    #    return v

    @validator('feature_type')
    def validate_feature_type(cls, v):
        if v not in ["gene", "mRNA"]:
            raise ValueError('Feature type must be either "gene" or "mRNA"')
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "genome_id": "96",
                "genome_path": "/data/biodata/example/genomes/dataset01",
                "chrom": "Chr1",
                "start": 10000,
                "end": 20000,
                "feature_type": "gene"
            }
        }
        
    )
class GenomicFeatureItem(BaseModel):
    id: str
    chrom: str 
    start: int
    end: int
    strand: str
    description: Optional[str] = None
    canonical_transcript: Optional[str] = None
    parent: Optional[str] = None

class GenomicFeatureResponse(BaseModel):
    file_path: str              # file path
    features: List[GenomicFeatureItem] # List of feature items
