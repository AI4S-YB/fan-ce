import os
import re
import shutil
import uuid

from fastapi import APIRouter, HTTPException

from omics.core.variant_utils import process_variant_file as process_vcf_file, check_vcf_file, extract_variants, get_gene_region
from omics.schemas.variant import *
from shared.responses import response_200
import subprocess

# 创建 APIRouter 实例
variant_router = APIRouter(
    prefix="/omics/variants",
    tags=["omics:variome"]
)

DOWNLOAD_BASE_URL = "http://yourdomain.com/downloads"  # 你可以换成真实域名
from config.settings import settings; DOWNLOAD_DIR = settings.DOWNLOAD_DIR


@variant_router.post("/file/process",
    summary="Process variant files (VCF/BCF) and create indexes")
async def process_variant_file_endpoint(request: VariantProcessRequest):
    try:
        # check if vcf_path is provided
        if not request.file_path:
            raise HTTPException(status_code=400, detail="file_path must be provided.")

        # using process_variant_file to process vcf file
        processed_vcf_path = process_vcf_file(request.file_path)

        # TODO: update vcf_path to processed_vcf_path in database 
        '''
            1. get file id according file_path from database
            2. update file_path to processed_vcf_path in database
        '''
        return response_200(
            code=2000,
            msg="Variant file processed successfully",
            data={
                "file_path": processed_vcf_path, 
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@variant_router.post("/region/example",
    summary="Get example region for a select VCF file")
async def get_region_example(request: VariantPathRequest):
    try:
        # check if file_path is provided
        if not request.file_path:
            raise HTTPException(status_code=400, detail="file_path must be provided.")

        # check file exist, accessible, valid vcf and index file
        if not check_vcf_file(request.file_path):
            raise HTTPException(
                status_code=400,
                detail="Invalid file_path. Please provide a valid path to a variant file."
            )


        # Use bcftools to get first non-header variant
        cmd = ["bash", "-c", f"bcftools view -H '{request.file_path}' | head -1"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract variant data: {result.stderr}"
            )

        # Get first variant line
        first_variant = result.stdout.split('\n')[0]
        if not first_variant:
            raise HTTPException(
                status_code=400,
                detail="No variants found in file"
            )

        # Parse first variant to get chromosome and position
        variant_fields = first_variant.split('\t')
        chrom = variant_fields[0]
        pos = int(variant_fields[1])

        # Generate two regions of 1000bp around the variant
        region1 = f"{chrom}:{max(1, pos-500)}-{pos+499}"
        region2 = f"{chrom}:{pos+500}-{pos+999}"
        
        example_data = {
            "ref_id": chrom,
            "variant_position": pos,
            "example_regions": [region1, region2]
        }
        
        return response_200(
            code=2000,
            msg="Region example data retrieved successfully",
            data=example_data
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@variant_router.post("/samples/list",
    summary="Get list of samples from a VCF file")
async def list_samples(request: VariantPathRequest):
    try:
        # check if vcf_path is provided
        if not request.file_path:
            raise HTTPException(status_code=400, detail="file_path must be provided.")

        # check file exist, accessible, valid vcf and index file
        if not check_vcf_file(request.file_path):
            raise HTTPException(
                status_code=400,
                detail="Invalid file_path. Please provide a valid path to a variant file."
            )

        # Extract samples from VCF file using bcftools query
        cmd = ["bcftools", "query", "-l", request.file_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract samples: {result.stderr}"
            )

        # Split the output into a list of sample names
        samples = result.stdout.strip().split('\n')
        
        return response_200(
            code=2000,
            msg="Samples retrieved successfully",
            data={
                "samples": samples,
                "count": len(samples)
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@variant_router.post("/query")
async def get_variants(request: VariantRequest):
    try:
        # check if vcf_path is provided
        if not request.vcf_path:
            raise HTTPException(status_code=400, detail="vcf_path must be provided.")

        # check file exist, accessible, valid vcf and index file
        if not check_vcf_file(request.vcf_path):
            raise HTTPException(
                status_code=400,
                detail="Invalid vcf_path. Please provide a valid path to a VCF file."
            )

        regions = request.regions if request.regions else []

        # Process multiple gene IDs if provided
        # 1. get genome_id from vcf_path
        '''
        metadata = get_metadata(request.vcf_path)
        if not metadata or 'genome_id' not in metadata:
            raise HTTPException(
                status_code=400,
                detail="No metadata or genome_id found for the provided vcf_path"
            )
        genome_id = request.gene_id

        if request.gene_ids:
            for gene_id in request.gene_ids:
                chr, start, end = get_gene_region(genome_id, gene_id)
                regions.append(f"{chr}:{start}-{end}")

        # Backward compatibility for single gene_id
        elif request.gene_id:
            chr, start, end = get_gene_region(genome_id, request.gene_id)
            regions.append(f"{chr}:{start}-{end}")
        '''

        if not regions:
            raise HTTPException(
                status_code=400,
                detail="Either regions or gene_ids must be provided."
            )

        # check region format chr:start-end
        for region in regions:
            if not re.match(r'^([a-zA-Z0-9_]+)(?::(\d+)(?:-(\d+))?)?$', region):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid region format: {region}. Expected format: chr1:1000-2000, chr1:1000"
                )

        # parse other parameters for extract vcf information 
        '''
            code for other parameters, using wangli's script 
        '''

        result = extract_variants(
            vcf_path=request.vcf_path,
            regions=regions,
            include_samples=request.include_samples,
            exclude_samples=request.exclude_samples
        )

        # Save compressed file to persistent download dir
        file_id = str(uuid.uuid4()) + ".vcf.gz"
        final_path = f"{DOWNLOAD_DIR}/{file_id}"
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        shutil.copyfile(result["vcf_path"], final_path)

        response = {
            "count": result["preview"].count("\n") if result["preview"] else 0,
            "size": result["size"],
            "preview": result["preview"] if result["size"] <= 1024 * 1024 else None,
            "download_url": f"{DOWNLOAD_BASE_URL}/{file_id}"
        }
        
        return response_200(
            code=2000,
            msg="Variants extracted successfully",
            data=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
