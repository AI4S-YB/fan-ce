import os

from fastapi import APIRouter, HTTPException

from basis.core.path_utils import get_genome_db_path
from basis.core.sqlite_utils import query_sqlite
from basis.schemas.genomic_feature import *

MAX_RECOED_NUM = 1_000  # 1K limit num for front-end display, if > 1k, return a download link

# 创建 APIRouter 实例
g_feature_router = APIRouter(
    prefix="/omics/genome/feature",
    tags=["omics:genome"]
)


@g_feature_router.post("/query", response_model=GenomicFeatureResponse)
async def get_features(request: GenomicFeatureRequest):
    try:
        # Get sqlite path from either genome_path or genome_id
        sqlite_db = None
        if hasattr(request, 'genome_path'):
            sqlite_db = os.path.join(request.genome_path, "genome.db")
        if hasattr(request, 'genome_id'):
            sqlite_db = get_genome_db_path(request.genome_id)

        # Check if sqlite path exists
        if not sqlite_db or not os.path.exists(sqlite_db):  # Fixed variable name from sqlite_path to sqlite_db
            raise HTTPException(status_code=404, detail="SQLite database file not found")

        # get features from sqlite db
        features = []

        table = "hse_genes" if request.feature_type == "gene" else "hse_transcripts"

        if request.chrom and request.start and request.end:
            query = f"""
                SELECT * FROM {table}
                WHERE chrom = ? AND start >= ? AND stop <= ?
                ORDER BY start LIMIT {MAX_RECOED_NUM}
            """
            params = (request.chrom, request.start, request.end)
        else:
            query = f"""
                SELECT * FROM {table}
                ORDER BY chrom, start LIMIT {MAX_RECOED_NUM}
            """
            params = ()

        rows = query_sqlite(sqlite_db, query, params)  # Fixed variable name from sqlite_path to sqlite_db

        for row in rows:
            features.append(GenomicFeatureItem(
                id=row.get("gene_id") or row.get("transcript_id"),
                chrom=row["chrom"],
                start=row["start"],
                end=row["stop"],
                strand=row["strand"],
                description=row.get("description") if "description" in row else None,
                canonical_transcript=row.get("canonical_transcript") if "canonical_transcript" in row else None,
                parent=row.get("gene_id") if request.feature_type == "transcript" else None
            ))

        return GenomicFeatureResponse(  # Fixed response model name
            file_path=sqlite_db,  # Fixed variable name from sqlite_path to sqlite_db
            features=features[:MAX_RECOED_NUM]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.get("/downloads/{filename}")
# async def download_file(filename: str):
#    file_path = os.path.join("/tmp/downloads", filename)
#    if not os.path.exists(file_path):
#        raise HTTPException(status_code=404, detail="File not found")
#    return FileResponse(file_path, filename=filename)
