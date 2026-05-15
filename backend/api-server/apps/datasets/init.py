import time
import json

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from db.database import MyDBManager, engine

from .constants import (
    DEFAULT_ASSET_FILE_TYPE_REGISTRY_ITEMS,
    DEFAULT_ASSET_TYPE_REGISTRY_ITEMS,
    DEFAULT_DATASET_KIND_REGISTRY_ITEMS,
)
from .crud import asset_file_type_registry_db, asset_type_registry_db, dataset_kind_registry_db
from .dataset_model import Dataset
from .models import (
    AssetFile,
    AssetFileTypeRegistry,
    AssetTypeRegistry,
    DatasetAsset,
    DatasetKindRegistry,
    DatasetLineageEdge,
    DatasetPublishRecord,
    DatasetRegistrationCandidate,
    DatasetRegistrationCandidateFile,
    DatasetRegistry,
    DatasetScanJob,
    DatasetScanRoot,
    DatasetStagingFile,
    DatasetVersion,
    DatasetVersionPublishRecord,
    DatasetWorkflowTask,
    FunctionalGene,
    PhenomeImportRun,
    PhenomeObservation,
    PhenomeSourceColumn,
    PhenomeSubject,
    PhenomeTrait,
    FunctionalTerm,
    FunctionalTermAssignment,
)


def init_dataset_tables():
    tables = [
        DatasetKindRegistry.__table__,
        AssetTypeRegistry.__table__,
        AssetFileTypeRegistry.__table__,
        DatasetScanRoot.__table__,
        DatasetScanJob.__table__,
        DatasetStagingFile.__table__,
        DatasetRegistrationCandidate.__table__,
        DatasetRegistrationCandidateFile.__table__,
        DatasetRegistry.__table__,
        Dataset.__table__,
        DatasetWorkflowTask.__table__,
        DatasetPublishRecord.__table__,
        DatasetVersion.__table__,
        DatasetAsset.__table__,
        AssetFile.__table__,
        DatasetLineageEdge.__table__,
        DatasetVersionPublishRecord.__table__,
        FunctionalGene.__table__,
        FunctionalTerm.__table__,
        FunctionalTermAssignment.__table__,
        PhenomeImportRun.__table__,
        PhenomeSubject.__table__,
        PhenomeTrait.__table__,
        PhenomeSourceColumn.__table__,
        PhenomeObservation.__table__,
    ]
    for table in tables:
        for attempt in range(3):
            try:
                table.create(bind=engine, checkfirst=True)
                break
            except OperationalError:
                if attempt == 2:
                    raise
                time.sleep(1)
    _ensure_dataset_schema_columns()
    _ensure_dataset_schema_column_types()
    _backfill_default_public_versions()


