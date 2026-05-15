from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional

# 表型数据查询模型
class TraitsQueryModel(BaseModel):
    """表型数据查询请求模型"""
    file_path: str = Field(
        title="文件路径",
        description="表型数据文件的路径"
    )
    traits: List[str] = Field(
        title="性状列表",
        description="要查询的性状名称列表，空列表表示查询所有性状"
    )
    samples: Optional[List[str]] = Field(
        title="样本列表",
        description="要查询的样本ID列表，None表示查询所有样本"
    )

    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_path": "",
                "traits": ["瓶插寿命", "乙烯敏感衰老", "2021年花瓣数量", "2022年花瓣数量", "2023年花瓣数量"],
                "samples": [ "RH00004", "RH00010", "RH00011", "RH00012", "RH00013", "RH00018", "RH00023"]
            }
        }
        
        
        
    )