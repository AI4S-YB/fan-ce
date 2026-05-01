from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


class VariantProcessRequest(BaseModel):
    file_path: str = Field(
        ...,
        title="Variant File Path",
        description="Path to the variant file that needs to be processed"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_path": " /data/biodata/example/variome/test.vcf"
            }
        }
        
    )
class VariantPathRequest(BaseModel):
    file_path: str = Field(
        ...,
        title="Variant File Path",
        description="Path to the variant file that needs to be processed"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_path": "/data/biodata/example/variome/test.bcf"
            }
        }
        
    )
class VariantProcessResponse(BaseModel):
    processed_path: str = Field(
        ...,
        title="Processed File Path",
        description="Path to the processed variant file"
    )
    status: str = Field(
        ...,
        title="Processing Status",
        description="Status of the variant processing (e.g., 'completed', 'failed')"
    )
    messages: str = Field(
        default="Successfully processed variant file",
        title="Processing Messages",
        description="Messages generated during variant processing"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "processed_path": "/path/to/processed/variant.vcf",
                "status": "completed",
                "messages": "Successfully processed variant file"
            }
        }
        
        
    )
class VariantRequest(BaseModel):
    vcf_path: str = Field(
        ..., 
        title="VCF File Path",
        description="Path to the VCF (Variant Call Format) file containing genetic variants"
    )
    regions: Optional[List[str]] = Field(
        None,
        title="Genomic Regions",
        description="List of genomic regions to filter variants (e.g., chr1:1000-2000)"
    )
    gene_id: Optional[str] = Field(
        None,
        title="Gene ID",
        description="Single gene identifier for backward compatibility"
    )        # For backward compatibility
    gene_ids: Optional[List[str]] = Field(
        None,
        title="Gene IDs",
        description="List of gene identifiers to filter variants"
    ) # New field for multiple genes
    include_samples: Optional[List[str]] = Field(
        None,
        title="Include Samples",
        description="List of sample IDs to include in the analysis"
    )
    exclude_samples: Optional[List[str]] = Field(
        None,
        title="Exclude Samples",
        description="List of sample IDs to exclude from the analysis"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "vcf_path": "/data/biodata/example/variome/test.bcf",
                "regions": ["Chr1A:80000-100000", "Chr1A:450000-500000"],
                "gene_id": "SAM1A000600",
                "gene_ids": ["SAM1A002100", "SAM1A002300"],
                "include_samples": ["110", "210"],
                "exclude_samples": ["401", "610"]
            }
        }
    )
class VariantResponse(BaseModel):
    count: int
    size: int
    download_url: Optional[str]
    preview: Optional[str]  # text preview of small result
