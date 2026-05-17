#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any

from modules.datasets.init import init_dataset_tables, seed_dataset_registry_defaults
from modules.datasets.models import (
    AssetFile,
    DatasetAsset,
    DatasetKindRegistry,
    DatasetLineageEdge,
    DatasetPublishRecord,
    DatasetRegistry,
    DatasetStagingFile,
    DatasetVersion,
    DatasetVersionPublishRecord,
    DatasetWorkflowTask,
    FunctionalGene,
    FunctionalTerm,
    FunctionalTermAssignment,
    PhenomeImportRun,
    PhenomeObservation,
    PhenomeSourceColumn,
    PhenomeSubject,
    PhenomeTrait,
)
from shared.database import MyDBManager


CANONICAL_TYPE_MAP = {
    "sequence": "genome",
    "variant": "variome",
    "expression": "transcriptome",
}

COMPAT_DATASET_KIND_CODES = {"sequence", "variant", "expression"}
DELETE_DATASET_NAMES = {"demo_expression", "demo_interaction"}


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


def _update_bundle_mode(extra_json: str | None, canonical_type: str) -> str | None:
    payload = _parse_json_object(extra_json)
    provisioning = payload.get("provisioning")
    if isinstance(provisioning, dict):
        mode = provisioning.get("mode")
        if mode == "sequence_bundle":
            provisioning["mode"] = "genome_bundle"
        elif mode == "variant_bundle":
            provisioning["mode"] = "variome_bundle"
        elif mode == "expression_bundle":
            provisioning["mode"] = "transcriptome_bundle"
        elif canonical_type in {"genome", "variome", "transcriptome"} and mode == f"{canonical_type}_bundle":
            pass
    return _encode_json_object(payload) if payload else extra_json


def migrate_legacy_dataset_types() -> list[str]:
    changes: list[str] = []
    with MyDBManager() as db:
        registry_rows = db.query(DatasetRegistry).order_by(DatasetRegistry.id.asc()).all()
        for registry_obj in registry_rows:
            canonical_type = CANONICAL_TYPE_MAP.get(str(registry_obj.dataset_type or "").lower())
            if not canonical_type:
                continue

            _update_attr(
                registry_obj,
                "dataset_type",
                canonical_type,
                changes,
                f"dataset_registry[{registry_obj.id}]",
            )
            updated_extra = _update_bundle_mode(registry_obj.extra_json, canonical_type)
            _update_attr(
                registry_obj,
                "extra_json",
                updated_extra,
                changes,
                f"dataset_registry[{registry_obj.id}]",
            )

            version_rows = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == registry_obj.id).all()
            for version_obj in version_rows:
                _update_attr(
                    version_obj,
                    "dataset_type",
                    canonical_type,
                    changes,
                    f"dataset_version[{version_obj.id}]",
                )
                updated_extra = _update_bundle_mode(version_obj.extra_json, canonical_type)
                _update_attr(
                    version_obj,
                    "extra_json",
                    updated_extra,
                    changes,
                    f"dataset_version[{version_obj.id}]",
                )
        db.commit()
    return changes


def _delete_dataset(db, dataset_id: int, changes: list[str]) -> None:
    version_ids = [
        item.id
        for item in db.query(DatasetVersion.id).filter(DatasetVersion.dataset_id == dataset_id).all()
    ]
    asset_ids = [
        item.id
        for item in db.query(DatasetAsset.id).filter(DatasetAsset.dataset_id == dataset_id).all()
    ]

    for model in (FunctionalGene, FunctionalTerm, FunctionalTermAssignment):
        db.query(model).filter(model.dataset_id == dataset_id).delete(synchronize_session=False)
    for model in (PhenomeImportRun, PhenomeSubject, PhenomeTrait, PhenomeSourceColumn, PhenomeObservation):
        db.query(model).filter(model.dataset_id == dataset_id).delete(synchronize_session=False)

    if version_ids or asset_ids:
        lineage_query = db.query(DatasetLineageEdge)
        if version_ids:
            lineage_query = lineage_query.filter(
                (DatasetLineageEdge.src_dataset_version_id.in_(version_ids))
                | (DatasetLineageEdge.dst_dataset_version_id.in_(version_ids))
                | (DatasetLineageEdge.src_asset_id.in_(asset_ids or [-1]))
                | (DatasetLineageEdge.dst_asset_id.in_(asset_ids or [-1]))
            )
        lineage_query.delete(synchronize_session=False)

    if version_ids:
        db.query(DatasetVersionPublishRecord).filter(
            (DatasetVersionPublishRecord.dataset_id == dataset_id)
            | (DatasetVersionPublishRecord.dataset_version_id.in_(version_ids))
        ).delete(synchronize_session=False)

    if asset_ids:
        db.query(AssetFile).filter(AssetFile.dataset_asset_id.in_(asset_ids)).delete(synchronize_session=False)
        db.query(DatasetAsset).filter(DatasetAsset.id.in_(asset_ids)).delete(synchronize_session=False)

    if version_ids:
        db.query(DatasetVersion).filter(DatasetVersion.id.in_(version_ids)).delete(synchronize_session=False)

    db.query(DatasetPublishRecord).filter(DatasetPublishRecord.dataset_id == dataset_id).delete(synchronize_session=False)
    db.query(DatasetWorkflowTask).filter(DatasetWorkflowTask.dataset_id == dataset_id).delete(synchronize_session=False)
    db.query(DatasetRegistry).filter(DatasetRegistry.id == dataset_id).delete(synchronize_session=False)
    db.query(DatasetStagingFile).filter(DatasetStagingFile.linked_dataset_id == dataset_id).delete(synchronize_session=False)
    changes.append(f"deleted dataset[{dataset_id}]")


def delete_demo_datasets() -> list[str]:
    changes: list[str] = []
    with MyDBManager() as db:
        rows = db.query(DatasetRegistry).filter(DatasetRegistry.title.in_(sorted(DELETE_DATASET_NAMES))).all()
        for registry_obj in rows:
            _delete_dataset(db=db, dataset_id=registry_obj.id, changes=changes)
        db.commit()
    return changes


def cleanup_compat_dataset_kinds() -> list[str]:
    changes: list[str] = []
    with MyDBManager() as db:
        rows = db.query(DatasetKindRegistry).filter(DatasetKindRegistry.code.in_(sorted(COMPAT_DATASET_KIND_CODES))).all()
        for row in rows:
            db.delete(row)
            changes.append(f"deleted dataset_kind_registry[{row.id}] {row.code}")
        db.commit()
    return changes


def summarize_current_state() -> list[str]:
    summary: list[str] = []
    with MyDBManager() as db:
        summary.append("dataset kinds:")
        for row in db.query(DatasetKindRegistry).order_by(DatasetKindRegistry.sort_order, DatasetKindRegistry.id).all():
            summary.append(f"  - {row.code} (active={row.is_active})")
        summary.append("datasets:")
        for row in db.query(DatasetRegistry).order_by(DatasetRegistry.id).all():
            summary.append(f"  - [{row.id}] {row.title}: {row.dataset_type}")
    return summary


def main() -> int:
    init_dataset_tables()
    seed_dataset_registry_defaults()

    print("[1/4] migrate legacy dataset types")
    for item in migrate_legacy_dataset_types():
        print(f"  - {item}")

    print("[2/4] delete demo datasets")
    for item in delete_demo_datasets():
        print(f"  - {item}")

    print("[3/4] cleanup compat dataset kinds")
    for item in cleanup_compat_dataset_kinds():
        print(f"  - {item}")

    print("[4/4] summary")
    for item in summarize_current_state():
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
