from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional

class PhenotypingBase(BaseModel):
    omics_type: str = Field(..., example="genomics")
    sample_id: str = Field(..., example="S12345")
    data: List[float] = Field(..., example=[0.1, 0.2, 0.3])


class PhenotypingCreateModel(PhenotypingBase):
    description: Optional[str] = Field(None, example="This is a test description")