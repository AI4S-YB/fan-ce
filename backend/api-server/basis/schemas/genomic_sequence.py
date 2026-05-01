from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List


class GenomicSequenceExampleRequest(BaseModel):
    genome_id: Optional[str] = Field(None, description="Genome ID, e.g., 'dataset01'. Required if genome_path is not provided")
    genome_path: Optional[str] = Field(None, description="Genome Path, e.g., '/path/to/genome'. Required if genome_id is not provided")
    seq_type: str = Field(None, description="Sequence Type, e.g., 'genome/mRNA/protein/CDS ....' Required only when genome_id is provided")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "genome_id": "82",
                "genome_path": "/data/biodata/example/genomes/dataset01",
                "seq_type": "genome",
            }
        }
        
    )
class GenomicSequenceRequest(BaseModel):
    genome_id: Optional[str] = Field(None, description="Genome ID, e.g., 'dataset01'. Required if genome_path is not provided")
    genome_path: Optional[str] = Field(None, description="Genome Path, e.g., '/path/to/genome'. Required if genome_id is not provided")
    seq_type: Optional[str] = Field(None, description="Sequence Type, e.g., 'genome/mRNA/protein/CDS ....' Required only when genome_id is provided")
    seq_id: str = Field(..., description="Sequence ID, e.g., 'chr1'")
    start: Optional[int] = Field(None, ge=1, description="Start position (1-based)")
    end: Optional[int] = Field(None, description="End position (inclusive)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "genome_id": "82",
                "genome_path": "/data/biodata/example/genomes/dataset01",
                "seq_type": "genome",
                "seq_id": "Chr1",
                "start": 1000,
                "end": 2000
            }
        }
    )
class GenomicSequenceResponse(BaseModel):
    genome_id: Optional[str] = None
    seq_type: Optional[str] = None
    seq_id: str
    sequence: Optional[str] = None
    length: int
    file_path: str
    start: Optional[int] = None
    end: Optional[int] = None
    download_url: Optional[str] = None


class RegionItem(BaseModel):
    seq_id: str
    start: Optional[int] = None
    end: Optional[int] = None


class GenomicBatchSequenceRequest(BaseModel):
    genome_id: Optional[str] = None
    genome_path: Optional[str] = None
    seq_type: str
    regions: List[RegionItem]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "genome_id": "82",
                "genome_path": "/data/biodata/example/genomes/dataset01",
                "seq_type": "genome",
                "regions": [
                    {
                        "seq_id": "Chr1",
                        "start": 1000,
                        "end": 2000
                    },
                    {
                        "seq_id": "Chr2", 
                        "start": 500,
                        "end": 1500
                    }
                ]
            }
        }
        
    )
class BatchSequenceResponseItem(BaseModel):
    seq_id: str
    start: Optional[int]
    end: Optional[int]
    sequence: Optional[str]
    length: int


class GenomicBatchSequenceResponse(BaseModel):
    genome_id: Optional[str] = None
    seq_type: Optional[str] = None
    file_path: str
    sequences: List[BatchSequenceResponseItem]
    download_url: Optional[str] = None


