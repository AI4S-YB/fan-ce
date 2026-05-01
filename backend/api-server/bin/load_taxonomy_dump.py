#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from apps.breeding.taxonomy_loader import load_taxonomy_dump
from db.database import MyDBManager


def main():
    parser = argparse.ArgumentParser(description="Load NCBI taxonomy dump into FAN-CE breeding taxonomy tables.")
    parser.add_argument("dump_path", help="Path to extracted taxdump directory or .tar.gz archive")
    parser.add_argument("--source-name", default="ncbi_taxdump", help="Source name label")
    parser.add_argument("--source-version", default=None, help="Source version label")
    parser.add_argument("--reset-existing", action="store_true", help="Delete existing taxonomy master rows before load")
    args = parser.parse_args()

    with MyDBManager() as db:
        result = load_taxonomy_dump(
            db=db,
            dump_path=args.dump_path,
            source_name=args.source_name,
            source_version=args.source_version,
            reset_existing=args.reset_existing,
        )
    print(result)


if __name__ == "__main__":
    main()
