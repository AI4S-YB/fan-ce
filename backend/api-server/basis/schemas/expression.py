from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional

# define request model for processing expression matrix
class ExpressionProcessRequest(BaseModel):
    input_file: str = Field(..., description="Input expression matrix file path")
    output_h5_file: Optional[str] = Field(None, description="Output HDF5 file path")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "input_file": "/data/biodata/example/transcriptome/01.phytohormones_RNAseq_count.txt",
                "output_h5_file": "/data/biodata/example/transcriptome/01.phytohormones_RNAseq.h5"
            }
        }
        
        
    )
class ExpressionQueryRequest(BaseModel):
    file_path: str = Field(..., description="HDF5表达矩阵文件路径")
    genes: Optional[List[str]] = Field(None, description="查询的基因列表，默认全部")
    samples: Optional[List[str]] = Field(None, description="查询的样本列表，默认全部")
    data_type: str = Field(..., description="Data type of expression values", enum=["count", "fpkm", "mean"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_path": "/data/biodata/example/transcriptome/01.phytohormones_RNAseq.h5",
                "genes": ["SAM1A000100", "SAM1A000200", "SAM1A000300", "SAM1A000400", "SAM1A000500"],
                "samples": ["H2O_1","H2O_2","H2O_3","AgNO3_1","AgNO3_2","AgNO3_3"],
                "data_type": "fpkm"
            }
        }
    )
class ExpressionResult(BaseModel):
    matrix: Optional[List[List[float]]] = Field(None, description="表达数据（较小时返回）")
    genes: List[str]
    samples: List[str]
    download_url: Optional[str] = Field(None, description="当数据较大时，提供下载链接")
