from fastapi import APIRouter, HTTPException, Query
import os
from basis.core.phenome_utils import process_phenome_file, get_sqlite_path, get_table_columns, get_first_column_data, get_phenome_data
from libs.responses.response import response_2000
from basis.schemas.traits import TraitsQueryModel



# 创建 APIRouter 实例
phenome_router = APIRouter(
    prefix="/omics/trait",
    tags=["omics:phenome"]
)

@phenome_router.post("/file/process", 
    summary="Process phenotype file and store in SQLite database")
async def process_phenome_data_file(file_path: str = Query(default="", description="Path to phenotype data file")):
    
    # Check input file and Get SQLite file path
    sqlite_file = get_sqlite_path(file_path)
    
    try:
        # Process the file directly from the provided path
        process_phenome_file(file_path, sqlite_file)
        
        return response_2000(
            code=2000,
            msg="File processed successfully",
            data={
                "sqlite_file": sqlite_file,
                "original_filename": os.path.basename(file_path)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")


@phenome_router.get("/names/list",
    summary="Get list of traits from phenotype data file")
async def get_traits_list(file_path: str = Query(default="", description="Path to phenotype data file")):
    
    # Get SQLite file path from the original file path
    sqlite_file = get_sqlite_path(file_path)
    
    try:
        # Get all column names from the SQLite table
        columns = get_table_columns(sqlite_file)
        
        return response_2000(
            code=2000,
            msg="Traits list retrieved successfully",
            data={
                "traits": columns,
                "count": len(columns)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve traits list: {str(e)}")


@phenome_router.get("/samples/list",
    summary="Get list of samples from phenotype data file")
async def get_samples_list(file_path: str = Query(default="", description="Path to phenotype data file")):
    
    # Get SQLite file path from the original file path
    sqlite_file = get_sqlite_path(file_path)
    
    try:
        # Get sample IDs from the first column
        samples = get_first_column_data(sqlite_file)
        
        return response_2000(
            code=2000,
            msg="Samples list retrieved successfully",
            data={
                "samples": samples,
                "count": len(samples)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve samples list: {str(e)}")

@phenome_router.post("/query",
    summary="Query phenotype data for specific traits")
async def query_phenome_data(query_params: TraitsQueryModel):

    # Get SQLite file path from the original file path
    sqlite_file = get_sqlite_path(query_params.file_path)
    
    try:
        # Get phenome data for specified traits and samples
        phenome_data, samples = get_phenome_data(sqlite_file, query_params.traits, query_params.samples)
        
        return response_2000(
            code=2000,
            msg="Phenotype data retrieved successfully",
            data={
                "phenome_data": phenome_data,
                "traits_queried": query_params.traits,
                "sample_count": len(samples) if samples else 0
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve phenotype data: {str(e)}")
