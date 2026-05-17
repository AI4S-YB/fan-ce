import gzip
import shutil
import os
import uuid
import datetime
from typing import List, Optional
from omics.schemas.ngs import NGSFileInfo

DOWNLOAD_BASE_URL = "http://localhost:8000/basis/downloads"
from config.settings import settings; DOWNLOAD_DIR = settings.DOWNLOAD_DIR

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def compress_file_to_gzip(file_path: str) -> str:
    gzip_path = os.path.join(DOWNLOAD_DIR, f"{uuid.uuid4().hex}.fasta.gz")
    with open(file_path, 'rb') as f_in:
        with gzip.open(gzip_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    return gzip_path


def generate_download_url(file_path: str) -> str:
    filename = os.path.basename(file_path)
    return f"{DOWNLOAD_BASE_URL}/{filename}"


def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.{decimal_places}f} {unit}"
        size /= 1024.0
    return f"{size:.{decimal_places}f} PB"

def list_ngs_files(
    directory: str,
    keyword: Optional[str] = None,
    modified_after: Optional[datetime.datetime] = None,
    modified_before: Optional[datetime.datetime] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    recursive: bool = True,
) -> List[NGSFileInfo]:
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")

    results = []
    walker = os.walk(directory) if recursive else [(directory, [], os.listdir(directory))]

    for root, _, files in walker:
        for file in files:
            # Define supported NGS file extensions
            ngs_extensions = ('.fastq', '.fastq.gz', '.fq', '.fq.gz',
                            '.fasta', '.fasta.gz', '.fa', '.fa.gz',
                            '.bam', '.sam', '.sra', '.bed', '.vcf',
                            '.vcf.gz', '.gff', '.gff3', '.gtf')
            if not file.lower().endswith(ngs_extensions):
                continue
            if keyword and keyword not in file:
                continue

            full_path = os.path.join(root, file)
            stat = os.stat(full_path)
            mod_time = datetime.datetime.fromtimestamp(stat.st_mtime)

            if modified_after and mod_time < modified_after:
                continue
            if modified_before and mod_time > modified_before:
                continue
            if min_size and stat.st_size < min_size:
                continue
            if max_size and stat.st_size > max_size:
                continue

            results.append(NGSFileInfo(
                name=file,
                path=full_path,
                size_bytes=stat.st_size,
                size_human=human_readable_size(stat.st_size),
                modified_time=mod_time.isoformat()
            ))
    return results