def _ensure_dataset_schema_columns():
    inspector = inspect(engine)
    table_columns = {
        "dataset_registry": {column["name"] for column in inspector.get_columns("dataset_registry")},
        "dataset_version": {column["name"] for column in inspector.get_columns("dataset_version")},
        "asset_file_type_registry": {column["name"] for column in inspector.get_columns("asset_file_type_registry")},
        "asset_file": {column["name"] for column in inspector.get_columns("asset_file")},
        "dataset_staging_file": {column["name"] for column in inspector.get_columns("dataset_staging_file")},
        "dataset_scan_root": {column["name"] for column in inspector.get_columns("dataset_scan_root")},
        "dataset_scan_job": {column["name"] for column in inspector.get_columns("dataset_scan_job")},
    }
    ddl_statements = []
    if "default_public_version_id" not in table_columns["dataset_registry"]:
        ddl_statements.append("ALTER TABLE dataset_registry ADD COLUMN default_public_version_id INTEGER")
    if "release_state" not in table_columns["dataset_version"]:
        ddl_statements.append("ALTER TABLE dataset_version ADD COLUMN release_state VARCHAR(32)")
    if "is_default_public" not in table_columns["dataset_version"]:
        ddl_statements.append("ALTER TABLE dataset_version ADD COLUMN is_default_public INTEGER DEFAULT 0")
    if "supported_file_formats" not in table_columns["asset_file_type_registry"]:
        ddl_statements.append("ALTER TABLE asset_file_type_registry ADD COLUMN supported_file_formats TEXT")
    if "asset_file_type_code" not in table_columns["asset_file"]:
        ddl_statements.append("ALTER TABLE asset_file ADD COLUMN asset_file_type_code VARCHAR(128)")
    if "source_mode" not in table_columns["dataset_staging_file"]:
        ddl_statements.append("ALTER TABLE dataset_staging_file ADD COLUMN source_mode VARCHAR(32)")
    if "scan_root_id" not in table_columns["dataset_staging_file"]:
        ddl_statements.append("ALTER TABLE dataset_staging_file ADD COLUMN scan_root_id INTEGER")
    if "scan_job_id" not in table_columns["dataset_staging_file"]:
        ddl_statements.append("ALTER TABLE dataset_staging_file ADD COLUMN scan_job_id INTEGER")
    if "relative_path" not in table_columns["dataset_staging_file"]:
        ddl_statements.append("ALTER TABLE dataset_staging_file ADD COLUMN relative_path VARCHAR(1024)")
    if "file_mtime" not in table_columns["dataset_staging_file"]:
        ddl_statements.append("ALTER TABLE dataset_staging_file ADD COLUMN file_mtime BIGINT")
    if "discovered_at" not in table_columns["dataset_staging_file"]:
        ddl_statements.append("ALTER TABLE dataset_staging_file ADD COLUMN discovered_at INTEGER")
    if "last_seen_at" not in table_columns["dataset_staging_file"]:
        ddl_statements.append("ALTER TABLE dataset_staging_file ADD COLUMN last_seen_at INTEGER")
    if "last_scan_time" not in table_columns["dataset_scan_root"]:
        ddl_statements.append("ALTER TABLE dataset_scan_root ADD COLUMN last_scan_time INTEGER")
    if "create_user_id" not in table_columns["dataset_scan_root"]:
        ddl_statements.append("ALTER TABLE dataset_scan_root ADD COLUMN create_user_id INTEGER")
    if "changed_file_count" not in table_columns["dataset_scan_job"]:
        ddl_statements.append("ALTER TABLE dataset_scan_job ADD COLUMN changed_file_count INTEGER DEFAULT 0")
    if "missing_file_count" not in table_columns["dataset_scan_job"]:
        ddl_statements.append("ALTER TABLE dataset_scan_job ADD COLUMN missing_file_count INTEGER DEFAULT 0")
    if "skipped_registered_count" not in table_columns["dataset_scan_job"]:
        ddl_statements.append("ALTER TABLE dataset_scan_job ADD COLUMN skipped_registered_count INTEGER DEFAULT 0")

    if ddl_statements:
        with engine.begin() as conn:
            for statement in ddl_statements:
                conn.execute(text(statement))

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE dataset_version
                SET release_state = CASE
                    WHEN visibility = 'public' OR lifecycle_state = 'public' THEN 'released'
                    ELSE 'unreleased'
                END
                WHERE release_state IS NULL OR release_state = ''
                """
            )
        )
        if "file_format" in table_columns["asset_file_type_registry"]:
            conn.execute(
                text(
                    """
                    UPDATE asset_file_type_registry
                    SET supported_file_formats = '["' || lower(file_format) || '"]'
                    WHERE (supported_file_formats IS NULL OR supported_file_formats = '')
                      AND file_format IS NOT NULL
                      AND file_format <> ''
                    """
                )
            )


def _ensure_dataset_schema_column_types():
    if engine.dialect.name not in {"postgresql"}:
        return

    inspector = inspect(engine)
    bigint_columns = (
        ("dataset_staging_file", "file_size"),
        ("asset_file", "file_size"),
    )

    with engine.begin() as conn:
        for table_name, column_name in bigint_columns:
            columns = {column["name"]: column for column in inspector.get_columns(table_name)}
            column = columns.get(column_name)
            if not column:
                continue
            if "BIGINT" in str(column["type"]).upper():
                continue
            conn.execute(text(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE BIGINT"))
        conn.execute(
            text(
                """
                UPDATE dataset_version
                SET is_default_public = 0
                WHERE is_default_public IS NULL
                """
            )
        )


def _backfill_default_public_versions():
    with MyDBManager() as db:
        registry_rows = db.query(DatasetRegistry).all()
        changed = False
        for registry_obj in registry_rows:
            version_rows = (
                db.query(DatasetVersion)
                .filter(DatasetVersion.database_id == registry_obj.database_id)
                .order_by(DatasetVersion.id.desc())
                .all()
            )
            if not version_rows:
                continue

            released_rows = [
                item
                for item in version_rows
                if (getattr(item, "release_state", None) in {"released", "deprecated"})
                or item.visibility == "public"
                or item.lifecycle_state == "public"
            ]
            if not released_rows:
                continue

            selected_version = None
            if getattr(registry_obj, "default_public_version_id", None):
                selected_version = next((item for item in released_rows if item.id == registry_obj.default_public_version_id), None)
            if not selected_version:
                selected_version = sorted(released_rows, key=lambda item: (bool(item.is_current), item.id), reverse=True)[0]

            if getattr(registry_obj, "default_public_version_id", None) != selected_version.id:
                registry_obj.default_public_version_id = selected_version.id
                changed = True

            for item in version_rows:
                should_default = item.id == selected_version.id
                next_default = 1 if should_default else 0
                if getattr(item, "is_default_public", 0) != next_default:
                    item.is_default_public = next_default
                    changed = True
                if should_default and item.lifecycle_state != "public":
                    item.lifecycle_state = "public"
                    changed = True
                if not should_default and item.lifecycle_state == "public":
                    item.lifecycle_state = "ready"
                    changed = True
                if item.visibility != "public" and item in released_rows:
                    item.visibility = "public"
                    changed = True
                if getattr(item, "release_state", None) not in {"released", "deprecated"} and item in released_rows:
                    item.release_state = "released"
                    changed = True

        if changed:
            db.commit()


def seed_dataset_registry_defaults():
    now = int(time.time())
    with MyDBManager() as db:
        dataset_kind_codes = {item["code"] for item in DEFAULT_DATASET_KIND_REGISTRY_ITEMS}
        for item in DEFAULT_DATASET_KIND_REGISTRY_ITEMS:
            existing = dataset_kind_registry_db.get_filter(db=db, filters={"code": item["code"]})
            if not existing:
                dataset_kind_registry_db.create_one(
                    db=db,
                    obj_in={
                        "code": item["code"],
                        "base_code": item["base_code"],
                        "name": item["name"],
                        "description": item["description"],
                        "is_system": item["is_system"],
                        "is_active": item["is_active"],
                        "sort_order": item["sort_order"],
                        "meta_json": None,
                        "create_time": now,
                        "update_time": now,
                    },
                )
                continue

            changed = False
            for field in ("base_code", "name", "description", "is_system", "is_active", "sort_order"):
                if getattr(existing, field) != item[field]:
                    setattr(existing, field, item[field])
                    changed = True
            if changed:
                existing.update_time = now

        for row in dataset_kind_registry_db.get_data(db=db, filters={}):
            if not row.is_system:
                continue
            if row.code in dataset_kind_codes:
                continue
            db.delete(row)

        for item in DEFAULT_ASSET_TYPE_REGISTRY_ITEMS:
            existing = asset_type_registry_db.get_filter(db=db, filters={"code": item["code"]})
            allowed_dataset_types = json.dumps(item["allowed_dataset_types"], ensure_ascii=False)
            if not existing:
                asset_type_registry_db.create_one(
                    db=db,
                    obj_in={
                        "code": item["code"],
                        "base_code": item["base_code"],
                        "name": item["name"],
                        "description": item["description"],
                        "allowed_dataset_types": allowed_dataset_types,
                        "is_system": item["is_system"],
                        "is_active": item["is_active"],
                        "sort_order": item["sort_order"],
                        "meta_json": None,
                        "create_time": now,
                        "update_time": now,
                    },
                )
                continue

            changed = False
            for field in ("base_code", "name", "description", "is_system", "is_active", "sort_order"):
                if getattr(existing, field) != item[field]:
                    setattr(existing, field, item[field])
                    changed = True
            if existing.allowed_dataset_types != allowed_dataset_types:
                existing.allowed_dataset_types = allowed_dataset_types
                changed = True
            if changed:
                existing.update_time = now

        asset_file_type_codes = {item["code"] for item in DEFAULT_ASSET_FILE_TYPE_REGISTRY_ITEMS}
        targeted_asset_types = {
            asset_type
            for item in DEFAULT_ASSET_FILE_TYPE_REGISTRY_ITEMS
            for asset_type in item["allowed_asset_types"]
        }
        for item in DEFAULT_ASSET_FILE_TYPE_REGISTRY_ITEMS:
            existing = asset_file_type_registry_db.get_filter(db=db, filters={"code": item["code"]})
            allowed_asset_types = json.dumps(item["allowed_asset_types"], ensure_ascii=False)
            supported_file_formats = json.dumps(item["supported_file_formats"], ensure_ascii=False)
            if not existing:
                asset_file_type_registry_db.create_one(
                    db=db,
                    obj_in={
                        "code": item["code"],
                        "base_code": item["base_code"],
                        "name": item["name"],
                        "description": item["description"],
                        "supported_file_formats": supported_file_formats,
                        "file_role": item["file_role"],
                        "allowed_asset_types": allowed_asset_types,
                        "is_system": item["is_system"],
                        "is_active": item["is_active"],
                        "sort_order": item["sort_order"],
                        "meta_json": None,
                        "create_time": now,
                        "update_time": now,
                    },
                )
                continue

            changed = False
            for field in (
                "base_code",
                "name",
                "description",
                "file_role",
                "is_system",
                "is_active",
                "sort_order",
            ):
                if getattr(existing, field) != item[field]:
                    setattr(existing, field, item[field])
                    changed = True
            if existing.supported_file_formats != supported_file_formats:
                existing.supported_file_formats = supported_file_formats
                changed = True
            if existing.allowed_asset_types != allowed_asset_types:
                existing.allowed_asset_types = allowed_asset_types
                changed = True
            if changed:
                existing.update_time = now

        for row in asset_file_type_registry_db.get_data(db=db, filters={}):
            if not row.is_system:
                continue
            if row.code in asset_file_type_codes:
                continue
            row_asset_types = set(json.loads(row.allowed_asset_types or "[]"))
            if not row_asset_types.intersection(targeted_asset_types):
                continue
            db.delete(row)
        db.commit()


from apps.datasets.tools import register_dataset_tools

register_dataset_tools()
