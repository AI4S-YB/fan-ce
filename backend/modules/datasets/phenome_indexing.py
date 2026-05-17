import os
import re
import sqlite3
import time
from typing import Any

from fastapi import HTTPException

from .models import PhenomeImportRun, PhenomeObservation, PhenomeSourceColumn, PhenomeSubject, PhenomeTrait


YEAR_PREFIX_PATTERN = re.compile(r"^\s*(\d{4})年(.+?)\s*$")


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return text == "" or text.upper() in {"NA", "N/A", "NULL", "NONE", "NAN"}


def _normalize_numeric(value: Any) -> float | None:
    if _is_missing_value(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    try:
        return float(text)
    except ValueError:
        return None


def _split_trait_timepoint(column_name: str) -> tuple[str, str | None, str]:
    column_name = str(column_name or "").strip()
    matched = YEAR_PREFIX_PATTERN.match(column_name)
    if matched:
        timepoint = matched.group(1)
        trait_name = matched.group(2).strip()
        return trait_name, timepoint, "year"
    return column_name, None, "none"


def _infer_value_type(values: list[Any]) -> str:
    non_missing = [value for value in values if not _is_missing_value(value)]
    if not non_missing:
        return "text"
    if all(_normalize_numeric(value) is not None for value in non_missing):
        return "numeric"
    return "text"


def _require_phenome_sqlite(file_path: str) -> None:
    if not file_path.endswith(".db") and not file_path.endswith(".sqlite"):
        raise HTTPException(status_code=400, detail="phenome indexer currently supports sqlite-backed assets only")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"phenome file not found: {file_path}")
    conn = sqlite3.connect(file_path)
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {str(row[0]) for row in cursor.fetchall()}
    finally:
        conn.close()
    if "phenotype" not in tables:
        raise HTTPException(status_code=400, detail="phenome sqlite schema is not supported yet")


def clear_phenome_index(db, *, dataset_id: int, version_id: int, asset_id: int) -> None:
    scope = {
        "dataset_id": dataset_id,
        "version_id": version_id,
        "asset_id": asset_id,
    }
    db.query(PhenomeObservation).filter_by(**scope).delete(synchronize_session=False)
    db.query(PhenomeSourceColumn).filter_by(**scope).delete(synchronize_session=False)
    db.query(PhenomeTrait).filter_by(**scope).delete(synchronize_session=False)
    db.query(PhenomeSubject).filter_by(**scope).delete(synchronize_session=False)
    db.query(PhenomeImportRun).filter_by(**scope).delete(synchronize_session=False)
    db.commit()


