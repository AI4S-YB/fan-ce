from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class PeakRequest(BaseModel):
    tech_type: str = Field(..., description="Technology type: chip-seq, atac-seq, dap-seq")
    chrom: str = Field(..., description="Chromosome name (e.g. 'chr1')")
    start: int = Field(..., ge=0, description="Start position (0-based)")
    end: int = Field(..., description="End position (inclusive)")

class PeakResponse(BaseModel):
    chrom: str
    start: int
    end: int
    name: str
    score: int
    strand: str