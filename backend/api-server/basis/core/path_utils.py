import os
import re
from db.database import get_db
from apps.databases.crud import database_db, database_file_db
from sqlalchemy.orm import Session
from basis.db.db import SessionLocal
from basis.models.meta_genome import GenomeMetadata

'''
def get_db():
    return SessionLocal()

def get_genome_base_dir(genome_id: str, db: Session = None) -> str:
    """Get the base directory path for a genome.
    
    Args:
        genome_id: The ID of the genome
        db: Database session dependency
        
    Returns:
        str: The base directory path for the genome
        
    Raises:
        HTTPException: If genome is not found
        ValueError: If path is empty or not readable
    """
    if db is None:
        db = get_db()
        close_db = True
    else:
        close_db = False

    try:
        genome = db.query(GenomeMetadata).filter_by(id=genome_id).first()
        if not genome:
            raise ValueError("Genome not found")
            
        if not genome.path:
            raise ValueError("Path is empty in genome metadata")
        if not os.path.exists(genome.path) or not os.access(genome.path, os.R_OK):
            raise ValueError(f"Path {genome.path} does not exist or is not readable")
            
        return genome.path
    finally:
        if close_db:
            db.close()
'''

def get_genome_base_dir(genome_id: str) -> str:
    db = get_db()
    db_file_obj = database_file_db.get_one(db=db, id=genome_id)
    if not db_file_obj:
        raise ValueError(f"Genome not found in database for id: {genome_id}")
    
    if not db_file_obj.path or not os.path.exists(db_file_obj.path):
        raise ValueError(f"Path does not exist in database for genome id: {genome_id}")

    return db_file_obj.path

def get_fasta_path(genome_path: str, seq_type: str) -> str:
        
    # base_dir = get_genome_base_dir(genome_id)
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
    db_file_obj = database_file_db.get_filter(db=db, id=genome_id)
    if not db_file_obj:
        raise ValueError(f"Genome not found in database for id: {genome_id}")
    
    if not db_file_obj.path or not os.path.exists(db_file_obj.path):
        raise ValueError(f"Path does not exist in database for genome id: {genome_id}")

    db_path = os.path.join(db_file_obj.path, "genome.db")
    if not os.path.exists(path):
        raise FileNotFoundError(f"SQLite database not found for genome_id: {genome_id}")

    return path