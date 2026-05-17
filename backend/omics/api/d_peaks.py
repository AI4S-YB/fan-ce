from fastapi import APIRouter, HTTPException
import subprocess
from pathlib import Path
from omics.schemas.sequence import (
    SequenceRequest, SequenceResponse
)


# 创建 APIRouter 实例
peaks_router = APIRouter(
    prefix="/peaks",
    tags=["MultiOmics API / peaks"]
)


# 支持的序列类型及其对应子目录
SEQ_TYPE_DIR = {
    "genome": "genome",
    "mRNA": "mrna",
    "protein": "protein"
}

DATA_ROOT = Path("omics/genome/")

def get_sequence_from_fasta(fasta_path: Path, region: str) -> str:
    try:
        result = subprocess.run(
            ["samtools", "faidx", str(fasta_path), region],
            capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().split("\n")
        sequence = ''.join(lines[1:])  # 去除 header 行
        return sequence
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"samtools faidx error: {e.stderr.strip()}")


@peaks_router.post("/peaks/", response_model=SequenceResponse, summary="Get peaks from regions")
async def get_sequence(request: SequenceRequest):
    seq_type = request.seq_type.lower()
    if seq_type not in SEQ_TYPE_DIR:
        raise HTTPException(status_code=400, detail=f"Invalid seq_type: {request.seq_type}. Must be one of {list(SEQ_TYPE_DIR.keys())}")

    # genome 类型必须指定 start 和 end
    if seq_type == "genome" and (request.start is None or request.end is None):
        raise HTTPException(status_code=400, detail="start and end are required for genome sequences")

    fasta_path = DATA_ROOT / SEQ_TYPE_DIR[seq_type] / f"{request.genome_id}.fasta"

    if not fasta_path.exists():
        raise HTTPException(status_code=404, detail=f"FASTA file not found: {fasta_path}")

    fai_path = fasta_path.with_suffix(fasta_path.suffix + ".fai")
    if not fai_path.exists():
        raise HTTPException(status_code=500, detail=f"Missing FASTA index (.fai): {fai_path}. Please run: samtools faidx {fasta_path}")

    # 获取整条染色体长度
    seq_len = None
    with open(fai_path) as f:
        for line in f:
            parts = line.strip().split("\t")
            if parts[0] == request.chromosome:
                seq_len = int(parts[1])
                break

    if seq_len is None:
        raise HTTPException(status_code=404, detail=f"Chromosome {request.chromosome} not found in {request.genome_id}")

    if request.start and request.end:
        if request.start > request.end or request.end > seq_len:
            raise HTTPException(status_code=400, detail="Invalid start/end range")

        region = f"{request.chromosome}:{request.start}-{request.end}"
        sequence = get_sequence_from_fasta(fasta_path, region)
        return SequenceResponse(
            genome_id=request.genome_id,
            seq_type=seq_type,
            chromosome=request.chromosome,
            sequence=sequence,
            length=len(sequence),
            file_path=str(fasta_path),
            start=request.start,
            end=request.end
        )
    else:
        # 不提取序列，只返回长度
        return SequenceResponse(
            genome_id=request.genome_id,
            seq_type=seq_type,
            chromosome=request.chromosome,
            sequence=None,
            length=seq_len,
            file_path=str(fasta_path),
            start=None,
            end=None
        )
