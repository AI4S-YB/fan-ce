#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from modules.datasets.bundle_provisioning import discover_sequence_bundle
from modules.datasets.init import init_dataset_tables
from modules.datasets.models import AssetFile, DatasetAsset, DatasetRegistry, DatasetVersion
from modules.datasets.services import dataset_domain_service
from shared.database import MyDBManager


def _parse_json_object(raw_value: str | None) -> dict[str, Any]:
    if not raw_value:
        return {}
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _encode_json_object(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _update_attr(obj: Any, field_name: str, new_value: Any, changes: list[str], label: str) -> None:
    if getattr(obj, field_name) == new_value:
        return
    setattr(obj, field_name, new_value)
    changes.append(f"{label}.{field_name}: {new_value}")


def _resolve_bundle_dir(primary_file: AssetFile, explicit_bundle_dir: str | None) -> Path:
    if explicit_bundle_dir:
        candidate = Path(explicit_bundle_dir).expanduser().resolve()
        return candidate if candidate.is_dir() else candidate.parent
    candidate = Path(primary_file.local_path).expanduser().resolve()
    return candidate.parent if candidate.is_file() else candidate


def _pick_current_version(db, dataset_id: int) -> DatasetVersion | None:
    rows = (
        db.query(DatasetVersion)
        .filter(DatasetVersion.dataset_id == dataset_id)
        .order_by(DatasetVersion.is_current.desc(), DatasetVersion.id.desc())
        .all()
    )
    return rows[0] if rows else None


def _primary_asset_plan(plan) -> Any:
    return next((item for item in plan.assets if item.is_query_entry), None) or (plan.assets[0] if plan.assets else None)


def _sync_registry_metadata(registry_obj: DatasetRegistry, plan, changes: list[str], now: int) -> None:
    primary_asset = _primary_asset_plan(plan)
    _update_attr(registry_obj, "title", plan.dataset_title, changes, f"dataset_registry[{registry_obj.id}]")
    _update_attr(registry_obj, "dataset_type", plan.dataset_type, changes, f"dataset_registry[{registry_obj.id}]")
    if plan.organism:
        _update_attr(registry_obj, "organism", plan.organism, changes, f"dataset_registry[{registry_obj.id}]")
    if primary_asset is not None:
        pass  # file_format / query_engine now live on dataset_version / dataset_asset

    extra_payload = _parse_json_object(registry_obj.meta_json)
    extra_payload["bundle"] = plan.bundle_meta
    extra_payload["provisioning"] = {
        "mode": f"{plan.dataset_type}_bundle",
        "primary_file_path": plan.primary_file_path,
    }
    encoded = _encode_json_object(extra_payload)
    _update_attr(registry_obj, "meta_json", encoded, changes, f"dataset_registry[{registry_obj.id}]")
    registry_obj.update_time = now


def _sync_current_version(version_obj: DatasetVersion, plan, changes: list[str], now: int) -> None:
    primary_asset = _primary_asset_plan(plan)
    _update_attr(version_obj, "title", plan.dataset_title, changes, f"dataset_version[{version_obj.id}]")
    _update_attr(version_obj, "dataset_type", plan.dataset_type, changes, f"dataset_version[{version_obj.id}]")
    _update_attr(version_obj, "file_path", plan.primary_file_path, changes, f"dataset_version[{version_obj.id}]")
    if primary_asset is not None:
        _update_attr(version_obj, "file_format", primary_asset.file_format, changes, f"dataset_version[{version_obj.id}]")
        _update_attr(version_obj, "query_engine", primary_asset.query_engine, changes, f"dataset_version[{version_obj.id}]")

    extra_payload = _parse_json_object(version_obj.meta_json)
    extra_payload["bundle"] = plan.bundle_meta
    extra_payload["provisioning"] = {
        "mode": f"{plan.dataset_type}_bundle",
        "primary_file_path": plan.primary_file_path,
    }
    encoded = _encode_json_object(extra_payload)
    _update_attr(version_obj, "meta_json", encoded, changes, f"dataset_version[{version_obj.id}]")
    version_obj.update_time = now


def _sync_current_assets(db, dataset_id: int, version_id: int, plan, changes: list[str], now: int) -> None:
    assets = (
        db.query(DatasetAsset)
        .filter(DatasetAsset.dataset_id == dataset_id, DatasetAsset.dataset_version_id == version_id)
        .all()
    )
    asset_by_code = {item.asset_code: item for item in assets}
    for asset_plan in plan.assets:
        asset_obj = asset_by_code.get(asset_plan.asset_code)
        if asset_obj is None:
            continue
        _update_attr(asset_obj, "asset_name", asset_plan.asset_name, changes, f"dataset_asset[{asset_obj.id}]")
        _update_attr(asset_obj, "asset_type", asset_plan.asset_type, changes, f"dataset_asset[{asset_obj.id}]")
        _update_attr(asset_obj, "file_format", asset_plan.file_format, changes, f"dataset_asset[{asset_obj.id}]")
        _update_attr(asset_obj, "query_engine", asset_plan.query_engine, changes, f"dataset_asset[{asset_obj.id}]")
        _update_attr(asset_obj, "is_query_entry", int(bool(asset_plan.is_query_entry)), changes, f"dataset_asset[{asset_obj.id}]")
        _update_attr(asset_obj, "display_order", asset_plan.display_order, changes, f"dataset_asset[{asset_obj.id}]")

        asset_meta = {
            "bundle_dir": plan.bundle_dir,
            "bundle_version": plan.version,
            "asset_code": asset_plan.asset_code,
            "asset_type": asset_plan.asset_type,
        }
        asset_meta.update(asset_plan.meta)
        _update_attr(
            asset_obj,
            "meta_json",
            _encode_json_object(asset_meta),
            changes,
            f"dataset_asset[{asset_obj.id}]",
        )
        asset_obj.update_time = now
        _sync_asset_files(db=db, asset_obj=asset_obj, asset_plan=asset_plan, changes=changes)


def _sync_asset_file(
    db,
    *,
    asset_obj,
    file_role: str,
    local_path: str,
    file_format: str | None,
    asset_file_type_code: str | None,
    index_of_file_id: int | None,
    meta_json: str | None,
    changes: list[str],
):
    existing = (
        db.query(AssetFile)
        .filter(AssetFile.dataset_asset_id == asset_obj.id, AssetFile.local_path == local_path)
        .first()
    )
    before = None
    if existing is not None:
        before = (
            existing.asset_file_type_code,
            existing.file_role,
            existing.file_format,
            existing.index_of_file_id,
            existing.meta_json,
        )
    file_obj = dataset_domain_service._ensure_asset_file_record(
        db=db,
        asset_obj=asset_obj,
        file_role=file_role,
        local_path=local_path,
        file_format=file_format,
        asset_file_type_code=asset_file_type_code,
        index_of_file_id=index_of_file_id,
        status="active",
        meta_json=meta_json,
    )
    after = (
        file_obj.asset_file_type_code,
        file_obj.file_role,
        file_obj.file_format,
        file_obj.index_of_file_id,
        file_obj.meta_json,
    )
    if before is None:
        changes.append(
            f"asset_file[{file_obj.id}] created: {file_obj.file_name} "
            f"(type={file_obj.asset_file_type_code}, role={file_obj.file_role})"
        )
    elif before != after:
        changes.append(
            f"asset_file[{file_obj.id}] updated: {file_obj.file_name} "
            f"(type={file_obj.asset_file_type_code}, role={file_obj.file_role})"
        )
    return file_obj


def _sync_asset_files(db, *, asset_obj, asset_plan, changes: list[str]) -> None:
    primary_file = _sync_asset_file(
        db=db,
        asset_obj=asset_obj,
        file_role="primary",
        local_path=asset_plan.local_path,
        file_format=asset_plan.file_format,
        asset_file_type_code=asset_plan.primary_asset_file_type_code,
        index_of_file_id=None,
        meta_json=_encode_json_object(asset_plan.primary_file_meta) if asset_plan.primary_file_meta else None,
        changes=changes,
    )
    for companion in asset_plan.companion_files:
        _sync_asset_file(
            db=db,
            asset_obj=asset_obj,
            file_role=companion.file_role,
            local_path=companion.local_path,
            file_format=companion.file_format,
            asset_file_type_code=companion.asset_file_type_code,
            index_of_file_id=primary_file.id if companion.file_role == "index" else None,
            meta_json=_encode_json_object(companion.meta) if companion.meta else None,
            changes=changes,
        )


def reconcile_genome_bundle_dataset(dataset_id: int, explicit_bundle_dir: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    with MyDBManager() as db:
        registry_rows = (
            db.query(DatasetRegistry)
            .filter(DatasetRegistry.dataset_id == dataset_id)
            .order_by(DatasetRegistry.id.asc())
            .all()
        )
        if not registry_rows:
            raise SystemExit(f"dataset not found: {dataset_id}")

        primary_file = (
            db.query(AssetFile)
            .filter(AssetFile.dataset_id == dataset_id)
            .order_by(AssetFile.id.asc())
            .first()
        )
        if primary_file is None or not primary_file.local_path:
            raise SystemExit(f"dataset {dataset_id} has no primary file path")

        dataset_name = registry_rows[0].title
        current_version = _pick_current_version(db, dataset_id)
        bundle_dir = _resolve_bundle_dir(primary_file, explicit_bundle_dir)
        organism = registry_rows[0].organism if registry_rows[0].organism else None
        version = current_version.version if current_version is not None else "v1"
        plan = discover_sequence_bundle(
            bundle_dir,
            dataset_title=dataset_name,
            version=version,
            organism=organism,
        )

        changes: list[str] = []
        now = int(time.time())

        for registry_obj in registry_rows:
            _sync_registry_metadata(registry_obj, plan, changes, now)

        version_rows = (
            db.query(DatasetVersion)
            .filter(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.id.asc())
            .all()
        )
        for version_obj in version_rows:
            _update_attr(version_obj, "dataset_type", plan.dataset_type, changes, f"dataset_version[{version_obj.id}]")
            version_obj.update_time = now

        if current_version is not None:
            _sync_current_version(current_version, plan, changes, now)
            _sync_current_assets(db, dataset_id, current_version.id, plan, changes, now)

        if dry_run:
            db.rollback()
        else:
            db.commit()

        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "bundle_dir": str(bundle_dir),
            "dataset_type": plan.dataset_type,
            "changes": changes,
            "dry_run": dry_run,
        }


def main() -> int:
    init_dataset_tables()
    parser = argparse.ArgumentParser(description="Reconcile existing genome bundle datasets to the canonical genome dataset type.")
    parser.add_argument("--database-id", type=int, action="append", required=True, help="Legacy dataset/database ID to reconcile.")
    parser.add_argument("--bundle-dir", default=None, help="Optional explicit bundle directory. When omitted, inferred from the primary file path.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without committing them.")
    args = parser.parse_args()

    for dataset_id in args.dataset_id:
        result = reconcile_genome_bundle_dataset(
            dataset_id=dataset_id,
            explicit_bundle_dir=args.bundle_dir,
            dry_run=args.dry_run,
        )
        print(f"[dataset {result['dataset_id']}] {result['dataset_name']} -> {result['dataset_type']}")
        print(f"bundle_dir: {result['bundle_dir']}")
        if result["changes"]:
            for item in result["changes"]:
                print(f"  - {item}")
        else:
            print("  - no changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
