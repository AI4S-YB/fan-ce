#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend" / "api-server"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from apps.datasets.crud import asset_file_db, dataset_asset_db
from apps.datasets.functional_indexing import rebuild_functional_annotation_index
from apps.datasets.init import init_dataset_tables
from db.database import MyDBManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rebuild PostgreSQL functional_annotation term index for an existing asset.")
    parser.add_argument("--asset-id", type=int, help="Existing dataset asset id.")
    parser.add_argument("--version-id", type=int, help="Existing dataset version id.")
    parser.add_argument("--asset-code", default="functional_annotation", help="Asset code to resolve from version. Default: functional_annotation")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.asset_id and not args.version_id:
        raise SystemExit("either --asset-id or --version-id is required")

    init_dataset_tables()

    with MyDBManager() as db:
        if args.asset_id:
            asset_obj = dataset_asset_db.get(db=db, id=args.asset_id)
        else:
            asset_obj = dataset_asset_db.get_filter(
                db=db,
                filters={"dataset_version_id": args.version_id, "asset_code": args.asset_code},
            )
            if not asset_obj:
                raise SystemExit(f"asset not found for version_id={args.version_id}, asset_code={args.asset_code}")

        primary_file = next(
            (
                item
                for item in asset_file_db.get_data(db=db, filters={"dataset_asset_id": asset_obj.id})
                if item.file_role == "primary"
            ),
            None,
        )
        if not primary_file:
            raise SystemExit(f"primary file not found for asset_id={asset_obj.id}")

        file_path = primary_file.local_path or primary_file.storage_uri or ""
        if file_path.startswith("file://"):
            file_path = file_path[len("file://") :]

        result = rebuild_functional_annotation_index(
            db=db,
            dataset_id=asset_obj.database_id,
            version_id=asset_obj.dataset_version_id,
            asset_id=asset_obj.id,
            file_path=file_path,
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
