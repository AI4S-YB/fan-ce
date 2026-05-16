import subprocess
from typing import Optional, List
import tempfile
import os


def process_sequence(fasta_path: str) -> bool:
    """
    Process a FASTA file by validating its existence, readability, format and creating samtools index
    
    Args:
        fasta_path: Path to the FASTA file
        
    Returns:
        bool: True if processing succeeds, False otherwise
    """
    # Check if file exists
    if not os.path.exists(fasta_path):
        raise FileNotFoundError(f"FASTA file not found: {fasta_path}")
    
    # Check if file is readable
    if not os.access(fasta_path, os.R_OK):
        raise PermissionError(f"FASTA file is not readable: {fasta_path}")
    
    # Basic FASTA format validation
    try:
        with open(fasta_path, 'r') as f:
            first_line = f.readline().strip()
            if not first_line.startswith('>'):
                raise ValueError(f"Invalid FASTA format: {fasta_path}")
    except UnicodeDecodeError:
        raise ValueError(f"File is not a text file: {fasta_path}")
        
    # Check if samtools index exists
    if not os.path.exists(f"{fasta_path}.fai"):
        # Create samtools index if not exists
        try:
            subprocess.run(
                ["samtools", "faidx", fasta_path],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create samtools index: {e.stderr.decode()}")

    return fasta_path


def extract_sequence(fasta_path: str, seq_id: str, start: Optional[int], end: Optional[int]) -> str:
    region = seq_id if start is None or end is None else f"{seq_id}:{start}-{end}"
    result = subprocess.run(
        ["samtools", "faidx", fasta_path, region],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout

def clean_fasta_sequence(sequence: str) -> str:
    """
    Clean sequence extracted by samtools by removing ID and newlines
    
    Args:
        sequence: Raw sequence string from samtools output
        
    Returns:
        Clean sequence string without ID and newlines
    """
    # Split by newlines and remove the first line (ID line)
    lines = sequence.strip().split('\n')
    if len(lines) <= 1:
        return ''
    
    # Join remaining lines and remove any whitespace
    return ''.join(lines[1:]).strip()


def extract_batch_sequences(fasta_path: str, regions: List[str]) -> (str, str):
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as region_file:
        region_file.write("\n".join(regions))
        region_file_path = region_file.name

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".fasta") as out_fasta:
        output_path = out_fasta.name

    subprocess.run(
        f"xargs samtools faidx {fasta_path} < {region_file_path} > {output_path}",
        shell=True,
        check=True
    )

    os.unlink(region_file_path)
    return output_path