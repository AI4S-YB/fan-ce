from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal, List
from pydantic import validator


class FeatureProcessRequest(BaseModel):
    """Model for feature processing request"""
    file_path: str = Field(..., description="Path to the feature file")
    file_type: Literal["bed", "gff", "other"] = Field(..., description="Type of the feature file")

class FeatureProcessResponse(BaseModel):
    """Model for feature processing response"""
    file_path: str = Field(..., description="Path to the processed file")
    status: Literal["success", "failed"] = Field(..., description="Processing status")
    message: str = Field(..., description="Processing result message")


class FeatureRequest(BaseModel):
    file_path: str = None     # file path for file-based extraction
    chrom: Optional[str] = Field(None, description="Chromosome ID")
    start: Optional[int] = Field(None, ge=1, description="Start position (1-based)")
    end: Optional[int] = Field(None, description="End position (inclusive)")
    file_type: Optional[Literal["bed", "gff", "vcf", 'other']] = Field("bed", description="File type supported by tabix")
    sbe_params: Optional[int] = Field(None, description="SBE parameters as a 3-digit integer for tabix when file_type is sbe")

    @validator('sbe_params')
    def validate_sbe_params(cls, v, values):
        if values.get('file_type') == 'sbe' and not v:
            raise ValueError("sbe_params is required when file_type is 'sbe'")
        if v and (v < 100 or v > 999):
            raise ValueError("sbe_params must be a 3-digit integer")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_path": "",
                "chrom": "Chr1A",
                "start": 100000,
                "end": 1000000,
                "file_type": "other",
                "sbe_params": None
            }
        }
        
    )
class FeatureResponse(BaseModel):
    file_path: str              # file path 
    features: List[List]        # List of lists containing feature data
