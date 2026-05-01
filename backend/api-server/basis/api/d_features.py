import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from basis.schemas.feature import *
from basis.core.feature_utils import process_tabix_file
from libs.responses.response import response_2000
import gzip


MAX_RECOED_NUM = 1_000  # 1K limit num for front-end display, if > 1k, return a download link

# 创建 APIRouter 实例
feature_router = APIRouter(
    prefix="/omics/features",
    tags=["omics:features"]
) 


@feature_router.post("/file/process", summary="Process feature file to create index")
async def process_feature_file(file_path: str = None, file_type: str = "other"):
    """
    Process a feature file using tabix indexing

    Args:
        file_path (str): Path to the feature file to be processed
        file_type (str): Type of the feature file (e.g., 'vcf', 'bed', 'gff', 'other')

    Returns:
        dict: A dictionary containing:
            - status (str): Processing status ('success' or 'error')
            - message (str): Description of the processing result

    Raises:
        HTTPException: If file not found (404), not readable (403), or processing fails (500)
    """
    if file_path is None:
        raise HTTPException(status_code=400, detail="file_path is required")
    try:
        # Check if file exists and is readable
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        if not os.access(file_path, os.R_OK):
            raise HTTPException(status_code=403, detail="File is not readable")

        # Process the file using process_tabix_file utility
        processed_path = process_tabix_file(file_path, file_type)

        if not processed_path:
            raise HTTPException(status_code=500, detail="Failed to process feature file")

        # update database

        return response_2000(
            code=2000,
            msg="Feature file processed successfully",
            data={
                "file_path": processed_path,
            }
        )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@feature_router.post("/fields/list", summary="Get header fields from a feature file")
async def get_file_fields(file_path: str = None, file_type: str = "other"):
    """
    Get header fields information from a feature file

    Args:
        file_path (str): Path to the feature file

    Returns:
        dict: A dictionary containing:
            - fields (list): List of field names from the file header
    """
    if file_path is None:
        raise HTTPException(status_code=400, detail="file_path is required")
            
    Raises:
        HTTPException: If file not found (404), not readable (403), or empty (400)
    """
    try:
        # Check if file exists and is readable
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        if not os.access(file_path, os.R_OK):
            raise HTTPException(status_code=403, detail="File is not readable")

        # Check if file is gzipped
        try:
            # Try to open as gzip first
            with gzip.open(file_path, 'rt') as f:
                first_line = f.readline().strip()
        except gzip.BadGzipFile:
            # If not gzipped, open as regular file
            with open(file_path, 'r') as f:
                first_line = f.readline().strip()
                
        if not first_line:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Split the header line into fields
        fields = first_line.split('\t')
        
        # If first line starts with #, use it as fields directly
        if first_line.startswith('#'):
            fields = [field.strip('# ') for field in fields]
        else:
            # Generate numbered fields based on column position
            fields = [f"[{i}]{value}" for i, value in enumerate(fields)]
        
        return response_2000(
            code=2000,
            msg="File fields retrieved successfully",
            data={
                "fields": fields
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@feature_router.post("/query", summary="Query features from a feature file")
async def get_features(request: FeatureRequest):

    try:
        # Check if file_path exists in request
        if not hasattr(request, 'file_path'):
            raise HTTPException(status_code=400, detail="file_path is required")
        
        # Check if file exists and is readable
        if not os.path.exists(request.file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        if not os.access(request.file_path, os.R_OK):
            raise HTTPException(status_code=403, detail="File is not readable")
        
        # Check if tabix index exists for the file
        index_path = request.file_path + '.tbi'
        if not os.path.exists(index_path):
            raise HTTPException(status_code=400, detail="Tabix index not found for the file")
        
        if not os.access(index_path, os.R_OK):
            raise HTTPException(status_code=403, detail="Tabix index is not readable")
        
        # Set default file_type to bed if not provided
        if not request.file_type:
            request.file_type = "bed"

        features = []
        
        # Check if chrom, start, and end are provided for tabix query
        if not request.chrom or not request.start or not request.end:
            raise HTTPException(status_code=400, detail="chrom, start, and end are required for tabix query")

        # Perform tabix query based on file type
        if request.file_type == "vcf":
            tabix_cmd = f"tabix -p vcf {request.file_path} {request.chrom}:{request.start}-{request.end}"
        elif request.file_type == "gff" or request.file_type == "gff3":
            tabix_cmd = f"tabix -p gff {request.file_path} {request.chrom}:{request.start}-{request.end}"
        elif request.file_type == "bed":
            tabix_cmd = f"tabix -p bed {request.file_path} {request.chrom}:{request.start}-{request.end}"
        else:   
            # Build tabix command with sbe parameters if available
            if hasattr(request, 'sbe_params') and request.sbe_params and len(request.sbe_params.split()) == 3 and all(param.isdigit() for param in request.sbe_params.split()):
                sbe_list = sbe_params.split()
                tabix_cmd = f"tabix -s {sbe_list[0]} -b {sbe_list[1]} -e {sbe_list[2]} {request.file_path} {request.chrom}:{request.start}-{request.end}"
            else:
                tabix_cmd = f"tabix {request.file_path} {request.chrom}:{request.start}-{request.end}"

        result = os.popen(tabix_cmd).read()
        
        # Process tabix results into features list
        for line in result.strip().split('\n'):
            if not line: continue
            fields = line.split('\t')
            features.append(fields)
                
        return response_2000(
            code=2000,
            msg="Features retrieved successfully",
            data={
                "file_path": request.file_path,
                "features": features[:MAX_RECOED_NUM]
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

