from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List


class SequenceProcessRequest(BaseModel):
    file_path: str = Field(..., description="Direct file path. Required if genome_id is not provided")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_path": ""
            }
        }
    )
class SequenceProcessResponse(BaseModel):
    file_path: str
    status: str
    message: str



class SequenceRequest(BaseModel):
    file_path: str = Field(None, description="Direct file path. Required if genome_id is not provided")
    seq_id: str = Field(..., description="Sequence ID, e.g., 'chr1'")
    start: Optional[int] = Field(None, ge=1, description="Start position (1-based)")
    end: Optional[int] = Field(None, description="End position (inclusive)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_path": "",
                "seq_id": "Chr1A",
                "start": 1000,
                "end": 2000
            }
        }
        
    )
class SequenceResponse(BaseModel):
    file_path: str
    seq_id: str
    start: Optional[int] = None
    end: Optional[int] = None
    sequence: Optional[str] = None
    length: int
    download_url: Optional[str] = None


class RegionItem(BaseModel):
    seq_id: str
    start: Optional[int] = None
    end: Optional[int] = None


class BatchSequenceRequest(BaseModel):
    file_path: str = Field(None, description="Direct file path. Required if genome_id is not provided")
    regions: List[RegionItem]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_path": "",
                "regions": [
                    {
                        "seq_id": "Chr1A",
                        "start": 1000,
                        "end": 2000
                    },
                    {
                        "seq_id": "Chr2A", 
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


class BatchSequenceResponse(BaseModel):
    file_path: str
    sequences: List[BatchSequenceResponseItem]
    download_url: Optional[str] = None

