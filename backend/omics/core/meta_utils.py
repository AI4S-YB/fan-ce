import os
from datetime import datetime
import subprocess
import sqlite3

# filter files by file extension in frontend, not in backend
def extract_basic_metadata(file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} does not exist.")

    stat = os.stat(file_path)
    return {
        "path": file_path,
        "name": os.path.basename(file_path),
        "size": stat.st_size,
        "modified_time": datetime.fromtimestamp(stat.st_mtime)
    }

def extract_genome_metadata(folder_path: str):
    if not os.path.isdir(folder_path):
        raise FileNotFoundError(f"{folder_path} is not a valid directory.")

    total_size = 0
    file_count = 0
    latest_mtime = 0

    for root, _, files in os.walk(folder_path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                stat = os.stat(fp)
                file_count += 1
                total_size += stat.st_size
                latest_mtime = max(latest_mtime, stat.st_mtime)
            except FileNotFoundError:
                continue

    return {
        "path": folder_path,
        "name": os.path.basename(folder_path),
        "file_count": file_count,
        "total_size": total_size,
        "modified_time": datetime.fromtimestamp(latest_mtime),
    }

# need a button in html to trigger this function, then show the result to user
def extract_vcf_metadata(file_path: str) -> dict:
    """
    Extract metadata from VCF/BCF file header
    Args:
        file_path: Path to VCF (.vcf.gz) or BCF file
    Returns:
        Dictionary containing metadata from the header
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} does not exist.")
    
    if not (file_path.endswith('.bcf') or file_path.endswith('.vcf.gz')):
        raise ValueError("File must be .bcf or .vcf.gz format")

    
    metadata = {
        "header_info": {},
    }
    
    try:
        # Use bcftools to view header
        cmd = ['bcftools', 'view', '--header-only', file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse header lines
        for line in result.stdout.split('\n'):
            if line.startswith('##'):
                # Extract key-value pairs from header lines
                if '=' in line:
                    key = line[2:].split('=')[0]
                    value = '='.join(line[2:].split('=')[1:])
                    metadata["header_info"][key] = value
            elif line.startswith('#CHROM'):
                # Get sample names from the header line
                fields = line.split('\t')
                if len(fields) > 9:  # If samples are present
                    metadata["samples"] = fields[9:]
                break
                
        return metadata
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error parsing VCF/BCF file: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while parsing file: {str(e)}")



