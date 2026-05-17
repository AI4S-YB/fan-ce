#!/usr/bin/env python
"""CLI 工具：导入 taxonomy dump 到数据库"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.database import MyDBManager
from modules.breeding.taxonomy_loader import load_taxonomy_dump


def main():
    parser = argparse.ArgumentParser(description="Load taxonomy dump into database")
    parser.add_argument("dump_path", help="Path to taxonomy dump directory or tar.gz")
    parser.add_argument("--source-name", default="ncbi_plant_taxdump")
    parser.add_argument("--source-version", default=None)
    parser.add_argument("--reset-existing", action="store_true")
    args = parser.parse_args()

    with MyDBManager() as db:
        result = load_taxonomy_dump(
            db=db,
            dump_path=args.dump_path,
            source_name=args.source_name,
            source_version=args.source_version,
            reset_existing=args.reset_existing,
        )
        print(f"Imported: {result['node_count']} nodes, {result['name_count']} names")


if __name__ == "__main__":
    main()