def rebuild_phenome_index(
    db,
    *,
    dataset_id: int,
    version_id: int,
    asset_id: int,
    file_path: str,
) -> dict[str, Any]:
    _require_phenome_sqlite(file_path)

    now = int(time.time())
    clear_phenome_index(db=db, dataset_id=dataset_id, version_id=version_id, asset_id=asset_id)

    conn = sqlite3.connect(file_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM phenotype").fetchall()
        columns = conn.execute("PRAGMA table_info(phenotype)").fetchall()
    finally:
        conn.close()

    if not columns:
        raise HTTPException(status_code=400, detail="phenome sqlite contains no phenotype columns")

    trait_columns = [dict(item) for item in columns if str(item["name"]) != "ID"]
    trait_values_by_name = {str(item["name"]): [] for item in trait_columns}
    trait_group_values: dict[str, list[Any]] = {}
    trait_group_meta: dict[str, dict[str, Any]] = {}
    row_dicts = [dict(row) for row in rows]
    for row in row_dicts:
        for trait_name in trait_values_by_name:
            trait_values_by_name[trait_name].append(row.get(trait_name))
    for column in trait_columns:
        source_name = str(column["name"])
        trait_name, timepoint, time_axis_type = _split_trait_timepoint(source_name)
        trait_group_values.setdefault(trait_name, []).extend(trait_values_by_name[source_name])
        meta = trait_group_meta.get(trait_name)
        if meta is None:
            trait_group_meta[trait_name] = {
                "display_order": column.get("cid"),
                "time_axis_type": time_axis_type,
            }
            continue
        if meta["display_order"] is None or (
            column.get("cid") is not None and column.get("cid") < meta["display_order"]
        ):
            meta["display_order"] = column.get("cid")
        if timepoint:
            meta["time_axis_type"] = "year"

    import_run = PhenomeImportRun(
        dataset_id=dataset_id,
        version_id=version_id,
        asset_id=asset_id,
        source_file_path=file_path,
        source_checksum=None,
        parser_name="phenome-sqlite-indexer",
        parser_version="v1",
        sheet_count=1,
        row_count=len(row_dicts),
        trait_count=len(trait_columns),
        observation_count=0,
        status="success",
        summary_json=None,
        create_time=now,
        update_time=now,
    )
    db.add(import_run)
    db.commit()
    db.refresh(import_run)

    subject_payloads = []
    subject_pk_by_row_key: dict[str, int] = {}
    for row_index, row in enumerate(row_dicts, start=1):
        subject_id = _normalize_text(row.get("ID")) or f"row_{row_index}"
        source_row_key = subject_id if subject_id else f"row_{row_index}"
        subject = PhenomeSubject(
            dataset_id=dataset_id,
            version_id=version_id,
            asset_id=asset_id,
            import_run_id=import_run.id,
            subject_id=subject_id,
            subject_name=subject_id,
            subject_name_cn=None,
            subject_name_en=None,
            subject_type="material_candidate",
            source_sheet="phenotype",
            source_row_key=source_row_key,
            meta_json=None,
            create_time=now,
            update_time=now,
        )
        subject_payloads.append(subject)
    db.add_all(subject_payloads)
    db.commit()
    for item in subject_payloads:
        db.refresh(item)
        subject_pk_by_row_key[item.source_row_key] = item.id

    trait_payloads = []
    for trait_name, meta in trait_group_meta.items():
        trait_payloads.append(
            PhenomeTrait(
                dataset_id=dataset_id,
                version_id=version_id,
                asset_id=asset_id,
                import_run_id=import_run.id,
                trait_code=trait_name,
                trait_name=trait_name,
                trait_name_cn=trait_name if re.search(r"[\u4e00-\u9fff]", trait_name) else None,
                trait_name_en=trait_name if not re.search(r"[\u4e00-\u9fff]", trait_name) else None,
                value_type=_infer_value_type(trait_group_values[trait_name]),
                unit=None,
                time_axis_type=meta["time_axis_type"],
                category_group=None,
                display_order=meta["display_order"],
                meta_json=None,
                create_time=now,
                update_time=now,
            )
        )
    db.add_all(trait_payloads)
    db.commit()

    trait_key_map: dict[str, PhenomeTrait] = {}
    for item in trait_payloads:
        db.refresh(item)
        trait_key_map[item.trait_code] = item

    source_columns = []
    for column in trait_columns:
        source_name = str(column["name"])
        trait_name, timepoint, _time_axis_type = _split_trait_timepoint(source_name)
        trait_obj = trait_key_map[trait_name]
        source_columns.append(
            PhenomeSourceColumn(
                dataset_id=dataset_id,
                version_id=version_id,
                asset_id=asset_id,
                import_run_id=import_run.id,
                source_sheet="phenotype",
                source_column_name=source_name,
                source_column_index=column.get("cid"),
                trait_id=trait_obj.id,
                trait_code=trait_obj.trait_code,
                timepoint=timepoint,
                parse_rule="year_prefix" if timepoint else "identity",
                meta_json=None,
                create_time=now,
            )
        )
    db.add_all(source_columns)
    db.commit()

    observation_payloads = []
    for row_index, row in enumerate(row_dicts, start=1):
        subject_id = _normalize_text(row.get("ID")) or f"row_{row_index}"
        source_row_key = subject_id if subject_id else f"row_{row_index}"
        subject_pk = subject_pk_by_row_key[source_row_key]
        for column in trait_columns:
            source_name = str(column["name"])
            trait_name, timepoint, _time_axis_type = _split_trait_timepoint(source_name)
            trait_obj = trait_key_map[trait_name]
            raw_value = row.get(source_name)
            is_missing = _is_missing_value(raw_value)
            observation_payloads.append(
                PhenomeObservation(
                    dataset_id=dataset_id,
                    version_id=version_id,
                    asset_id=asset_id,
                    import_run_id=import_run.id,
                    subject_pk=subject_pk,
                    trait_id=trait_obj.id,
                    trait_code=trait_obj.trait_code,
                    timepoint=timepoint,
                    obs_date=None,
                    value_numeric=_normalize_numeric(raw_value),
                    value_text=None if _normalize_numeric(raw_value) is not None else (_normalize_text(raw_value) if not is_missing else None),
                    value_category=None,
                    raw_value=None if raw_value is None else str(raw_value),
                    is_missing=1 if is_missing else 0,
                    source_sheet="phenotype",
                    source_row_key=source_row_key,
                    source_column_name=source_name,
                    qc_status="parsed",
                    meta_json=None,
                    create_time=now,
                )
            )
    db.add_all(observation_payloads)
    import_run.observation_count = len(observation_payloads)
    import_run.summary_json = (
        '{"source_table":"phenotype","subject_count":%d,"trait_count":%d,"observation_count":%d}'
        % (len(subject_payloads), len(trait_payloads), len(observation_payloads))
    )
    db.add(import_run)
    db.commit()

    return {
        "dataset_id": dataset_id,
        "version_id": version_id,
        "asset_id": asset_id,
        "file_path": file_path,
        "source_table": "phenotype",
        "import_run_id": import_run.id,
        "subject_count": len(subject_payloads),
        "trait_count": len(trait_payloads),
        "observation_count": len(observation_payloads),
    }


class PhenomeBreedingBridge:
    """Bridge phenome index subjects to breeding materials."""

    @staticmethod
    def map_subject_to_material(
        db, subject_name, dataset_id, version_id, asset_id
    ) -> dict:
        """Match a phenome subject_name to BreedingMaterial by material_code or material_name."""
        from modules.breeding.models import BreedingMaterial, BreedingPhenotypeSubjectMap

        material = (
            db.query(BreedingMaterial)
            .filter(
                (BreedingMaterial.material_code == subject_name)
                | (BreedingMaterial.material_name == subject_name)
            )
            .first()
        )
        if not material:
            return {"mapped": False, "subject_name": subject_name, "reason": "No matching material found"}

        existing = (
            db.query(BreedingPhenotypeSubjectMap)
            .filter_by(
                dataset_id=dataset_id,
                version_id=version_id,
                asset_id=asset_id,
                row_key=subject_name,
            )
            .first()
        )
        if not existing:
            pmap = BreedingPhenotypeSubjectMap(
                dataset_id=dataset_id,
                version_id=version_id,
                asset_id=asset_id,
                row_key=subject_name,
                material_id=material.id,
                mapping_status="matched",
                mapping_method="inferred",
                confidence="medium",
            )
            db.add(pmap)
            db.commit()

        return {
            "mapped": True,
            "subject_name": subject_name,
            "material_id": material.id,
            "material_code": material.material_code,
        }
