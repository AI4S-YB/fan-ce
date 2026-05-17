import os
import re
from shared.database import get_db
from modules.datasets.models import AssetFile


def get_genome_base_dir(genome_id: str) -> str:
    db = get_db()
    db_file_obj = db.query(AssetFile).filter(AssetFile.id == genome_id).first()
    if not db_file_obj:
        raise ValueError(f"Genome not found for id: {genome_id}")

    file_path = db_file_obj.local_path or db_file_obj.storage_uri
    if not file_path or not os.path.exists(file_path):
        raise ValueError(f"Path does not exist for genome id: {genome_id}")

    return file_path


def get_fasta_path(genome_path: str, seq_type: str) -> str:
    base_dir = genome_path

    seq_type = seq_type.lower()
    if seq_type == "genome":
        seq_type = "chromosome"
        path = os.path.join(base_dir, "genome.fa.gz")
    elif seq_type == "mrna":
        path = os.path.join(base_dir, "mRNA.fa.gz")
    elif seq_type == "cds":
        path = os.path.join(base_dir, "cds.fa.gz")
    elif seq_type == "protein":
        path = os.path.join(base_dir, "protein.fa.gz")
    elif seq_type == "gene":
        path = os.path.join(base_dir, "gene.fa.gz")
    else:
        raise ValueError(f"Invalid seq_type: {seq_type}")

    if not os.path.exists(path):
        raise FileNotFoundError(f"FASTA file not found for {genome_path} and {seq_type}")

    return path


def get_genome_db_path(genome_id: str) -> str:
    db = get_db()
    db_file_obj = db.query(AssetFile).filter(AssetFile.id == genome_id).first()
    if not db_file_obj:
        raise ValueError(f"Genome not found for id: {genome_id}")

    file_path = db_file_obj.local_path or db_file_obj.storage_uri
    if not file_path or not os.path.exists(file_path):
        raise ValueError(f"Path does not exist for genome id: {genome_id}")

    db_path = os.path.join(file_path, "genome.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"SQLite database not found for genome_id: {genome_id}")

    return db_path
