from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class GenomeProcessRequest(BaseModel):
    """Request model for processing genome files"""
    genome_path: str  # Path to genome folder
    operation: Optional[str] = "insert"  # Operation type: 'insert' or 'delete'

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "genome_path": "",
                "operation": "insert"
            }
        }
        
    )
class GenomePathInput(BaseModel):
    path: str

class GenomeEnhancementCreate(BaseModel):
    term_id: str
    term_name: str
    term_description: Optional[str] = None
    value: str

class GenomeEnhancementOut(GenomeEnhancementCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)
class GenomeMetadataOut(BaseModel):
    id: int
    path: str
    name: str
    file_count: int
    total_size: int
    modified_time: datetime
    enhancements: List[GenomeEnhancementOut] = []

    model_config = ConfigDict(from_attributes=True)
