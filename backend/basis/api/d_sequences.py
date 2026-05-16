import os
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from basis.schemas.sequence import *
from basis.core.samtools_utils import process_sequence, extract_sequence, extract_batch_sequences
from basis.core.file_utils import compress_file_to_gzip, generate_download_url
from libs.responses.response import response_2000


MAX_INLINE_SIZE = 1_000_000  # 1MB limit size for front-end display, if > 1MB, return a download link

# 创建 APIRouter 实例
sequence_router = APIRouter(
    prefix="/omics/sequence",
    tags=["omics:sequence"]
)

@sequence_router.post("/file/process", summary="Process sequence file to create index")
async def process_sequence_file(request: SequenceProcessRequest):
    try:
        # Process the sequence file using process_sequence function
        processed_path = process_sequence(request.file_path)

        return response_2000(
            code=2000,
            msg="Sequence file processed successfully",
            data={
                "file_path": processed_path
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@sequence_router.post("/fetch", summary="Fetch a single sequence from a sequence file")
async def get_single_sequence(request: SequenceRequest):
    try:
        sequence_text = extract_sequence(request.file_path, request.seq_id, request.start, request.end)
        sequence_lines = sequence_text.strip().split("\n")
        sequence_str = "".join(sequence_lines[1:])

        if len(sequence_str) > MAX_INLINE_SIZE:
            # for sequence > 1MB, return a download link
            temp_fasta = f"/tmp/{request.seq_id}_{uuid.uuid4().hex}.fasta"
            with open(temp_fasta, "w") as f:
                f.write(sequence_text)
            gzip_path = compress_file_to_gzip(temp_fasta)

            return response_2000(
                code=2000,
                msg="Sequence fetched successfully, please download the sequence file through the download link",
                data={
                    "seq_id": request.seq_id,
                    "sequence": None,
                    "length": len(sequence_str),
                    "file_path": request.file_path,
                    "start": request.start,
                    "end": request.end,
                    "download_url": generate_download_url(gzip_path)
                }
            )
        else:
            # for sequence < 1MB, return the sequence directly
            return response_2000(
                code=2000,
                msg="Sequence fetched successfully",
                data={
                    "seq_id": request.seq_id,
                    "sequence": sequence_str,
                    "length": len(sequence_str),
                    "file_path": request.file_path,
                    "start": request.start,
                    "end": request.end
                }
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@sequence_router.post("/batchquery", summary="Fetch multiple sequences from a sequence file")
async def get_batch_sequences(request: BatchSequenceRequest):
    try:
        regions = [
            f"{item.seq_id}:{item.start}-{item.end}" if item.start and item.end else item.seq_id
            for item in request.regions
        ]
        output_path = extract_batch_sequences(request.file_path, regions)

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

        return response_2000(
            code=2000,
            msg="Batch sequences fetched successfully",
            data={
                "file_path": output_path,
                "sequences": [seq.dict() for seq in sequences],
                "download_url": download_url
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@sequence_router.get("/downloads/{filename}")
async def download_file(filename: str):
    file_path = os.path.join("/tmp/downloads", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)




