from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Optional

class PathRequest(BaseModel):
    path: str = Field(..., description="本地文件或文件夹路径")

class AnalyzeResponse(BaseModel):
    detect: Dict[str, Any]
    metadata: Dict[str, Any]

class BatchAnalyzeResponse(BaseModel):
    items: List[AnalyzeResponse] = Field(..., description="批量分析结果列表")
    total_files: int = Field(..., description="总文件数量")
    directory_path: str = Field(..., description="分析的文件夹路径")