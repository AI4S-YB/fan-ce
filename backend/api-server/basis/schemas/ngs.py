from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

class NGSFileFilterRequest(BaseModel):
    directory: str = Field(..., description="目标目录路径")
    keyword: Optional[str] = Field(None, description="文件名关键词")
    recursive: bool = Field(default=True, description="是否递归子目录")
    modified_after: Optional[datetime] = Field(None, description="修改时间不早于")
    modified_before: Optional[datetime] = Field(None, description="修改时间不晚于")
    min_size_bytes: Optional[int] = Field(None, description="最小文件大小")
    max_size_bytes: Optional[int] = Field(None, description="最大文件大小")
    sort_by: Optional[str] = Field(None, description="排序字段：size 或 modified")
    sort_order: Optional[str] = Field("asc", description="排序顺序：asc 或 desc")
    page: int = Field(1, ge=1, description="分页页码，从 1 开始")
    page_size: int = Field(20, ge=1, le=1000, description="每页条数")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "directory": "/data/biodata/example/fastq",
                "recursive": True,
                "min_size_bytes": 1000,
                "max_size_bytes": 10000000000,
                "sort_by": "modified",
                "sort_order": "desc",
                "page": 1,
                "page_size": 20,
            }
        }
    )


class NGSFileInfo(BaseModel):
    name: str
    path: str
    size_bytes: int
    size_human: str
    modified_time: str

class NGSFileListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    files: List[NGSFileInfo]
