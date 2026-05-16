from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class FilePathInput(BaseModel):
    path: str

class EnhancementItemCreate(BaseModel):
    term_id: str
    term_name: str
    term_description: Optional[str] = None
    value: str

class EnhancementItemOut(EnhancementItemCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)
class EnhancementCreate(BaseModel):
    enhancements: List[EnhancementItemCreate]

class EnhancementOut(BaseModel):
    enhancements: List[EnhancementItemOut]

    model_config = ConfigDict(from_attributes=True)
class FileMetadataOut(BaseModel):
    id: int
    path: str
    name: str
    size: int
    modified_time: datetime
    enhancements: List[EnhancementItemOut] = []

    model_config = ConfigDict(from_attributes=True)
