#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend" / "api-server"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from apps.datasets.bundle_provisioning import discover_sequence_bundle, provision_sequence_bundle
from apps.datasets.init import init_dataset_tables, seed_dataset_registry_defaults
from db.database import MyDBManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Provision a genome-style sequence bundle into the Dataset platform.")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory, for example /path/to/genome/dataset01")
    parser.add_argument("--title", help="Dataset title. Defaults to the bundle directory name.")
    parser.add_argument("--version", default="v1", help="Dataset version name to provision. Default: v1")
    parser.add_argument("--dataset-id", type=int, help="Reuse an existing dataset id instead of resolving by title.")
    parser.add_argument("--organism", help="Dataset organism metadata.")
    parser.add_argument("--assembly", help="Dataset assembly metadata.")
    parser.add_argument("--project-id", type=int, default=0, help="Optional project scope.")
    parser.add_argument("--team-id", type=int, default=0, help="Optional team scope.")
    parser.add_argument("--publish", action="store_true", help="Publish the provisioned version after registration.")
    parser.add_argument("--dry-run", action="store_true", help="Only print the discovered bundle plan.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.dry_run:
        plan = discover_sequence_bundle(
            args.bundle_dir,
            dataset_title=args.title,
            version=args.version,
            organism=args.organism,
            assembly=args.assembly,
        )
        print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
        return 0

    init_dataset_tables()
    seed_dataset_registry_defaults()
    admin_user = SimpleNamespace(id=1, is_superman=True, user_type=1)
    with MyDBManager() as db:
        result = provision_sequence_bundle(
            db=db,
            bundle_dir=args.bundle_dir,
            user=admin_user,
            dataset_title=args.title,
            version=args.version,
            dataset_id=args.dataset_id,
            project_id=args.project_id,
            team_id=args.team_id,
            organism=args.organism,
            assembly=args.assembly,
            publish=args.publish,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
