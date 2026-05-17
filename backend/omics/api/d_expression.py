import os

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse

from shared.database import get_db
from modules.datasets.models import AssetFile
from omics.core.expression_utils import process_rnaseq_file, extract_expression_matrix, load_gene_sample_names
from omics.schemas.expression import ExpressionProcessRequest, ExpressionQueryRequest, ExpressionResult
from shared.responses import response_200
from sqlalchemy import desc
import h5py

# 创建 APIRouter 实例
rnaseq_router = APIRouter(
    prefix="/omics/rnaseq",
    tags=["omics:transcriptome"]
)

@rnaseq_router.post("/file/process",
    summary="Process RNA-Seq expression file and convert to HDF5 format")
async def process_expression_file(req: ExpressionProcessRequest, db=Depends(get_db)):
    """
    Process RNA-Seq expression file and convert to HDF5 format
    
    Args:
        file_path: Path to input RNA-Seq expression file
        output_h5_file: Path to output HDF5 file (optional, defaults to input_file + .h5)
        
    Returns:
        Dict containing processing status and output file path
    """
    try:

        # Set default output file path if not provided
        if not hasattr(req, 'output_h5_file') or req.output_h5_file is None:
            output_h5_file = f"{req.input_file}.h5"
        else:
            output_h5_file = req.output_h5_file
            
        # Process the RNA-Seq file，convert to HDF5 format, the function can check the input file
        output_h5_file = process_rnaseq_file( req.input_file, output_h5_file)

        # Query asset file table by path
        rnaseq_file_obj = db.query(AssetFile).filter(
            (AssetFile.local_path == req.input_file) | (AssetFile.storage_uri == req.input_file)
        ).first()

        if rnaseq_file_obj is None:
            raise HTTPException(
                status_code=404,
                detail=f"Expression file not found: {req.input_file}"
            )

        # Update file path
        rnaseq_file_obj.local_path = output_h5_file
        db.flush()

        return response_200(
            code=2000,
            msg="File processed successfully",
            data={
                "file_path": output_h5_file
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


@rnaseq_router.get("/genes/list", 
    summary="List genes in the expression file")
async def list_genes(file_path: str = "", max_records: int = 100):
    try:
        genes, _ = load_gene_sample_names(file_path)
        # Limit the number of returned genes based on max_records
        total_count = len(genes)
        genes = genes[:max_records]
        return response_200(
            code=2000,
            msg="Genes listed successfully",
            data={
                "genes": genes,
                "file_path": file_path,
                "total_count": total_count
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rnaseq_router.get("/samples/list",
    summary="List samples in the expression file")
async def list_samples(file_path: str = "", max_records: int = 1000):
    try:
        _, samples = load_gene_sample_names(file_path)
        # Limit the number of returned samples based on max_records
        samples = samples[:max_records]
        return response_200(
            code=2000,
            msg="Samples listed successfully",
            data={
                "samples": samples,
                "file_path": file_path,
                "total_count": len(samples)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rnaseq_router.get("/filepath/fetch",
    summary="Get the path of expression matrix file")
async def get_expression_file_path(
    file_name: str = "",
):
    """
    Get the file path of expression matrix from HDF5 file
    
    Args:
        file_name: Name of the expression file to search for
        
    Returns:
        Dict containing file paths from HDF5 meta group
    """
    try:
        # Verify file exists and is HDF5 format
        if not os.path.exists(file_name):
            raise HTTPException(
                status_code=404,
                detail=f"File not found on disk: {file_name}"
            )
            
        if not file_name.endswith('.h5'):
            raise HTTPException(
                status_code=400,
                detail="File must be in HDF5 format"
            )

        # Read file paths from HDF5 meta group
        with h5py.File(file_name, 'r') as f:
            if 'meta' not in f:
                raise HTTPException(
                    status_code=404,
                    detail="Meta group not found in HDF5 file"
                )
                
            meta_group = f['meta']
            
            # Get count file path from dataset
            count_file_path = None
            if 'count_file_path' in meta_group:
                count_file_path = meta_group['count_file_path'][()].decode('utf-8')
            
            # Get fpkm file path from dataset  
            fpkm_file_path = None
            if 'fpkm_file_path' in meta_group:
                fpkm_file_path = meta_group['fpkm_file_path'][()].decode('utf-8')

            if count_file_path is None and fpkm_file_path is None:
                raise HTTPException(
                    status_code=404,
                    detail="No expression file paths found in meta group"
                )

        return response_200(
            code=2000,
            msg="File paths retrieved successfully",
            data={
                "file_name": os.path.basename(file_name),
                "count_file_path": count_file_path,
                "fpkm_file_path": fpkm_file_path
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving file paths: {str(e)}"
        )


@rnaseq_router.get("/types/list",
    summary="list expression type names from HDF5 file")
async def list_types(file_path: str = ""):
    """
    list all matrix group names from HDF5 file
    
    Args:
        file_path: Path to the HDF5 file
        
    Returns:
        Dict containing list of matrix group names
    """
    try:
        # Verify file exists and is HDF5 format
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"File not found on disk: {file_path}"
            )
            
        if not file_path.endswith('.h5'):
            raise HTTPException(
                status_code=400,
                detail="File must be in HDF5 format"
            )

        # Read matrix group names from HDF5 file
        matrix_types = []
        with h5py.File(file_path, 'r') as f:
            # Get all group names that contain 'matrix' in their path
            def get_matrix_groups(name, obj):
                if isinstance(obj, h5py.Dataset) and 'matrix' in name.lower():
                    # Extract just the group name without 'matrix' in the path
                    group_name = name.split('/')[-2] if '/' in name else name
                    matrix_types.append(group_name)
            
            # Visit all groups and datasets in the file
            f.visititems(get_matrix_groups)
            
            if not matrix_types:
                raise HTTPException(
                    status_code=404,
                    detail="No matrix groups found in HDF5 file"
                )

        return response_200(
            code=2000,
            msg="Matrix types retrieved successfully",
            data={
                "file_path": file_path,
                "matrix_types": matrix_types
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving matrix types: {str(e)}"
        )


@rnaseq_router.post("/query", response_model=ExpressionResult)
async def query_expression(req: ExpressionQueryRequest):
    try:
        # Check if genes list is empty
        if not req.genes:
            raise HTTPException(
                status_code=400,
                detail="Gene list cannot be empty"
            )


        matrix, genes, samples, download_path = extract_expression_matrix(
            req.file_path, req.data_type, req.genes, req.samples
        )
        download_url = None
        if download_path:
            filename = os.path.basename(download_path)
            download_url = f"/download/{filename}"
        
        return response_200(
            code=2000,
            msg="Expression data queried successfully",
            data={
                "matrix": matrix,
                "genes": genes,
                "samples": samples,
                "download_url": download_url
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rnaseq_router.get("/download/{filename}")
async def download_file(filename: str):
    file_path = f"{settings.RUNTIME_DIR}/{filename}"
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename, media_type="application/gzip")
