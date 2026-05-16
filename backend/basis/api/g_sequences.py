from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from basis.schemas.genomic_sequence import *
from basis.core.path_utils import get_fasta_path, get_genome_base_dir
from basis.core.samtools_utils import extract_sequence, extract_batch_sequences
from basis.core.file_utils import compress_file_to_gzip, generate_download_url
from libs.responses.response import response_2000
import os
import uuid

MAX_INLINE_SIZE = 1_000_000  # 1MB limit size for front-end display, if > 1MB, return a download link

# 创建 APIRouter 实例
g_sequence_router = APIRouter(
    prefix="/omics/genome/sequence",
    tags=["omics:genome"]
)

def get_example_info(genome_path: str, seq_type: str) -> list:
    """
    Get example sequence information based on genome path and sequence type
    Uses .fai index file to get sequence information instead of reading fasta directly
    """
    fasta_path = get_fasta_path(genome_path, seq_type)
    fai_path = f"{fasta_path}.fai"
    
    try:
        # For genome sequences, get 2 chromosome IDs and generate regions
        if seq_type == "genome":
            example_info = []
            with open(fai_path) as f:
                chr_ids = []
                for line in f:
                    chr_id = line.strip().split()[0]
                    chr_ids.append(chr_id)
                    if len(chr_ids) == 2:
                        break
                        
            example_info = [
                {"chr": chr_ids[0], "start": 1, "end": 1000},
                {"chr": chr_ids[1], "start": 1, "end": 1000}
            ]
            
        # For other sequence types, get first 20 sequence IDs
        else:
            example_info = []
            with open(fai_path) as f:
                for line in f:
                    seq_id = line.strip().split()[0]
                    example_info.append(seq_id)
                    if len(example_info) == 20:
                        break
            
        return example_info
        
    except Exception as e:
        raise Exception(f"Failed to get example info: {str(e)}")



@g_sequence_router.post("/example", description="Example genome_path: ")
async def get_genome_sequence_example(request: GenomicSequenceExampleRequest ):

    try:
        if request.genome_path:
            example_info = get_example_info(request.genome_path, request.seq_type)
        else:
            if not request.genome_id:
                raise HTTPException(status_code=400, detail="genome_id or genome_path is required")
            
            genome_base_dir = get_genome_base_dir(request.genome_id)
            example_info = get_example_info(genome_base_dir, request.seq_type)
            
        return response_2000(
            code=2000,
            msg="success",
            data={
                "example_info": example_info,
                "note": "These are example information showing how to retrieve sequences"
            }
        )
                    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@g_sequence_router.post("/fetch", response_model=GenomicSequenceResponse)
async def get_single_sequence(request: GenomicSequenceRequest):
    try:
        if request.genome_path:
            fasta_path = get_fasta_path(request.genome_path, request.seq_type)
        else:
            if not request.genome_id:
                raise HTTPException(status_code=400, detail="genome_id or genome_path is required")
            
            genome_base_dir = get_genome_base_dir(request.genome_id)
            fasta_path = get_fasta_path(genome_base_dir, request.seq_type)

        sequence_text = extract_sequence(fasta_path, request.seq_id, request.start, request.end)
        sequence_lines = sequence_text.strip().split("\n")
        sequence_str = "".join(sequence_lines[1:])

        if len(sequence_str) > MAX_INLINE_SIZE:
            temp_fasta = f"/tmp/{request.seq_id}_{uuid.uuid4().hex}.fasta"
            with open(temp_fasta, "w") as f:
                f.write(sequence_text)
            gzip_path = compress_file_to_gzip(temp_fasta)
            response_data = {
                "genome_id": request.genome_id,
                "seq_type": request.seq_type,
                "seq_id": request.seq_id,
                "sequence": None,
                "length": len(sequence_str),
                "file_path": fasta_path,
                "start": request.start,
                "end": request.end,
                "download_url": generate_download_url(gzip_path)
            }
            return response_2000(
                code=2000,
                msg="success",
                data=response_data)
        else:
            response_data = {
                "genome_id": request.genome_id,
                "seq_type": request.seq_type,
                "seq_id": request.seq_id,
                "sequence": sequence_str,
                "length": len(sequence_str),
                "file_path": fasta_path,
                "start": request.start,
                "end": request.end
            }
            return response_2000(
                code=2000,
                msg="success",
                data=response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@g_sequence_router.post("/batchquery", response_model=GenomicBatchSequenceResponse)
async def get_batch_sequences(request: GenomicBatchSequenceRequest):
    try:
        if request.genome_path:
            fasta_path = get_fasta_path(request.genome_path, request.seq_type)
        else:
            if not request.genome_id:
                raise HTTPException(status_code=400, detail="genome_id or genome_path is required")
            
            genome_base_dir = get_genome_base_dir(request.genome_id)
            fasta_path = get_fasta_path(genome_base_dir, request.seq_type)
        
        regions = [
            f"{item.seq_id}:{item.start}-{item.end}" if item.start and item.end else item.seq_id
            for item in request.regions
        ]
        output_path = extract_batch_sequences(fasta_path, regions)

        total_seq = ""
        sequences = []
        with open(output_path) as f:
            seq_id, seq = None, []
            start, end = None, None
            for line in f:
                if line.startswith(">"):
                    if seq_id:
                        full_seq = "".join(seq)
                        sequences.append(BatchSequenceResponseItem(
                            seq_id=seq_id.split(":")[0],
                            start=start,
                            end=end,
                            sequence=None if len(full_seq) > MAX_INLINE_SIZE else full_seq,
                            length=len(full_seq)
                        ))
                        total_seq += full_seq
                    header = line.strip()[1:]
                    parts = header.split(":")
                    seq_id = parts[0]
                    if len(parts) == 2 and "-" in parts[1]:
                        start, end = map(int, parts[1].split("-"))
                    else:
                        start = end = None
                    seq = []
                else:
                    seq.append(line.strip())
            if seq_id:
                full_seq = "".join(seq)
                sequences.append(BatchSequenceResponseItem(
                    seq_id=seq_id,
                    start=start,
                    end=end,
                    sequence=None if len(full_seq) > MAX_INLINE_SIZE else full_seq,
                    length=len(full_seq)
                ))
                total_seq += full_seq

        download_url = None
        if len(total_seq) > MAX_INLINE_SIZE:
            gzip_path = compress_file_to_gzip(output_path)
            download_url = generate_download_url(gzip_path)

        return GenomicBatchSequenceResponse(
            genome_id=request.genome_id,
            seq_type=request.seq_type,
            file_path=output_path,
            sequences=sequences,
            download_url=download_url
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@g_sequence_router.get("/downloads/{filename}")
async def download_file(filename: str):
    file_path = os.path.join("/tmp/downloads", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)




