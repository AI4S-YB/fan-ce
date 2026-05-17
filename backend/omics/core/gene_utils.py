import json
import os
import sqlite3
import subprocess
from fastapi import HTTPException
from typing import List, Dict, Optional
from omics.core.samtools_utils import extract_sequence, clean_fasta_sequence

def extract_genomic_sequences(
    genome_path: str,
    transcript_id: str,
    chrom: Optional[str] = None,
    start: Optional[int] = None,
    stop: Optional[int] = None
) -> Dict[str, str]:

    sequences = {}
    base_dir = genome_path
    required_files = ["genome.fa.gz", "mRNA.fa.gz", "protein.fa.gz"]

    for rfile in required_files:
        if not os.path.exists(os.path.join(base_dir, rfile)):
            raise HTTPException(status_code=404, detail=f"Required {rfile} not found")

    sequences['mRNA'] = clean_fasta_sequence(extract_sequence(os.path.join(base_dir, "mRNA.fa.gz"), transcript_id, None, None))
    sequences['protein'] = clean_fasta_sequence(extract_sequence(os.path.join(base_dir, "protein.fa.gz"), transcript_id, None, None))

    if chrom and start and stop:
        sequences['gene'] = clean_fasta_sequence(extract_sequence(os.path.join(base_dir, "genome.fa.gz"), chrom, start, stop))

    if os.path.exists(os.path.join(base_dir, "cds.fa.gz")):
        sequences['CDS'] = clean_fasta_sequence(extract_sequence(os.path.join(base_dir, "cds.fa.gz"), transcript_id, None, None))            

    return sequences    
