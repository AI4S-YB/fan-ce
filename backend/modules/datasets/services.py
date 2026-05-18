import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
import uuid
import gzip
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import or_

from modules.breeding.models import (
    BreedingDataFile,
    BreedingDatasetAssayLink,
    BreedingDatasetSubjectLink,
    BreedingObservation,
    BreedingPhenotypeSubjectMap,
    BreedingVariantSampleMap,
)
from modules.datasets.adapters import dataset_adapter_registry
from omics.core.expression_utils import process_rnaseq_file
from omics.core.samtools_utils import process_sequence
from omics.core.variant_utils import process_variant_file

from .interaction_matrix import inspect_interaction_matrix, list_interaction_resolutions
from .functional_indexing import clear_functional_annotation_index, rebuild_functional_annotation_index
from .phenome_indexing import clear_phenome_index, rebuild_phenome_index
from .constants import (
    DATASET_LIFECYCLE_STATES,
    DEFAULT_DATASET_VERSION,
    FILE_TYPE_QUERY_ENGINES,
    LIFECYCLE_TRANSITIONS,
    WORKFLOW_TASK_STATUS,
    WORKFLOW_TASK_TYPES,
)
from .crud import (
    asset_file_db,
    asset_file_type_registry_db,
    asset_type_registry_db,
    dataset_asset_db,
    dataset_kind_registry_db,
    dataset_lineage_edge_db,
    dataset_publish_record_db,
    dataset_registry_db,
    dataset_scan_job_db,
    dataset_scan_root_db,
    dataset_staging_file_db,
    dataset_version_db,
    dataset_version_publish_record_db,
    dataset_workflow_task_db,
)
from .models import (
    AssetFile,
    DatasetAsset,
    DatasetVersion,
    FunctionalGene,
    FunctionalTerm,
    FunctionalTermAssignment,
    PhenomeImportRun,
    PhenomeObservation,
    PhenomeSourceColumn,
    PhenomeSubject,
    PhenomeTrait,
    AssetTypeRegistry,
    DatasetRegistry,
)
from config.settings import settings
from shared.database import MyDBManager, mydb


def validate_lineage_relation_type(relation_type: str) -> bool:
    VALID_TYPES = {"derived_from", "derived_from_legacy", "cites", "supersedes", "complements", "references"}
    if relation_type not in VALID_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid relation_type: '{relation_type}'. Must be one of: {sorted(VALID_TYPES)}",
        )
    return True


# ── Legacy bridge stub (databases table removed, database_id kept as column) ──
class _LegacyBridgeStub:
    """Minimal stub replacing dataset_legacy_bridge."""

    def get_database(self, db, dataset_id):
        return db.query(DatasetRegistry).filter(DatasetRegistry.id == dataset_id).first()

    def list_databases(self, db, page=0, size=0, filters=None, filters_exp=None, sort="-id"):
        """Query DatasetRegistry directly (was legacy databases table)."""
        from types import SimpleNamespace

        query = db.query(DatasetRegistry)
        if filters:
            for k, v in filters.items():
                if hasattr(DatasetRegistry, k):
                    query = query.filter(getattr(DatasetRegistry, k) == v)
        if filters_exp:
            for fe in filters_exp:
                if len(fe) == 3 and hasattr(DatasetRegistry, fe[0]):
                    query = query.filter(getattr(DatasetRegistry, fe[0]) == fe[2])

        total = query.count()
        if size > 0:
            # page is 1-based from frontend, SQL offset is 0-based
            p = max(0, (page or 1) - 1)
            query = query.offset(p * size).limit(size)
        # size=0 means "return all" (used by post-filter path)

        rows = query.all()

        items = [SimpleNamespace(
            id=r.id,
            dataset_code=getattr(r, 'dataset_code', ''),
            title=getattr(r, 'title', ''),
            organism=getattr(r, 'organism', ''),
            file_format=getattr(r, 'file_format', ''),
            lifecycle_state=getattr(r, 'lifecycle_state', ''),
            visibility=getattr(r, 'visibility', ''),
            create_time=getattr(r, 'create_time', None),
            update_time=getattr(r, 'update_time', None),
        ) for r in rows]
        return {"dataList": items, "total": total}

    def create_database(self, db, obj_in):
        raise NotImplementedError("Use DatasetRegistry directly")

    def update_database(self, db, db_obj, obj_in):
        pass

    def get_primary_file(self, db, dataset_id):
        return None

    def create_primary_file(self, db, **kwargs):
        pass

    def update_primary_file(self, db, **kwargs):
        pass

    def list_meta(self, db, dataset_id):
        """Return metadata for a dataset. Replaced by direct query."""
        registry = db.query(DatasetRegistry).filter(DatasetRegistry.id == dataset_id).first()
        if not registry:
            return []
        return [{"key": "dataset_code", "value": registry.dataset_code or ""},
                {"key": "organism", "value": str(registry.organism) if registry.organism else ""}]

    def list_project_links_by_project(self, db, project_id):
        return []

    def create_project_link(self, db, **kwargs):
        pass

    def delete_legacy_cascade(self, db, dataset_id):
        pass


dataset_legacy_bridge = _LegacyBridgeStub()


class DatasetDomainService:
    VALID_RELATION_TYPES = {
        "derived_from", "derived_from_legacy", "cites",
        "supersedes", "complements", "references",
    }
    DATASET_TYPE_ALIASES = {
        "sequence": "genome",
        "genome_sequence": "genome",
        "expression": "transcriptome",
        "rnaseq": "transcriptome",
        "variant": "variome",
        "vcf": "variome",
        "phenotype": "phenome",
    }
    FILE_FORMAT_TO_DATASET_TYPE = {
        "fa": "genome",
        "fasta": "genome",
        "fna": "genome",
        "fa.gz": "genome",
        "fasta.gz": "genome",
        "fna.gz": "genome",
        "vcf": "variome",
        "vcf.gz": "variome",
        "bcf": "variome",
        "h5": "transcriptome",
        "hdf5": "transcriptome",
        "xlsx": "phenome",
        "xls": "phenome",
        "csv": "phenome",
        "tsv": "phenome",
        "gff": "annotation",
        "gff.gz": "annotation",
        "gff3": "annotation",
        "gff3.gz": "annotation",
        "gtf": "annotation",
        "gtf.gz": "annotation",
        "bed": "signal",
        "bed.gz": "signal",
        "bedpe": "interaction",
        "bedpe.gz": "interaction",
        "pairs": "interaction",
        "pairs.gz": "interaction",
        "cool": "interaction",
        "mcool": "interaction",
        "bw": "signal",
        "bigwig": "signal",
    }
    DATASET_TYPE_TO_ASSET_TYPE = {
        "genome": "reference_fasta",
        "annotation": "gene_annotation",
        "variome": "variant_vcf",
        "transcriptome": "expression_matrix",
        "signal": "signal_track",
        "phenome": "phenotype_table",
        "interaction": "interaction_matrix",
        "generic": "metadata_table",
    }

    def _canonical_dataset_type(self, dataset_type):
        normalized = (dataset_type or "generic").lower()
        return self.DATASET_TYPE_ALIASES.get(normalized, normalized)

    def _canonicalize_dataset_type_list(self, values):
        normalized = []
        seen = set()
        for value in values or []:
            code = self._canonical_dataset_type(self._normalize_registry_code(value, "dataset_type"))
            if code in seen:
                continue
            seen.add(code)
            normalized.append(code)
        return normalized

    def _dataset_type_matches(self, dataset_type_value, expected):
        if not expected:
            return True
        return self._canonical_dataset_type(dataset_type_value) == self._canonical_dataset_type(expected)

    def _canonicalize_asset_type_list(self, values):
        normalized = []
        seen = set()
        for value in values or []:
            code = self._normalize_registry_code(value, "asset_type")
            if code in seen:
                continue
            seen.add(code)
            normalized.append(code)
        return normalized

    def _normalize_registry_code(self, value, field_name):
        code = str(value or "").strip().lower().replace(" ", "_")
        if not code:
            raise HTTPException(status_code=400, detail=f"{field_name} is required")
        return code

    def _normalize_file_role(self, value, field_name="file_role"):
        role = str(value or "").strip().lower().replace(" ", "_")
        if not role:
            raise HTTPException(status_code=400, detail=f"{field_name} is required")
        return role

    def _parse_json_list(self, value):
        if not value:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(parsed, list):
            return []
        return [str(item) for item in parsed if str(item).strip()]

    def _encode_json_list(self, values):
        if values is None:
            return None
        normalized = []
        seen = set()
        for item in values:
            code = self._canonical_dataset_type(self._normalize_registry_code(item, "allowed_dataset_types item"))
            if code in seen:
                continue
            seen.add(code)
            normalized.append(code)
        return json.dumps(normalized, ensure_ascii=False)

    def _encode_json_asset_type_list(self, values):
        if values is None:
            return None
        normalized = []
        seen = set()
        for item in values:
            code = self._normalize_registry_code(item, "allowed_asset_types item")
            if code in seen:
                continue
            seen.add(code)
            normalized.append(code)
        return json.dumps(normalized, ensure_ascii=False)

    def _normalize_file_format_value(self, value, field_name="file_format"):
        file_format = str(value or "").strip().lower().lstrip(".")
        if not file_format:
            raise HTTPException(status_code=400, detail=f"{field_name} is required")
        return file_format

    def _normalize_file_format_list(self, values, field_name="supported_file_formats", require_non_empty=True):
        normalized = []
        seen = set()
        for item in values or []:
            file_format = self._normalize_file_format_value(item, field_name)
            if file_format in seen:
                continue
            seen.add(file_format)
            normalized.append(file_format)
        if require_non_empty and not normalized:
            raise HTTPException(status_code=400, detail=f"{field_name} is required")
        return normalized

    def _encode_json_file_format_list(self, values):
        if values is None:
            return None
        return json.dumps(self._normalize_file_format_list(values), ensure_ascii=False)

    def _build_dataset_kind_registry_payload(self, registry_obj):
        return {
            "id": registry_obj.id,
            "code": registry_obj.code,
            "base_code": registry_obj.base_code,
            "name": registry_obj.name,
            "description": registry_obj.description,
            "is_system": bool(registry_obj.is_system),
            "is_active": bool(registry_obj.is_active),
            "sort_order": registry_obj.sort_order,
            "meta_json": registry_obj.meta_json,
            "create_time": registry_obj.create_time,
            "update_time": registry_obj.update_time,
        }

    def _build_asset_type_registry_payload(self, registry_obj):
        return {
            "id": registry_obj.id,
            "code": registry_obj.code,
            "base_code": registry_obj.base_code,
            "name": registry_obj.name,
            "description": registry_obj.description,
            "allowed_dataset_types": self._canonicalize_dataset_type_list(self._parse_json_list(registry_obj.allowed_dataset_types)),
            "is_system": bool(registry_obj.is_system),
            "is_active": bool(registry_obj.is_active),
            "sort_order": registry_obj.sort_order,
            "meta_json": registry_obj.meta_json,
            "create_time": registry_obj.create_time,
            "update_time": registry_obj.update_time,
        }

    def _build_asset_file_type_registry_payload(self, registry_obj):
        supported_file_formats = self._normalize_file_format_list(
            self._parse_json_list(registry_obj.supported_file_formats),
            "supported_file_formats",
            require_non_empty=False,
        )
        return {
            "id": registry_obj.id,
            "code": registry_obj.code,
            "base_code": registry_obj.base_code,
            "name": registry_obj.name,
            "description": registry_obj.description,
            "supported_file_formats": supported_file_formats,
            "file_role": registry_obj.file_role,
            "allowed_asset_types": self._canonicalize_asset_type_list(self._parse_json_list(registry_obj.allowed_asset_types)),
            "is_system": bool(registry_obj.is_system),
            "is_active": bool(registry_obj.is_active),
            "sort_order": registry_obj.sort_order,
            "meta_json": registry_obj.meta_json,
            "create_time": registry_obj.create_time,
            "update_time": registry_obj.update_time,
        }

    def _get_organism_name(self, db, tax_id):
        """Look up scientific_name for a taxonomy tax_id."""
        if not tax_id:
            return None
        from modules.breeding.models import BreedingTaxonomyNode
        node = db.query(BreedingTaxonomyNode).filter(BreedingTaxonomyNode.tax_id == tax_id).first()
        return node.scientific_name if node else None

    def _get_dataset_kind_registry_by_code(self, db, code):
        return dataset_kind_registry_db.get_filter(db=db, filters={"code": code})

    def _get_asset_type_registry_by_code(self, db, code):
        return asset_type_registry_db.get_filter(db=db, filters={"code": code})

    def _get_asset_file_type_registry_by_code(self, db, code):
        return asset_file_type_registry_db.get_filter(db=db, filters={"code": code})

    def _require_dataset_kind_code(self, db, dataset_type, active_only=True):
        code = self._normalize_registry_code(dataset_type or "generic", "dataset_type")
        canonical_code = self._canonical_dataset_type(code)
        registry_obj = self._get_dataset_kind_registry_by_code(db=db, code=code)
        canonical_registry_obj = (
            self._get_dataset_kind_registry_by_code(db=db, code=canonical_code)
            if canonical_code != code
            else registry_obj
        )

        preferred_obj = canonical_registry_obj or registry_obj
        if preferred_obj and (not active_only or preferred_obj.is_active):
            return preferred_obj.code, preferred_obj
        if registry_obj and (not active_only or registry_obj.is_active):
            return registry_obj.code, registry_obj
        if not preferred_obj and not registry_obj:
            raise HTTPException(status_code=400, detail=f"dataset_kind is not registered: {code}")
        inactive_code = preferred_obj.code if preferred_obj else code
        if active_only:
            if registry_obj and not registry_obj.is_active and canonical_registry_obj and canonical_registry_obj.is_active:
                return canonical_registry_obj.code, canonical_registry_obj
            if canonical_registry_obj and not canonical_registry_obj.is_active and registry_obj and registry_obj.is_active:
                return registry_obj.code, registry_obj
            raise HTTPException(status_code=400, detail=f"dataset_kind is inactive: {code}")
        return inactive_code, preferred_obj or registry_obj

    def _require_asset_type_code(self, db, asset_type, dataset_type=None, active_only=True):
        code = self._normalize_registry_code(asset_type, "asset_type")
        registry_obj = self._get_asset_type_registry_by_code(db=db, code=code)
        if not registry_obj:
            raise HTTPException(status_code=400, detail=f"asset_type is not registered: {code}")
        if active_only and not registry_obj.is_active:
            raise HTTPException(status_code=400, detail=f"asset_type is inactive: {code}")
        normalized_dataset_type = None
        if dataset_type:
            normalized_dataset_type, _ = self._require_dataset_kind_code(db=db, dataset_type=dataset_type, active_only=False)
        allowed_dataset_types = self._canonicalize_dataset_type_list(self._parse_json_list(registry_obj.allowed_dataset_types))
        if normalized_dataset_type and allowed_dataset_types and normalized_dataset_type not in allowed_dataset_types:
            raise HTTPException(
                status_code=400,
                detail=f"asset_type {code} is not allowed for dataset_kind {normalized_dataset_type}",
            )
        return code, registry_obj

    def _list_asset_file_type_registry_rows(self, db, asset_type, active_only=True):
        normalized_asset_type = self._normalize_registry_code(asset_type, "asset_type")
        rows = asset_file_type_registry_db.get_data(db=db, filters={})
        matched_rows = []
        for row in rows:
            if active_only and not row.is_active:
                continue
            allowed_asset_types = self._canonicalize_asset_type_list(self._parse_json_list(row.allowed_asset_types))
            if allowed_asset_types and normalized_asset_type not in allowed_asset_types:
                continue
            matched_rows.append(row)
        return sorted(matched_rows, key=lambda item: (item.sort_order or 0, item.id))

    def _validate_asset_file_registry_binding(self, db, asset_type, file_role, file_format=None, local_path=None, asset_file_type_code=None):
        normalized_asset_type = self._normalize_registry_code(asset_type, "asset_type")
        normalized_file_role = self._normalize_file_role(file_role)
        resolved_file_format = file_format or (self._guess_file_suffix(local_path) if local_path else None)
        if resolved_file_format:
            resolved_file_format = self._normalize_file_format_value(resolved_file_format)

        registry_rows = self._list_asset_file_type_registry_rows(db=db, asset_type=normalized_asset_type, active_only=True)
        if not registry_rows:
            return None, resolved_file_format
        if not resolved_file_format:
            raise HTTPException(
                status_code=400,
                detail=f"file_format is required for asset_type {normalized_asset_type}",
            )

        if asset_file_type_code:
            normalized_type_code = self._normalize_registry_code(asset_file_type_code, "asset_file_type_code")
            registry_row = self._get_asset_file_type_registry_by_code(db=db, code=normalized_type_code)
            if not registry_row or (registry_row.is_active is not None and not registry_row.is_active):
                raise HTTPException(status_code=400, detail=f"asset_file_type not found: {normalized_type_code}")
            allowed_asset_types = self._canonicalize_asset_type_list(self._parse_json_list(registry_row.allowed_asset_types))
            if allowed_asset_types and normalized_asset_type not in allowed_asset_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"asset_file_type {normalized_type_code} is not allowed for asset_type {normalized_asset_type}",
                )
            row_file_role = self._normalize_file_role(registry_row.file_role)
            if row_file_role != normalized_file_role:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"asset_file_type {normalized_type_code} requires file_role {row_file_role}, "
                        f"got {normalized_file_role}"
                    ),
                )
            supported_file_formats = self._normalize_file_format_list(
                self._parse_json_list(registry_row.supported_file_formats),
                "supported_file_formats",
                require_non_empty=False,
            )
            if supported_file_formats and resolved_file_format not in supported_file_formats:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"asset_file_type {normalized_type_code} does not support file_format {resolved_file_format}; "
                        f"allowed={json.dumps(supported_file_formats, ensure_ascii=False)}"
                    ),
                )
            return registry_row, resolved_file_format

        matched_rows = []
        for row in registry_rows:
            row_file_role = self._normalize_file_role(row.file_role)
            if row_file_role != normalized_file_role:
                continue
            supported_file_formats = self._normalize_file_format_list(
                self._parse_json_list(row.supported_file_formats),
                "supported_file_formats",
                require_non_empty=False,
            )
            if resolved_file_format in supported_file_formats:
                matched_rows.append(row)

        if len(matched_rows) == 1:
            return matched_rows[0], resolved_file_format
        if len(matched_rows) > 1:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"asset file type is ambiguous for asset_type {normalized_asset_type}: "
                    f"file_role={normalized_file_role}, file_format={resolved_file_format}; "
                    f"matched={json.dumps([row.code for row in matched_rows], ensure_ascii=False)}; "
                    f"asset_file_type_code is required"
                ),
            )

        allowed_summaries = []
        for row in registry_rows:
            supported_file_formats = self._normalize_file_format_list(
                self._parse_json_list(row.supported_file_formats),
                "supported_file_formats",
                require_non_empty=False,
            )
            allowed_summaries.append(
                {
                    "code": row.code,
                    "file_role": row.file_role,
                    "supported_file_formats": supported_file_formats,
                }
            )
        raise HTTPException(
            status_code=400,
            detail=(
                f"asset file is not allowed for asset_type {normalized_asset_type}: "
                f"file_role={normalized_file_role}, file_format={resolved_file_format}; "
                f"allowed={json.dumps(allowed_summaries, ensure_ascii=False)}"
            ),
        )

    def _validate_asset_files_against_asset_type(self, db, asset_obj, asset_type):
        asset_rows = self._list_asset_file_rows(db=db, asset_id=asset_obj.id)
        for row in asset_rows:
            self._validate_asset_file_registry_binding(
                db=db,
                asset_type=asset_type,
                file_role=row.file_role,
                file_format=row.file_format,
                local_path=row.local_path,
                asset_file_type_code=getattr(row, "asset_file_type_code", None),
            )

    def _get_preferred_primary_asset_file_type_code(self, db, asset_type):
        registry_rows = self._list_asset_file_type_registry_rows(db=db, asset_type=asset_type, active_only=True)
        for row in registry_rows:
            if self._normalize_file_role(row.file_role) == "primary":
                return row.code
        return None

    def _should_sync_asset_primary_profile(self, db, asset_obj, registry_row, file_role):
        if self._normalize_file_role(file_role) != "primary":
            return False
        if registry_row is None:
            return True
        preferred_code = self._get_preferred_primary_asset_file_type_code(db=db, asset_type=asset_obj.asset_type)
        if preferred_code:
            return registry_row.code == preferred_code
        return True

    def _now(self):
        return datetime.now(timezone.utc)

    @staticmethod
    def _merge_meta_json(existing_json, new_fields):
        """Merge new_fields into existing meta_json, preserving existing keys."""
        merged = {}
        if existing_json:
            try:
                merged = json.loads(existing_json) if isinstance(existing_json, str) else (existing_json or {})
            except (TypeError, json.JSONDecodeError):
                merged = {}
        merged.update(new_fields or {})
        return json.dumps(merged, ensure_ascii=False)

    def _is_platform_admin(self, user):
        if not user:
            return False
        return bool(getattr(user, "is_superman", False) or getattr(user, "user_type", 0) == 1)

    def _require_platform_admin(self, user, detail="platform admin permission required"):
        if self._is_platform_admin(user):
            return
        raise HTTPException(status_code=403, detail=detail)

    @staticmethod
    def can_access_dataset(*, db, dataset_visibility, dataset_team_id=None, dataset_project_id=None, user_team_ids=None, user_project_ids=None):
        """Check if a user can access a dataset based on its visibility.

        Community Edition: only public visibility grants access.
        Team/project membership is no longer checked.
        """
        if dataset_visibility == "public":
            return True
        return False

    def _can_access_dataset(self, db, database_obj, user):
        # 1. 未认证用户 -> 允许（后续由 API 层做认证检查）
        if not user:
            return True
        # 2. 平台 admin -> 允许
        if self._is_platform_admin(user):
            return True
        # 3. 数据 owner -> 允许
        user_id = getattr(user, "id", None)
        if user_id and database_obj.user_id == user_id:
            return True
        # 4. public 数据 -> 任何认证用户可访问
        if getattr(database_obj, "default_public_version_id", None):
            return True
        # 5. 否则拒绝
        return False

    def _ensure_dataset_read_access(self, db, dataset_id, user):
        database_obj = db.query(DatasetRegistry).filter(DatasetRegistry.id == dataset_id).first()
        if self._can_access_dataset(db=db, database_obj=database_obj, user=user):
            return database_obj
        raise HTTPException(status_code=403, detail=f"dataset read access denied: {dataset_id}")

    def _ensure_dataset_write_access(self, db, dataset_id, user):
        database_obj = db.query(DatasetRegistry).filter(DatasetRegistry.id == dataset_id).first()
        if self._can_access_dataset(db=db, database_obj=database_obj, user=user):
            return database_obj
        raise HTTPException(status_code=403, detail=f"dataset write access denied: {dataset_id}")

    def _ensure_version_read_access(self, db, version_id, user):
        version_obj = dataset_version_db.get(db=db, id=version_id)
        self._ensure_dataset_read_access(db=db, dataset_id=version_obj.dataset_id, user=user)
        return version_obj

    def _ensure_version_write_access(self, db, version_id, user):
        version_obj = dataset_version_db.get(db=db, id=version_id)
        self._ensure_dataset_write_access(db=db, dataset_id=version_obj.dataset_id, user=user)
        return version_obj

    def _get_asset_dataset_id(self, db, asset_obj):
        """Get dataset_id from an asset via its version."""
        if not asset_obj or not asset_obj.dataset_version_id:
            return None
        version = dataset_version_db.get(db=db, id=asset_obj.dataset_version_id)
        return version.dataset_id if version else None

    def _ensure_asset_read_access(self, db, asset_id, user):
        asset_obj = dataset_asset_db.get(db=db, id=asset_id)
        self._ensure_dataset_read_access(db=db, dataset_id=self._get_asset_dataset_id(db, asset_obj), user=user)
        return asset_obj

    def _ensure_asset_write_access(self, db, asset_id, user):
        asset_obj = dataset_asset_db.get(db=db, id=asset_id)
        self._ensure_dataset_write_access(db=db, dataset_id=self._get_asset_dataset_id(db, asset_obj), user=user)
        return asset_obj

    def _ensure_asset_file_read_access(self, db, asset_file_id, user):
        file_obj = asset_file_db.get(db=db, id=asset_file_id)
        self._ensure_dataset_read_access(db=db, dataset_id=file_obj.dataset_id, user=user)
        return file_obj

    def _ensure_asset_file_write_access(self, db, asset_file_id, user):
        file_obj = asset_file_db.get(db=db, id=asset_file_id)
        self._ensure_dataset_write_access(db=db, dataset_id=file_obj.dataset_id, user=user)
        return file_obj

    def _get_lineage_dataset_ids(self, db, lineage_obj):
        dataset_ids = set()
        if getattr(lineage_obj, "src_dataset_version_id", None):
            src_version = dataset_version_db.get_one(db=db, id=lineage_obj.src_dataset_version_id)
            if src_version and src_version.dataset_id:
                dataset_ids.add(src_version.dataset_id)
        if getattr(lineage_obj, "dst_dataset_version_id", None):
            dst_version = dataset_version_db.get_one(db=db, id=lineage_obj.dst_dataset_version_id)
            if dst_version and dst_version.dataset_id:
                dataset_ids.add(dst_version.dataset_id)
        return dataset_ids

    def _can_access_lineage(self, db, lineage_obj, user):
        if not user or self._is_platform_admin(user):
            return True
        dataset_ids = self._get_lineage_dataset_ids(db=db, lineage_obj=lineage_obj)
        if not dataset_ids:
            return True
        return all(
            self._can_access_dataset(db=db, database_obj=db.query(DatasetRegistry).filter(DatasetRegistry.id == dataset_id).first(), user=user)
            for dataset_id in dataset_ids
        )

    def _ensure_lineage_read_access(self, db, lineage_obj, user):
        if self._can_access_lineage(db=db, lineage_obj=lineage_obj, user=user):
            return lineage_obj
        raise HTTPException(status_code=403, detail=f"dataset lineage read access denied: {lineage_obj.id}")

    def _ensure_lineage_write_access(self, db, lineage_obj, user):
        if self._can_access_lineage(db=db, lineage_obj=lineage_obj, user=user):
            return lineage_obj
        raise HTTPException(status_code=403, detail=f"dataset lineage write access denied: {lineage_obj.id}")

    def _ensure_task_access(self, db, task_obj, user, write=False):
        if not user or self._is_platform_admin(user):
            return task_obj
        if task_obj.dataset_id:
            if write:
                self._ensure_dataset_write_access(db=db, dataset_id=task_obj.dataset_id, user=user)
            else:
                self._ensure_dataset_read_access(db=db, dataset_id=task_obj.dataset_id, user=user)
            return task_obj
        if getattr(task_obj, "operator_id", None) == getattr(user, "id", None):
            return task_obj
        raise HTTPException(status_code=403, detail=f"workflow task access denied: {task_obj.id}")

    def _ensure_assignable_scope(self, db, user, team_id=None, project_id=None):
        # Community Edition: platform admin can assign any scope
        if not user or self._is_platform_admin(user):
            return
        # Non-admin users can only assign to themselves (no team/project scoping)
        return

    def _update_db_obj(self, db, db_obj, **updates):
        for field, value in updates.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def _attach_query_runtime(self, dataset_payload, db):
        dataset_payload["_runtime_context"] = {"db": db}
        return dataset_payload

    def _is_functional_annotation_asset(self, asset_obj):
        if not asset_obj:
            return False
        return (
            str(getattr(asset_obj, "asset_type", "") or "").lower() == "functional_annotation"
            or str(getattr(asset_obj, "query_engine", "") or "").lower() == "functional_annotation"
        )

    def _maybe_rebuild_functional_annotation_index(self, db, asset_obj):
        if not self._is_functional_annotation_asset(asset_obj):
            return None
        primary_file_path = self._resolve_asset_primary_file_path(db=db, asset_obj=asset_obj)
        if not primary_file_path:
            return None
        return rebuild_functional_annotation_index(
            db=db,
            dataset_id=self._get_asset_dataset_id(db, asset_obj),
            version_id=asset_obj.dataset_version_id,
            asset_id=asset_obj.id,
            file_path=primary_file_path,
        )

    def _clear_functional_annotation_index(self, db, asset_obj):
        if not self._is_functional_annotation_asset(asset_obj):
            return
        clear_functional_annotation_index(
            db=db,
            dataset_id=self._get_asset_dataset_id(db, asset_obj),
            version_id=asset_obj.dataset_version_id,
            asset_id=asset_obj.id,
        )

    def _is_phenome_index_asset(self, asset_obj):
        if not asset_obj:
            return False
        asset_type = str(getattr(asset_obj, "asset_type", "") or "").lower()
        query_engine = str(getattr(asset_obj, "query_engine", "") or "").lower()
        return asset_type == "phenotype_index" or query_engine == "phenome"

    def _maybe_rebuild_phenome_index(self, db, asset_obj):
        if not self._is_phenome_index_asset(asset_obj):
            return None
        primary_file_path = self._resolve_asset_primary_file_path(db=db, asset_obj=asset_obj)
        if not primary_file_path:
            return None
        return rebuild_phenome_index(
            db=db,
            dataset_id=self._get_asset_dataset_id(db, asset_obj),
            version_id=asset_obj.dataset_version_id,
            asset_id=asset_obj.id,
            file_path=primary_file_path,
        )

    def _clear_phenome_index(self, db, asset_obj):
        if not self._is_phenome_index_asset(asset_obj):
            return
        clear_phenome_index(
            db=db,
            dataset_id=self._get_asset_dataset_id(db, asset_obj),
            version_id=asset_obj.dataset_version_id,
            asset_id=asset_obj.id,
        )

    def _normalize_file_format(self, file_obj):
        if not file_obj:
            return None
        if file_obj.type:
            return str(file_obj.type).lower().lstrip(".")
        if file_obj.data_type and str(file_obj.data_type).lower() not in {"file", "generic"}:
            return str(file_obj.data_type).lower()
        return None

    def _infer_dataset_type(self, database_obj, file_obj):
        file_format = self._normalize_file_format(file_obj)
        if file_format and file_format in self.FILE_FORMAT_TO_DATASET_TYPE:
            return self.FILE_FORMAT_TO_DATASET_TYPE[file_format]
        if file_obj and file_obj.data_type and str(file_obj.data_type).lower() not in {"file", "generic"}:
            return file_obj.data_type
        if file_obj and file_obj.type:
            return file_obj.type.lstrip(".")
        return database_obj.type or "generic"

    def _infer_state(self, database_obj):
        if getattr(database_obj, "default_public_version_id", None):
            return "public"
        if getattr(database_obj, "is_active", False):
            return "uploaded"
        return "draft"

    def _infer_visibility(self, database_obj):
        return "public" if getattr(database_obj, "default_public_version_id", None) else "private"

    def _collect_meta(self, db, database_id):
        meta_items = dataset_legacy_bridge.list_meta(db=db, dataset_id=database_id)
        return [
            {
                "id": getattr(item, 'id', None),
                "key": getattr(item, 'key', ''),
                "value": getattr(item, 'value', ''),
                "code": getattr(item, 'code', ''),
                "type": getattr(item, 'type', ''),
                "description": getattr(item, 'description', ''),
            }
            for item in meta_items
        ]

    def _collect_projects(self, db, database_id):
        # TODO(Task-4): Community Edition — system_project removed. Restore via brd_program lookup.
        return []

    def _guess_name_from_path(self, file_path):
        return Path(file_path).name

    def _guess_file_suffix(self, file_path):
        file_name = Path(file_path).name.lower()
        if file_name.endswith(".vcf.gz"):
            return "vcf.gz"
        for suffix in ("gff3.gz", "gff.gz", "gtf.gz", "bedpe.gz", "pairs.gz", "bed.gz", "fa.gz", "fasta.gz", "fna.gz"):
            if file_name.endswith(f".{suffix}"):
                return suffix
        suffix = Path(file_path).suffix.lower().lstrip(".")
        return suffix

    def _to_file_type(self, file_format):
        if not file_format:
            return None
        return f".{str(file_format).lstrip('.')}"

    def _to_storage_uri(self, file_path):
        if not file_path:
            return None
        if "://" in file_path:
            return file_path
        return f"file://{file_path}"

    def _normalize_local_path(self, file_path):
        if not file_path:
            return None
        if "://" in file_path:
            if file_path.startswith("file://"):
                return file_path[len("file://") :]
            return None
        return file_path

    def _get_primary_file_from_asset_payload(self, asset_payload):
        if not asset_payload:
            return None
        files = asset_payload.get("files") or []
        primary_file = next((item for item in files if item.get("file_role") == "primary"), None)
        if primary_file:
            return primary_file
        return files[0] if files else None

    def _resolve_dataset_primary_file_payload(self, dataset_payload):
        query_entry_asset = dataset_payload.get("query_entry_asset")
        if not query_entry_asset:
            asset_items = dataset_payload.get("assets") or []
            query_entry_asset = next((item for item in asset_items if item.get("is_query_entry")), None)
            if not query_entry_asset and asset_items:
                query_entry_asset = asset_items[0]
        primary_file = self._get_primary_file_from_asset_payload(query_entry_asset)
        if primary_file:
            return primary_file
        return dataset_payload.get("file")

    def _resolve_dataset_primary_file_path(self, dataset_payload):
        file_payload = self._resolve_dataset_primary_file_payload(dataset_payload) or {}
        return self._normalize_local_path(
            file_payload.get("local_path")
            or file_payload.get("path")
            or file_payload.get("storage_uri")
        )

    def _resolve_version_primary_file_path(self, db, version_obj):
        if not version_obj:
            return None
        asset_payloads = self._ensure_assets_for_version(db=db, version_obj=version_obj)
        query_entry_asset = next((item for item in asset_payloads if item["is_query_entry"]), None)
        if not query_entry_asset and asset_payloads:
            query_entry_asset = asset_payloads[0]
        primary_file = self._get_primary_file_from_asset_payload(query_entry_asset)
        if primary_file:
            return self._normalize_local_path(
                primary_file.get("local_path")
                or primary_file.get("path")
                or primary_file.get("storage_uri")
            )
        return self._normalize_local_path(getattr(version_obj, "file_path", None))

    def _resolve_asset_primary_file_path(self, db, asset_obj):
        if not asset_obj:
            return None
        file_rows = self._list_asset_file_rows(db=db, asset_id=asset_obj.id)
        primary_file = next((item for item in file_rows if item.file_role == "primary"), None)
        if not primary_file and file_rows:
            primary_file = file_rows[0]
        if not primary_file:
            return None
        return self._normalize_local_path(primary_file.local_path or primary_file.storage_uri)

    def _build_file_access_payload(self, file_path):
        return {
            "exists_on_server": bool(file_path and os.path.exists(file_path)),
        }

    def _get_dataset_staging_root(self):
        configured = settings.app_options.get("dataset_staging.dir")
        root = configured or os.path.join(settings.BASE_PATH, "runtime", "dataset-staging")
        os.makedirs(root, exist_ok=True)
        return root

    def _get_dataset_storage_root(self):
        configured = settings.app_options.get("dataset_storage.dir")
        root = configured or os.path.join(settings.BASE_PATH, "runtime", "datasets")
        os.makedirs(root, exist_ok=True)
        return root

    def _build_staging_local_path(self, source_name):
        safe_name = Path(source_name or "upload.bin").name
        date_dir = time.strftime("%Y%m%d")
        target_dir = os.path.join(self._get_dataset_staging_root(), date_dir)
        os.makedirs(target_dir, exist_ok=True)
        return os.path.join(target_dir, f"{uuid.uuid4().hex}_{safe_name}")

    def _build_dataset_staging_payload(self, staging_obj):
        return {
            "id": staging_obj.id,
            "staging_code": staging_obj.staging_code,
            "source_name": staging_obj.source_name,
            "file_name": staging_obj.file_name,
            "storage_uri": staging_obj.storage_uri,
            "local_path": staging_obj.local_path,
            "file_format": staging_obj.file_format,
            "file_size": staging_obj.file_size,
            "dataset_type": staging_obj.dataset_type,
            "source_mode": getattr(staging_obj, "source_mode", None),
            "scan_root_id": getattr(staging_obj, "scan_root_id", None),
            "scan_job_id": getattr(staging_obj, "scan_job_id", None),
            "relative_path": getattr(staging_obj, "relative_path", None),
            "file_mtime": getattr(staging_obj, "file_mtime", None),
            "discover_time": getattr(staging_obj, "discover_time", None),
            "last_seen_time": getattr(staging_obj, "last_seen_time", None),
            "status": staging_obj.status,
            "linked_dataset_id": staging_obj.linked_dataset_id,
            "create_user_id": staging_obj.create_user_id,
            "meta_json": staging_obj.meta_json,
            "create_time": staging_obj.create_time,
            "update_time": staging_obj.update_time,
        }

    def _build_scan_root_payload(self, root_obj):
        last_scan_time = getattr(root_obj, "last_scan_time", None)
        return {
            "id": root_obj.id,
            "root_code": root_obj.root_code,
            "name": root_obj.name,
            "root_path": root_obj.root_path,
            "description": root_obj.description,
            "scan_recursive": bool(getattr(root_obj, "scan_recursive", 1)),
            "include_hidden": bool(getattr(root_obj, "include_hidden", 0)),
            "is_active": bool(getattr(root_obj, "is_active", 1)),
            "last_scan_time": last_scan_time,
            "create_user_id": getattr(root_obj, "create_user_id", None),
            "create_time": getattr(root_obj, "create_time", None),
            "update_time": getattr(root_obj, "update_time", None),
        }

    def _build_scan_job_payload(self, job_obj):
        return {
            "id": job_obj.id,
            "root_id": job_obj.root_id,
            "job_code": job_obj.job_code,
            "status": job_obj.status,
            "scanned_dir_count": getattr(job_obj, "scanned_dir_count", 0),
            "scanned_file_count": getattr(job_obj, "scanned_file_count", 0),
            "staged_file_count": getattr(job_obj, "staged_file_count", 0),
            "skipped_file_count": getattr(job_obj, "skipped_file_count", 0),
            "changed_file_count": getattr(job_obj, "changed_file_count", 0),
            "missing_file_count": getattr(job_obj, "missing_file_count", 0),
            "skipped_registered_count": getattr(job_obj, "skipped_registered_count", 0),
            "error_message": getattr(job_obj, "error_message", None),
            "start_time": getattr(job_obj, "start_time", None),
            "finish_time": getattr(job_obj, "finish_time", None),
            "create_user_id": getattr(job_obj, "create_user_id", None),
            "create_time": getattr(job_obj, "create_time", None),
            "update_time": getattr(job_obj, "update_time", None),
        }

    def _staging_file_format(self, staging_obj):
        file_format = str(getattr(staging_obj, "file_format", "") or "").strip().lower()
        if file_format:
            return file_format
        return str(self._guess_file_suffix(getattr(staging_obj, "local_path", None)) or "").strip().lower()

    def _staging_name_hint(self, staging_obj):
        return str(getattr(staging_obj, "file_name", None) or getattr(staging_obj, "source_name", None) or "").lower()

    def _is_index_format(self, file_format):
        return file_format in {"fai", "gzi", "tbi", "csi"}

    def _is_metadata_format(self, file_format):
        return file_format in {"json", "yaml", "yml", "txt", "md"}

    def _infer_file_role(self, staging_obj):
        file_format = self._staging_file_format(staging_obj)
        if self._is_index_format(file_format):
            return "index"
        if self._is_metadata_format(file_format):
            return "metadata"
        return "primary"

    def _resolve_file_role(self, db, staging_obj, dataset_type):
        _asset_type, asset_file_type_code = self._infer_asset_mapping(staging_obj, dataset_type, db=db)
        if asset_file_type_code:
            registry_row = asset_file_type_registry_db.get_filter(db=db, filters={"code": asset_file_type_code})
            if registry_row and getattr(registry_row, "file_role", None):
                return registry_row.file_role
        return self._infer_file_role(staging_obj=staging_obj)

    def _infer_asset_mapping(self, staging_obj, dataset_type, db=None):
        dataset_type = self._canonical_dataset_type(dataset_type or "generic")
        file_format = self._staging_file_format(staging_obj)
        name_hint = self._staging_name_hint(staging_obj)

        if dataset_type == "genome":
            if file_format in {"fa", "fasta", "fna", "fa.gz", "fasta.gz", "fna.gz"}:
                if any(keyword in name_hint for keyword in {"pep", "protein", ".faa", "protein_sequence"}):
                    return "gene_annotation", "protein_sequence"
                if any(keyword in name_hint for keyword in {"mrna", "cdna", "cds", "transcript"}):
                    return "gene_annotation", "transcript_sequence"
                return "reference_fasta", "genome_sequence"
            if file_format in {"fai", "gzi"}:
                return "reference_fasta", "genome_sequence_index"
            if file_format in {"gff", "gff.gz", "gff3", "gff3.gz", "gtf", "gtf.gz"}:
                return "gene_annotation", "gene_models"
            if file_format == "tbi":
                return "gene_annotation", "gene_models_index"
            if file_format in {"db", "sqlite"}:
                if any(keyword in name_hint for keyword in {"func", "functional", "interpro", "kegg", "go", "genome.db"}):
                    return "functional_annotation", "functional_annotation_db"
                return "gene_annotation", "gene_models"
            if file_format in {"csv", "tsv", "xlsx", "xls", "h5", "hdf5"}:
                return "functional_annotation", "functional_annotation_table"

        if dataset_type == "variome":
            if file_format in {"vcf", "vcf.gz", "bcf"}:
                return "variant_vcf", "variant_calls"
            if file_format in {"tbi", "csi"}:
                return "variant_vcf", "variant_calls_index"

        if dataset_type == "transcriptome":
            if file_format in {"h5", "hdf5"}:
                return "expression_matrix", "expression_matrix_store"
            if file_format in {"csv", "tsv", "xlsx", "xls"}:
                return "expression_matrix", "expression_quant_table"

        if dataset_type == "phenome":
            if file_format in {"db", "sqlite"}:
                return "phenotype_index", "phenotype_query_index_db"
            if file_format in {"csv", "tsv", "xlsx", "xls"}:
                return "phenotype_table", "phenotype_observation_table"

        return self._default_asset_type(dataset_type, db=db), None

    def _asset_name_from_type(self, asset_type):
        return asset_type.replace("_", " ").title()

    def _get_primary_staging(self, db, staging_file_ids):
        staging_objs = [dataset_staging_file_db.get(db=db, id=sid) for sid in staging_file_ids]
        if not staging_objs:
            raise HTTPException(status_code=400, detail="no staging files found")
        return staging_objs[0], staging_objs

    def _find_existing_version_asset(self, db, version_id, asset_type):
        asset_rows = dataset_asset_db.get_data(db=db, filters={"dataset_version_id": version_id})
        for asset_obj in sorted(asset_rows, key=lambda item: (item.display_order or 0, item.id)):
            if str(getattr(asset_obj, "asset_type", "") or "").lower() == str(asset_type or "").lower():
                return asset_obj
        return None

    def _ensure_asset(self, db, *, version_obj, asset_type, file_format, is_query_entry, user):
        existing = self._find_existing_version_asset(db=db, version_id=version_obj.id, asset_type=asset_type)
        if existing:
            return self.get_dataset_asset(db=db, asset_id=existing.id, user=user)
        return self.create_dataset_asset(
            db=db,
            request_data=SimpleNamespace(
                version_id=version_obj.id,
                asset_code=None,
                asset_name=self._asset_name_from_type(asset_type),
                asset_type=asset_type,
                file_format=file_format,
                storage_backend="local",
                workflow_state="ready",
                status="active",
                is_required=True,
                is_query_entry=is_query_entry,
                display_order=0,
                meta_json=None,
                local_path=None,
            ),
            user=user,
        )

    def _build_managed_asset_file_path(self, dataset_payload, version_payload, asset_payload, file_payload):
        role_dir = file_payload["file_role"] or "primary"
        file_name = file_payload["file_name"] or Path(file_payload["local_path"] or file_payload["storage_uri"]).name
        target_dir = os.path.join(
            self._get_dataset_storage_root(),
            dataset_payload["dataset_code"],
            "versions",
            version_payload["version"],
            "assets",
            asset_payload["asset_code"],
            role_dir,
        )
        os.makedirs(target_dir, exist_ok=True)
        return os.path.join(target_dir, file_name)

    def _relocate_dataset_files_to_managed_storage(self, db, dataset_id):
        dataset_payload = self.get_dataset(db=db, dataset_id=dataset_id)
        version_payload = dataset_payload.get("current_version")
        if not version_payload:
            return dataset_payload
        primary_asset = dataset_payload.get("query_entry_asset")
        asset_items = dataset_payload.get("assets") or []
        if primary_asset:
            asset_items = sorted(asset_items, key=lambda item: item["id"] != primary_asset["id"])
        for asset_payload in asset_items:
            for file_payload in asset_payload.get("files", []):
                local_path = file_payload.get("local_path")
                if not local_path or not os.path.exists(local_path):
                    continue
                target_path = self._build_managed_asset_file_path(
                    dataset_payload=dataset_payload,
                    version_payload=version_payload,
                    asset_payload=asset_payload,
                    file_payload=file_payload,
                )
                if os.path.abspath(local_path) == os.path.abspath(target_path):
                    continue
                shutil.move(local_path, target_path)
                file_obj = asset_file_db.get(db=db, id=file_payload["id"])
                self._update_db_obj(
                    db,
                    file_obj,
                    local_path=target_path,
                    storage_uri=self._to_storage_uri(target_path),
                    file_name=Path(target_path).name,
                    file_size=os.path.getsize(target_path),
                    update_time=self._now(),
                )
                if file_payload["file_role"] == "primary":
                    version_obj = dataset_version_db.get(db=db, id=asset_payload["version_id"])
                    self._update_db_obj(db, version_obj, file_path=target_path, update_time=self._now())
                    database_file_obj = dataset_legacy_bridge.get_primary_file(db=db, dataset_id=dataset_id)
                    if database_file_obj:
                        self._update_db_obj(db, database_file_obj, path=target_path)
        return self.get_dataset(db=db, dataset_id=dataset_id)

    def _default_asset_type(self, dataset_type, db=None):
        if db is not None:
            return self._resolve_default_asset_type_code(db=db, dataset_type=dataset_type)
        return self.DATASET_TYPE_TO_ASSET_TYPE.get(self._canonical_dataset_type(dataset_type), "metadata_table")

    def _resolve_default_asset_type_code(self, db, dataset_type):
        """Look up the default asset type for a dataset_type from AssetTypeRegistry.

        Registry entries take precedence over the hardcoded fallback map.
        Highest sort_order wins among matching active entries.
        """
        canonical = self._canonical_dataset_type(dataset_type)
        rows = (
            db.query(AssetTypeRegistry)
            .filter(AssetTypeRegistry.is_active == True)
            .order_by(AssetTypeRegistry.sort_order.desc())
            .all()
        )
        for row in rows:
            allowed = self._canonicalize_dataset_type_list(
                self._parse_json_list(row.allowed_dataset_types)
            )
            if not allowed or canonical in allowed:
                return row.code
        return self.DATASET_TYPE_TO_ASSET_TYPE.get(canonical, "metadata_table")

    def _default_asset_code(self, asset_type):
        return (asset_type or "asset").replace("-", "_").replace(" ", "_").lower()

    def _asset_name_from_version(self, version_obj, asset_type):
        title = getattr(version_obj, "title", None) or getattr(version_obj, "version", None) or "dataset-asset"
        return f"{title}:{asset_type}"

    def _detect_index_file_paths(self, file_path, dataset_type):
        if not file_path:
            return []
        dataset_type = self._canonical_dataset_type(dataset_type)
        if dataset_type == "genome":
            return [
                index_path
                for index_path in [f"{file_path}.fai", f"{file_path}.gzi"]
                if os.path.exists(index_path)
            ]
        if dataset_type == "variome":
            candidates = []
            if file_path.endswith(".vcf.gz"):
                candidates.extend([f"{file_path}.tbi", f"{file_path}.csi"])
            elif file_path.endswith(".bcf"):
                candidates.append(f"{file_path}.csi")
            return [item for item in candidates if os.path.exists(item)]
        if dataset_type == "annotation":
            if file_path.endswith(".gz"):
                return [item for item in [f"{file_path}.tbi", f"{file_path}.csi"] if os.path.exists(item)]
            return []
        if dataset_type == "signal":
            if file_path.endswith(".bed.gz"):
                return [item for item in [f"{file_path}.tbi", f"{file_path}.csi"] if os.path.exists(item)]
            return []
        if dataset_type == "interaction":
            if file_path.endswith(".gz"):
                return [item for item in [f"{file_path}.tbi", f"{file_path}.csi"] if os.path.exists(item)]
            return []
        return []

    def _build_asset_file_payload(self, file_obj):
        return {
            "id": file_obj.id,
            "dataset_asset_id": file_obj.dataset_asset_id,
            "asset_file_type_code": getattr(file_obj, "asset_file_type_code", None),
            "file_role": file_obj.file_role,
            "file_name": file_obj.file_name,
            "storage_uri": file_obj.storage_uri,
            "local_path": file_obj.local_path,
            "file_format": file_obj.file_format,
            "mime_type": file_obj.mime_type,
            "checksum_type": file_obj.checksum_type,
            "checksum_value": file_obj.checksum_value,
            "file_size": file_obj.file_size,
            "compress_type": file_obj.compress_type,
            "index_of_file_id": file_obj.index_of_file_id,
            "status": file_obj.status,
            "meta_json": file_obj.meta_json,
            "is_downloadable": getattr(file_obj, "is_downloadable", False),
            "create_time": file_obj.create_time,
            "update_time": file_obj.update_time,
        }

    def _build_dataset_asset_payload(self, asset_obj, files=None):
        return {
            "id": asset_obj.id,
            "dataset_id": None,
            "version_id": asset_obj.dataset_version_id,
            "asset_code": asset_obj.asset_code,
            "asset_name": asset_obj.asset_name,
            "asset_type": asset_obj.asset_type,
            "file_format": asset_obj.file_format,
            "storage_backend": asset_obj.storage_backend,
            "workflow_state": asset_obj.workflow_state,
            "status": asset_obj.status,
            "is_required": bool(asset_obj.is_required),
            "is_query_entry": bool(asset_obj.is_query_entry),
            "display_order": asset_obj.display_order,
            "meta_json": asset_obj.meta_json,
            "files": files or [],
            "create_time": asset_obj.create_time,
            "update_time": asset_obj.update_time,
        }

    def _build_lineage_payload(self, db, lineage_obj):
        src_version = dataset_version_db.get_one(db=db, id=lineage_obj.src_dataset_version_id) if lineage_obj.src_dataset_version_id else None
        dst_version = dataset_version_db.get_one(db=db, id=lineage_obj.dst_dataset_version_id) if lineage_obj.dst_dataset_version_id else None
        src_asset = dataset_asset_db.get_one(db=db, id=lineage_obj.src_asset_id) if lineage_obj.src_asset_id else None
        dst_asset = dataset_asset_db.get_one(db=db, id=lineage_obj.dst_asset_id) if lineage_obj.dst_asset_id else None
        src_database = dataset_legacy_bridge.get_database(db=db, dataset_id=src_version.dataset_id) if src_version else None
        dst_database = dataset_legacy_bridge.get_database(db=db, dataset_id=dst_version.dataset_id) if dst_version else None
        src_registry = dataset_registry_db.get_filter(db=db, filters={"id": src_version.dataset_id}) if src_version else None
        dst_registry = dataset_registry_db.get_filter(db=db, filters={"id": dst_version.dataset_id}) if dst_version else None
        return {
            "id": lineage_obj.id,
            "dataset_id": src_version.dataset_id if src_version else None,
            "src_dataset_id": src_version.dataset_id if src_version else None,
            "src_dataset_code": src_registry.dataset_code if src_registry else None,
            "src_dataset_title": getattr(src_database, 'title', '') or getattr(src_database, 'name', '') if src_database else None,
            "src_dataset_type": src_registry.dataset_type if src_registry else None,
            "src_version_id": lineage_obj.src_dataset_version_id,
            "src_version": src_version.version if src_version else None,
            "src_asset_id": lineage_obj.src_asset_id,
            "src_asset_code": src_asset.asset_code if src_asset else None,
            "dst_dataset_id": dst_version.dataset_id if dst_version else None,
            "dst_dataset_code": dst_registry.dataset_code if dst_registry else None,
            "dst_dataset_title": getattr(dst_database, 'title', '') or getattr(dst_database, 'name', '') if dst_database else None,
            "dst_dataset_type": dst_registry.dataset_type if dst_registry else None,
            "dst_version_id": lineage_obj.dst_dataset_version_id,
            "dst_version": dst_version.version if dst_version else None,
            "dst_asset_id": lineage_obj.dst_asset_id,
            "dst_asset_code": dst_asset.asset_code if dst_asset else None,
            "relation_type": lineage_obj.relation_type,
            "detail_json": lineage_obj.detail_json,
            "create_user_id": lineage_obj.create_user_id,
            "create_time": lineage_obj.create_time,
        }

    def _list_public_lineage(self, db, version_id=None, dataset_id=None, limit=50):
        if dataset_id is not None:
            public_versions = self._list_public_version_objs(db=db, dataset_id=dataset_id)
            released_version_ids = {v.id for v in public_versions}
            if not released_version_ids:
                return []

            lineage_rows = dataset_lineage_edge_db.get_data(db=db, filters={})
            matched = []
            all_dataset_ids = set()
            for item in lineage_rows:
                if item.src_dataset_version_id not in released_version_ids and item.dst_dataset_version_id not in released_version_ids:
                    continue
                sv = dataset_version_db.get_one(db=db, id=item.src_dataset_version_id) if item.src_dataset_version_id else None
                dv = dataset_version_db.get_one(db=db, id=item.dst_dataset_version_id) if item.dst_dataset_version_id else None
                if not sv or not dv:
                    continue
                if not sv.visibility == "public" or not dv.visibility == "public":
                    continue
                matched.append((item, sv, dv))
                all_dataset_ids.add(sv.dataset_id)
                all_dataset_ids.add(dv.dataset_id)

            if not matched:
                return []

            # Bulk fetch registries — 1 query instead of 2 per edge
            registries = db.query(DatasetRegistry).filter(
                DatasetRegistry.id.in_(all_dataset_ids),
            ).all()
            registry_map = {r.dataset_id: r for r in registries}

            matched.sort(key=lambda x: x[0].id, reverse=True)
            results = []
            for item, sv, dv in matched[:limit]:
                src_reg = registry_map.get(sv.dataset_id)
                dst_reg = registry_map.get(dv.dataset_id)
                if not src_reg or not dst_reg:
                    continue
                results.append({
                    "id": item.id,
                    "relation_type": item.relation_type,
                    "src_dataset_id": sv.dataset_id,
                    "src_dataset_title": src_reg.title or "",
                    "src_dataset_type": src_reg.dataset_type or "",
                    "src_dataset_code": src_reg.dataset_code or "",
                    "src_version": sv.version or "",
                    "dst_dataset_id": dv.dataset_id,
                    "dst_dataset_title": dst_reg.title or "",
                    "dst_dataset_type": dst_reg.dataset_type or "",
                    "dst_dataset_code": dst_reg.dataset_code or "",
                    "dst_version": dv.version or "",
                })
            return results

        # version_id branch
        version_obj = dataset_version_db.get(db=db, id=version_id)
        if not version_obj or not version_obj.visibility == "public":
            return []
        lineage_rows = dataset_lineage_edge_db.get_data(db=db, filters={})
        matched = []
        all_dataset_ids = set()
        for item in lineage_rows:
            if item.src_dataset_version_id != version_id and item.dst_dataset_version_id != version_id:
                continue
            sv = dataset_version_db.get_one(db=db, id=item.src_dataset_version_id) if item.src_dataset_version_id else None
            dv = dataset_version_db.get_one(db=db, id=item.dst_dataset_version_id) if item.dst_dataset_version_id else None
            if not sv or not dv:
                continue
            if not sv.visibility == "public" or not dv.visibility == "public":
                continue
            matched.append((item, sv, dv))
            all_dataset_ids.add(sv.dataset_id)
            all_dataset_ids.add(dv.dataset_id)

        if not matched:
            return []

        registries = db.query(DatasetRegistry).filter(
            DatasetRegistry.id.in_(all_dataset_ids),
        ).all()
        registry_map = {r.dataset_id: r for r in registries}

        matched.sort(key=lambda x: x[0].id, reverse=True)
        results = []
        for item, sv, dv in matched[:limit]:
            src_reg = registry_map.get(sv.dataset_id)
            dst_reg = registry_map.get(dv.dataset_id)
            if not src_reg or not dst_reg:
                continue
            results.append({
                "id": item.id,
                "relation_type": item.relation_type,
                "src_dataset_id": sv.dataset_id,
                "src_dataset_title": src_reg.title or "",
                "src_dataset_type": src_reg.dataset_type or "",
                "src_dataset_code": src_reg.dataset_code or "",
                "src_version": sv.version or "",
                "dst_dataset_id": dv.dataset_id,
                "dst_dataset_title": dst_reg.title or "",
                "dst_dataset_type": dst_reg.dataset_type or "",
                "dst_dataset_code": dst_reg.dataset_code or "",
                "dst_version": dv.version or "",
            })
        return results

    def _list_asset_file_rows(self, db, asset_id):
        rows = asset_file_db.get_data(db=db, filters={"dataset_asset_id": asset_id})
        return sorted(rows, key=lambda item: (item.file_role != "primary", item.id))

    def _serialize_asset_rows(self, db, asset_rows):
        asset_rows = sorted(asset_rows, key=lambda item: (-int(bool(item.is_query_entry)), item.display_order or 0, item.id))
        payload = []
        for asset_obj in asset_rows:
            file_rows = self._list_asset_file_rows(db=db, asset_id=asset_obj.id)
            payload.append(
                self._build_dataset_asset_payload(
                    asset_obj,
                    files=[self._build_asset_file_payload(item) for item in file_rows],
                )
            )
        return payload

    def _build_asset_list_payload(self, db, version_id):
        version_obj = dataset_version_db.get(db=db, id=version_id)
        return self._ensure_assets_for_version(db=db, version_obj=version_obj)

    def _normalize_query_entry_assets(self, db, version_id, selected_asset_id=None):
        asset_rows = dataset_asset_db.get_data(db=db, filters={"dataset_version_id": version_id})
        if not asset_rows:
            return
        if selected_asset_id is None:
            current = next((item for item in asset_rows if item.is_query_entry), None)
            selected_asset_id = current.id if current else asset_rows[0].id
        for asset_obj in asset_rows:
            should_be_entry = asset_obj.id == selected_asset_id
            if bool(asset_obj.is_query_entry) != should_be_entry:
                self._update_db_obj(
                    db,
                    asset_obj,
                    is_query_entry=True if should_be_entry else 0,
                    update_time=self._now(),
                )

    def _ensure_asset_file_record(
        self,
        db,
        asset_obj,
        file_role,
        local_path,
        file_format=None,
        asset_file_type_code=None,
        index_of_file_id=None,
        status="active",
        meta_json=None,
    ):
        if not local_path:
            return None
        normalized_file_role = self._normalize_file_role(file_role)
        registry_row, resolved_file_format = self._validate_asset_file_registry_binding(
            db=db,
            asset_type=asset_obj.asset_type,
            file_role=normalized_file_role,
            file_format=file_format,
            local_path=local_path,
            asset_file_type_code=asset_file_type_code,
        )
        resolved_asset_file_type_code = registry_row.code if registry_row else None
        existing_rows = self._list_asset_file_rows(db=db, asset_id=asset_obj.id)
        target = None
        for row in existing_rows:
            if row.file_role != normalized_file_role:
                continue
            if row.local_path != local_path:
                continue
            if normalized_file_role == "index" and index_of_file_id and row.index_of_file_id != index_of_file_id:
                continue
            target = row
            break
        file_name = Path(local_path).name
        payload = {
            "dataset_id": None,
            "dataset_asset_id": asset_obj.id,
            "asset_file_type_code": resolved_asset_file_type_code,
            "file_role": normalized_file_role,
            "file_name": file_name,
            "storage_uri": self._to_storage_uri(local_path),
            "local_path": local_path,
            "file_format": resolved_file_format,
            "file_size": os.path.getsize(local_path) if os.path.exists(local_path) else None,
            "index_of_file_id": index_of_file_id,
            "status": status,
            "meta_json": meta_json,
            "update_time": self._now(),
        }
        if target:
            return self._update_db_obj(db, target, **payload)
        payload["create_time"] = self._now()
        return asset_file_db.create_one(db=db, obj_in=payload)

    def _ensure_assets_for_version(self, db, version_obj):
        if not version_obj:
            return []
        registry = dataset_registry_db.get(db=db, id=version_obj.dataset_id)
        dataset_type = registry.dataset_type if registry else "generic"
        asset_rows = dataset_asset_db.get_data(db=db, filters={"dataset_version_id": version_obj.id})
        asset_rows = sorted(asset_rows, key=lambda item: (-int(bool(item.is_query_entry)), item.display_order or 0, item.id))
        if not asset_rows and not None:
            return []

        if None:
            # Legacy compatibility: bootstrap the asset/file rows from version.file_path
            # so query paths can continue reading from asset-first payloads.
            default_asset_type = self._default_asset_type(dataset_type, db=db)
            default_asset_code = self._default_asset_code(default_asset_type)
            default_asset = next((item for item in asset_rows if item.asset_code == default_asset_code), None)
            if not default_asset:
                default_asset = next((item for item in asset_rows if item.is_query_entry), None)
            if not default_asset and asset_rows:
                default_asset = asset_rows[0]
            if not default_asset:
                default_asset = dataset_asset_db.create_one(
                    db=db,
                    obj_in={
                        "dataset_version_id": version_obj.id,
                        "asset_code": default_asset_code,
                        "asset_name": self._asset_name_from_version(version_obj, default_asset_type),
                        "asset_type": default_asset_type,
                        "file_format": None,
                        "storage_backend": "local",
                        "workflow_state": version_obj.lifecycle_state or "draft",
                        "status": "active",
                        "is_required": True,
                        "is_query_entry": True,
                        "display_order": 0,
                        "meta_json": None,
                        "create_time": self._now(),
                        "update_time": self._now(),
                    },
                )
            else:
                default_asset = self._update_db_obj(
                    db,
                    default_asset,
                    asset_name=default_asset.asset_name or self._asset_name_from_version(version_obj, default_asset_type),
                    asset_type=default_asset.asset_type or default_asset_type,
                    file_format=None or default_asset.file_format,
                    workflow_state=version_obj.lifecycle_state or default_asset.workflow_state,
                    status=default_asset.status or "active",
                    update_time=self._now(),
                )
            existing_file_rows = self._list_asset_file_rows(db=db, asset_id=default_asset.id)
            has_primary_file = any(row.file_role == "primary" for row in existing_file_rows)
            if not has_primary_file:
                primary_file = self._ensure_asset_file_record(
                    db=db,
                    asset_obj=default_asset,
                    file_role="primary",
                    local_path=None,
                    file_format=None,
                    status="active",
                )
                for index_path in self._detect_index_file_paths(None, dataset_type):
                    self._ensure_asset_file_record(
                        db=db,
                        asset_obj=default_asset,
                        file_role="index",
                        local_path=index_path,
                        file_format=self._guess_file_suffix(index_path),
                        index_of_file_id=primary_file.id if primary_file else None,
                        status="active",
                    )
        self._normalize_query_entry_assets(db=db, version_id=version_obj.id)
        asset_rows = dataset_asset_db.get_data(db=db, filters={"dataset_version_id": version_obj.id})
        return self._serialize_asset_rows(db=db, asset_rows=asset_rows)

    def _resolve_dataset_type_from_path(self, file_path, dataset_type=None):
        if dataset_type:
            return dataset_type
        suffix = self._guess_file_suffix(file_path)
        base_type = self.FILE_FORMAT_TO_DATASET_TYPE.get(suffix, "generic")
        if base_type == "generic" and suffix in {"sqlite", "db"}:
            path_lower = Path(file_path).parent.name.lower()
            for keyword, dtype in [
                ("phenotype", "phenome"),
                ("phenome", "phenome"),
                ("trait", "phenome"),
                ("genome", "genome"),
                ("annotation", "annotation"),
                ("function", "annotation"),
                ("go_", "annotation"),
                ("kegg", "annotation"),
                ("expression", "transcriptome"),
                ("rnaseq", "transcriptome"),
            ]:
                if keyword in path_lower:
                    return dtype
        return base_type

    def _validate_local_file_exists(self, file_path):
        if not file_path:
            raise HTTPException(status_code=400, detail="file_path is required")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"file not found on server: {file_path}")
        if not os.access(file_path, os.R_OK):
            raise HTTPException(status_code=403, detail=f"file is not readable: {file_path}")

    def _require_binary(self, binary_name):
        if shutil.which(binary_name):
            return
        raise HTTPException(
            status_code=503,
            detail=f"required system binary is not available: {binary_name}",
        )

    def _validate_sequence_file(self, file_path):
        self._validate_local_file_exists(file_path)
        with open(file_path, "r", encoding="utf-8") as handle:
            first_line = handle.readline().strip()
        if not first_line.startswith(">"):
            raise HTTPException(status_code=400, detail=f"invalid FASTA file: {file_path}")
        return {"format": "fasta", "index_exists": os.path.exists(f"{file_path}.fai")}

    def _validate_variant_file(self, file_path):
        self._validate_local_file_exists(file_path)
        suffix = self._guess_file_suffix(file_path)
        if suffix not in {"vcf", "vcf.gz", "bcf"}:
            raise HTTPException(status_code=400, detail=f"unsupported variant file format: {file_path}")
        index_path = f"{file_path}.tbi" if suffix == "vcf.gz" else (f"{file_path}.csi" if suffix == "bcf" else None)
        return {"format": suffix, "index_exists": os.path.exists(index_path) if index_path else False}

    def _validate_expression_file(self, file_path):
        self._validate_local_file_exists(file_path)
        suffix = self._guess_file_suffix(file_path)
        if suffix in {"h5", "hdf5"}:
            validated_path = process_rnaseq_file(file_path, file_path)
            return {"format": suffix, "validated_path": validated_path, "converted": False}
        if suffix not in {"csv", "tsv", "txt", "gz"}:
            raise HTTPException(status_code=400, detail=f"unsupported expression file format: {file_path}")
        return {"format": suffix, "validated_path": file_path, "converted": False}

    def _validate_annotation_file(self, file_path):
        self._validate_local_file_exists(file_path)
        suffix = self._guess_file_suffix(file_path)
        if suffix in {"sqlite", "db"}:
            return {"format": suffix, "validated_path": file_path, "indexed": True}
        if suffix not in {"gff", "gff.gz", "gff3", "gff3.gz", "gtf", "gtf.gz"}:
            raise HTTPException(status_code=400, detail=f"unsupported annotation file format: {file_path}")
        opener = gzip.open if suffix.endswith(".gz") else open
        with opener(file_path, "rt", encoding="utf-8") as handle:
            first_data_line = ""
            for line in handle:
                if line.startswith("#") or not line.strip():
                    continue
                first_data_line = line.strip()
                break
        if not first_data_line:
            raise HTTPException(status_code=400, detail=f"annotation file contains no feature rows: {file_path}")
        if len(first_data_line.split("\t")) < 9:
            raise HTTPException(status_code=400, detail=f"invalid GFF/GTF file: {file_path}")
        index_exists = os.path.exists(f"{file_path}.tbi") or os.path.exists(f"{file_path}.csi")
        return {"format": suffix, "validated_path": file_path, "indexed": index_exists}

    def _validate_signal_file(self, file_path):
        self._validate_local_file_exists(file_path)
        suffix = self._guess_file_suffix(file_path)
        if suffix in {"bw", "bigwig"}:
            return {"format": suffix, "validated_path": file_path, "indexed": True}
        if suffix not in {"bed", "bed.gz"}:
            raise HTTPException(status_code=400, detail=f"unsupported signal file format: {file_path}")
        opener = gzip.open if suffix.endswith(".gz") else open
        with opener(file_path, "rt", encoding="utf-8") as handle:
            first_data_line = ""
            for line in handle:
                if line.startswith("#") or not line.strip():
                    continue
                first_data_line = line.strip()
                break
        if not first_data_line:
            raise HTTPException(status_code=400, detail=f"signal file contains no feature rows: {file_path}")
        if len(first_data_line.split("\t")) < 3:
            raise HTTPException(status_code=400, detail=f"invalid BED file: {file_path}")
        index_exists = os.path.exists(f"{file_path}.tbi") or os.path.exists(f"{file_path}.csi")
        return {"format": suffix, "validated_path": file_path, "indexed": index_exists}

    def _validate_interaction_file(self, file_path):
        self._validate_local_file_exists(file_path)
        suffix = self._guess_file_suffix(file_path)
        if suffix in {"cool", "mcool"}:
            matrix_meta = inspect_interaction_matrix(file_path)
            result = {
                "format": suffix,
                "validated_path": file_path,
                "indexed": True,
                "bin_size": matrix_meta["bin_size"],
                "balanced_supported": matrix_meta["balanced_supported"],
                "shape": matrix_meta["shape"],
            }
            if suffix == "mcool":
                resolutions = list_interaction_resolutions(file_path)
                result["available_resolutions"] = resolutions["resolutions"]
                result["default_resolution"] = resolutions["default_resolution"]
            else:
                result["resolution"] = matrix_meta["resolution"]
            return result
        if suffix not in {"bedpe", "bedpe.gz", "pairs", "pairs.gz"}:
            raise HTTPException(status_code=400, detail=f"unsupported interaction file format: {file_path}")
        opener = gzip.open if suffix.endswith(".gz") else open
        with opener(file_path, "rt", encoding="utf-8") as handle:
            first_data_line = ""
            for line in handle:
                if line.startswith("#") or not line.strip():
                    continue
                first_data_line = line.strip()
                break
        if not first_data_line:
            raise HTTPException(status_code=400, detail=f"interaction file contains no records: {file_path}")
        if len(first_data_line.split("\t")) < 6:
            raise HTTPException(status_code=400, detail=f"invalid BEDPE/pairs file: {file_path}")
        index_exists = os.path.exists(f"{file_path}.tbi") or os.path.exists(f"{file_path}.csi")
        return {"format": suffix, "validated_path": file_path, "indexed": index_exists}

    def _validate_generic_file(self, file_path):
        self._validate_local_file_exists(file_path)
        return {"format": self._guess_file_suffix(file_path) or "generic", "validated_path": file_path}

    def _validate_phenome_file(self, file_path):
        self._validate_local_file_exists(file_path)
        suffix = self._guess_file_suffix(file_path)
        if suffix in {"db", "sqlite"}:
            return {"format": suffix, "validated_path": file_path, "indexed": True}
        if suffix not in {"xlsx", "xls", "csv", "tsv"}:
            raise HTTPException(status_code=400, detail=f"unsupported phenome file format: {file_path}")
        return {"format": suffix, "validated_path": file_path, "indexed": False}

    def _validate_by_dataset_type(self, file_path, dataset_type):
        dataset_type = self._canonical_dataset_type(dataset_type)
        if dataset_type == "genome":
            return self._validate_sequence_file(file_path)
        if dataset_type == "variome":
            return self._validate_variant_file(file_path)
        if dataset_type == "transcriptome":
            return self._validate_expression_file(file_path)
        if dataset_type == "annotation":
            return self._validate_annotation_file(file_path)
        if dataset_type == "signal":
            return self._validate_signal_file(file_path)
        if dataset_type == "phenome":
            return self._validate_phenome_file(file_path)
        if dataset_type == "interaction":
            return self._validate_interaction_file(file_path)
        return self._validate_generic_file(file_path)

    def _index_annotation_file(self, file_path):
        suffix = self._guess_file_suffix(file_path)
        if suffix in {"sqlite", "db"}:
            return {
                "indexed_path": file_path,
                "index_files": [],
                "operation": "sqlite-ready",
            }
        if suffix not in {"gff", "gff.gz", "gff3", "gff3.gz", "gtf", "gtf.gz"}:
            raise HTTPException(status_code=400, detail=f"unsupported annotation file format: {file_path}")
        self._require_binary("tabix")
        indexed_path = file_path
        if not suffix.endswith(".gz"):
            self._require_binary("bgzip")
            indexed_path = f"{file_path}.gz"
            with open(indexed_path, "wb") as handle:
                subprocess.run(["bgzip", "-c", file_path], stdout=handle, check=True)
        if not os.path.exists(f"{indexed_path}.tbi") and not os.path.exists(f"{indexed_path}.csi"):
            subprocess.run(["tabix", "-p", "gff", indexed_path], check=True)
        index_files = [item for item in [f"{indexed_path}.tbi", f"{indexed_path}.csi"] if os.path.exists(item)]
        return {
            "indexed_path": indexed_path,
            "index_files": index_files,
            "operation": "tabix-gff",
        }

    def _index_signal_file(self, file_path):
        suffix = self._guess_file_suffix(file_path)
        if suffix in {"bw", "bigwig"}:
            return {
                "indexed_path": file_path,
                "index_files": [],
                "operation": "bigwig-ready",
            }
        if suffix not in {"bed", "bed.gz"}:
            raise HTTPException(status_code=400, detail=f"unsupported signal file format: {file_path}")
        self._require_binary("tabix")
        indexed_path = file_path
        if suffix != "bed.gz":
            self._require_binary("bgzip")
            indexed_path = f"{file_path}.gz"
            with open(indexed_path, "wb") as handle:
                subprocess.run(["bgzip", "-c", file_path], stdout=handle, check=True)
        if not os.path.exists(f"{indexed_path}.tbi") and not os.path.exists(f"{indexed_path}.csi"):
            subprocess.run(["tabix", "-p", "bed", indexed_path], check=True)
        index_files = [item for item in [f"{indexed_path}.tbi", f"{indexed_path}.csi"] if os.path.exists(item)]
        return {
            "indexed_path": indexed_path,
            "index_files": index_files,
            "operation": "tabix-bed",
        }

    def _index_interaction_file(self, file_path):
        suffix = self._guess_file_suffix(file_path)
        if suffix in {"cool", "mcool"}:
            matrix_meta = inspect_interaction_matrix(file_path)
            result = {
                "indexed_path": file_path,
                "index_files": [],
                "operation": "cooler-ready",
                "bin_size": matrix_meta["bin_size"],
                "balanced_supported": matrix_meta["balanced_supported"],
            }
            if suffix == "mcool":
                resolutions = list_interaction_resolutions(file_path)
                result["available_resolutions"] = resolutions["resolutions"]
                result["default_resolution"] = resolutions["default_resolution"]
            else:
                result["resolution"] = matrix_meta["resolution"]
            return result
        if suffix not in {"bedpe", "bedpe.gz", "pairs", "pairs.gz"}:
            raise HTTPException(status_code=400, detail=f"unsupported interaction file format: {file_path}")
        self._require_binary("tabix")
        indexed_path = file_path
        if not suffix.endswith(".gz"):
            self._require_binary("bgzip")
            indexed_path = f"{file_path}.gz"
            with open(indexed_path, "wb") as handle:
                subprocess.run(["bgzip", "-c", file_path], stdout=handle, check=True)
        if not os.path.exists(f"{indexed_path}.tbi") and not os.path.exists(f"{indexed_path}.csi"):
            subprocess.run(["tabix", "-s", "1", "-b", "2", "-e", "3", indexed_path], check=True)
        index_files = [item for item in [f"{indexed_path}.tbi", f"{indexed_path}.csi"] if os.path.exists(item)]
        return {
            "indexed_path": indexed_path,
            "index_files": index_files,
            "operation": "tabix-bedpe",
        }

    def _index_by_dataset_type(self, file_path, dataset_type, output_file_path=None):
        dataset_type = self._canonical_dataset_type(dataset_type)
        if dataset_type == "genome":
            self._require_binary("samtools")
            indexed_path = process_sequence(file_path)
            return {
                "indexed_path": indexed_path,
                "index_files": [f"{indexed_path}.fai"] if os.path.exists(f"{indexed_path}.fai") else [],
                "operation": "faidx",
            }
        if dataset_type == "variome":
            self._require_binary("bcftools")
            indexed_path = process_variant_file(file_path)
            index_files = []
            if indexed_path.endswith(".bcf") and os.path.exists(f"{indexed_path}.csi"):
                index_files.append(f"{indexed_path}.csi")
            if indexed_path.endswith(".vcf.gz") and os.path.exists(f"{indexed_path}.tbi"):
                index_files.append(f"{indexed_path}.tbi")
            return {
                "indexed_path": indexed_path,
                "index_files": index_files,
                "operation": "bcftools-index",
            }
        if dataset_type == "transcriptome":
            target_h5 = output_file_path or (file_path if self._guess_file_suffix(file_path) in {"h5", "hdf5"} else f"{file_path}.h5")
            indexed_path = process_rnaseq_file(file_path, target_h5)
            return {
                "indexed_path": indexed_path,
                "index_files": [],
                "operation": "hdf5-convert",
            }
        if dataset_type == "annotation":
            return self._index_annotation_file(file_path)
        if dataset_type == "signal":
            return self._index_signal_file(file_path)
        if dataset_type == "phenome":
            return {
                "indexed_path": file_path,
                "index_files": [],
                "operation": "phenome-ready",
            }
        if dataset_type == "interaction":
            return self._index_interaction_file(file_path)
        return {
            "indexed_path": file_path,
            "index_files": [],
            "operation": "noop",
        }

    def _resolve_ingest_target(self, db, request_data, user=None):
        if request_data.id:
            dataset_payload = self.get_dataset(db=db, dataset_id=request_data.id, user=user)
            file_path = self._resolve_dataset_primary_file_path(dataset_payload)
            dataset_type = request_data.dataset_type or dataset_payload.get("dataset_type")
            return {
                "dataset_id": request_data.id,
                "dataset_payload": dataset_payload,
                "file_path": file_path,
                "dataset_type": dataset_type,
                "persist": request_data.persist_result,
            }
        if request_data.file_path:
            dataset_type = self._resolve_dataset_type_from_path(request_data.file_path, request_data.dataset_type)
            return {
                "dataset_id": None,
                "dataset_payload": None,
                "file_path": request_data.file_path,
                "dataset_type": dataset_type,
                "persist": False,
            }
        raise HTTPException(status_code=400, detail="either dataset id or file_path is required")

    def _write_workflow_result(self, db, dataset_id, operator_id, task_type, from_lifecycle_state, to_lifecycle_state, status, detail):
        if not dataset_id:
            return
        registry_obj = dataset_registry_db.get_filter(db=db, filters={"id": dataset_id})
        if registry_obj:
            dataset_registry_db.update_one(
                db=db,
                db_obj=registry_obj,
                obj_in={
                    "lifecycle_state": to_lifecycle_state,
                    "update_time": self._now(),
                },
            )
        dataset_workflow_task_db.create_one(
            db=db,
            obj_in={
                "dataset_id": dataset_id,
                "task_type": task_type,
                "status": status,
                "from_lifecycle_state": from_lifecycle_state,
                "to_lifecycle_state": to_lifecycle_state,
                "operator_id": operator_id,
                "detail": detail,
                "create_time": self._now(),
                "finish_time": self._now() if status != "running" else None,
            },
        )

    def _parse_task_detail(self, detail):
        if not detail:
            return None
        if isinstance(detail, dict):
            return detail
        try:
            parsed = json.loads(detail)
        except (TypeError, json.JSONDecodeError):
            return None
        return parsed if isinstance(parsed, dict) else None

    def _encode_task_detail(self, detail):
        if detail is None:
            return None
        if isinstance(detail, str):
            parsed = self._parse_task_detail(detail)
            return json.dumps(parsed, ensure_ascii=False) if parsed is not None else detail
        return json.dumps(detail, ensure_ascii=False)

    def _build_workflow_task_payload(self, task_obj):
        detail_json = self._parse_task_detail(task_obj.detail)
        return {
            "id": task_obj.id,
            "dataset_id": task_obj.dataset_id,
            "task_type": task_obj.task_type,
            "status": task_obj.status,
            "from_lifecycle_state": task_obj.from_lifecycle_state,
            "to_lifecycle_state": task_obj.to_lifecycle_state,
            "operator_id": task_obj.operator_id,
            "detail": task_obj.detail,
            "detail_json": detail_json,
            "is_async": bool(detail_json and detail_json.get("async_task")),
            "create_time": task_obj.create_time,
            "finish_time": task_obj.finish_time,
        }

    def _update_task_detail(self, detail_json, **kwargs):
        detail_json = dict(detail_json or {})
        for key, value in kwargs.items():
            if value is not None:
                detail_json[key] = value
        return detail_json

    def _update_dataset_lifecycle_state(self, db, dataset_id, state):
        if not dataset_id or not state:
            return
        registry_obj = dataset_registry_db.get_filter(db=db, filters={"id": dataset_id})
        if not registry_obj:
            return
        dataset_registry_db.update_one(
            db=db,
            db_obj=registry_obj,
            obj_in={
                "lifecycle_state": state,
                "update_time": self._now(),
            },
        )

    def _build_ingest_task_detail(self, action, request_payload, retry_of_task_id=None, attempt=1):
        return {
            "async_task": True,
            "action": action,
            "request": request_payload,
            "retry_of_task_id": retry_of_task_id,
            "attempt": attempt,
            "submitted_at": self._now(),
        }

    def _normalize_async_ingest_request_payload(self, action, request_payload):
        normalized = dict(request_payload or {})
        normalized.pop("action", None)
        if action != "pipeline":
            normalized.pop("run_validate", None)
            normalized.pop("run_index", None)
        return normalized

    def _get_async_task_running_state(self, action, request_payload):
        if action == "validate":
            return "validating"
        if action == "index":
            return "indexing"
        if action == "pipeline":
            if request_payload.get("run_validate", True):
                return "validating"
            if request_payload.get("run_index", True):
                return "indexing"
        return None

    def _create_ingest_workflow_task(self, db, action, request_payload, operator_id, retry_of_task_id=None, attempt=1):
        dataset_id = request_payload.get("id")
        from_state = None
        if dataset_id:
            dataset_payload = self.get_dataset(db=db, dataset_id=dataset_id)
            from_state = dataset_payload.get("lifecycle_state")
        task_obj = dataset_workflow_task_db.create_one(
            db=db,
            obj_in={
                "dataset_id": dataset_id,
                "task_type": action,
                "status": "pending",
                "from_lifecycle_state": from_state,
                "to_lifecycle_state": from_state,
                "operator_id": operator_id,
                "detail": self._encode_task_detail(
                    self._build_ingest_task_detail(
                        action=action,
                        request_payload=request_payload,
                        retry_of_task_id=retry_of_task_id,
                        attempt=attempt,
                    )
                ),
                "create_time": self._now(),
                "finish_time": None,
            },
        )
        return self._build_workflow_task_payload(task_obj)

    def register_dataset_source(self, db, request_data, user):
        operator_id = user.id
        file_path = request_data.file_path
        self._validate_local_file_exists(file_path)
        self._ensure_assignable_scope(
            db=db,
            user=user,
            team_id=getattr(request_data, "team_id", 0) or 0,
            project_id=getattr(request_data, "project_id", 0) or 0,
        )
        dataset_type = self._resolve_dataset_type_from_path(file_path, request_data.dataset_type)
        dataset_type, _dataset_kind = self._require_dataset_kind_code(db=db, dataset_type=dataset_type)
        dataset_name = request_data.name or self._guess_name_from_path(file_path)
        file_suffix = self._guess_file_suffix(file_path)
        preview = {
            "dry_run": bool(request_data.dry_run),
            "dataset_name": dataset_name,
            "dataset_type": dataset_type,
            "team_id": getattr(request_data, "team_id", 0) or 0,
            "project_id": getattr(request_data, "project_id", 0) or 0,
            "file": {
                "path": file_path,
                "type": f".{file_suffix}" if file_suffix and not file_suffix.startswith(".") else file_suffix,
                "size": os.path.getsize(file_path),
            },
            "lifecycle_state": "uploaded",
            "visibility": "public" if request_data.is_public else "private"  # is_public removed,
        }
        if request_data.dry_run:
            return preview

        create_time = self._now()
        database_obj = dataset_legacy_bridge.create_database(
            db=db,
            obj_in={
                "name": dataset_name,
                "user_id": operator_id,
                "type": dataset_type,
                "status": 1,
                "is_active": True,
                "is_delete": False,
                "create_time": create_time,
                "remark": request_data.remark,
                "team_id": getattr(request_data, "team_id", 0) or 0,
            },
        )
        dataset_legacy_bridge.create_primary_file(
            db=db,
            obj_in={
                "uid": str(uuid.uuid4()),
                "size": os.path.getsize(file_path),
                "name": dataset_name,
                "file_name": Path(file_path).stem,
                "path": file_path,
                "type": f".{file_suffix}" if file_suffix and not file_suffix.startswith(".") else Path(file_path).suffix,
                "data_type": dataset_type,
                "dataset_id": database_obj.id,
                "status": 1,
                "create_time": create_time,
            },
        )
        if request_data.project_id:
            dataset_legacy_bridge.create_project_link(
                db=db,
                obj_in={"dataset_id": database_obj.id, "project_id": request_data.project_id},
            )
        registry_obj = self.ensure_registry(db=db, database_obj=database_obj)
        dataset_workflow_task_db.create_one(
            db=db,
            obj_in={
                "dataset_id": database_obj.id,
                "task_type": "upload",
                "status": "success",
                "from_lifecycle_state": "draft",
                "to_lifecycle_state": to_lifecycle_state,
                "operator_id": operator_id,
                "detail": "dataset registered from existing server file",
                "create_time": create_time,
                "finish_time": create_time,
            },
        )
        return self.get_dataset(db=db, dataset_id=database_obj.id)

    def validate_ingest_target(self, db, request_data, user, write_workflow_task=True):
        operator_id = user.id
        target = self._resolve_ingest_target(db=db, request_data=request_data, user=user)
        file_path = target["file_path"]
        dataset_type = target["dataset_type"]
        validation = self._validate_by_dataset_type(file_path=file_path, dataset_type=dataset_type)
        result = {
            "dataset_id": target["dataset_id"],
            "file_path": file_path,
            "dataset_type": dataset_type,
            "validation": validation,
        }

        if target["dataset_id"] and target["persist"]:
            before_state = target["dataset_payload"]["lifecycle_state"]
            registry_obj = dataset_registry_db.get_filter(db=db, filters={"id": target["dataset_id"]})
            if registry_obj:
                dataset_registry_db.update_one(
                    db=db,
                    db_obj=registry_obj,
                    obj_in={
                        "validation_summary": json.dumps(validation, ensure_ascii=False),
                        "lifecycle_state": "validated",
                        "update_time": self._now(),
                    },
                )
            if write_workflow_task:
                self._write_workflow_result(
                    db=db,
                    dataset_id=target["dataset_id"],
                    operator_id=operator_id,
                    task_type="validate",
                    from_lifecycle_state=before_state,
                    to_lifecycle_state="validated",
                    status="success",
                    detail=request_data.detail or "dataset validation completed",
                )
            self.sync_current_version_from_dataset_id(db=db, dataset_id=target["dataset_id"])
            result["dataset"] = self.get_dataset(db=db, dataset_id=target["dataset_id"])

        return result

    def index_ingest_target(self, db, request_data, user, write_workflow_task=True):
        operator_id = user.id
        target = self._resolve_ingest_target(db=db, request_data=request_data, user=user)
        file_path = target["file_path"]
        dataset_type = target["dataset_type"]
        index_result = self._index_by_dataset_type(
            file_path=file_path,
            dataset_type=dataset_type,
            output_file_path=request_data.output_file_path,
        )
        result = {
            "dataset_id": target["dataset_id"],
            "file_path": file_path,
            "dataset_type": dataset_type,
            "index": index_result,
        }

        if target["dataset_id"] and target["persist"]:
            before_state = self.get_dataset(db=db, dataset_id=target["dataset_id"])["lifecycle_state"]
            if index_result["indexed_path"] != file_path:
                file_obj = dataset_legacy_bridge.get_primary_file(db=db, dataset_id=target["dataset_id"])
                if file_obj:
                    new_suffix = self._guess_file_suffix(index_result["indexed_path"])
                    dataset_legacy_bridge.update_primary_file(
                        db=db,
                        db_obj=file_obj,
                        obj_in={
                            "path": index_result["indexed_path"],
                            "type": f".{new_suffix}" if new_suffix else file_obj.type,
                        },
                    )
            registry_obj = dataset_registry_db.get_filter(db=db, filters={"id": target["dataset_id"]})
            if registry_obj:
                dataset_registry_db.update_one(
                    db=db,
                    db_obj=registry_obj,
                    obj_in={
                        "index_summary": json.dumps(index_result, ensure_ascii=False),
                        "lifecycle_state": "ready",
                        "update_time": self._now(),
                    },
                )
            if write_workflow_task:
                self._write_workflow_result(
                    db=db,
                    dataset_id=target["dataset_id"],
                    operator_id=operator_id,
                    task_type="index",
                    from_lifecycle_state=before_state,
                    to_lifecycle_state="ready",
                    status="success",
                    detail=request_data.detail or index_result["operation"],
                )
            self.sync_current_version_from_dataset_id(db=db, dataset_id=target["dataset_id"])
            result["dataset"] = self.get_dataset(db=db, dataset_id=target["dataset_id"])

        return result

    def run_ingest_pipeline(self, db, request_data, user, write_workflow_task=True):
        output = {
            "dataset_id": request_data.id,
            "file_path": request_data.file_path,
            "steps": [],
        }
        if request_data.run_validate:
            validate_result = self.validate_ingest_target(
                db=db,
                request_data=request_data,
                user=user,
                write_workflow_task=write_workflow_task,
            )
            output["steps"].append({"step": "validate", "result": validate_result})
            if validate_result.get("dataset_id"):
                output["dataset_id"] = validate_result["dataset_id"]
        if request_data.run_index:
            index_result = self.index_ingest_target(
                db=db,
                request_data=request_data,
                user=user,
                write_workflow_task=write_workflow_task,
            )
            output["steps"].append({"step": "index", "result": index_result})
            if index_result.get("dataset_id"):
                output["dataset_id"] = index_result["dataset_id"]
        return output

    def submit_ingest_task(self, db, request_data, user):
        action = str(request_data.action or "").strip().lower()
        if action not in {"validate", "index", "pipeline"}:
            raise HTTPException(status_code=400, detail="unsupported ingest action")
        request_payload = self._normalize_async_ingest_request_payload(
            action=action,
            request_payload=request_data.dict(exclude_none=True),
        )
        if request_payload.get("id"):
            self._ensure_dataset_write_access(db=db, dataset_id=request_payload["id"], user=user)
        return self._create_ingest_workflow_task(
            db=db,
            action=action,
            request_payload=request_payload,
            operator_id=user.id,
        )

    def get_task_info(self, db, task_id, user=None):
        task_obj = dataset_workflow_task_db.get(db=db, id=task_id)
        self._ensure_task_access(db=db, task_obj=task_obj, user=user, write=False)
        return self._build_workflow_task_payload(task_obj)

    def retry_ingest_task(self, db, task_id, user):
        task_obj = dataset_workflow_task_db.get(db=db, id=task_id)
        self._ensure_task_access(db=db, task_obj=task_obj, user=user, write=True)
        detail_json = self._parse_task_detail(task_obj.detail) or {}
        action = detail_json.get("action") or task_obj.task_type
        request_payload = self._normalize_async_ingest_request_payload(
            action=action,
            request_payload=detail_json.get("request"),
        )
        if not request_payload:
            raise HTTPException(status_code=400, detail="task request payload is missing")
        if action not in {"validate", "index", "pipeline"}:
            raise HTTPException(status_code=400, detail="task is not retryable")
        if task_obj.status not in {"failed", "success"}:
            raise HTTPException(status_code=400, detail="only completed ingest tasks can be retried")
        next_attempt = int(detail_json.get("attempt") or 1) + 1
        return self._create_ingest_workflow_task(
            db=db,
            action=action,
            request_payload=request_payload,
            operator_id=user.id,
            retry_of_task_id=task_obj.id,
            attempt=next_attempt,
        )

    def run_ingest_task(self, task_id):
        from .schemas import DatasetIngestActionRequest, DatasetIngestPipelineRequest

        with MyDBManager() as db:
            task_obj = dataset_workflow_task_db.get_one(db=db, id=task_id)
            if not task_obj:
                return

            detail_json = self._parse_task_detail(task_obj.detail) or {}
            action = detail_json.get("action") or task_obj.task_type
            request_payload = self._normalize_async_ingest_request_payload(
                action=action,
                request_payload=detail_json.get("request") or {},
            )
            dataset_id = task_obj.dataset_id or request_payload.get("id")
            if action not in {"validate", "index", "pipeline"}:
                dataset_workflow_task_db.update_one(
                    db=db,
                    db_obj=task_obj,
                    obj_in={
                        "status": "failed",
                        "to_lifecycle_state": "failed",
                        "detail": self._encode_task_detail(
                            self._update_task_detail(
                                detail_json,
                                error={"message": f"unsupported ingest action: {action}"},
                                finish_time=self._now(),
                            )
                        ),
                        "finish_time": self._now(),
                    },
                )
                return

            running_state = self._get_async_task_running_state(action=action, request_payload=request_payload)
            started_at = self._now()
            dataset_workflow_task_db.update_one(
                db=db,
                db_obj=task_obj,
                obj_in={
                    "status": "running",
                    "to_lifecycle_state": running_state or task_obj.to_lifecycle_state,
                    "detail": self._encode_task_detail(
                        self._update_task_detail(
                            detail_json,
                            start_time=started_at,
                            running_state=running_state,
                            error=None,
                        )
                    ),
                    "finish_time": None,
                },
            )
            if dataset_id and running_state:
                self._update_dataset_lifecycle_state(db=db, dataset_id=dataset_id, state=running_state)
                self.sync_current_version_from_dataset_id(db=db, dataset_id=dataset_id)

            task_obj = dataset_workflow_task_db.get(db=db, id=task_id)
            task_detail = self._parse_task_detail(task_obj.detail) or detail_json
            user = SimpleNamespace(id=task_obj.operator_id or 0)

            try:
                if action == "validate":
                    request_model = DatasetIngestActionRequest(**request_payload)
                    result = self.validate_ingest_target(db=db, request_data=request_model, user=user, write_workflow_task=False)
                elif action == "index":
                    request_model = DatasetIngestActionRequest(**request_payload)
                    result = self.index_ingest_target(db=db, request_data=request_model, user=user, write_workflow_task=False)
                else:
                    request_model = DatasetIngestPipelineRequest(**request_payload)
                    result = self.run_ingest_pipeline(db=db, request_data=request_model, user=user, write_workflow_task=False)

                dataset_payload = self.get_dataset(db=db, dataset_id=dataset_id) if dataset_id else None
                final_state = dataset_payload.get("lifecycle_state") if dataset_payload else task_obj.to_lifecycle_state
                dataset_workflow_task_db.update_one(
                    db=db,
                    db_obj=task_obj,
                    obj_in={
                        "status": "success",
                        "to_lifecycle_state": final_state,
                        "detail": self._encode_task_detail(
                            self._update_task_detail(
                                task_detail,
                                result=result,
                                finish_time=self._now(),
                            )
                        ),
                        "finish_time": self._now(),
                    },
                )
            except Exception as exc:
                db.rollback()
                if dataset_id:
                    self._update_dataset_lifecycle_state(db=db, dataset_id=dataset_id, state="failed")
                    self.sync_current_version_from_dataset_id(db=db, dataset_id=dataset_id)
                message = exc.detail if isinstance(exc, HTTPException) else str(exc)
                dataset_workflow_task_db.update_one(
                    db=db,
                    db_obj=dataset_workflow_task_db.get(db=db, id=task_id),
                    obj_in={
                        "status": "failed",
                        "to_lifecycle_state": "failed",
                        "detail": self._encode_task_detail(
                            self._update_task_detail(
                                task_detail,
                                error={
                                    "type": exc.__class__.__name__,
                                    "message": message,
                                },
                                finish_time=self._now(),
                            )
                        ),
                        "finish_time": self._now(),
                    },
                )

    def ensure_registry(self, db, database_obj):
        database_id = database_obj.id
        database_name = getattr(database_obj, "name", None) or getattr(database_obj, "title", "")
        database_type = getattr(database_obj, "type", None) or getattr(database_obj, "dataset_type", "generic")
        database_is_public = getattr(database_obj, "default_public_version_id", None)
        database_is_active = getattr(database_obj, "is_active", False)
        registry_obj = dataset_registry_db.get_filter(db=db, filters={"id": database_id})
        file_obj = dataset_legacy_bridge.get_primary_file(db=db, dataset_id=database_id)
        if registry_obj:
            update_data = {
                "title": registry_obj.title or database_name,
                "dataset_type": registry_obj.dataset_type or self._infer_dataset_type(database_obj, file_obj),
                "update_time": self._now(),
            }
            registry_obj = dataset_registry_db.update_one(db=db, db_obj=registry_obj, obj_in=update_data)
            return registry_obj

        return dataset_registry_db.create_one(
            db=db,
            obj_in={
                "dataset_id": database_id,
                "dataset_code": f"ds-{database_id}",
                "dataset_type": self._infer_dataset_type(database_obj, file_obj),
                "title": database_name,
                "create_time": self._now(),
                "update_time": self._now(),
            },
        )

    def build_dataset_payload(self, db, database_obj):
        database_data = {
            "id": database_obj.id,
            "name": getattr(database_obj, 'title', '') or getattr(database_obj, 'name', ''),
            "status": getattr(database_obj, 'lifecycle_state', '') or getattr(database_obj, 'status', 'draft'),
            "user_id": getattr(database_obj, 'user_id', None),
            "remark": getattr(database_obj, 'description_md', '') or getattr(database_obj, 'remark', ''),
            "is_active": True,
            "create_time": getattr(database_obj, 'create_time', 0),
        }
        registry_obj = self.ensure_registry(db=db, database_obj=database_obj)
        dataset_kind_obj = self._get_dataset_kind_registry_by_code(db=db, code=registry_obj.dataset_type)
        file_obj = dataset_legacy_bridge.get_primary_file(db=db, dataset_id=database_data["id"])
        current_version = dataset_version_db.get_filter(db=db, filters={"dataset_id": database_data["id"], "is_current": True})
        file_payload = {
            "id": file_obj.id, "name": file_obj.name, "path": file_obj.path,
            "type": file_obj.type, "data_type": file_obj.data_type,
            "size": file_obj.size, "meta_json": file_obj.meta_json,
        } if file_obj else None
        workflow_tasks = dataset_workflow_task_db.get_data(db=db, filters={"id": database_data["id"]})
        publish_records = dataset_publish_record_db.get_data(db=db, filters={"id": database_data["id"]})
        return {
            "id": database_data["id"],
            "legacy_database_id": database_data["id"],
            "dataset_code": registry_obj.dataset_code,
            "title": registry_obj.title or database_data["name"],
            "name": database_data["name"],
            "dataset_type": registry_obj.dataset_type,
            "dataset_kind": self._build_dataset_kind_registry_payload(dataset_kind_obj) if dataset_kind_obj else None,
            "version": current_version.version if current_version else "",
            "lifecycle_state": "",
            "visibility": "",
            "organism": registry_obj.organism,
            "organism_name": self._get_organism_name(db, registry_obj.organism),
            "description_md": registry_obj.description_md,
            "meta_json": registry_obj.meta_json,
            "default_public_version_id": getattr(registry_obj, "default_public_version_id", None),
            "status": database_data["status"],
            "user_id": database_data["user_id"],
            "remark": database_data["remark"],
            "is_active": database_data["is_active"],
            "file": file_payload,
            "query_profile": {
                "file_format": "",
                "validation_summary": "",
                "index_summary": "",
            },
            "query_adapter": None,
            "assets": [],
            "query_entry_asset": None,
            "projects": self._collect_projects(db=db, database_id=database_data["id"]),
            "meta_items": self._collect_meta(db=db, database_id=database_data["id"]),
            "workflow_tasks": [
                self._build_workflow_task_payload(item)
                for item in sorted(workflow_tasks, key=lambda item: item.id, reverse=True)
            ],
            "publish_records": [
                {
                    "id": item.id,
                    "action": item.action,
                    "visibility_before": item.visibility_before,
                    "visibility_after": item.visibility_after,
                    "lifecycle_before": item.lifecycle_before,
                    "lifecycle_after": item.lifecycle_after,
                    "operator_id": item.operator_id,
                    "note": item.note,
                    "create_time": item.create_time,
                }
                for item in sorted(publish_records, key=lambda item: item.id, reverse=True)
            ],
            "create_time": database_data["create_time"],
            "update_time": registry_obj.update_time,
        }

    def _apply_assets_to_dataset_payload(self, db, dataset_payload, version_obj):
        if not version_obj:
            dataset_payload["assets"] = []
            dataset_payload["query_entry_asset"] = None
            return dataset_payload

        asset_payloads = self._ensure_assets_for_version(db=db, version_obj=version_obj)
        dataset_payload["assets"] = asset_payloads
        self._apply_query_asset_to_dataset_payload(dataset_payload)
        return dataset_payload

    def _apply_query_asset_to_dataset_payload(self, dataset_payload, asset_payload=None):
        asset_payloads = dataset_payload.get("assets") or []
        query_entry_asset = asset_payload
        if not query_entry_asset:
            query_entry_asset = next((item for item in asset_payloads if item["is_query_entry"]), None)
        if not query_entry_asset and asset_payloads:
            query_entry_asset = asset_payloads[0]
        dataset_payload["query_entry_asset"] = query_entry_asset

        if not query_entry_asset:
            return dataset_payload

        primary_file = next((item for item in query_entry_asset["files"] if item["file_role"] == "primary"), None)
        if not primary_file and query_entry_asset["files"]:
            primary_file = query_entry_asset["files"][0]
        file_payload = dict(dataset_payload["file"]) if dataset_payload.get("file") else {}
        primary_file_path = None
        resolved_file_format = dataset_payload["query_profile"]["file_format"]
        if primary_file:
            primary_file_path = self._normalize_local_path(primary_file["local_path"] or primary_file["storage_uri"])
            resolved_file_format = (
                primary_file.get("file_format")
                or query_entry_asset.get("file_format")
                or dataset_payload["query_profile"]["file_format"]
            )
            file_payload.update(
                {
                    "id": primary_file["id"],
                    "name": primary_file["file_name"] or file_payload.get("name"),
                    "path": primary_file["local_path"] or primary_file["storage_uri"],
                    "type": self._to_file_type(primary_file["file_format"]) or file_payload.get("type"),
                    "data_type": dataset_payload["dataset_type"],
                    "size": primary_file["file_size"],
                    "storage_uri": primary_file["storage_uri"],
                    "file_role": primary_file["file_role"],
                }
            )
            dataset_payload["file"] = file_payload

        index_summary = dataset_payload["query_profile"]["index_summary"]
        if not index_summary and primary_file_path:
            detected_index_files = self._detect_index_file_paths(primary_file_path, dataset_payload["dataset_type"])
            if detected_index_files:
                index_summary = json.dumps(
                    {
                        "indexed_path": primary_file_path,
                        "index_files": detected_index_files,
                        "operation": "detected-existing-index",
                    },
                    ensure_ascii=False,
                )

        dataset_payload["query_profile"] = {
            "file_format": resolved_file_format,
            "query_engine": query_entry_asset.get("query_engine", "") or dataset_payload["query_profile"].get("query_engine", ""),
            "validation_summary": dataset_payload["query_profile"]["validation_summary"],
            "index_summary": index_summary,
        }
        return dataset_payload

    def _select_asset_for_query(self, dataset_payload, asset_code=None):
        if not asset_code:
            return dataset_payload

        selected_payload = deepcopy(dataset_payload)
        asset_payloads = selected_payload.get("assets") or []
        selected_asset = next((item for item in asset_payloads if item.get("asset_code") == asset_code), None)
        if not selected_asset:
            raise HTTPException(status_code=404, detail=f"dataset asset not found for query: {asset_code}")

        for item in asset_payloads:
            item["is_query_entry"] = item.get("asset_code") == asset_code
        self._apply_query_asset_to_dataset_payload(selected_payload, asset_payload=selected_asset)
        selected_payload["query_adapter"] = dataset_adapter_registry.describe(selected_payload)
        return selected_payload

    def _build_dataset_version_payload(self, version_obj, db=None):
        file_path = self._normalize_local_path(getattr(version_obj, "file_path", None))
        if db:
            file_path = self._resolve_version_primary_file_path(db=db, version_obj=version_obj) or file_path
        registry_dataset_type = None
        if db:
            reg = dataset_registry_db.get(db=db, id=version_obj.dataset_id)
            registry_dataset_type = reg.dataset_type if reg else None
        return {
            "id": version_obj.id,
            "dataset_id": version_obj.dataset_id,
            "version": version_obj.version,
            "title": version_obj.title,
            "dataset_type": registry_dataset_type,
            "lifecycle_state": version_obj.lifecycle_state,
            "visibility": version_obj.visibility,
            "file_path": file_path,
            "file_format": None,
            "validation_summary": None,
            "index_summary": None,
            "meta_json": version_obj.meta_json,
            "is_current": bool(version_obj.is_current),
            "create_time": version_obj.create_time,
            "update_time": version_obj.update_time,
        }

    def _build_version_publish_record_payload(self, record_obj):
        return {
            "id": record_obj.id,
            "dataset_id": None,
            "version_id": record_obj.dataset_version_id,
            "version": record_obj.version,
            "action": record_obj.action,
            "visibility_before": record_obj.visibility_before,
            "visibility_after": record_obj.visibility_after,
            "lifecycle_before": record_obj.lifecycle_before,
            "lifecycle_after": record_obj.lifecycle_after,
            "operator_id": record_obj.operator_id,
            "note": record_obj.note,
            "create_time": record_obj.create_time,
        }

    def _is_version_publicly_released(self, version_obj):
        return getattr(version_obj, "visibility", "") == "public"

    def _create_version_publish_record(
        self,
        db,
        version_snapshot,
        action,
        operator_id,
        next_visibility,
        next_lifecycle_state,
        note=None,
    ):
        if not version_snapshot:
            return None
        return dataset_version_publish_record_db.create_one(
            db=db,
            obj_in={
                "dataset_id": version_snapshot["dataset_id"],
                "dataset_version_id": version_snapshot["id"],
                "version": version_snapshot["version"],
                "action": action,
                "visibility_before": version_snapshot["visibility"],
                "visibility_after": next_visibility,
                "lifecycle_before": version_snapshot["lifecycle_state"],
                "lifecycle_after": next_lifecycle_state,
                "operator_id": operator_id,
                "note": note,
                "create_time": self._now(),
            },
        )

    def _get_public_version_obj(self, db, dataset_id, dataset_payload=None):
        database_obj = db.query(DatasetRegistry).filter(DatasetRegistry.id == dataset_id).first()
        registry_obj = self.ensure_registry(db=db, database_obj=database_obj)
        default_public_version_id = getattr(registry_obj, "default_public_version_id", None)
        if default_public_version_id:
            try:
                version_obj = dataset_version_db.get(db=db, id=default_public_version_id)
            except Exception:
                version_obj = None
            if version_obj and version_obj.dataset_id == dataset_id and version_obj.visibility == "public":
                return version_obj

        version_rows = dataset_version_db.get_data(db=db, filters={"dataset_id": dataset_id})
        default_public_versions = [
            row
            for row in version_rows
            if row.is_current and row.visibility == "public" and row.visibility == "public"
        ]
        if default_public_versions:
            default_public_versions = sorted(default_public_versions, key=lambda item: item.id, reverse=True)
            return dataset_version_db.get(db=db, id=default_public_versions[0].id)

        return None

    def _list_public_version_objs(self, db, dataset_id):
        version_rows = dataset_version_db.get_data(db=db, filters={"dataset_id": dataset_id})
        public_versions = [row for row in version_rows if row.visibility == "public"]
        return sorted(
            public_versions,
            key=lambda item: (item.is_current and item.visibility == "public", bool(item.is_current), item.id),
            reverse=True,
        )

    def _get_public_version_obj_by_id(self, db, dataset_id, version_id):
        registry = db.query(DatasetRegistry).filter(DatasetRegistry.id == dataset_id).first()
        if not registry:
            raise HTTPException(status_code=404, detail=f"Public dataset not found: {dataset_id}")
        database_id = registry.id
        version_obj = dataset_version_db.get(db=db, id=version_id)
        if version_obj.dataset_id != database_id or not version_obj.visibility == "public":
            raise HTTPException(status_code=404, detail=f"public dataset version not found: dataset={dataset_id}, version={version_id}")
        return version_obj

    def _normalize_version_public_flags(self, db, dataset_id, default_version_id=None):
        version_rows = dataset_version_db.get_data(db=db, filters={"dataset_id": dataset_id})
        for row in version_rows:
            update_data = {}
            if row.visibility != next_visibility:
                update_data["visibility"] = next_visibility
            if update_data:
                update_data["update_time"] = self._now()
                row_obj = dataset_version_db.get(db=db, id=row.id)
                dataset_version_db.update_one(db=db, db_obj=row_obj, obj_in=update_data)

    def _sync_registry_public_state(self, db, dataset_id, default_public_version_id=None):
        database_obj = db.query(DatasetRegistry).filter(DatasetRegistry.id == dataset_id).first()
        registry_obj = self.ensure_registry(db=db, database_obj=database_obj)
        update_data = {
            "default_public_version_id": default_public_version_id,
            "update_time": self._now(),
        }
        dataset_registry_db.update_one(db=db, db_obj=registry_obj, obj_in=update_data)

        dataset_legacy_bridge.update_database(
            db=db,
            db_obj=database_obj,
            obj_in={},
        )

        # Cascade: if dataset becomes private, remove all site bindings
        if not bool(default_public_version_id):
            from modules.platform.models import PlatformSiteDatasetLink

            db.query(PlatformSiteDatasetLink).filter(
                PlatformSiteDatasetLink.dataset_id == dataset_id
            ).delete()

    def _set_default_public_version(self, db, dataset_id, version_obj, note, operator_id):
        self._normalize_version_public_flags(db=db, dataset_id=dataset_id, default_version_id=version_obj.id)
        selected_version = dataset_version_db.get(db=db, id=version_obj.id)
        self._sync_registry_public_state(db=db, dataset_id=dataset_id, default_public_version_id=selected_version.id)
        self._create_version_publish_record(
            db=db,
            version_snapshot={
                "id": selected_version.id,
                "dataset_id": selected_version.dataset_id,
                "version": selected_version.version,
                "visibility": selected_version.visibility,
                "lifecycle_state": selected_version.lifecycle_state,
            },
            action="set_default_public",
            operator_id=operator_id,
            next_visibility="public",
            next_lifecycle_state=selected_version.lifecycle_state,
            note=note or f"set default public version {selected_version.version}",
        )
        return selected_version

    def _build_public_dataset_summary(self, db, dataset_id):
        """Lightweight public dataset payload for the /info endpoint.

        Returns only the fields the public-web frontend actually renders.
        Target: ~5 DB queries, <100ms.
        """
        # 1. Registry row
        registry = db.query(DatasetRegistry).filter(
            DatasetRegistry.id == dataset_id,
        ).first()
        if not registry:
            raise HTTPException(status_code=404, detail=f"Public dataset not found: {dataset_id}")

        # 2. Current version
        current_version = db.query(DatasetVersion).filter(
            DatasetVersion.dataset_id == registry.id,
            DatasetVersion.is_current == True,
        ).first()

        version_str = current_version.version if current_version else ""
        dataset_type = registry.dataset_type if registry else ""
        organism = registry.organism

        # 3. Query entry asset (needed by GeneSearch, GeneInfo, Genotype, Phenotype, Expression)
        query_entry_asset = None
        if current_version:
            qea = db.query(DatasetAsset).filter(
                DatasetAsset.dataset_version_id == current_version.id,
                DatasetAsset.is_query_entry == True,
            ).first()
            if qea:
                query_entry_asset = {"id": qea.id, "asset_code": qea.asset_code, "asset_name": qea.asset_name}

        # 4. Primary file (needed by Detail.vue and Tools.vue)
        primary_file = None
        if current_version:
            primary_asset = db.query(DatasetAsset).filter_by(
                dataset_version_id=current_version.id,
            ).order_by(DatasetAsset.is_query_entry.desc(), DatasetAsset.id.asc()).first()
            if primary_asset:
                pf = db.query(AssetFile).filter_by(
                    dataset_asset_id=primary_asset.id,
                ).order_by(AssetFile.id.asc()).first()
                if pf:
                    primary_file = {
                        "id": pf.id,
                        "name": pf.file_name or "",
                        "size": pf.file_size or 0,
                        "format": pf.file_format or "",
                    }

        # 5. All assets with their files (needed by Detail.vue)
        assets = []
        if current_version:
            asset_rows = db.query(DatasetAsset).filter_by(
                dataset_version_id=current_version.id,
            ).order_by(DatasetAsset.display_order.asc(), DatasetAsset.id.asc()).all()
            if asset_rows:
                asset_ids = [a.id for a in asset_rows]
                all_files = db.query(AssetFile).filter(
                    AssetFile.dataset_asset_id.in_(asset_ids),
                ).order_by(AssetFile.id.asc()).all()
                files_by_asset = {}
                for f in all_files:
                    files_by_asset.setdefault(f.dataset_asset_id, []).append(f)
                for a in asset_rows:
                    flist = files_by_asset.get(a.id, [])
                    assets.append({
                        "id": a.id,
                        "asset_code": a.asset_code,
                        "asset_name": a.asset_name,
                        "asset_type": a.asset_type,
                        "file_format": a.file_format,
                        "files": [
                            {"id": f.id, "file_name": f.file_name, "file_format": f.file_format, "file_size": f.file_size}
                            for f in flist
                        ],
                    })

        return {
            "id": registry.id,
            "dataset_code": registry.dataset_code,
            "title": registry.title or "",
            "dataset_type": dataset_type,
            "organism": organism,
            "organism_name": self._get_organism_name(db, organism),
            "version": version_str,
            "lifecycle_state": "",
            "visibility": "public",
            "description_md": registry.description_md or "",
            "meta_json": registry.meta_json,
            "query_entry_asset": query_entry_asset,
            "primary_file": primary_file,
            "assets": assets,
        }

    def _build_public_dataset_payload(self, db, dataset_id, version_obj=None):
        registry = db.query(DatasetRegistry).filter(DatasetRegistry.id == dataset_id).first()
        if not registry:
            raise HTTPException(status_code=404, detail=f"Public dataset not found: {dataset_id}")
        database_id = registry.id
        database_obj = dataset_legacy_bridge.get_database(db=db, dataset_id=database_id)
        dataset_payload = self.build_dataset_payload(db=db, database_obj=database_obj)
        current_version = self.ensure_current_version(db=db, dataset_payload=dataset_payload)
        dataset_payload["current_version"] = self._build_dataset_version_payload(current_version, db=db)
        dataset_payload["version_count"] = len(dataset_version_db.get_data(db=db, filters={"dataset_id": database_id}))

        public_version = version_obj or self._get_public_version_obj(db=db, dataset_id=database_id, dataset_payload=dataset_payload)
        if not public_version:
            raise HTTPException(status_code=404, detail=f"public dataset version not found: {dataset_id}")
        if version_obj and not public_version.visibility == "public":
            raise HTTPException(status_code=404, detail=f"public dataset version not found: dataset={dataset_id}, version={public_version.id}")

        dataset_payload = self._apply_version_to_dataset_payload(db=db, dataset_payload=dataset_payload, version_obj=public_version)
        dataset_payload = self._apply_assets_to_dataset_payload(db=db, dataset_payload=dataset_payload, version_obj=public_version)
        dataset_payload["visibility"] = "public"
        default_public_version = self._get_public_version_obj(db=db, dataset_id=database_id, dataset_payload=dataset_payload)
        dataset_payload["default_public_version"] = self._build_dataset_version_payload(default_public_version, db=db) if default_public_version else None
        dataset_payload["selected_version"] = self._build_dataset_version_payload(public_version, db=db)
        dataset_payload["published_version"] = self._build_dataset_version_payload(public_version, db=db)
        dataset_payload["public_versions"] = [
            self._build_dataset_version_payload(item, db=db) for item in self._list_public_version_objs(db=db, dataset_id=database_id)
        ]
        dataset_payload["lineage"] = self._list_public_lineage(db=db, version_id=public_version.id, limit=50)
        dataset_payload["query_adapter"] = dataset_adapter_registry.describe(dataset_payload)
        return dataset_payload

    def _build_dataset_payload_for_version(self, db, version_obj):
        database_obj = dataset_legacy_bridge.get_database(db=db, dataset_id=version_obj.dataset_id)
        dataset_payload = self.build_dataset_payload(db=db, database_obj=database_obj)
        current_version = self.ensure_current_version(db=db, dataset_payload=dataset_payload)
        dataset_payload["current_version"] = self._build_dataset_version_payload(current_version, db=db) if current_version else None
        dataset_payload["version_count"] = len(dataset_version_db.get_data(db=db, filters={"dataset_id": version_obj.dataset_id}))
        dataset_payload = self._apply_version_to_dataset_payload(db=db, dataset_payload=dataset_payload, version_obj=version_obj)
        dataset_payload = self._apply_assets_to_dataset_payload(db=db, dataset_payload=dataset_payload, version_obj=version_obj)
        dataset_payload["selected_version"] = self._build_dataset_version_payload(version_obj, db=db)
        public_version = self._get_public_version_obj(db=db, dataset_id=version_obj.dataset_id, dataset_payload=dataset_payload)
        dataset_payload["default_public_version"] = self._build_dataset_version_payload(public_version, db=db) if public_version else None
        dataset_payload["published_version"] = self._build_dataset_version_payload(public_version, db=db) if public_version else None
        dataset_payload["query_adapter"] = dataset_adapter_registry.describe(dataset_payload)
        return dataset_payload

    def _apply_version_to_dataset_payload(self, db, dataset_payload, version_obj):
        if not version_obj:
            return dataset_payload

        dataset_payload["version"] = version_obj.version
        dataset_payload["title"] = version_obj.title or dataset_payload["title"]
        dataset_payload["lifecycle_state"] = version_obj.lifecycle_state or dataset_payload["lifecycle_state"]
        dataset_payload["visibility"] = version_obj.visibility or dataset_payload["visibility"]
        dataset_payload["dataset_type"] = dataset_payload["dataset_type"]
        dataset_kind_obj = self._get_dataset_kind_registry_by_code(db=db, code=dataset_payload["dataset_type"])
        dataset_payload["dataset_kind"] = self._build_dataset_kind_registry_payload(dataset_kind_obj) if dataset_kind_obj else None

        file_payload = dict(dataset_payload["file"]) if dataset_payload.get("file") else {}
        effective_file_path = self._resolve_version_primary_file_path(db=db, version_obj=version_obj)
        if effective_file_path:
            file_payload["path"] = effective_file_path
            file_payload["type"] = self._to_file_type(None) or file_payload.get("type")
            file_payload["data_type"] = file_payload.get("data_type")
            file_payload["name"] = file_payload.get("name") or version_obj.title or dataset_payload["title"]
            dataset_payload["file"] = file_payload

        dataset_payload["query_profile"] = {
            "file_format": None or dataset_payload["query_profile"].get("file_format", ""),
            "query_engine": None or dataset_payload["query_profile"].get("query_engine", ""),
            "validation_summary": None
            if None is not None
            else None,
            "index_summary": None
            if None is not None
            else None,
        }
        return dataset_payload

    def _build_version_data_from_dataset_payload(self, dataset_payload):
        file_payload = dataset_payload.get("file") or {}
        query_profile = dataset_payload["query_profile"]
        published_version = dataset_payload.get("published_version") or {}
        return {
            "dataset_id": dataset_payload["id"],
            "version": dataset_payload["version"],
            "title": dataset_payload["title"],
            "dataset_type": dataset_payload["dataset_type"],
            "lifecycle_state": dataset_payload["lifecycle_state"],
            "visibility": dataset_payload["visibility"],
            "file_path": file_payload.get("path"),
            "file_format": query_profile["file_format"],
            "query_engine": query_profile.get("query_engine", ""),
            "validation_summary": query_profile["validation_summary"],
            "index_summary": query_profile["index_summary"],
            "is_current": True,
            "update_time": self._now(),
        }

    def _ensure_version_current_flag(self, db, database_id, version_name):
        version_rows = dataset_version_db.get_data(db=db, filters={"dataset_id": database_id})
        version_snapshots = [
            {
                "id": row.id,
                "version": row.version,
                "is_current": bool(row.is_current),
            }
            for row in version_rows
        ]
        target_exists = False
        for row in version_snapshots:
            should_be_current = row["version"] == version_name
            if should_be_current:
                target_exists = True
            if row["is_current"] != should_be_current:
                row_obj = dataset_version_db.get(db=db, id=row["id"])
                dataset_version_db.update_one(
                    db=db,
                    db_obj=row_obj,
                    obj_in={"is_current": True if should_be_current else 0, "update_time": self._now()},
                )
        if target_exists:
            return dataset_version_db.get_filter(
                db=db,
                filters={"dataset_id": database_id, "version": version_name},
            )
        return None

    def sync_current_version_from_dataset_payload(self, db, dataset_payload):
        version_name = dataset_payload["version"]
        database_id = dataset_payload["id"]
        version_obj = dataset_version_db.get_filter(
            db=db,
            filters={"dataset_id": database_id, "version": version_name},
        )
        version_data = self._build_version_data_from_dataset_payload(dataset_payload)
        if version_obj and getattr(version_obj, "meta_json", None) is not None:
            version_data["meta_json"] = version_obj.meta_json
        self._ensure_version_current_flag(db=db, database_id=database_id, version_name=version_name)
        if version_obj:
            dataset_version_db.update_one(db=db, db_obj=version_obj, obj_in=version_data)
            version_obj = dataset_version_db.get_filter(
                db=db,
                filters={"dataset_id": database_id, "version": version_name},
            )
            self._ensure_assets_for_version(db=db, version_obj=version_obj)
            return version_obj

        version_data["create_time"] = dataset_payload["create_time"] or self._now()
        version_obj = dataset_version_db.create_one(db=db, obj_in=version_data)
        self._ensure_version_current_flag(db=db, database_id=database_id, version_name=version_name)
        self._ensure_assets_for_version(db=db, version_obj=version_obj)
        return version_obj

    def sync_current_version_from_dataset_id(self, db, dataset_id):
        database_obj = db.query(DatasetRegistry).filter(DatasetRegistry.id == dataset_id).first()
        dataset_payload = self.build_dataset_payload(db=db, database_obj=database_obj)
        return self.sync_current_version_from_dataset_payload(db=db, dataset_payload=dataset_payload)

    def ensure_current_version(self, db, dataset_payload):
        database_id = dataset_payload["id"]
        version_name = dataset_payload["version"]
        version_obj = self._ensure_version_current_flag(db=db, database_id=database_id, version_name=version_name)
        if version_obj:
            return version_obj

        version_data = self._build_version_data_from_dataset_payload(dataset_payload)
        version_data["create_time"] = dataset_payload["create_time"] or self._now()
        version_obj = dataset_version_db.create_one(db=db, obj_in=version_data)
        self._ensure_version_current_flag(db=db, database_id=database_id, version_name=version_name)
        self._ensure_assets_for_version(db=db, version_obj=version_obj)
        return version_obj

    def list_datasets(self, db, request_data, user=None):
        filters = {}
        filters_exp = []
        database_ids = []
        if request_data.project_id:
            database_ids = [
                item.dataset_id
                for item in dataset_legacy_bridge.list_project_links_by_project(db=db, project_id=request_data.project_id)
            ]
        if database_ids:
            filters_exp.append({"name": "id", "exp": "contain", "value": database_ids})
        elif request_data.project_id:
            filters_exp.append({"name": "id", "exp": "contain", "value": [-1]})
        if request_data.dataset_id:
            filters["id"] = request_data.dataset_id
        if request_data.name:
            filters_exp.append({"name": "name", "exp": "like", "value": request_data.name})

        need_post_filter = any(
            [
                request_data.dataset_type,
                request_data.lifecycle_state,
                request_data.visibility,
                getattr(request_data, 'keyword', None),
                bool(user and not self._is_platform_admin(user)),
            ]
        )
        query_page = 0 if need_post_filter else request_data.page
        query_size = 0 if need_post_filter else request_data.size

        page_obj = dataset_legacy_bridge.list_databases(
            db=db,
            page=query_page,
            size=query_size,
            filters=filters,
            filters_exp=filters_exp,
            sort="-id",
        )

        data_list = []
        database_ids = [item.id for item in page_obj["dataList"]]
        for database_id in database_ids:
            try:
                database_obj = dataset_legacy_bridge.get_database(db=db, dataset_id=database_id)
                if user and not self._can_access_dataset(db=db, database_obj=database_obj, user=user):
                    continue
                payload = self.build_dataset_payload(db=db, database_obj=database_obj)
                current_version = self.ensure_current_version(db=db, dataset_payload=payload)
                payload = self._apply_version_to_dataset_payload(db=db, dataset_payload=payload, version_obj=current_version)
                payload = self._apply_assets_to_dataset_payload(db=db, dataset_payload=payload, version_obj=current_version)
                payload["query_adapter"] = {}
                try:
                    payload["query_adapter"] = dataset_adapter_registry.describe(payload)
                except Exception:
                    pass
            except Exception as e:
                import sys, traceback; print(f"[ERROR] list_datasets id={database_id}: {e}", file=sys.stderr); traceback.print_exc(file=sys.stderr)
                continue
            if request_data.dataset_type and not self._dataset_type_matches(payload["dataset_type"], request_data.dataset_type):
                continue
            if request_data.lifecycle_state and payload["lifecycle_state"] != request_data.lifecycle_state:
                continue
            if request_data.visibility and payload["visibility"] != request_data.visibility:
                continue
            if getattr(request_data, 'keyword', None):
                keyword = request_data.keyword.strip().lower()
                desc = (payload.get("description_md") or "").lower()
                extra = (payload.get("meta_json") or "").lower()
                if keyword not in desc and keyword not in extra:
                    continue
            data_list.append(payload)

        total = len(data_list) if need_post_filter else page_obj["total"]
        if need_post_filter and request_data.page and request_data.size:
            start = (request_data.page - 1) * request_data.size
            end = start + request_data.size
            data_list = data_list[start:end]

        page_obj["dataList"] = data_list
        page_obj["total"] = total
        return page_obj

    def get_dataset(self, db, dataset_id, user=None):
        database_obj = self._ensure_dataset_read_access(db=db, dataset_id=dataset_id, user=user)
        payload = self.build_dataset_payload(db=db, database_obj=database_obj)
        current_version = self.ensure_current_version(db=db, dataset_payload=payload)
        payload = self._apply_version_to_dataset_payload(db=db, dataset_payload=payload, version_obj=current_version)
        payload = self._apply_assets_to_dataset_payload(db=db, dataset_payload=payload, version_obj=current_version)
        payload["query_adapter"] = {}
        try:
            payload["query_adapter"] = dataset_adapter_registry.describe(payload)
        except Exception:
            pass
        payload["current_version"] = self._build_dataset_version_payload(current_version, db=db)
        public_version = self._get_public_version_obj(db=db, dataset_id=dataset_id, dataset_payload=payload)
        payload["default_public_version"] = self._build_dataset_version_payload(public_version, db=db) if public_version else None
        payload["published_version"] = self._build_dataset_version_payload(public_version, db=db) if public_version else None
        payload["version_count"] = len(dataset_version_db.get_data(db=db, filters={"dataset_id": payload["id"]}))
        return payload

    def update_dataset(self, db, dataset_id, request_data, user=None):
        database_obj = self._ensure_dataset_write_access(db=db, dataset_id=dataset_id, user=user)
        registry_obj = self.ensure_registry(db=db, database_obj=database_obj)

        database_update = {}
        if request_data.title:
            database_update["name"] = request_data.title
        if database_update:
            dataset_legacy_bridge.update_database(db=db, db_obj=database_obj, obj_in=database_update)
            registry_obj = dataset_registry_db.get_filter(db=db, filters={"id": dataset_id})

        registry_update = {"update_time": self._now()}
        for field in [
            "title",
            "dataset_type",
            "version",
            "organism",
                        "file_format",
            "validation_summary",
            "index_summary",
            "meta_json",
            "description_md",
        ]:
            value = getattr(request_data, field, None)
            if value is not None:
                if field == "dataset_type":
                    value, _dataset_kind = self._require_dataset_kind_code(db=db, dataset_type=value)
                registry_update[field] = value
        dataset_registry_db.update_one(db=db, db_obj=registry_obj, obj_in=registry_update)
        self.sync_current_version_from_dataset_id(db=db, dataset_id=dataset_id)
        return self.get_dataset(db=db, dataset_id=dataset_id, user=user)

    def transition_state(self, db, dataset_id, request_data, user):
        operator_id = user.id
        if request_data.target_state not in DATASET_LIFECYCLE_STATES:
            raise HTTPException(status_code=4000, detail="invalid dataset lifecycle state")
        if request_data.task_type and request_data.task_type not in WORKFLOW_TASK_TYPES:
            raise HTTPException(status_code=4000, detail="invalid workflow task type")
        if request_data.status and request_data.status not in WORKFLOW_TASK_STATUS:
            raise HTTPException(status_code=4000, detail="invalid workflow task status")

        database_obj = self._ensure_dataset_write_access(db=db, dataset_id=dataset_id, user=user)
        current_ver = dataset_version_db.get_filter(db=db, filters={"dataset_id": dataset_id, "is_current": True})
        registry_obj = self.ensure_registry(db=db, database_obj=database_obj)
        before_state = current_ver.lifecycle_state if current_ver else "draft"
        before_visibility = current_ver.visibility if current_ver else "private"
        allowed_states = LIFECYCLE_TRANSITIONS.get(before_state, set())
        if request_data.target_state not in allowed_states:
            raise HTTPException(
                status_code=4000,
                detail=f"illegal state transition: {before_state} -> {request_data.target_state}",
            )

        update_data = {
            "lifecycle_state": request_data.target_state,
            "visibility": "public" if request_data.target_state == "public" else before_visibility,
            "update_time": self._now(),
        }
        dataset_registry_db.update_one(db=db, db_obj=registry_obj, obj_in=update_data)

        detail = request_data.detail
        if detail and detail.startswith("{"):
            try:
                detail = json.dumps(json.loads(detail), ensure_ascii=False)
            except json.JSONDecodeError:
                pass

        dataset_workflow_task_db.create_one(
            db=db,
            obj_in={
                "dataset_id": dataset_id,
                "task_type": request_data.task_type or "sync",
                "status": request_data.status or "success",
                "from_lifecycle_state": before_state,
                "to_lifecycle_state": request_data.target_state,
                "operator_id": operator_id,
                "detail": detail,
                "create_time": self._now(),
                "finish_time": self._now() if request_data.status != "running" else None,
            },
        )
        self.sync_current_version_from_dataset_id(db=db, dataset_id=dataset_id)
        return self.get_dataset(db=db, dataset_id=dataset_id, user=user)

    def publish_dataset(self, db, dataset_id, request_data, user):
        operator_id = user.id
        self._ensure_dataset_write_access(db=db, dataset_id=dataset_id, user=user)
        dataset_payload = self.get_dataset(db=db, dataset_id=dataset_id, user=user)
        current_version = dataset_payload["current_version"]
        if current_version.get("lifecycle_state") != "ready":
            raise HTTPException(status_code=4000, detail="dataset version must be ready before publish")

        before_visibility = current_version.get("visibility")
        before_state = current_version.get("lifecycle_state")
        self.release_dataset_version(db=db, version_id=current_version["id"], request_data=request_data, user=user)
        dataset_publish_record_db.create_one(
            db=db,
            obj_in={
                "dataset_id": dataset_id,
                "action": "publish",
                "visibility_before": before_visibility,
                "visibility_after": "public",
                "lifecycle_before": before_state,
                "lifecycle_after": before_state,
                "operator_id": operator_id,
                "note": request_data.note or f"publish dataset current version {current_version['version']}",
                "create_time": self._now(),
            },
        )
        dataset_workflow_task_db.create_one(
            db=db,
            obj_in={
                "dataset_id": dataset_id,
                "task_type": "publish",
                "status": "success",
                "from_lifecycle_state": before_state,
                "to_lifecycle_state": before_state,
                "operator_id": operator_id,
                "detail": request_data.note or f"publish dataset current version {current_version['version']}",
                "create_time": self._now(),
                "finish_time": self._now(),
            },
        )
        self.sync_current_version_from_dataset_id(db=db, dataset_id=dataset_id)
        return self.get_dataset(db=db, dataset_id=dataset_id, user=user)

    def unpublish_dataset(self, db, dataset_id, request_data, user):
        operator_id = user.id
        database_obj = self._ensure_dataset_write_access(db=db, dataset_id=dataset_id, user=user)
        registry_obj = self.ensure_registry(db=db, database_obj=database_obj)
        if not getattr(registry_obj, "default_public_version_id", None):
            raise HTTPException(status_code=4000, detail="dataset is not public")

        version_rows = dataset_version_db.get_data(db=db, filters={"dataset_id": dataset_id})
        before_state = version_rows[0].lifecycle_state if version_rows else None
        version_rows = dataset_version_db.get_data(db=db, filters={"dataset_id": dataset_id})
        candidate_public_version_ids = {getattr(registry_obj, "default_public_version_id", None)} - {None}
        for version_obj in version_rows:
            is_candidate = (
                version_obj.visibility == "public"
                or version_obj.is_current and version_obj.visibility == "public"
                or version_obj.id in candidate_public_version_ids
                or version_obj.visibility == "public"
            )
            if not is_candidate:
                continue
            if version_obj.visibility == "public":
                self.withdraw_dataset_version(db=db, version_id=version_obj.id, request_data=request_data, user=user)
                continue

            dataset_version_db.update_one(
                db=db,
                db_obj=version_obj,
                obj_in={
                    "visibility": "private",
                    "update_time": self._now(),
                },
            )

        registry_obj = dataset_registry_db.get_filter(db=db, filters={"id": dataset_id})
        if getattr(registry_obj, "default_public_version_id", None):
            self._normalize_version_public_flags(db=db, dataset_id=dataset_id, default_version_id=None)
            self._sync_registry_public_state(db=db, dataset_id=dataset_id, default_public_version_id=None)
            registry_obj = dataset_registry_db.get_filter(db=db, filters={"id": dataset_id})
        next_state = version_rows[0].lifecycle_state if version_rows else None
        dataset_publish_record_db.create_one(
            db=db,
            obj_in={
                "dataset_id": dataset_id,
                "action": "unpublish",
                "visibility_before": "public",
                "visibility_after": "private",
                "lifecycle_before": before_state,
                "lifecycle_after": next_state,
                "operator_id": operator_id,
                "note": request_data.note,
                "create_time": self._now(),
            },
        )
        dataset_workflow_task_db.create_one(
            db=db,
            obj_in={
                "dataset_id": dataset_id,
                "task_type": "unpublish",
                "status": "success",
                "from_lifecycle_state": before_state,
                "to_lifecycle_state": before_state,
                "operator_id": operator_id,
                "detail": request_data.note,
                "create_time": self._now(),
                "finish_time": self._now(),
            },
        )
        self.sync_current_version_from_dataset_id(db=db, dataset_id=dataset_id)
        return self.get_dataset(db=db, dataset_id=dataset_id, user=user)

    def get_task_list(self, db, dataset_id, limit, user=None):
        self._ensure_dataset_read_access(db=db, dataset_id=dataset_id, user=user)
        tasks = dataset_workflow_task_db.get_data(db=db, filters={"id": dataset_id})
        tasks = sorted(tasks, key=lambda item: item.id, reverse=True)[:limit]
        return [self._build_workflow_task_payload(item) for item in tasks]

    def delete_dataset(self, db, dataset_id, user=None):
        database_obj = self._ensure_dataset_write_access(db=db, dataset_id=dataset_id, user=user)
        payload = self.get_dataset(db=db, dataset_id=dataset_id, user=user)
        registry_obj = dataset_registry_db.get_filter(db=db, filters={"id": dataset_id})
        registry_id = getattr(registry_obj, "id", None)

        version_rows = dataset_version_db.get_data(db=db, filters={"dataset_id": dataset_id}) or []
        asset_rows = dataset_asset_db.get_data(db=db, filters={"id": dataset_id}) or []
        version_ids = [item.id for item in version_rows]
        asset_ids = [item.id for item in asset_rows]
        asset_file_rows = []
        asset_file_ids = []
        if asset_ids:
            asset_file_rows = self._list_asset_file_rows(db=db, asset_id=asset_ids[0]) if len(asset_ids) == 1 else []
            if not asset_file_rows:
                asset_file_rows = db.query(asset_file_db.model).filter(asset_file_db.model.dataset_asset_id.in_(asset_ids)).all()
            asset_file_ids = [item.id for item in asset_file_rows]

        for model in (FunctionalGene, FunctionalTerm, FunctionalTermAssignment):
            db.query(model).filter(model.dataset_id == dataset_id).delete(synchronize_session=False)
        for model in (PhenomeImportRun, PhenomeSubject, PhenomeTrait, PhenomeSourceColumn, PhenomeObservation):
            db.query(model).filter(model.dataset_id == dataset_id).delete(synchronize_session=False)

        breeding_subject_filters = []
        breeding_assay_filters = []
        if registry_id:
            breeding_subject_filters.append(BreedingDatasetSubjectLink.dataset_id == registry_id)
            breeding_assay_filters.append(BreedingDatasetAssayLink.dataset_id == registry_id)
        if version_ids:
            breeding_subject_filters.append(BreedingDatasetSubjectLink.version_id.in_(version_ids))
            breeding_assay_filters.append(BreedingDatasetAssayLink.version_id.in_(version_ids))
        if asset_ids:
            breeding_subject_filters.append(BreedingDatasetSubjectLink.asset_id.in_(asset_ids))
            breeding_assay_filters.append(BreedingDatasetAssayLink.asset_id.in_(asset_ids))
        if breeding_subject_filters:
            db.query(BreedingDatasetSubjectLink).filter(or_(*breeding_subject_filters)).delete(synchronize_session=False)
        if breeding_assay_filters:
            db.query(BreedingDatasetAssayLink).filter(or_(*breeding_assay_filters)).delete(synchronize_session=False)

        breeding_data_file_filters = []
        if registry_id:
            breeding_data_file_filters.append(BreedingDataFile.dataset_id == registry_id)
        if version_ids:
            breeding_data_file_filters.append(BreedingDataFile.version_id.in_(version_ids))
        if asset_ids:
            breeding_data_file_filters.append(BreedingDataFile.asset_id.in_(asset_ids))
        if asset_file_ids:
            breeding_data_file_filters.append(BreedingDataFile.asset_file_id.in_(asset_file_ids))
        if breeding_data_file_filters:
            db.query(BreedingDataFile).filter(or_(*breeding_data_file_filters)).delete(synchronize_session=False)

        breeding_observation_filters = []
        if registry_id:
            breeding_observation_filters.append(BreedingObservation.source_dataset_id == registry_id)
        if version_ids:
            breeding_observation_filters.append(BreedingObservation.source_version_id.in_(version_ids))
        if asset_ids:
            breeding_observation_filters.append(BreedingObservation.source_asset_id.in_(asset_ids))
        if breeding_observation_filters:
            db.query(BreedingObservation).filter(or_(*breeding_observation_filters)).delete(synchronize_session=False)

        breeding_variant_filters = []
        breeding_phenotype_filters = []
        if registry_id:
            breeding_variant_filters.append(BreedingVariantSampleMap.dataset_id == registry_id)
            breeding_phenotype_filters.append(BreedingPhenotypeSubjectMap.dataset_id == registry_id)
        if version_ids:
            breeding_variant_filters.append(BreedingVariantSampleMap.version_id.in_(version_ids))
            breeding_phenotype_filters.append(BreedingPhenotypeSubjectMap.version_id.in_(version_ids))
        if asset_ids:
            breeding_variant_filters.append(BreedingVariantSampleMap.asset_id.in_(asset_ids))
            breeding_phenotype_filters.append(BreedingPhenotypeSubjectMap.asset_id.in_(asset_ids))
        if breeding_variant_filters:
            db.query(BreedingVariantSampleMap).filter(or_(*breeding_variant_filters)).delete(synchronize_session=False)
        if breeding_phenotype_filters:
            db.query(BreedingPhenotypeSubjectMap).filter(or_(*breeding_phenotype_filters)).delete(synchronize_session=False)

        if version_ids or asset_ids:
            lineage_filters = []
            if version_ids:
                lineage_filters.extend([
                    dataset_lineage_edge_db.model.src_dataset_version_id.in_(version_ids),
                    dataset_lineage_edge_db.model.dst_dataset_version_id.in_(version_ids),
                ])
            if asset_ids:
                lineage_filters.extend([
                    dataset_lineage_edge_db.model.src_asset_id.in_(asset_ids),
                    dataset_lineage_edge_db.model.dst_asset_id.in_(asset_ids),
                ])
            if lineage_filters:
                db.query(dataset_lineage_edge_db.model).filter(or_(*lineage_filters)).delete(
                    synchronize_session=False
                )

        if version_ids:
            db.query(dataset_version_publish_record_db.model).filter(
                dataset_version_publish_record_db.model.dataset_version_id.in_(version_ids)
            ).delete(synchronize_session=False)

        if asset_ids:
            db.query(asset_file_db.model).filter(asset_file_db.model.dataset_asset_id.in_(asset_ids)).delete(
                synchronize_session=False
            )
            db.query(dataset_asset_db.model).filter(dataset_asset_db.model.id.in_(asset_ids)).delete(
                synchronize_session=False
            )

        if version_ids:
            db.query(dataset_version_db.model).filter(dataset_version_db.model.id.in_(version_ids)).delete(
                synchronize_session=False
            )

        db.query(dataset_publish_record_db.model).filter(dataset_publish_record_db.model.dataset_id == dataset_id).delete(
            synchronize_session=False
        )
        db.query(dataset_workflow_task_db.model).filter(dataset_workflow_task_db.model.dataset_id == dataset_id).delete(
            synchronize_session=False
        )
        db.query(dataset_registry_db.model).filter(dataset_registry_db.model.id == dataset_id).delete(
            synchronize_session=False
        )
        db.query(dataset_staging_file_db.model).filter(dataset_staging_file_db.model.linked_dataset_id == dataset_id).delete(
            synchronize_session=False
        )
        dataset_legacy_bridge.delete_legacy_cascade(db=db, dataset_id=dataset_id)
        db.commit()

        return {
            "deleted": True,
            "delete_mode": "record_only",
            "item": payload,
            "message": f"dataset {database_obj.id} records deleted; files kept on disk",
        }

    def get_publish_record_list(self, db, dataset_id, limit, user=None):
        self._ensure_dataset_read_access(db=db, dataset_id=dataset_id, user=user)
        records = dataset_publish_record_db.get_data(db=db, filters={"id": dataset_id})
        records = sorted(records, key=lambda item: item.id, reverse=True)[:limit]
        return [
            {
                "id": item.id,
                "action": item.action,
                "visibility_before": item.visibility_before,
                "visibility_after": item.visibility_after,
                "lifecycle_before": item.lifecycle_before,
                "lifecycle_after": item.lifecycle_after,
                "operator_id": item.operator_id,
                "note": item.note,
                "create_time": item.create_time,
            }
            for item in records
        ]

    def get_version_publish_record_list(self, db, dataset_id=None, version_id=None, limit=20, user=None):
        if dataset_id is not None:
            self._ensure_dataset_read_access(db=db, dataset_id=dataset_id, user=user)
        if version_id is not None:
            version_obj = self._ensure_version_read_access(db=db, version_id=version_id, user=user)
        filters = {}
        if version_id is not None:
            filters["dataset_version_id"] = version_id
        elif dataset_id is not None:
            version_ids = [v.id for v in dataset_version_db.get_data(db=db, filters={"dataset_id": dataset_id})]
            if version_ids:
                filters["dataset_version_id"] = version_ids[0] if len(version_ids) == 1 else version_ids
        records = dataset_version_publish_record_db.get_data(db=db, filters=filters) if filters else []
        if user and not self._is_platform_admin(user) and not filters:
            records = [
                item
                for item in records
                if self._can_access_dataset(
                    db=db,
                    database_obj=dataset_legacy_bridge.get_database(
                        db=db,
                        dataset_id=dataset_version_db.get(db=db, id=item.dataset_version_id).dataset_id if item.dataset_version_id else None,
                    ),
                    user=user,
                )
            ]
        records = sorted(records, key=lambda item: item.id, reverse=True)[:limit]
        return {
            "dataset_id": dataset_id,
            "version_id": version_id,
            "items": [self._build_version_publish_record_payload(item) for item in records],
        }

    def list_dataset_assets(self, db, version_id, user=None):
        version_obj = self._ensure_version_read_access(db=db, version_id=version_id, user=user)
        return {
            "version_id": version_id,
            "dataset_id": version_obj.dataset_id,
            "version": version_obj.version,
            "items": self._build_asset_list_payload(db=db, version_id=version_id),
        }

    def get_dataset_asset(self, db, asset_id, user=None):
        asset_obj = self._ensure_asset_read_access(db=db, asset_id=asset_id, user=user)
        file_rows = self._list_asset_file_rows(db=db, asset_id=asset_id)
        return self._build_dataset_asset_payload(
            asset_obj,
            files=[self._build_asset_file_payload(item) for item in file_rows],
        )

    def _next_asset_code(self, db, version_id, asset_type):
        base_code = self._default_asset_code(asset_type)
        existing_rows = dataset_asset_db.get_data(db=db, filters={"dataset_version_id": version_id})
        existing_codes = {item.asset_code for item in existing_rows}
        if base_code not in existing_codes:
            return base_code
        index = 2
        while f"{base_code}_{index}" in existing_codes:
            index += 1
        return f"{base_code}_{index}"

    def create_dataset_asset(self, db, request_data, user):
        version_obj = self._ensure_version_write_access(db=db, version_id=request_data.version_id, user=user)
        registry = dataset_registry_db.get(db=db, id=version_obj.dataset_id)
        dataset_type = registry.dataset_type if registry else "generic"
        asset_type, _asset_type = self._require_asset_type_code(
            db=db,
            asset_type=request_data.asset_type,
            dataset_type=dataset_type,
        )
        asset_code = request_data.asset_code or self._next_asset_code(
            db=db,
            version_id=request_data.version_id,
            asset_type=asset_type,
        )
        existing = dataset_asset_db.get_filter(db=db, filters={"dataset_version_id": request_data.version_id, "asset_code": asset_code})
        if existing:
            raise HTTPException(status_code=400, detail=f"dataset asset already exists: {asset_code}")
        if request_data.local_path:
            self._validate_local_file_exists(request_data.local_path)
        asset_file_format = request_data.file_format or (self._guess_file_suffix(request_data.local_path) if request_data.local_path else None)
        if asset_file_format:
            _registry_row, asset_file_format = self._validate_asset_file_registry_binding(
                db=db,
                asset_type=asset_type,
                file_role="primary",
                file_format=asset_file_format,
                local_path=request_data.local_path,
            )
        asset_obj = dataset_asset_db.create_one(
            db=db,
            obj_in={
                "dataset_id": version_obj.dataset_id,
                "dataset_version_id": request_data.version_id,
                "asset_code": asset_code,
                "asset_name": request_data.asset_name,
                "asset_type": asset_type,
                "file_format": asset_file_format,
                "query_engine": request_data.query_engine or FILE_TYPE_QUERY_ENGINES.get(
                    (asset_file_format or "").lower(),
                    "file",
                ),
                "storage_backend": request_data.storage_backend or "local",
                "workflow_state": request_data.workflow_state or "draft",
                "status": request_data.status or "active",
                "is_required": bool(request_data.is_required),
                "is_query_entry": bool(request_data.is_query_entry),
                "display_order": request_data.display_order or 0,
                "meta_json": request_data.meta_json,
                "create_time": self._now(),
                "update_time": self._now(),
            },
        )
        if request_data.is_query_entry:
            self._normalize_query_entry_assets(db=db, version_id=request_data.version_id, selected_asset_id=asset_obj.id)
        if request_data.local_path:
            self._ensure_asset_file_record(
                db=db,
                asset_obj=asset_obj,
                file_role="primary",
                local_path=request_data.local_path,
                file_format=request_data.file_format,
                asset_file_type_code=None,
                status="active",
            )
            self._maybe_rebuild_functional_annotation_index(db=db, asset_obj=asset_obj)
            self._maybe_rebuild_phenome_index(db=db, asset_obj=asset_obj)
        return self.get_dataset_asset(db=db, asset_id=asset_obj.id, user=user)

    def update_dataset_asset(self, db, asset_id, request_data, user):
        asset_obj = self._ensure_asset_write_access(db=db, asset_id=asset_id, user=user)
        version_obj = dataset_version_db.get(db=db, id=asset_obj.dataset_version_id)
        update_data = {"update_time": self._now()}
        next_asset_type = asset_obj.asset_type
        for field in [
            "asset_name",
            "asset_type",
            "file_format",
            "storage_backend",
            "workflow_state",
            "status",
            "display_order",
            "meta_json",
        ]:
            value = getattr(request_data, field, None)
            if value is not None:
                if field == "asset_type":
                    value, _asset_type = self._require_asset_type_code(
                        db=db,
                        asset_type=value,
                        dataset_type=dataset_type,
                    )
                    next_asset_type = value
                update_data[field] = value
        if request_data.asset_type is not None:
            self._validate_asset_files_against_asset_type(db=db, asset_obj=asset_obj, asset_type=next_asset_type)
        next_asset_file_format = update_data.get("file_format", asset_obj.file_format)
        if next_asset_file_format:
            _registry_row, normalized_file_format = self._validate_asset_file_registry_binding(
                db=db,
                asset_type=next_asset_type,
                file_role="primary",
                file_format=next_asset_file_format,
            )
            update_data["file_format"] = normalized_file_format
        if request_data.is_required is not None:
            update_data["is_required"] = 1 if request_data.is_required else 0
        if request_data.is_query_entry is not None:
            update_data["is_query_entry"] = 1 if request_data.is_query_entry else 0
        asset_obj = self._update_db_obj(db, asset_obj, **update_data)
        if request_data.is_query_entry:
            self._normalize_query_entry_assets(db=db, version_id=asset_obj.dataset_version_id, selected_asset_id=asset_obj.id)
        elif request_data.is_query_entry is False:
            self._normalize_query_entry_assets(db=db, version_id=asset_obj.dataset_version_id)
        return self.get_dataset_asset(db=db, asset_id=asset_id, user=user)

    def delete_dataset_asset(self, db, asset_id, user):
        asset_obj = self._ensure_asset_write_access(db=db, asset_id=asset_id, user=user)
        payload = self.get_dataset_asset(db=db, asset_id=asset_id, user=user)
        version_id = asset_obj.dataset_version_id
        self._clear_functional_annotation_index(db=db, asset_obj=asset_obj)
        self._clear_phenome_index(db=db, asset_obj=asset_obj)

        lineage_rows = dataset_lineage_edge_db.get_data(db=db, filters={})
        related_lineage_ids = [
            item.id
            for item in lineage_rows
            if item.src_asset_id == asset_id or item.dst_asset_id == asset_id
        ]
        if related_lineage_ids:
            dataset_lineage_edge_db.remove_batch_ids(db=db, ids=related_lineage_ids)

        file_rows = self._list_asset_file_rows(db=db, asset_id=asset_id)
        if file_rows:
            asset_file_db.remove_batch_ids(db=db, ids=[item.id for item in file_rows])

        dataset_asset_db.remove(db=db, id=asset_id)
        self._normalize_query_entry_assets(db=db, version_id=version_id)
        return {"deleted": True, "item": payload}

    def list_asset_files(self, db, asset_id, user=None):
        asset_obj = self._ensure_asset_read_access(db=db, asset_id=asset_id, user=user)
        file_rows = self._list_asset_file_rows(db=db, asset_id=asset_id)
        return {
            "asset_id": asset_id,
            "version_id": asset_obj.dataset_version_id,
            "dataset_id": None,
            "items": [self._build_asset_file_payload(item) for item in file_rows],
        }

    def get_asset_file(self, db, asset_file_id, user=None):
        file_obj = self._ensure_asset_file_read_access(db=db, asset_file_id=asset_file_id, user=user)
        return self._build_asset_file_payload(file_obj)

    def register_asset_file(self, db, request_data, user):
        asset_obj = self._ensure_asset_write_access(db=db, asset_id=request_data.asset_id, user=user)
        self._validate_local_file_exists(request_data.local_path)
        file_obj = self._ensure_asset_file_record(
            db=db,
            asset_obj=asset_obj,
            file_role=request_data.file_role,
            local_path=request_data.local_path,
            file_format=request_data.file_format,
            asset_file_type_code=request_data.asset_file_type_code,
            index_of_file_id=request_data.index_of_file_id,
            status=request_data.status or "active",
            meta_json=request_data.meta_json,
        )
        registry_row, _resolved_file_format = self._validate_asset_file_registry_binding(
            db=db,
            asset_type=asset_obj.asset_type,
            file_role=file_obj.file_role,
            file_format=file_obj.file_format,
            local_path=file_obj.local_path,
            asset_file_type_code=getattr(file_obj, "asset_file_type_code", None),
        )
        if self._should_sync_asset_primary_profile(db=db, asset_obj=asset_obj, registry_row=registry_row, file_role=request_data.file_role):
            self._update_db_obj(
                db,
                asset_obj,
                file_format=file_obj.file_format or asset_obj.file_format,
                query_engine=asset_obj.query_engine or FILE_TYPE_QUERY_ENGINES.get(
                    (file_obj.file_format or "").lower(),
                    "file",
                ),
                update_time=self._now(),
            )
            asset_obj = dataset_asset_db.get(db=db, id=asset_obj.id)
            self._maybe_rebuild_functional_annotation_index(db=db, asset_obj=asset_obj)
            self._maybe_rebuild_phenome_index(db=db, asset_obj=asset_obj)
        return self._build_asset_file_payload(file_obj)

    def update_asset_file(self, db, asset_file_id, request_data, user):
        file_obj = self._ensure_asset_file_write_access(db=db, asset_file_id=asset_file_id, user=user)
        asset_obj = dataset_asset_db.get(db=db, id=file_obj.dataset_asset_id)
        update_data = {"update_time": self._now()}
        next_file_role = request_data.file_role if request_data.file_role is not None else file_obj.file_role
        next_local_path = request_data.local_path if request_data.local_path is not None else file_obj.local_path
        next_file_format = request_data.file_format
        next_asset_file_type_code = (
            request_data.asset_file_type_code
            if request_data.asset_file_type_code is not None
            else getattr(file_obj, "asset_file_type_code", None)
        )
        if next_file_format is None:
            next_file_format = self._guess_file_suffix(next_local_path) if request_data.local_path is not None else file_obj.file_format
        # Only validate registry binding when changing file-related fields
        registry_row = None
        normalized_file_format = next_file_format
        has_registry_change = (
            request_data.file_role is not None
            or request_data.file_format is not None
            or request_data.asset_file_type_code is not None
            or request_data.local_path is not None
        )
        if has_registry_change:
            registry_row, normalized_file_format = self._validate_asset_file_registry_binding(
                db=db,
                asset_type=asset_obj.asset_type,
                file_role=next_file_role,
                file_format=next_file_format,
                local_path=next_local_path,
                asset_file_type_code=next_asset_file_type_code,
            )
        for field in [
            "asset_file_type_code",
            "file_role",
            "storage_uri",
            "file_format",
            "mime_type",
            "checksum_type",
            "checksum_value",
            "compress_type",
            "index_of_file_id",
            "status",
            "meta_json",
            "is_downloadable",
        ]:
            value = getattr(request_data, field, None)
            if value is not None:
                if field == "file_role":
                    value = self._normalize_file_role(value)
                if field == "file_format":
                    value = normalized_file_format
                if field == "asset_file_type_code":
                    value = registry_row.code if registry_row else value
                update_data[field] = value
        if request_data.local_path is not None:
            self._validate_local_file_exists(request_data.local_path)
            update_data["local_path"] = request_data.local_path
            update_data["storage_uri"] = request_data.storage_uri or self._to_storage_uri(request_data.local_path)
            update_data["file_name"] = Path(request_data.local_path).name
            update_data["file_size"] = os.path.getsize(request_data.local_path)
            update_data["file_format"] = normalized_file_format
        file_obj = self._update_db_obj(db, file_obj, **update_data)
        if self._should_sync_asset_primary_profile(db=db, asset_obj=asset_obj, registry_row=registry_row, file_role=file_obj.file_role):
            self._update_db_obj(
                db,
                asset_obj,
                file_format=file_obj.file_format or asset_obj.file_format,
                update_time=self._now(),
            )
            self._maybe_rebuild_functional_annotation_index(db=db, asset_obj=asset_obj)
            self._maybe_rebuild_phenome_index(db=db, asset_obj=asset_obj)
        return self._build_asset_file_payload(file_obj)

    def delete_asset_file(self, db, asset_file_id, user):
        file_obj = self._ensure_asset_file_write_access(db=db, asset_file_id=asset_file_id, user=user)
        asset_obj = dataset_asset_db.get(db=db, id=file_obj.dataset_asset_id)
        referenced_rows = asset_file_db.get_data(db=db, filters={"index_of_file_id": asset_file_id})
        if referenced_rows:
            raise HTTPException(
                status_code=400,
                detail="asset file is referenced by index files; remove dependent files first",
            )
        payload = self._build_asset_file_payload(file_obj)
        registry_row, _resolved_file_format = self._validate_asset_file_registry_binding(
            db=db,
            asset_type=asset_obj.asset_type,
            file_role=file_obj.file_role,
            file_format=file_obj.file_format,
            local_path=file_obj.local_path,
            asset_file_type_code=getattr(file_obj, "asset_file_type_code", None),
        )
        if self._should_sync_asset_primary_profile(db=db, asset_obj=asset_obj, registry_row=registry_row, file_role=file_obj.file_role):
            self._clear_functional_annotation_index(db=db, asset_obj=asset_obj)
            self._clear_phenome_index(db=db, asset_obj=asset_obj)
        asset_file_db.remove(db=db, id=asset_file_id)
        return {"deleted": True, "item": payload}

    def list_dataset_lineage(self, db, dataset_id=None, version_id=None, limit=50, user=None):
        if dataset_id is not None:
            self._ensure_dataset_read_access(db=db, dataset_id=dataset_id, user=user)
        if version_id is not None:
            version_obj = self._ensure_version_read_access(db=db, version_id=version_id, user=user)
            if dataset_id is None:
                dataset_id = version_obj.dataset_id
        lineage_rows = dataset_lineage_edge_db.get_data(db=db, filters={})
        if dataset_id is not None:
            matched_rows = []
            for item in lineage_rows:
                src_version = dataset_version_db.get_one(db=db, id=item.src_dataset_version_id) if item.src_dataset_version_id else None
                dst_version = dataset_version_db.get_one(db=db, id=item.dst_dataset_version_id) if item.dst_dataset_version_id else None
                if (src_version and src_version.dataset_id == dataset_id) or (dst_version and dst_version.dataset_id == dataset_id):
                    matched_rows.append(item)
            lineage_rows = matched_rows
        if version_id is not None:
            lineage_rows = [
                item
                for item in lineage_rows
                if item.src_dataset_version_id == version_id or item.dst_dataset_version_id == version_id
            ]
        if user and not self._is_platform_admin(user):
            lineage_rows = [
                item
                for item in lineage_rows
                if self._can_access_lineage(db=db, lineage_obj=item, user=user)
            ]
        lineage_rows = sorted(lineage_rows, key=lambda item: item.id, reverse=True)[:limit]
        return {
            "dataset_id": dataset_id,
            "version_id": version_id,
            "items": [self._build_lineage_payload(db=db, lineage_obj=item) for item in lineage_rows],
        }

    def create_dataset_lineage(self, db, request_data, user):
        relation_type = request_data.relation_type
        if relation_type not in self.VALID_RELATION_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid relation_type: '{relation_type}'. Must be one of: {sorted(self.VALID_RELATION_TYPES)}",
            )
        src_version = self._ensure_version_write_access(db=db, version_id=request_data.src_version_id, user=user)
        dst_version = self._ensure_version_write_access(db=db, version_id=request_data.dst_version_id, user=user)
        if request_data.src_asset_id:
            self._ensure_asset_write_access(db=db, asset_id=request_data.src_asset_id, user=user)
        if request_data.dst_asset_id:
            self._ensure_asset_write_access(db=db, asset_id=request_data.dst_asset_id, user=user)
        lineage_obj = dataset_lineage_edge_db.create_one(
            db=db,
            obj_in={
                "dataset_id": src_version.dataset_id,
                "src_dataset_version_id": request_data.src_version_id,
                "src_asset_id": request_data.src_asset_id,
                "dst_dataset_version_id": request_data.dst_version_id,
                "dst_asset_id": request_data.dst_asset_id,
                "relation_type": request_data.relation_type,
                "detail_json": request_data.detail_json,
                "create_user_id": user.id,
                "create_time": self._now(),
            },
        )
        return self._build_lineage_payload(db=db, lineage_obj=lineage_obj)

    def delete_dataset_lineage(self, db, lineage_id, user):
        lineage_obj = dataset_lineage_edge_db.get(db=db, id=lineage_id)
        self._ensure_lineage_write_access(db=db, lineage_obj=lineage_obj, user=user)
        payload = self._build_lineage_payload(db=db, lineage_obj=lineage_obj)
        dataset_lineage_edge_db.remove(db=db, id=lineage_id)
        return {"deleted": True, "item": payload}

    def get_options(self, db, request_data, user=None):
        dataset_type_filter = None
        if request_data.dataset_type:
            dataset_type_filter, _dataset_kind = self._require_dataset_kind_code(
                db=db,
                dataset_type=request_data.dataset_type,
                active_only=False,
            )
        filters = {}
        filters_exp = []
        database_ids = []
        if request_data.project_id:
            database_ids = [
                item.dataset_id
                for item in dataset_legacy_bridge.list_project_links_by_project(db=db, project_id=request_data.project_id)
            ]
        if database_ids:
            filters_exp.append({"name": "id", "exp": "contain", "value": database_ids})
        elif request_data.project_id:
            filters_exp.append({"name": "id", "exp": "contain", "value": [-1]})
        if request_data.dataset_id:
            filters["id"] = request_data.dataset_id
        if request_data.name:
            filters_exp.append({"name": "name", "exp": "like", "value": request_data.name})

        query_page = request_data.page if not (user and not self._is_platform_admin(user)) else 0
        query_size = request_data.size if not (user and not self._is_platform_admin(user)) else 0

        page_obj = dataset_legacy_bridge.list_databases(
            db=db,
            page=query_page,
            size=query_size,
            filters=filters,
            filters_exp=filters_exp,
            sort="-id",
        )

        options = []
        for database_obj in page_obj["dataList"]:
            try:
                if user and not self._can_access_dataset(db=db, database_obj=database_obj, user=user):
                    continue
                dataset_payload = self.build_dataset_payload(db=db, database_obj=database_obj)
                current_version = self.ensure_current_version(db=db, dataset_payload=dataset_payload)
                dataset_payload = self._apply_version_to_dataset_payload(
                    db=db,
                    dataset_payload=dataset_payload,
                    version_obj=current_version,
                )
                dataset_payload = self._apply_assets_to_dataset_payload(
                    db=db,
                    dataset_payload=dataset_payload,
                    version_obj=current_version,
                )
                payload = {
                    "id": database_obj.id,
                    "name": dataset_payload["title"] or database_obj.name,
                    "title": dataset_payload["title"] or database_obj.name,
                    "dataset_code": dataset_payload["dataset_code"],
                    "dataset_type": dataset_payload["dataset_type"],
                    "lifecycle_state": dataset_payload["lifecycle_state"],
                    "visibility": dataset_payload["visibility"],
                    "version": dataset_payload.get("version"),
                    "file_path": self._resolve_dataset_primary_file_path(dataset_payload),
                    "file_format": dataset_payload["query_profile"]["file_format"],
                }
            except Exception:
                continue
            if dataset_type_filter and not self._dataset_type_matches(payload["dataset_type"], dataset_type_filter):
                continue
            if request_data.lifecycle_state and payload["lifecycle_state"] != request_data.lifecycle_state:
                continue
            if request_data.visibility and payload["visibility"] != request_data.visibility:
                continue
            options.append(payload)
        if user and not self._is_platform_admin(user) and request_data.page and request_data.size:
            start = (request_data.page - 1) * request_data.size
            end = start + request_data.size
            options = options[start:end]
        return options

    def upload_staging_file(self, db, upload_file, user, dataset_type=None, meta_json=None):
        source_name = upload_file.filename or "upload.bin"
        local_path = self._build_staging_local_path(source_name)
        with open(local_path, "wb") as output_handle:
            shutil.copyfileobj(upload_file.file, output_handle)
        resolved_dataset_type = self._resolve_dataset_type_from_path(local_path, dataset_type)
        resolved_dataset_type, _dataset_kind = self._require_dataset_kind_code(
            db=db,
            dataset_type=resolved_dataset_type,
            active_only=False,
        )
        now = self._now()
        staging_obj = dataset_staging_file_db.create_one(
            db=db,
            obj_in={
                "staging_code": f"stg-{uuid.uuid4().hex[:12]}",
                "source_name": source_name,
                "file_name": Path(local_path).name,
                "storage_uri": self._to_storage_uri(local_path),
                "local_path": local_path,
                "file_format": self._guess_file_suffix(local_path),
                "file_size": os.path.getsize(local_path),
                "dataset_type": resolved_dataset_type,
                "source_mode": "upload",
                "status": "uploaded",
                "linked_dataset_id": None,
                "create_user_id": user.id,
                "meta_json": meta_json,
                "create_time": now,
                "update_time": now,
            },
        )
        return self._build_dataset_staging_payload(staging_obj)

    def _normalize_scan_root_path(self, root_path):
        normalized = self._normalize_local_path(root_path)
        if not normalized:
            raise HTTPException(status_code=400, detail="root_path is required")
        return os.path.realpath(normalized)

    def _get_scan_browse_root(self):
        configured_root = settings.app_options.get("dataset_scan.browse_root")
        if configured_root:
            normalized_root = self._normalize_local_path(configured_root)
            if normalized_root:
                return os.path.realpath(normalized_root)
        # Safe fallback instead of /
        return os.path.realpath(f"{settings.RUNTIME_DIR}/dataset_scan")

    def _resolve_scan_browse_path(self, requested_path):
        browse_root = self._get_scan_browse_root()
        current_path = self._normalize_local_path(requested_path) if requested_path else browse_root
        current_path = os.path.realpath(current_path or browse_root)
        if not os.path.exists(current_path):
            raise HTTPException(status_code=404, detail=f"browse path not found: {current_path}")
        if not os.path.isdir(current_path):
            raise HTTPException(status_code=400, detail=f"browse path is not a directory: {current_path}")
        if browse_root != "/":
            try:
                common_path = os.path.commonpath([browse_root, current_path])
            except ValueError as error:
                raise HTTPException(status_code=400, detail="browse path is outside browse root") from error
            if common_path != browse_root:
                raise HTTPException(status_code=400, detail="browse path is outside browse root")
        return browse_root, current_path

    def _iter_scan_files(self, root_path, scan_recursive=True, include_hidden=False):
        scanned_dir_count = 0
        if scan_recursive:
            for current_dir, dir_names, file_names in os.walk(root_path, followlinks=False):
                scanned_dir_count += 1
                if not include_hidden:
                    dir_names[:] = [item for item in dir_names if not item.startswith(".")]
                    file_names = [item for item in file_names if not item.startswith(".")]
                for file_name in file_names:
                    if file_name in {".DS_Store", "Thumbs.db"}:
                        continue
                    absolute_path = os.path.realpath(os.path.join(current_dir, file_name))
                    if not os.path.isfile(absolute_path):
                        continue
                    yield scanned_dir_count, absolute_path
        else:
            scanned_dir_count = 1
            for entry in os.scandir(root_path):
                if not entry.is_file():
                    continue
                if not include_hidden and entry.name.startswith("."):
                    continue
                if entry.name in {".DS_Store", "Thumbs.db"}:
                    continue
                yield scanned_dir_count, os.path.realpath(entry.path)

    def _build_registered_dataset_file_paths(self, db):
        registered_paths = set()
        batch_size = 5000
        offset = 0
        while True:
            rows = (
                db.query(asset_file_db.model.local_path, asset_file_db.model.storage_uri)
                .filter(asset_file_db.model.local_path.isnot(None))
                .limit(batch_size)
                .offset(offset)
                .all()
            )
            if not rows:
                break
            for local_path, storage_uri in rows:
                for raw_path in [local_path, storage_uri]:
                    normalized_path = self._normalize_local_path(raw_path)
                    if not normalized_path:
                        continue
                    try:
                        registered_paths.add(os.path.realpath(normalized_path))
                    except OSError:
                        continue
            offset += batch_size

        offset = 0
        while True:
            rows = (
                db.query(dataset_version_db.model.file_path)
                .filter(dataset_version_db.model.file_path.isnot(None))
                .limit(batch_size)
                .offset(offset)
                .all()
            )
            if not rows:
                break
            for (file_path,) in rows:
                normalized_path = self._normalize_local_path(file_path)
                if not normalized_path:
                    continue
                try:
                    registered_paths.add(os.path.realpath(normalized_path))
                except OSError:
                    continue
            offset += batch_size

        return registered_paths

    def browse_scan_root_path(self, db, request_data, user):
        browse_root, current_path = self._resolve_scan_browse_path(request_data.path)
        entries = []
        files = []
        try:
            with os.scandir(current_path) as iterator:
                for entry in iterator:
                    if entry.is_dir(follow_symlinks=False):
                        if not request_data.show_hidden and entry.name.startswith("."):
                            continue
                        try:
                            stat_result = entry.stat(follow_symlinks=False)
                        except (FileNotFoundError, PermissionError):
                            continue
                        entries.append({
                            "name": entry.name,
                            "path": os.path.realpath(entry.path),
                            "is_dir": True,
                            "modified_time": int(stat_result.st_mtime),
                        })
                    elif entry.is_file(follow_symlinks=False):
                        if not request_data.show_hidden and entry.name.startswith("."):
                            continue
                        if entry.name in {".DS_Store", "Thumbs.db"}:
                            continue
                        try:
                            stat_result = entry.stat(follow_symlinks=False)
                        except (FileNotFoundError, PermissionError):
                            continue
                        file_path = os.path.realpath(entry.path)
                        file_format = self._guess_file_suffix(file_path)
                        files.append({
                            "name": entry.name,
                            "path": file_path,
                            "is_dir": False,
                            "size": stat_result.st_size,
                            "format": file_format,
                            "modified_time": int(stat_result.st_mtime),
                        })
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=f"permission denied: {current_path}") from error

        entries.sort(key=lambda item: item["name"].lower())
        files.sort(key=lambda item: item["name"].lower())

        parent_path = None
        if current_path != browse_root:
            next_parent = os.path.dirname(current_path.rstrip(os.sep)) or browse_root
            parent_path = os.path.realpath(next_parent)
            if browse_root != "/":
                try:
                    common_path = os.path.commonpath([browse_root, parent_path])
                except ValueError:
                    parent_path = browse_root
                else:
                    if common_path != browse_root:
                        parent_path = browse_root

        result = {
            "browse_root": browse_root,
            "current_path": current_path,
            "parent_path": parent_path,
            "entries": entries,
            "files": files,
        }
        if not settings.app_options.get("dataset_scan.browse_root"):
            result["warning"] = "browse_root not configured; using fallback path"
        return result

    def _upsert_scan_staging_file(self, db, *, root_obj, job_obj, absolute_path, user, registered_paths=None):
        normalized_path = self._normalize_local_path(absolute_path)
        try:
            real_path = os.path.realpath(normalized_path)
            if registered_paths and real_path in registered_paths:
                return None, False, True, False
            relative_path = os.path.relpath(normalized_path, root_obj.root_path)
            stat_result = os.stat(normalized_path)
        except (PermissionError, OSError):
            return None, False, False, False
        file_format = self._guess_file_suffix(normalized_path)
        dataset_type = self._resolve_dataset_type_from_path(normalized_path, None)
        now = self._now()
        existing = (
            db.query(dataset_staging_file_db.model)
            .filter(dataset_staging_file_db.model.local_path == normalized_path)
            .first()
        )
        payload = {
            "source_name": relative_path,
            "file_name": os.path.basename(normalized_path),
            "storage_uri": self._to_storage_uri(normalized_path),
            "local_path": normalized_path,
            "file_format": file_format,
            "file_size": stat_result.st_size,
            "dataset_type": dataset_type,
            "source_mode": "server_scan",
            "scan_root_id": root_obj.id,
            "scan_job_id": job_obj.id,
            "relative_path": relative_path,
            "file_mtime": int(stat_result.st_mtime),
            "status": "discovered",
            "linked_dataset_id": getattr(existing, "linked_dataset_id", None) if existing else None,
            "create_user_id": user.id,
            "meta_json": self._merge_meta_json(
                getattr(existing, "meta_json", None) if existing else None,
                {"scan_root_code": root_obj.root_code},
            ),
            "last_seen_time": now,
            "update_time": now,
        }
        if existing:
            file_changed = (
                int(getattr(existing, "file_size", 0) or 0) != int(stat_result.st_size)
                or int(getattr(existing, "file_mtime", 0) or 0) != int(stat_result.st_mtime)
            )
            payload["status"] = "changed" if file_changed else "seen"
            if not getattr(existing, "discover_time", None):
                payload["discover_time"] = now
            return self._update_db_obj(db, existing, **payload), False, False, file_changed
        payload["staging_code"] = f"stg-{uuid.uuid4().hex[:12]}"
        payload["discover_time"] = now
        payload["create_time"] = now
        staging_obj = dataset_staging_file_db.create_one(db=db, obj_in=payload)
        return staging_obj, True, False, False

    def _mark_missing_scan_staging_files(self, db, *, root_obj, seen_paths, now):
        missing_count = 0
        normalized_seen_paths = {self._normalize_local_path(item) for item in seen_paths if item}
        existing_rows = dataset_staging_file_db.get_data(db=db, filters={"scan_root_id": root_obj.id})
        for row in existing_rows:
            if getattr(row, "source_mode", None) != "server_scan":
                continue
            local_path = self._normalize_local_path(getattr(row, "local_path", None))
            if not local_path or local_path in normalized_seen_paths:
                continue
            if str(getattr(row, "status", "") or "") == "missing":
                continue
            self._update_db_obj(
                db,
                row,
                status="missing",
                update_time=now,
            )
            missing_count += 1
        return missing_count

    def _validate_staging_available(self, staging_obj):
        current_status = str(getattr(staging_obj, "status", "") or "").strip().lower()
        if current_status in {"missing", "deleted", "consumed", "registered"}:
            raise HTTPException(
                status_code=400,
                detail=f"staging file is not available: {getattr(staging_obj, 'id', None)}",
            )
        linked_dataset_id = getattr(staging_obj, "linked_dataset_id", None)
        if linked_dataset_id:
            raise HTTPException(
                status_code=400,
                detail=f"staging file is already linked to dataset: {getattr(staging_obj, 'id', None)}",
            )
        local_path = getattr(staging_obj, "local_path", None)
        if not local_path or not os.path.exists(local_path):
            raise HTTPException(
                status_code=400,
                detail=f"staging file not found: {getattr(staging_obj, 'id', None)}",
            )

    def validate_staging_files(self, staging_entries, declared_dataset_type=None):
        """Validate staging files before registration.

        Returns a list of error strings. Empty list means validation passed.
        """
        errors = []
        for entry in staging_entries:
            local_path = entry.get("local_path") or entry.get("path")
            if not local_path:
                errors.append(f"missing path for staging entry: {entry}")
                continue
            if not os.path.exists(local_path):
                errors.append(f"file not found: {local_path}")
                continue
            if not os.access(local_path, os.R_OK):
                errors.append(f"file not readable: {local_path}")
                continue

        if declared_dataset_type:
            for entry in staging_entries:
                local_path = entry.get("local_path") or entry.get("path")
                if not local_path or not os.path.exists(local_path):
                    continue
                file_format = entry.get("file_format") or self._guess_file_suffix(local_path)
                inferred_type = self._resolve_dataset_type_from_path(local_path, None)
                if inferred_type != "generic" and inferred_type != declared_dataset_type:
                    errors.append(
                        f"format mismatch: {os.path.basename(local_path)} appears to be "
                        f"'{inferred_type}' but staging declares '{declared_dataset_type}'"
                    )

        return errors

    def register_staging_files(self, db, request_data, user):
        """Register staging files directly as a new dataset."""
        staging_file_ids = request_data.staging_file_ids
        dataset_type = request_data.dataset_type or "generic"
        dataset_type, _dataset_kind = self._require_dataset_kind_code(
            db=db, dataset_type=dataset_type, active_only=False,
        )

        # 1. Load and validate all staging files
        staging_objs = []
        for sid in staging_file_ids:
            staging_obj = dataset_staging_file_db.get(db=db, id=sid)
            self._validate_staging_available(staging_obj)
            staging_objs.append(staging_obj)

        primary_staging = staging_objs[0]
        dataset_name = request_data.name or self._guess_name_from_path(
            getattr(primary_staging, "local_path", "")
        )

        # 2. Validate the staging file set
        staging_entries = [
            {
                "local_path": getattr(s, "local_path", None),
                "file_format": self._staging_file_format(s),
            }
            for s in staging_objs
        ]
        validation_errors = self.validate_staging_files(staging_entries, declared_dataset_type=dataset_type)
        if validation_errors:
            raise HTTPException(
                status_code=400,
                detail=f"validation failed: {'; '.join(validation_errors)}",
            )

        # 3. Create DatasetRegistry via register_dataset_source
        dataset_payload = self.register_dataset_source(
            db=db,
            request_data=SimpleNamespace(
                file_path=getattr(primary_staging, "local_path", ""),
                name=dataset_name,
                dataset_type=dataset_type,
                remark=getattr(request_data, "remark", None),
                dry_run=False,
                team_id=getattr(request_data, "team_id", 0) or 0,
                project_id=getattr(request_data, "project_id", 0) or 0,
            ),
            user=user,
        )
        dataset_id = dataset_payload["id"]

        # 4. Set organism on registry
        registry_obj = dataset_registry_db.get_filter(db=db, filters={"id": dataset_id})
        if registry_obj and getattr(request_data, "organism", None):
            dataset_registry_db.update_one(
                db=db, db_obj=registry_obj,
                obj_in={"organism": request_data.organism, "update_time": self._now()},
            )

        # 5. Sync current version
        version_obj = self.sync_current_version_from_dataset_id(db=db, dataset_id=dataset_id)

        # 6. Create assets and files from staging files
        asset_payload_cache = {}
        for staging_obj in staging_objs:
            asset_type, asset_file_type_code = self._infer_asset_mapping(
                staging_obj, dataset_type, db=db,
            )
            file_format = self._staging_file_format(staging_obj)
            file_role = self._resolve_file_role(
                db=db, staging_obj=staging_obj, dataset_type=dataset_type,
            )

            cache_key = asset_type
            asset_payload = asset_payload_cache.get(cache_key)
            if not asset_payload:
                asset_payload = self._ensure_asset(
                    db=db,
                    version_obj=version_obj,
                    asset_type=asset_type,
                    file_format=file_format,
                    is_query_entry=(asset_type == self._default_asset_type(dataset_type, db=db)),
                    user=user,
                )
                asset_payload_cache[cache_key] = asset_payload

            asset_files = self.list_asset_files(db=db, asset_id=asset_payload["id"], user=user)["items"]
            primary_asset_file = next(
                (item for item in asset_files if item["file_role"] == "primary"), None
            )
            self.register_asset_file(
                db=db,
                request_data=SimpleNamespace(
                    asset_id=asset_payload["id"],
                    file_role=file_role,
                    asset_file_type_code=asset_file_type_code,
                    local_path=getattr(staging_obj, "local_path", ""),
                    file_format=file_format,
                    index_of_file_id=(
                        primary_asset_file["id"]
                        if file_role == "index" and primary_asset_file
                        else None
                    ),
                    status="active",
                    meta_json=None,
                ),
                user=user,
            )

        # 7. Mark staging files as registered
        now = self._now()
        for staging_obj in staging_objs:
            dataset_staging_file_db.update_one(
                db=db, db_obj=staging_obj,
                obj_in={
                    "status": "registered",
                    "linked_dataset_id": dataset_id,
                    "update_time": now,
                },
            )

        return self.get_dataset(db=db, dataset_id=dataset_id)

    def list_staging_files(self, db, request_data):
        rows = dataset_staging_file_db.get_data(db=db, filters={})
        filtered_rows = []
        keyword = str(request_data.keyword or "").strip().lower()
        dataset_type_filter = None
        if request_data.dataset_type:
            dataset_type_filter, _dataset_kind = self._require_dataset_kind_code(
                db=db,
                dataset_type=request_data.dataset_type,
                active_only=False,
            )
        for row in rows:
            if request_data.status and row.status != request_data.status:
                continue
            if request_data.source_mode and getattr(row, "source_mode", None) != request_data.source_mode:
                continue
            if request_data.scan_root_id and getattr(row, "scan_root_id", None) != request_data.scan_root_id:
                continue
            if dataset_type_filter and not self._dataset_type_matches(row.dataset_type, dataset_type_filter):
                continue
            if keyword:
                haystack = " ".join(
                    [
                        str(row.staging_code or ""),
                        str(row.source_name or ""),
                        str(row.file_name or ""),
                        str(row.local_path or ""),
                        str(getattr(row, "relative_path", "") or ""),
                    ]
                ).lower()
                if keyword not in haystack:
                    continue
            filtered_rows.append(row)
        view_mode = str(getattr(request_data, "view_mode", "flat") or "flat").strip().lower()
        if view_mode == "directory":
            # Load scan_root_rows for path context
            scan_root_rows = dataset_scan_root_db.get_data(db=db, filters={})
            return self._build_directory_view(filtered_rows, scan_root_rows)
        items = [self._build_dataset_staging_payload(row) for row in filtered_rows]
        items = sorted(items, key=lambda item: item["id"], reverse=True)
        total = len(items)
        if request_data.page and request_data.size:
            start = (request_data.page - 1) * request_data.size
            end = start + request_data.size
            items = items[start:end]
        return {"dataList": items, "total": total}

    def _build_directory_view(self, staging_items, scan_root_rows=None):
        """Build a file-level tree from staging files grouped by scan root.

        Directory nodes: name, path, is_dir=True, file_count, children.
        File nodes: name, path, is_dir=False, size, format, staging_id.
        """
        scan_root_paths = {}
        if scan_root_rows:
            for root in scan_root_rows:
                scan_root_paths[root.id] = os.path.realpath(
                    self._normalize_local_path(root.root_path)
                )

        items_by_root: dict = {}
        orphan_files = []

        for item in staging_items:
            local_path = self._normalize_local_path(getattr(item, "local_path", None))
            if not local_path:
                continue

            real_path = os.path.realpath(local_path)
            root_id = getattr(item, "scan_root_id", None)
            root_path = scan_root_paths.get(root_id) if root_id else None

            if not root_path:
                orphan_files.append(self._build_dataset_staging_payload(item))
                continue

            root_real = os.path.realpath(root_path) + os.sep
            if not real_path.startswith(root_real):
                orphan_files.append(self._build_dataset_staging_payload(item))
                continue

            relative = real_path[len(root_real):]
            parts = relative.split(os.sep)
            if len(parts) == 1:
                orphan_files.append(self._build_dataset_staging_payload(item))
                continue

            if root_id not in items_by_root:
                items_by_root[root_id] = []
            # Store: (path_parts, file_name, size, format, staging_id)
            file_size = getattr(item, "file_size", None) or 0
            file_format = getattr(item, "file_format", "") or ""
            staging_id = getattr(item, "id", 0) or 0
            items_by_root[root_id].append((parts[:-1], parts[-1], file_size, file_format, staging_id))

        tree_roots = []
        for root_id, file_entries in items_by_root.items():
            root_path = scan_root_paths.get(root_id)
            if not root_path:
                continue
            root_real = os.path.realpath(root_path)

            # Build nested dict tree[dir_component] = {"__files": [...], subdir: {...}}
            tree: dict = {}
            for dir_parts, file_name, file_size, file_format, staging_id in file_entries:
                node = tree
                for part in dir_parts:
                    if part not in node:
                        node[part] = {}
                    node = node[part]
                node.setdefault("__files", [])
                node["__files"].append({
                    "name": file_name,
                    "size": file_size,
                    "format": file_format,
                    "staging_id": staging_id,
                })

            def build_tree_nodes(parent_path, subtree):
                nodes = []
                # Directories first
                for name, content in sorted(subtree.items(), key=lambda kv: kv[0].lower()):
                    if name.startswith("__"):
                        continue
                    child_path = os.path.join(parent_path, name) + os.sep
                    file_list = content.get("__files", [])
                    children = build_tree_nodes(child_path, content)
                    total_count = len(file_list) + sum(
                        c.get("_total_files", c["file_count"]) if c.get("is_dir") else 1
                        for c in children
                    )
                    nodes.append({
                        "name": name,
                        "path": child_path,
                        "is_dir": True,
                        "file_count": total_count,
                        "children": [
                            *_build_file_nodes(child_path, file_list),
                            *children,
                        ],
                        "_total_files": total_count,
                    })
                return nodes

            def _build_file_nodes(parent_path, file_list):
                return sorted([
                    {
                        "name": f["name"],
                        "path": os.path.join(parent_path, f["name"]),
                        "is_dir": False,
                        "size": f["size"],
                        "format": f["format"],
                        "staging_id": f["staging_id"],
                    }
                    for f in file_list
                ], key=lambda x: x["name"].lower())

            tree_roots.append({
                "scan_root_id": root_id,
                "root_path": root_real + os.sep,
                "root_name": os.path.basename(root_real) or (root_real.rstrip(os.sep) or root_real),
                "children": build_tree_nodes(root_real + os.sep, tree),
            })

        # Strip internal _total_files from nodes
        def strip_internal(node):
            node.pop("_total_files", None)
            if node.get("children"):
                for child in node["children"]:
                    strip_internal(child)

        for t in tree_roots:
            for child in t["children"]:
                strip_internal(child)

        return {
            "trees": tree_roots,
            "orphan_files": orphan_files,
        }

    def get_staging_file(self, db, staging_id):
        staging_obj = dataset_staging_file_db.get(db=db, id=staging_id)
        return self._build_dataset_staging_payload(staging_obj)

    def delete_staging_file(self, db, staging_id, user):
        staging_obj = dataset_staging_file_db.get(db=db, id=staging_id)
        payload = self._build_dataset_staging_payload(staging_obj)
        source_mode = getattr(staging_obj, "source_mode", None) or "upload"
        should_delete_local_file = source_mode == "upload"
        if should_delete_local_file and staging_obj.local_path and os.path.exists(staging_obj.local_path):
            os.remove(staging_obj.local_path)
        dataset_staging_file_db.remove(db=db, id=staging_id)
        return {"deleted": True, "item": payload}

    def register_dataset_from_staging(self, db, staging_id, request_data, user):
        staging_obj = dataset_staging_file_db.get(db=db, id=staging_id)
        if staging_obj.status == "deleted":
            raise HTTPException(status_code=400, detail="staging file is deleted")
        if not staging_obj.local_path or not os.path.exists(staging_obj.local_path):
            raise HTTPException(status_code=404, detail=f"staging file not found: {staging_obj.local_path}")
        result = self.register_dataset_source(
            db=db,
            request_data=type(
                "DatasetRegisterFromStaging",
                (),
                {
                    "file_path": staging_obj.local_path,
                    "name": request_data.name,
                    "dataset_type": request_data.dataset_type or staging_obj.dataset_type,
                    "remark": request_data.remark,
                    "dry_run": request_data.dry_run,
                    "team_id": getattr(request_data, "team_id", 0) or 0,
                    "project_id": getattr(request_data, "project_id", 0) or 0,
                },
            )(),
            user=user,
        )
        if request_data.dry_run:
            preview = dict(result)
            preview["staging_file"] = self._build_dataset_staging_payload(staging_obj)
            return preview
        if not request_data.keep_staging_file:
            result = self._relocate_dataset_files_to_managed_storage(db=db, dataset_id=result["id"])
        update_data = {
            "status": "registered",
            "update_time": self._now(),
            "linked_dataset_id": result["id"],
        }
        if not request_data.keep_staging_file:
            update_data["status"] = "consumed"
            update_data["local_path"] = None
            update_data["storage_uri"] = None
        staging_obj = self._update_db_obj(db, staging_obj, **update_data)
        output = dict(result)
        output["staging_file"] = self._build_dataset_staging_payload(staging_obj)
        return output

    def list_scan_roots(self, db, request_data):
        rows = dataset_scan_root_db.get_data(db=db, filters={})
        keyword = str(request_data.keyword or "").strip().lower()
        items = []
        for row in rows:
            if request_data.is_active is not None and bool(row.is_active) != bool(request_data.is_active):
                continue
            if keyword:
                haystack = " ".join(
                    [
                        str(row.root_code or ""),
                        str(row.name or ""),
                        str(row.root_path or ""),
                        str(row.description or ""),
                    ]
                ).lower()
                if keyword not in haystack:
                    continue
            items.append(self._build_scan_root_payload(row))
        items = sorted(items, key=lambda item: item["id"], reverse=True)
        total = len(items)
        if request_data.page and request_data.size:
            start = (request_data.page - 1) * request_data.size
            end = start + request_data.size
            items = items[start:end]
        return {"dataList": items, "total": total}

    def get_scan_root(self, db, root_id):
        root_obj = dataset_scan_root_db.get(db=db, id=root_id)
        return self._build_scan_root_payload(root_obj)

    def create_scan_root(self, db, request_data, user):
        normalized_root_path = self._normalize_scan_root_path(request_data.root_path)
        if not os.path.isdir(normalized_root_path):
            raise HTTPException(status_code=400, detail=f"scan root does not exist: {normalized_root_path}")
        existing = (
            db.query(dataset_scan_root_db.model)
            .filter(dataset_scan_root_db.model.root_path == normalized_root_path)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail=f"scan root already exists: {normalized_root_path}")
        now = self._now()
        root_obj = dataset_scan_root_db.create_one(
            db=db,
            obj_in={
                "root_code": f"scan-{uuid.uuid4().hex[:12]}",
                "name": request_data.name.strip(),
                "root_path": normalized_root_path,
                "description": request_data.description,
                "scan_recursive": 1 if request_data.scan_recursive else 0,
                "include_hidden": 1 if request_data.include_hidden else 0,
                "is_active": True if request_data.is_active else 0,
                "last_scan_time": None,
                "create_user_id": user.id,
                "create_time": now,
                "update_time": now,
            },
        )
        return self._build_scan_root_payload(root_obj)

    def update_scan_root(self, db, root_id, request_data, user):
        root_obj = dataset_scan_root_db.get(db=db, id=root_id)
        update_data = {"update_time": self._now()}
        if request_data.name is not None:
            update_data["name"] = request_data.name.strip()
        if request_data.root_path is not None:
            normalized_root_path = self._normalize_scan_root_path(request_data.root_path)
            if not os.path.isdir(normalized_root_path):
                raise HTTPException(status_code=400, detail=f"scan root does not exist: {normalized_root_path}")
            duplicated = (
                db.query(dataset_scan_root_db.model)
                .filter(
                    dataset_scan_root_db.model.root_path == normalized_root_path,
                    dataset_scan_root_db.model.id != root_obj.id,
                )
                .first()
            )
            if duplicated:
                raise HTTPException(status_code=400, detail=f"scan root already exists: {normalized_root_path}")
            update_data["root_path"] = normalized_root_path
        if request_data.description is not None:
            update_data["description"] = request_data.description
        if request_data.scan_recursive is not None:
            update_data["scan_recursive"] = 1 if request_data.scan_recursive else 0
        if request_data.include_hidden is not None:
            update_data["include_hidden"] = 1 if request_data.include_hidden else 0
        if request_data.is_active is not None:
            update_data["is_active"] = 1 if request_data.is_active else 0
        root_obj = self._update_db_obj(db, root_obj, **update_data)
        return self._build_scan_root_payload(root_obj)

    def delete_scan_root(self, db, root_id, user):
        root_obj = dataset_scan_root_db.get(db=db, id=root_id)
        payload = self._build_scan_root_payload(root_obj)
        dataset_scan_root_db.remove(db=db, id=root_id)
        return {"deleted": True, "item": payload}

    def list_scan_jobs(self, db, request_data):
        rows = dataset_scan_job_db.get_data(db=db, filters={})
        items = []
        for row in rows:
            if request_data.root_id and row.root_id != request_data.root_id:
                continue
            items.append(self._build_scan_job_payload(row))
        items = sorted(items, key=lambda item: item["id"], reverse=True)
        total = len(items)
        if request_data.page and request_data.size:
            start = (request_data.page - 1) * request_data.size
            end = start + request_data.size
            items = items[start:end]
        return {"dataList": items, "total": total}

    def run_scan_root(self, db, root_id, user):
        root_obj = dataset_scan_root_db.get(db=db, id=root_id)
        if not bool(root_obj.is_active):
            raise HTTPException(status_code=400, detail="scan root is inactive")
        if not os.path.isdir(root_obj.root_path):
            raise HTTPException(status_code=400, detail=f"scan root does not exist: {root_obj.root_path}")

        # Concurrency control: prevent duplicate running jobs for the same root
        running_job = (
            db.query(dataset_scan_job_db.model)
            .filter(
                dataset_scan_job_db.model.root_id == root_id,
                dataset_scan_job_db.model.status == "running",
            )
            .first()
        )
        if running_job:
            raise HTTPException(
                status_code=409,
                detail=f"scan root {root_id} already has a running job: {running_job.job_code}",
            )

        now = self._now()
        job_obj = dataset_scan_job_db.create_one(
            db=db,
            obj_in={
                "root_id": root_obj.id,
                "job_code": f"scan-job-{uuid.uuid4().hex[:12]}",
                "status": "running",
                "scanned_dir_count": 0,
                "scanned_file_count": 0,
                "staged_file_count": 0,
                "skipped_file_count": 0,
                "changed_file_count": 0,
                "missing_file_count": 0,
                "skipped_registered_count": 0,
                "error_message": None,
                "start_time": now,
                "finish_time": None,
                "create_user_id": user.id,
                "create_time": now,
                "update_time": now,
            },
        )
        scanned_dir_count = 0
        scanned_file_count = 0
        staged_file_count = 0
        skipped_file_count = 0
        changed_file_count = 0
        missing_file_count = 0
        skipped_registered_count = 0
        registered_paths = self._build_registered_dataset_file_paths(db=db)
        seen_paths = set()
        try:
            for scanned_dir_count, absolute_path in self._iter_scan_files(
                root_obj.root_path,
                scan_recursive=bool(root_obj.scan_recursive),
                include_hidden=bool(root_obj.include_hidden),
            ):
                scanned_file_count += 1
                seen_paths.add(self._normalize_local_path(absolute_path))
                _staging_obj, created, skipped_registered, file_changed = self._upsert_scan_staging_file(
                    db=db,
                    root_obj=root_obj,
                    job_obj=job_obj,
                    absolute_path=absolute_path,
                    user=user,
                    registered_paths=registered_paths,
                )
                if skipped_registered:
                    skipped_registered_count += 1
                    skipped_file_count += 1
                elif created:
                    staged_file_count += 1
                else:
                    if file_changed:
                        changed_file_count += 1
                    skipped_file_count += 1
            finished_at = self._now()
            missing_file_count = self._mark_missing_scan_staging_files(
                db=db,
                root_obj=root_obj,
                seen_paths=seen_paths,
                now=finished_at,
            )
            job_obj = self._update_db_obj(
                db,
                job_obj,
                status="success",
                scanned_dir_count=scanned_dir_count,
                scanned_file_count=scanned_file_count,
                staged_file_count=staged_file_count,
                skipped_file_count=skipped_file_count,
                changed_file_count=changed_file_count,
                missing_file_count=missing_file_count,
                skipped_registered_count=skipped_registered_count,
                finish_time=finished_at,
                update_time=finished_at,
            )
            self._update_db_obj(db, root_obj, last_scan_time=finished_at, update_time=finished_at)
            return {
                "job": self._build_scan_job_payload(job_obj),
                "root": self._build_scan_root_payload(root_obj),
            }
        except (OSError, IOError, PermissionError, HTTPException) as error:
            failed_at = self._now()
            job_obj = self._update_db_obj(
                db,
                job_obj,
                status="failed",
                scanned_dir_count=scanned_dir_count,
                scanned_file_count=scanned_file_count,
                staged_file_count=staged_file_count,
                skipped_file_count=skipped_file_count,
                changed_file_count=changed_file_count,
                missing_file_count=missing_file_count,
                skipped_registered_count=skipped_registered_count,
                error_message=str(error),
                finish_time=failed_at,
                update_time=failed_at,
            )
            raise HTTPException(
                status_code=500,
                detail=f"scan root failed: {root_obj.root_path}: {error}",
            ) from error

    def list_dataset_kind_registry(self, db, request_data):
        rows = dataset_kind_registry_db.get_data(db=db, filters={})
        items = []
        keyword = str(request_data.keyword or "").strip().lower()
        code_filter = self._normalize_registry_code(request_data.code, "code") if request_data.code else None
        base_code_filter = self._normalize_registry_code(request_data.base_code, "base_code") if request_data.base_code else None
        for row in rows:
            if code_filter and row.code != code_filter:
                continue
            if base_code_filter and row.base_code != base_code_filter:
                continue
            if request_data.is_active is not None and bool(row.is_active) != bool(request_data.is_active):
                continue
            if keyword:
                haystack = " ".join(
                    [
                        str(row.code or ""),
                        str(row.base_code or ""),
                        str(row.name or ""),
                        str(row.description or ""),
                    ]
                ).lower()
                if keyword not in haystack:
                    continue
            items.append(self._build_dataset_kind_registry_payload(row))
        items = sorted(items, key=lambda item: (item["sort_order"] or 0, item["id"]))
        total = len(items)
        if request_data.page and request_data.size:
            start = (request_data.page - 1) * request_data.size
            end = start + request_data.size
            items = items[start:end]
        return {"dataList": items, "total": total}

    def get_dataset_kind_options(self, db, request_data):
        rows = dataset_kind_registry_db.get_data(db=db, filters={})
        options = []
        for row in rows:
            if request_data.active_only and not row.is_active:
                continue
            options.append(
                {
                    "id": row.id,
                    "code": row.code,
                    "name": row.name,
                    "base_code": row.base_code,
                    "description": row.description,
                    "is_active": bool(row.is_active),
                    "is_system": bool(row.is_system),
                    "sort_order": row.sort_order,
                    "label": row.name,
                    "value": row.code,
                }
            )
        return sorted(options, key=lambda item: (item["sort_order"] or 0, item["id"]))

    def get_dataset_kind_registry(self, db, registry_id):
        registry_obj = dataset_kind_registry_db.get(db=db, id=registry_id)
        return self._build_dataset_kind_registry_payload(registry_obj)

    def _dataset_kind_in_use(self, db, code):
        if dataset_registry_db.get_filter(db=db, filters={"dataset_type": code}):
            return "dataset_registry"
        for row in asset_type_registry_db.get_data(db=db, filters={}):
            if code in self._canonicalize_dataset_type_list(self._parse_json_list(row.allowed_dataset_types)):
                return "asset_type_registry"
        return None

    def create_dataset_kind_registry(self, db, request_data, user):
        self._require_platform_admin(user, detail="only platform admin can manage dataset kind registry")
        now = self._now()
        code = self._normalize_registry_code(request_data.code, "code")
        base_code = self._normalize_registry_code(request_data.base_code, "base_code")
        existing = dataset_kind_registry_db.get_filter(db=db, filters={"code": code})
        if existing:
            raise HTTPException(status_code=400, detail=f"dataset_kind already exists: {code}")
        registry_obj = dataset_kind_registry_db.create_one(
            db=db,
            obj_in={
                "code": code,
                "base_code": base_code,
                "name": request_data.name,
                "description": request_data.description,
                "is_system": False,
                "is_active": True if request_data.is_active is None else (1 if request_data.is_active else 0),
                "sort_order": request_data.sort_order or 0,
                "meta_json": request_data.meta_json,
                "create_time": now,
                "update_time": now,
            },
        )
        return self._build_dataset_kind_registry_payload(registry_obj)

    def update_dataset_kind_registry(self, db, registry_id, request_data, user):
        self._require_platform_admin(user, detail="only platform admin can manage dataset kind registry")
        registry_obj = dataset_kind_registry_db.get(db=db, id=registry_id)
        update_data = {"update_time": self._now()}
        if request_data.code is not None:
            new_code = self._normalize_registry_code(request_data.code, "code")
            if registry_obj.is_system and new_code != registry_obj.code:
                raise HTTPException(status_code=400, detail="system dataset_kind code cannot be changed")
            if new_code != registry_obj.code:
                usage = self._dataset_kind_in_use(db=db, code=registry_obj.code)
                if usage:
                    raise HTTPException(status_code=400, detail=f"dataset_kind is in use and code cannot be changed: {usage}")
                existing = dataset_kind_registry_db.get_filter(db=db, filters={"code": new_code})
                if existing and existing.id != registry_obj.id:
                    raise HTTPException(status_code=400, detail=f"dataset_kind already exists: {new_code}")
            update_data["code"] = new_code
        if request_data.base_code is not None:
            update_data["base_code"] = self._normalize_registry_code(request_data.base_code, "base_code")
        for field in ["name", "description", "sort_order", "meta_json"]:
            value = getattr(request_data, field, None)
            if value is not None:
                update_data[field] = value
        if request_data.is_active is not None:
            update_data["is_active"] = 1 if request_data.is_active else 0
        registry_obj = self._update_db_obj(db, registry_obj, **update_data)
        return self._build_dataset_kind_registry_payload(registry_obj)

    def delete_dataset_kind_registry(self, db, registry_id, user):
        self._require_platform_admin(user, detail="only platform admin can manage dataset kind registry")
        registry_obj = dataset_kind_registry_db.get(db=db, id=registry_id)
        if registry_obj.is_system:
            raise HTTPException(status_code=400, detail="system dataset_kind cannot be deleted")
        usage = self._dataset_kind_in_use(db=db, code=registry_obj.code)
        if usage:
            raise HTTPException(status_code=400, detail=f"dataset_kind is in use: {usage}")
        payload = self._build_dataset_kind_registry_payload(registry_obj)
        dataset_kind_registry_db.remove(db=db, id=registry_id)
        return {"deleted": True, "item": payload}

    def list_asset_type_registry(self, db, request_data):
        rows = asset_type_registry_db.get_data(db=db, filters={})
        items = []
        keyword = str(request_data.keyword or "").strip().lower()
        code_filter = self._normalize_registry_code(request_data.code, "code") if request_data.code else None
        base_code_filter = self._normalize_registry_code(request_data.base_code, "base_code") if request_data.base_code else None
        dataset_type_filter = None
        if request_data.dataset_type:
            dataset_type_filter, _dataset_kind = self._require_dataset_kind_code(
                db=db,
                dataset_type=request_data.dataset_type,
                active_only=False,
            )
        for row in rows:
            allowed_dataset_types = self._canonicalize_dataset_type_list(self._parse_json_list(row.allowed_dataset_types))
            if code_filter and row.code != code_filter:
                continue
            if base_code_filter and row.base_code != base_code_filter:
                continue
            if request_data.is_active is not None and bool(row.is_active) != bool(request_data.is_active):
                continue
            if dataset_type_filter and allowed_dataset_types and dataset_type_filter not in allowed_dataset_types:
                continue
            if keyword:
                haystack = " ".join(
                    [
                        str(row.code or ""),
                        str(row.base_code or ""),
                        str(row.name or ""),
                        str(row.description or ""),
                        " ".join(allowed_dataset_types),
                    ]
                ).lower()
                if keyword not in haystack:
                    continue
            items.append(self._build_asset_type_registry_payload(row))
        items = sorted(items, key=lambda item: (item["sort_order"] or 0, item["id"]))
        total = len(items)
        if request_data.page and request_data.size:
            start = (request_data.page - 1) * request_data.size
            end = start + request_data.size
            items = items[start:end]
        return {"dataList": items, "total": total}

    def get_asset_type_options(self, db, request_data):
        rows = asset_type_registry_db.get_data(db=db, filters={})
        dataset_type_filter = None
        if request_data.dataset_type:
            dataset_type_filter, _dataset_kind = self._require_dataset_kind_code(
                db=db,
                dataset_type=request_data.dataset_type,
                active_only=bool(request_data.active_only),
            )
        options = []
        for row in rows:
            allowed_dataset_types = self._canonicalize_dataset_type_list(self._parse_json_list(row.allowed_dataset_types))
            if request_data.active_only and not row.is_active:
                continue
            if dataset_type_filter and allowed_dataset_types and dataset_type_filter not in allowed_dataset_types:
                continue
            options.append(
                {
                    "id": row.id,
                    "code": row.code,
                    "name": row.name,
                    "base_code": row.base_code,
                    "description": row.description,
                    "allowed_dataset_types": allowed_dataset_types,
                    "is_active": bool(row.is_active),
                    "is_system": bool(row.is_system),
                    "sort_order": row.sort_order,
                    "label": row.name,
                    "value": row.code,
                }
            )
        return sorted(options, key=lambda item: (item["sort_order"] or 0, item["id"]))

    def get_asset_type_registry(self, db, registry_id):
        registry_obj = asset_type_registry_db.get(db=db, id=registry_id)
        return self._build_asset_type_registry_payload(registry_obj)

    def _asset_type_in_use(self, db, code):
        if dataset_asset_db.get_filter(db=db, filters={"asset_type": code}):
            return "dataset_asset"
        for row in asset_file_type_registry_db.get_data(db=db, filters={}):
            if code in self._canonicalize_asset_type_list(self._parse_json_list(row.allowed_asset_types)):
                return "asset_file_type_registry"
        return None

    def create_asset_type_registry(self, db, request_data, user):
        self._require_platform_admin(user, detail="only platform admin can manage asset type registry")
        now = self._now()
        code = self._normalize_registry_code(request_data.code, "code")
        base_code = self._normalize_registry_code(request_data.base_code, "base_code")
        existing = asset_type_registry_db.get_filter(db=db, filters={"code": code})
        if existing:
            raise HTTPException(status_code=400, detail=f"asset_type already exists: {code}")
        allowed_dataset_types = []
        for item in request_data.allowed_dataset_types or []:
            normalized_type, _dataset_kind = self._require_dataset_kind_code(db=db, dataset_type=item, active_only=False)
            if normalized_type not in allowed_dataset_types:
                allowed_dataset_types.append(normalized_type)
        registry_obj = asset_type_registry_db.create_one(
            db=db,
            obj_in={
                "code": code,
                "base_code": base_code,
                "name": request_data.name,
                "description": request_data.description,
                "allowed_dataset_types": self._encode_json_list(allowed_dataset_types),
                "is_system": False,
                "is_active": True if request_data.is_active is None else (1 if request_data.is_active else 0),
                "sort_order": request_data.sort_order or 0,
                "meta_json": request_data.meta_json,
                "create_time": now,
                "update_time": now,
            },
        )
        return self._build_asset_type_registry_payload(registry_obj)

    def update_asset_type_registry(self, db, registry_id, request_data, user):
        self._require_platform_admin(user, detail="only platform admin can manage asset type registry")
        registry_obj = asset_type_registry_db.get(db=db, id=registry_id)
        update_data = {"update_time": self._now()}
        if request_data.code is not None:
            new_code = self._normalize_registry_code(request_data.code, "code")
            if registry_obj.is_system and new_code != registry_obj.code:
                raise HTTPException(status_code=400, detail="system asset_type code cannot be changed")
            if new_code != registry_obj.code:
                usage = self._asset_type_in_use(db=db, code=registry_obj.code)
                if usage:
                    raise HTTPException(status_code=400, detail=f"asset_type is in use and code cannot be changed: {usage}")
                existing = asset_type_registry_db.get_filter(db=db, filters={"code": new_code})
                if existing and existing.id != registry_obj.id:
                    raise HTTPException(status_code=400, detail=f"asset_type already exists: {new_code}")
            update_data["code"] = new_code
        if request_data.base_code is not None:
            update_data["base_code"] = self._normalize_registry_code(request_data.base_code, "base_code")
        if request_data.allowed_dataset_types is not None:
            normalized_dataset_types = []
            for item in request_data.allowed_dataset_types:
                normalized_type, _dataset_kind = self._require_dataset_kind_code(db=db, dataset_type=item, active_only=False)
                if normalized_type not in normalized_dataset_types:
                    normalized_dataset_types.append(normalized_type)
            update_data["allowed_dataset_types"] = self._encode_json_list(normalized_dataset_types)
        for field in ["name", "description", "sort_order", "meta_json"]:
            value = getattr(request_data, field, None)
            if value is not None:
                update_data[field] = value
        if request_data.is_active is not None:
            update_data["is_active"] = 1 if request_data.is_active else 0
        registry_obj = self._update_db_obj(db, registry_obj, **update_data)
        return self._build_asset_type_registry_payload(registry_obj)

    def delete_asset_type_registry(self, db, registry_id, user):
        self._require_platform_admin(user, detail="only platform admin can manage asset type registry")
        registry_obj = asset_type_registry_db.get(db=db, id=registry_id)
        if registry_obj.is_system:
            raise HTTPException(status_code=400, detail="system asset_type cannot be deleted")
        usage = self._asset_type_in_use(db=db, code=registry_obj.code)
        if usage:
            raise HTTPException(status_code=400, detail=f"asset_type is in use: {usage}")
        payload = self._build_asset_type_registry_payload(registry_obj)
        asset_type_registry_db.remove(db=db, id=registry_id)
        return {"deleted": True, "item": payload}

    def list_asset_file_type_registry(self, db, request_data):
        rows = asset_file_type_registry_db.get_data(db=db, filters={})
        items = []
        keyword = str(request_data.keyword or "").strip().lower()
        code_filter = self._normalize_registry_code(request_data.code, "code") if request_data.code else None
        base_code_filter = self._normalize_registry_code(request_data.base_code, "base_code") if request_data.base_code else None
        asset_type_filter = self._normalize_registry_code(request_data.asset_type, "asset_type") if request_data.asset_type else None
        file_format_filter = str(request_data.file_format or "").strip().lower() or None
        file_role_filter = self._normalize_file_role(request_data.file_role) if request_data.file_role else None
        for row in rows:
            allowed_asset_types = self._canonicalize_asset_type_list(self._parse_json_list(row.allowed_asset_types))
            supported_file_formats = self._normalize_file_format_list(
                self._parse_json_list(row.supported_file_formats),
                "supported_file_formats",
                require_non_empty=False,
            )
            if code_filter and row.code != code_filter:
                continue
            if base_code_filter and row.base_code != base_code_filter:
                continue
            if request_data.is_active is not None and bool(row.is_active) != bool(request_data.is_active):
                continue
            if asset_type_filter and allowed_asset_types and asset_type_filter not in allowed_asset_types:
                continue
            if file_format_filter and file_format_filter not in supported_file_formats:
                continue
            if file_role_filter and str(row.file_role or "").lower() != file_role_filter:
                continue
            if keyword:
                haystack = " ".join(
                    [
                        str(row.code or ""),
                        str(row.base_code or ""),
                        str(row.name or ""),
                        str(row.description or ""),
                        " ".join(supported_file_formats),
                        str(row.file_role or ""),
                        " ".join(allowed_asset_types),
                    ]
                ).lower()
                if keyword not in haystack:
                    continue
            items.append(self._build_asset_file_type_registry_payload(row))
        items = sorted(items, key=lambda item: (item["sort_order"] or 0, item["id"]))
        total = len(items)
        if request_data.page and request_data.size:
            start = (request_data.page - 1) * request_data.size
            end = start + request_data.size
            items = items[start:end]
        return {"dataList": items, "total": total}

    def get_asset_file_type_options(self, db, request_data):
        rows = asset_file_type_registry_db.get_data(db=db, filters={})
        asset_type_filter = self._normalize_registry_code(request_data.asset_type, "asset_type") if request_data.asset_type else None
        options = []
        for row in rows:
            allowed_asset_types = self._canonicalize_asset_type_list(self._parse_json_list(row.allowed_asset_types))
            supported_file_formats = self._normalize_file_format_list(
                self._parse_json_list(row.supported_file_formats),
                "supported_file_formats",
                require_non_empty=False,
            )
            if request_data.active_only and not row.is_active:
                continue
            if asset_type_filter and allowed_asset_types and asset_type_filter not in allowed_asset_types:
                continue
            options.append(
                {
                    "id": row.id,
                    "code": row.code,
                    "name": row.name,
                    "base_code": row.base_code,
                    "description": row.description,
                    "supported_file_formats": supported_file_formats,
                    "file_role": row.file_role,
                    "allowed_asset_types": allowed_asset_types,
                    "is_active": bool(row.is_active),
                    "is_system": bool(row.is_system),
                    "sort_order": row.sort_order,
                    "label": row.name,
                    "value": row.code,
                }
            )
        return sorted(options, key=lambda item: (item["sort_order"] or 0, item["id"]))

    def get_asset_file_type_registry(self, db, registry_id):
        registry_obj = asset_file_type_registry_db.get(db=db, id=registry_id)
        return self._build_asset_file_type_registry_payload(registry_obj)

    def _asset_file_type_in_use(self, db, registry_obj):
        allowed_asset_types = self._canonicalize_asset_type_list(self._parse_json_list(registry_obj.allowed_asset_types))
        supported_file_formats = set(
            self._normalize_file_format_list(
                self._parse_json_list(registry_obj.supported_file_formats),
                "supported_file_formats",
                require_non_empty=False,
            )
        )
        file_role = str(registry_obj.file_role or "").lower()
        if not supported_file_formats:
            return None
        for file_obj in asset_file_db.get_data(db=db, filters={}):
            if str(file_obj.file_format or "").lower() not in supported_file_formats:
                continue
            if file_role and str(file_obj.file_role or "").lower() != file_role:
                continue
            if not allowed_asset_types:
                return "asset_file"
            asset_obj = dataset_asset_db.get(db=db, id=file_obj.dataset_asset_id)
            if asset_obj and asset_obj.asset_type in allowed_asset_types:
                return "asset_file"
        return None

    def create_asset_file_type_registry(self, db, request_data, user):
        self._require_platform_admin(user, detail="only platform admin can manage asset file type registry")
        now = self._now()
        code = self._normalize_registry_code(request_data.code, "code")
        base_code = self._normalize_registry_code(request_data.base_code, "base_code")
        existing = asset_file_type_registry_db.get_filter(db=db, filters={"code": code})
        if existing:
            raise HTTPException(status_code=400, detail=f"asset_file_type already exists: {code}")
        allowed_asset_types = []
        for item in request_data.allowed_asset_types or []:
            normalized_type, _asset_type = self._require_asset_type_code(db=db, asset_type=item, active_only=False)
            if normalized_type not in allowed_asset_types:
                allowed_asset_types.append(normalized_type)
        supported_file_formats = self._normalize_file_format_list(request_data.supported_file_formats)
        registry_obj = asset_file_type_registry_db.create_one(
            db=db,
            obj_in={
                "code": code,
                "base_code": base_code,
                "name": request_data.name,
                "description": request_data.description,
                "supported_file_formats": self._encode_json_file_format_list(supported_file_formats),
                "file_role": self._normalize_file_role(request_data.file_role),
                "allowed_asset_types": self._encode_json_asset_type_list(allowed_asset_types),
                "is_system": False,
                "is_active": True if request_data.is_active is None else (1 if request_data.is_active else 0),
                "sort_order": request_data.sort_order or 0,
                "meta_json": request_data.meta_json,
                "create_time": now,
                "update_time": now,
            },
        )
        return self._build_asset_file_type_registry_payload(registry_obj)

    def update_asset_file_type_registry(self, db, registry_id, request_data, user):
        self._require_platform_admin(user, detail="only platform admin can manage asset file type registry")
        registry_obj = asset_file_type_registry_db.get(db=db, id=registry_id)
        update_data = {"update_time": self._now()}
        if request_data.code is not None:
            new_code = self._normalize_registry_code(request_data.code, "code")
            if registry_obj.is_system and new_code != registry_obj.code:
                raise HTTPException(status_code=400, detail="system asset_file_type code cannot be changed")
            existing = self._get_asset_file_type_registry_by_code(db=db, code=new_code)
            if existing and existing.id != registry_obj.id:
                raise HTTPException(status_code=400, detail=f"asset_file_type already exists: {new_code}")
            update_data["code"] = new_code
        if request_data.base_code is not None:
            update_data["base_code"] = self._normalize_registry_code(request_data.base_code, "base_code")
        if request_data.allowed_asset_types is not None:
            normalized_asset_types = []
            for item in request_data.allowed_asset_types:
                normalized_type, _asset_type = self._require_asset_type_code(db=db, asset_type=item, active_only=False)
                if normalized_type not in normalized_asset_types:
                    normalized_asset_types.append(normalized_type)
            update_data["allowed_asset_types"] = self._encode_json_asset_type_list(normalized_asset_types)
        if request_data.supported_file_formats is not None:
            update_data["supported_file_formats"] = self._encode_json_file_format_list(request_data.supported_file_formats)
        if request_data.file_role is not None:
            update_data["file_role"] = self._normalize_file_role(request_data.file_role)
        for field in ["name", "description", "sort_order", "meta_json"]:
            value = getattr(request_data, field, None)
            if value is not None:
                update_data[field] = value
        if request_data.is_active is not None:
            update_data["is_active"] = 1 if request_data.is_active else 0
        registry_obj = self._update_db_obj(db, registry_obj, **update_data)
        return self._build_asset_file_type_registry_payload(registry_obj)

    def delete_asset_file_type_registry(self, db, registry_id, user):
        self._require_platform_admin(user, detail="only platform admin can manage asset file type registry")
        registry_obj = asset_file_type_registry_db.get(db=db, id=registry_id)
        if registry_obj.is_system:
            raise HTTPException(status_code=400, detail="system asset_file_type cannot be deleted")
        usage = self._asset_file_type_in_use(db=db, registry_obj=registry_obj)
        if usage:
            raise HTTPException(status_code=400, detail=f"asset_file_type is in use: {usage}")
        payload = self._build_asset_file_type_registry_payload(registry_obj)
        asset_file_type_registry_db.remove(db=db, id=registry_id)
        return {"deleted": True, "item": payload}

    def list_dataset_versions(self, db, dataset_id, user=None):
        dataset_payload = self.get_dataset(db=db, dataset_id=dataset_id, user=user)
        version_rows = dataset_version_db.get_data(db=db, filters={"dataset_id": dataset_id})
        version_rows = sorted(version_rows, key=lambda item: item.id, reverse=True)
        return {
            "dataset_id": dataset_id,
            "dataset_code": dataset_payload["dataset_code"],
            "current_version": dataset_payload["current_version"],
            "default_public_version": dataset_payload.get("default_public_version"),
            "published_version": dataset_payload["published_version"],
            "items": [self._build_dataset_version_payload(item, db=db) for item in version_rows],
        }

    def get_dataset_version(self, db, version_id, user=None):
        version_obj = self._ensure_version_read_access(db=db, version_id=version_id, user=user)
        payload = self._build_dataset_version_payload(version_obj, db=db)
        payload["assets"] = self._build_asset_list_payload(db=db, version_id=version_id)
        payload["lineage"] = self.list_dataset_lineage(db=db, version_id=version_id, limit=50, user=user)["items"]
        return payload

    def get_dataset_version_query_capabilities(self, db, version_id, asset_code=None, user=None):
        version_obj = self._ensure_version_read_access(db=db, version_id=version_id, user=user)
        dataset_payload = self._build_dataset_payload_for_version(db=db, version_obj=version_obj)
        dataset_payload = self._select_asset_for_query(dataset_payload, asset_code=asset_code)
        file_path = self._resolve_dataset_primary_file_path(dataset_payload)
        return {
            "dataset_id": version_obj.dataset_id,
            "version_id": version_obj.id,
            "dataset_code": dataset_payload["dataset_code"],
            "version": dataset_payload.get("selected_version"),
            "dataset_type": dataset_payload["dataset_type"],
            "query_entry_asset": dataset_payload.get("query_entry_asset"),
            "assets": dataset_payload.get("assets", []),
            "file_path": file_path,
            "file_access": self._build_file_access_payload(file_path),
            "query_profile": dataset_payload["query_profile"],
            "query_adapter": dataset_payload["query_adapter"],
            "available_adapters": dataset_adapter_registry.list_adapters(),
        }

    def execute_dataset_version_query(self, db, version_id, operation, asset_code=None, params=None, user=None):
        version_obj = self._ensure_version_read_access(db=db, version_id=version_id, user=user)
        dataset_payload = self._build_dataset_payload_for_version(db=db, version_obj=version_obj)
        dataset_payload = self._select_asset_for_query(dataset_payload, asset_code=asset_code)
        dataset_payload = self._attach_query_runtime(dataset_payload, db)
        params = params or {}
        result = dataset_adapter_registry.execute(dataset_payload=dataset_payload, operation=operation, params=params)
        result["query_adapter"] = dataset_payload["query_adapter"]
        result["version"] = dataset_payload.get("selected_version")
        return result

    def create_dataset_version(self, db, request_data, user):
        self._ensure_dataset_write_access(db=db, dataset_id=request_data.dataset_id, user=user)
        dataset_payload = self.get_dataset(db=db, dataset_id=request_data.dataset_id, user=user)
        existing = dataset_version_db.get_filter(
            db=db,
            filters={"dataset_id": request_data.dataset_id, "version": request_data.version},
        )
        if existing:
            raise HTTPException(status_code=400, detail=f"dataset version already exists: {request_data.version}")
        file_path = request_data.file_path or self._resolve_dataset_primary_file_path(dataset_payload)
        if request_data.file_path:
            self._validate_local_file_exists(file_path)
        file_format = self._guess_file_suffix(file_path) if file_path else dataset_payload["query_profile"]["file_format"]
        dataset_type = self._resolve_dataset_type_from_path(file_path, dataset_payload["dataset_type"]) if file_path else dataset_payload["dataset_type"]
        dataset_type, _dataset_kind = self._require_dataset_kind_code(db=db, dataset_type=dataset_type)
        version_obj = dataset_version_db.create_one(
            db=db,
            obj_in={
                "dataset_id": request_data.dataset_id,
                "version": request_data.version,
                "title": request_data.title or dataset_payload["title"],
                "dataset_type": dataset_type,
                "lifecycle_state": "draft",
                "visibility": "private",
                "file_path": file_path,
                "file_format": file_format,
                "query_engine": FILE_TYPE_QUERY_ENGINES.get(file_format or "", dataset_payload["query_profile"].get("query_engine", "")),
                "validation_summary": None,
                "index_summary": None,
                "meta_json": request_data.meta_json,
                "is_current": 0,
                "create_time": self._now(),
                "update_time": self._now(),
            },
        )
        self._ensure_assets_for_version(db=db, version_obj=version_obj)
        return self._build_dataset_version_payload(version_obj, db=db)

    def activate_dataset_version(self, db, version_id, request_data, user):
        operator_id = user.id
        version_obj = self._ensure_version_write_access(db=db, version_id=version_id, user=user)
        dataset_id = version_obj.dataset_id
        version_name = version_obj.version
        version_title = version_obj.title
        version_file_format = None
        version_validation_summary = None
        version_index_summary = None
        version_meta_json = version_obj.meta_json
        database_obj = db.query(DatasetRegistry).filter(DatasetRegistry.id == dataset_id).first()
        registry_obj = self.ensure_registry(db=db, database_obj=database_obj)
        lifecycle_state = version_obj.lifecycle_state

        self._ensure_version_current_flag(db=db, database_id=dataset_id, version_name=version_name)
        version_obj = dataset_version_db.get(db=db, id=version_id)
        dataset_version_db.update_one(
            db=db,
            db_obj=version_obj,
            obj_in={"is_current": True, "update_time": self._now()},
        )
        registry_obj = dataset_registry_db.get_filter(db=db, filters={"id": dataset_id})
        dataset_registry_db.update_one(
            db=db,
            db_obj=registry_obj,
            obj_in={
                "version": version_name,
                "title": version_title or registry_obj.title,
                "dataset_type": registry_obj.dataset_type,
                "file_format": version_file_format or "",
                "validation_summary": version_validation_summary
                if version_validation_summary is not None
                else None,
                "index_summary": version_index_summary
                if version_index_summary is not None
                else None,
                "meta_json": version_meta_json if version_meta_json is not None else registry_obj.meta_json,
                "update_time": self._now(),
            },
        )
        dataset_workflow_task_db.create_one(
            db=db,
            obj_in={
                "dataset_id": dataset_id,
                "task_type": "sync",
                "status": "success",
                "from_lifecycle_state": lifecycle_state,
                "to_lifecycle_state": lifecycle_state,
                "operator_id": operator_id,
                "detail": request_data.note or f"activate dataset version {version_name}",
                "create_time": self._now(),
                "finish_time": self._now(),
            },
        )
        self._ensure_assets_for_version(db=db, version_obj=version_obj)
        return self.get_dataset(db=db, dataset_id=dataset_id, user=user)

    def release_dataset_version(self, db, version_id, request_data, user):
        operator_id = user.id
        version_obj = self._ensure_version_write_access(db=db, version_id=version_id, user=user)
        if version_obj.lifecycle_state != "ready":
            raise HTTPException(status_code=400, detail="dataset version must be ready before release")
        registry_obj = self.ensure_registry(
            db=db,
            database_obj=dataset_legacy_bridge.get_database(db=db, dataset_id=version_obj.dataset_id),
        )
        had_default_public = bool(getattr(registry_obj, "default_public_version_id", None))

        before_visibility = version_obj.visibility
        before_lifecycle_state = version_obj.lifecycle_state
        update_data = {
            "visibility": "public",
            "update_time": self._now(),
        }
        if version_obj.visibility != "public":
            update_data["visibility"] = "public"
        version_obj = dataset_version_db.update_one(db=db, db_obj=version_obj, obj_in=update_data)

        self._create_version_publish_record(
            db=db,
            version_snapshot={
                "id": version_obj.id,
                "dataset_id": version_obj.dataset_id,
                "version": version_obj.version,
                "visibility": before_visibility,
                "lifecycle_state": before_lifecycle_state,
            },
            action="release",
            operator_id=operator_id,
            next_visibility="public",
            next_lifecycle_state=before_lifecycle_state,
            note=request_data.note or f"release dataset version {version_obj.version}",
        )

        default_public = self._get_public_version_obj(db=db, dataset_id=version_obj.dataset_id)
        if not had_default_public:
            version_obj = self._set_default_public_version(
                db=db,
                dataset_id=version_obj.dataset_id,
                version_obj=version_obj,
                note=request_data.note,
                operator_id=operator_id,
            )
        else:
            self._normalize_version_public_flags(
                db=db,
                dataset_id=version_obj.dataset_id,
                default_version_id=default_public.id,
            )
            self._sync_registry_public_state(
                db=db,
                dataset_id=version_obj.dataset_id,
                default_public_version_id=default_public.id,
            )
        return self.get_dataset_version(db=db, version_id=version_obj.id, user=user)

    def _check_breeding_references(self, db, version_id):
        """Check all breeding link tables for references to a dataset version."""
        details = []
        variant_maps = (
            db.query(BreedingVariantSampleMap).filter_by(version_id=version_id).all()
        )
        for v in variant_maps:
            details.append({
                "table": "brd_variant_sample_map",
                "id": v.id,
                "material_id": v.material_id,
                "vcf_sample_name": v.vcf_sample_name,
            })

        pheno_maps = (
            db.query(BreedingPhenotypeSubjectMap).filter_by(version_id=version_id).all()
        )
        for p in pheno_maps:
            details.append({
                "table": "brd_phenotype_subject_map",
                "id": p.id,
                "material_id": p.material_id,
                "trait_code": p.trait_code,
            })

        subject_links = (
            db.query(BreedingDatasetSubjectLink).filter_by(version_id=version_id).all()
        )
        for s in subject_links:
            details.append({
                "table": "brd_dataset_subject_link",
                "id": s.id,
                "program_id": s.program_id,
                "material_id": s.material_id,
            })

        assay_links = (
            db.query(BreedingDatasetAssayLink).filter_by(version_id=version_id).all()
        )
        for a in assay_links:
            details.append({
                "table": "brd_dataset_assay_link",
                "id": a.id,
                "assay_id": a.assay_id,
            })

        return {
            "has_references": len(details) > 0,
            "total_references": len(details),
            "variant_sample_map_count": len(variant_maps),
            "phenotype_subject_map_count": len(pheno_maps),
            "dataset_subject_link_count": len(subject_links),
            "dataset_assay_link_count": len(assay_links),
            "details": details,
        }

    def withdraw_dataset_version(self, db, version_id, request_data, user):
        operator_id = user.id
        version_obj = self._ensure_version_write_access(db=db, version_id=version_id, user=user)
        if not version_obj.visibility == "public":
            raise HTTPException(status_code=400, detail="dataset version is not released")
        current_default_public = self._get_public_version_obj(db=db, dataset_id=version_obj.dataset_id)

        before_visibility = version_obj.visibility
        before_lifecycle_state = version_obj.lifecycle_state
        was_default_public = version_obj.is_current and version_obj.visibility == "public"
        version_obj = dataset_version_db.update_one(
            db=db,
            db_obj=version_obj,
            obj_in={
                "visibility": "private",
                "update_time": self._now(),
            },
        )
        self._create_version_publish_record(
            db=db,
            version_snapshot={
                "id": version_obj.id,
                "dataset_id": version_obj.dataset_id,
                "version": version_obj.version,
                "visibility": before_visibility,
                "lifecycle_state": before_lifecycle_state,
            },
            action="withdraw",
            operator_id=operator_id,
            next_visibility="private",
            next_lifecycle_state=before_lifecycle_state,
            note=request_data.note or f"withdraw dataset version {version_obj.version}",
        )

        self._normalize_version_public_flags(
            db=db,
            dataset_id=version_obj.dataset_id,
            default_version_id=None if was_default_public else getattr(current_default_public, "id", None),
        )
        self._sync_registry_public_state(
            db=db,
            dataset_id=version_obj.dataset_id,
            default_public_version_id=None if was_default_public else getattr(current_default_public, "id", None),
        )
        result = self.get_dataset_version(db=db, version_id=version_obj.id, user=user)
        breeding_refs = self._check_breeding_references(db=db, version_id=version_obj.id)
        result["_breeding_references"] = breeding_refs
        return result

    def set_default_public_dataset_version(self, db, version_id, request_data, user):
        operator_id = user.id
        version_obj = self._ensure_version_write_access(db=db, version_id=version_id, user=user)
        if not version_obj.visibility == "public":
            raise HTTPException(status_code=400, detail="dataset version must be released before setting default public")

        version_obj = self._set_default_public_version(
            db=db,
            dataset_id=version_obj.dataset_id,
            version_obj=version_obj,
            note=request_data.note,
            operator_id=operator_id,
        )
        return self.get_dataset_version(db=db, version_id=version_obj.id, user=user)

    def get_query_capabilities(self, db, dataset_id, asset_code=None, user=None):
        dataset_payload = self.get_dataset(db=db, dataset_id=dataset_id, user=user)
        dataset_payload = self._select_asset_for_query(dataset_payload, asset_code=asset_code)
        file_path = self._resolve_dataset_primary_file_path(dataset_payload)
        return {
            "dataset_id": dataset_id,
            "dataset_code": dataset_payload["dataset_code"],
            "dataset_type": dataset_payload["dataset_type"],
            "query_entry_asset": dataset_payload.get("query_entry_asset"),
            "assets": dataset_payload.get("assets", []),
            "file_path": file_path,
            "file_access": self._build_file_access_payload(file_path),
            "query_profile": dataset_payload["query_profile"],
            "query_adapter": dataset_payload["query_adapter"],
            "available_adapters": dataset_adapter_registry.list_adapters(),
        }

    def execute_query(self, db, dataset_id, operation, asset_code=None, params=None, user=None):
        dataset_payload = self.get_dataset(db=db, dataset_id=dataset_id, user=user)
        dataset_payload = self._select_asset_for_query(dataset_payload, asset_code=asset_code)
        dataset_payload = self._attach_query_runtime(dataset_payload, db)
        params = params or {}
        result = dataset_adapter_registry.execute(dataset_payload=dataset_payload, operation=operation, params=params)
        result["query_adapter"] = dataset_payload["query_adapter"]
        return result

    def list_public_datasets(self, request_data):
        db = mydb.get_dbs()
        try:
            dataset_type_filter = None
            if request_data.dataset_type:
                dataset_type_filter, _dataset_kind = self._require_dataset_kind_code(
                    db=db,
                    dataset_type=request_data.dataset_type,
                    active_only=False,
                )

            # Lightweight query — avoid _build_public_dataset_payload per dataset
            query = db.query(DatasetRegistry).filter(
                DatasetRegistry.default_public_version_id.isnot(None),
            )
            if dataset_type_filter:
                query = query.filter(DatasetRegistry.dataset_type.in_([dataset_type_filter]))

            registry_rows = query.order_by(DatasetRegistry.id.desc()).all()

            # Build organism name cache from taxonomy
            from modules.breeding.models import BreedingTaxonomyNode
            tax_ids = {r.organism for r in registry_rows if r.organism}
            taxon_map = {}
            if tax_ids:
                nodes = db.query(BreedingTaxonomyNode).filter(BreedingTaxonomyNode.tax_id.in_(tax_ids)).all()
                taxon_map = {n.tax_id: n.scientific_name for n in nodes}

            data_list = []
            for item in registry_rows:
                if request_data.dataset_id and item.id != request_data.dataset_id:
                    continue
                if request_data.name and request_data.name not in (item.title or "") and request_data.name not in (item.dataset_code or ""):
                    continue
                kind_obj = self._get_dataset_kind_registry_by_code(db=db, code=item.dataset_type)
                data_list.append({
                    "id": item.id,
                    "dataset_id": item.id,
                    "dataset_code": item.dataset_code,
                    "title": item.title,
                    "dataset_type": item.dataset_type,
                    "dataset_kind": self._build_dataset_kind_registry_payload(kind_obj) if kind_obj else None,
                    "organism": item.organism,
                    "organism_name": taxon_map.get(item.organism) if item.organism else None,
                    "version": "",
                    "lifecycle_state": "",
                    "description_md": (item.description_md or "")[:500],
                    "meta_json": item.meta_json,
                })

            total = len(data_list)
            if request_data.page and request_data.size:
                start = (request_data.page - 1) * request_data.size
                end = start + request_data.size
                data_list = data_list[start:end]

            return {"dataList": data_list, "items": data_list, "total": total}
        finally:
            db.close()

    def get_public_dataset(self, dataset_id):
        db = mydb.get_dbs()
        try:
            return self._build_public_dataset_summary(db=db, dataset_id=dataset_id)
        finally:
            db.close()

        db = mydb.get_dbs()
        try:
            dataset_payload = self._build_public_dataset_payload(db=db, dataset_id=dataset_id)
            items = list(dataset_payload.get("public_versions", []))
            normalized_keyword = str(keyword or "").strip().lower()
            if normalized_keyword:
                items = [
                    item
                    for item in items
                    if normalized_keyword in str(item.get("version") or "").lower()
                    or normalized_keyword in str(item.get("title") or "").lower()
                ]
            if is_current is not None:
                items = [item for item in items if bool(item.get("is_current")) is bool(is_current)]
            return {
                "dataset_id": dataset_id,
                "dataset_code": dataset_payload["dataset_code"],
                "default_public_version": dataset_payload.get("default_public_version"),
                "total": len(items),
                "filters": {
                    "keyword": keyword or "",
                    "is_current": is_current,
                },
                "items": items,
            }
        finally:
            db.close()

    def list_public_dataset_versions(self, dataset_id, keyword=None, is_current=None):
        db = mydb.get_dbs()
        try:
            dataset_payload = self._build_public_dataset_payload(db=db, dataset_id=dataset_id)
            items = list(dataset_payload.get("public_versions", []))
            if keyword:
                kw = str(keyword).strip().lower()
                items = [i for i in items if kw in str(i.get("version") or "").lower() or kw in str(i.get("title") or "").lower()]
            if is_current is not None:
                items = [i for i in items if bool(i.get("is_current")) is bool(is_current)]
            return {
                "dataset_id": dataset_id,
                "items": items,
                "total": len(items),
            }
        finally:
            db.close()

    def get_public_dataset_version(self, dataset_id, version_id):
        db = mydb.get_dbs()
        try:
            version_obj = self._get_public_version_obj_by_id(db=db, dataset_id=dataset_id, version_id=version_id)
            return self._build_public_dataset_payload(db=db, dataset_id=dataset_id, version_obj=version_obj)
        finally:
            db.close()

    def get_public_query_capabilities(self, dataset_id, asset_code=None):
        db = mydb.get_dbs()
        try:
            dataset_payload = self._build_public_dataset_payload(db=db, dataset_id=dataset_id)
        finally:
            db.close()
        dataset_payload = self._select_asset_for_query(dataset_payload, asset_code=asset_code)
        file_path = self._resolve_dataset_primary_file_path(dataset_payload)
        return {
            "dataset_id": dataset_id,
            "dataset_code": dataset_payload["dataset_code"],
            "dataset_type": dataset_payload["dataset_type"],
            "query_entry_asset": dataset_payload.get("query_entry_asset"),
            "assets": dataset_payload.get("assets", []),
            "file_path": file_path,
            "file_access": self._build_file_access_payload(file_path),
            "query_profile": dataset_payload["query_profile"],
            "query_adapter": dataset_payload["query_adapter"],
            "published_version": dataset_payload["published_version"],
            "available_adapters": dataset_adapter_registry.list_adapters(),
        }

    def get_public_dataset_version_query_capabilities(self, dataset_id, version_id, asset_code=None):
        dataset_payload = self.get_public_dataset_version(dataset_id=dataset_id, version_id=version_id)
        dataset_payload = self._select_asset_for_query(dataset_payload, asset_code=asset_code)
        file_path = self._resolve_dataset_primary_file_path(dataset_payload)
        return {
            "dataset_id": dataset_id,
            "version_id": version_id,
            "dataset_code": dataset_payload["dataset_code"],
            "dataset_type": dataset_payload["dataset_type"],
            "query_entry_asset": dataset_payload.get("query_entry_asset"),
            "assets": dataset_payload.get("assets", []),
            "file_path": file_path,
            "file_access": self._build_file_access_payload(file_path),
            "query_profile": dataset_payload["query_profile"],
            "query_adapter": dataset_payload["query_adapter"],
            "default_public_version": dataset_payload.get("default_public_version"),
            "published_version": dataset_payload["published_version"],
            "available_adapters": dataset_adapter_registry.list_adapters(),
        }

    def execute_public_query(self, dataset_id, operation, asset_code=None, params=None):
        db = mydb.get_dbs()
        try:
            dataset_payload = self._build_public_dataset_payload(db=db, dataset_id=dataset_id)
            dataset_payload = self._select_asset_for_query(dataset_payload, asset_code=asset_code)
            dataset_payload = self._attach_query_runtime(dataset_payload, db)
            params = params or {}
            result = dataset_adapter_registry.execute(dataset_payload=dataset_payload, operation=operation, params=params)
            result["query_adapter"] = dataset_payload["query_adapter"]
            result["published_version"] = dataset_payload["published_version"]
            return result
        finally:
            db.close()

    def execute_public_dataset_version_query(self, dataset_id, version_id, operation, asset_code=None, params=None):
        db = mydb.get_dbs()
        try:
            version_obj = self._get_public_version_obj_by_id(db=db, dataset_id=dataset_id, version_id=version_id)
            dataset_payload = self._build_public_dataset_payload(db=db, dataset_id=dataset_id, version_obj=version_obj)
            dataset_payload = self._select_asset_for_query(dataset_payload, asset_code=asset_code)
            dataset_payload = self._attach_query_runtime(dataset_payload, db)
            params = params or {}
            result = dataset_adapter_registry.execute(dataset_payload=dataset_payload, operation=operation, params=params)
            result["query_adapter"] = dataset_payload["query_adapter"]
            result["default_public_version"] = dataset_payload.get("default_public_version")
            result["published_version"] = dataset_payload["published_version"]
            return result
        finally:
            db.close()

    def batch_sequence_retrieval(self, request_data):
        """Resolve gene IDs or coordinates and extract sequences via samtools faidx."""
        import os, uuid, sqlite3, subprocess

        db = mydb.get_dbs()
        try:
            dataset_id = request_data.dataset_id
            seq_type = request_data.sequence_type
            inputs = [s.strip() for s in request_data.inputs if s.strip()]
            if not inputs:
                raise HTTPException(status_code=400, detail="No inputs provided")

            genome_path = None
            mrna_path = None
            protein_path = None
            func_anno_path = None

            cur_ver = db.query(DatasetVersion).filter(
                DatasetVersion.dataset_id == dataset_id,
                DatasetVersion.is_current == True,
            ).first()

            if cur_ver:
                asset_rows = db.query(DatasetAsset).filter_by(
                    dataset_version_id=cur_ver.id,
                ).all()
                for asset in asset_rows:
                    files = db.query(AssetFile).filter_by(dataset_asset_id=asset.id).all()
                    for f in files:
                        fp = f.local_path or f.storage_uri or ""
                        role = f.file_role or ""
                        if not fp or not os.path.exists(fp) or "index" in role.lower():
                            continue
                        if asset.asset_type == "reference_fasta":
                            genome_path = fp
                        elif asset.asset_type == "gene_annotation" and role == "transcript_sequence":
                            if "cds" in f.file_name.lower():
                                pass  # skip CDS, prefer mRNA
                            elif not mrna_path:
                                mrna_path = fp
                        elif asset.asset_type == "gene_annotation" and role == "protein_sequence":
                            protein_path = fp
                        elif asset.asset_type == "functional_annotation" and f.file_format in ("db", "sqlite"):
                            func_anno_path = fp

            gene_map = {}
            if seq_type != "genome":
                if not func_anno_path:
                    raise HTTPException(status_code=400, detail="No functional annotation DB for gene resolution")
                conn = sqlite3.connect(func_anno_path)
                conn.row_factory = sqlite3.Row
                for gene_id in inputs:
                    row = conn.execute(
                        "SELECT gene_id, chrom, start, stop, strand, canonical_transcript FROM hse_genes WHERE gene_id = ?",
                        (gene_id,),
                    ).fetchone()
                    if row:
                        gene_map[gene_id] = {
                            "chrom": row["chrom"],
                            "start": row["start"],
                            "stop": row["stop"],
                            "strand": row["strand"] or "+",
                            "transcript_id": row["canonical_transcript"] or gene_id,
                        }
                conn.close()

            regions = []
            errors = []

            if seq_type == "genome":
                if not genome_path:
                    raise HTTPException(status_code=400, detail="Genome FASTA not available")
                for inp in inputs:
                    if ":" in inp:
                        regions.append((inp, inp, genome_path))
                    else:
                        errors.append({"input": inp, "error": "Invalid format. Expected: seq_id:start-end"})

            elif seq_type == "mrna":
                if not mrna_path:
                    raise HTTPException(status_code=400, detail="mRNA FASTA not available")
                for inp in inputs:
                    regions.append((inp, inp, mrna_path))

            elif seq_type == "protein":
                if not protein_path:
                    raise HTTPException(status_code=400, detail="Protein FASTA not available")
                for inp in inputs:
                    regions.append((inp, inp, protein_path))

            elif seq_type in ("gene", "gene_up", "gene_down", "gene_up_down"):
                if not genome_path:
                    raise HTTPException(status_code=400, detail="Genome FASTA not available")
                up = request_data.upstream if "up" in seq_type else 0
                down = request_data.downstream if "down" in seq_type else 0
                for inp in inputs:
                    ginfo = gene_map.get(inp)
                    if not ginfo:
                        errors.append({"input": inp, "error": "Gene not found"})
                        continue
                    chrom = ginfo["chrom"]
                    if seq_type == "gene":
                        region = f"{chrom}:{ginfo['start']}-{ginfo['stop']}"
                    elif seq_type == "gene_up":
                        region = f"{chrom}:{max(1, ginfo['start'] - up)}-{ginfo['start']}"
                    elif seq_type == "gene_down":
                        region = f"{chrom}:{ginfo['stop']}-{ginfo['stop'] + down}"
                    else:
                        region = f"{chrom}:{max(1, ginfo['start'] - up)}-{ginfo['stop'] + down}"
                    regions.append((inp, region, genome_path))
            else:
                raise HTTPException(status_code=400, detail=f"Unknown sequence_type: {seq_type}")

            if not regions:
                return {"sequences": errors, "total_length": 0, "truncated": False}

            by_path = {}
            for inp, reg, fp in regions:
                by_path.setdefault(fp, []).append((inp, reg))

            results = list(errors)
            total_len = 0

            for fp, items in by_path.items():
                for inp, reg in items:
                    if not reg or not all(c.isalnum() or c in ':_-.' for c in reg):
                        seq = ""
                    else:
                        try:
                            import shutil as _shutil
                            samtools_bin = _shutil.which("samtools") or "samtools"
                            result = subprocess.run(
                                [samtools_bin, "faidx", fp, reg],
                                capture_output=True, text=True, timeout=30,
                            )
                            seq_lines = result.stdout.strip().split("\n")
                            seq = "".join(seq_lines[1:]) if len(seq_lines) > 1 else ""
                        except Exception:
                            seq = ""
                    total_len += len(seq)
                    results.append({
                        "input": inp,
                        "header": f">{inp}" if seq_type == "genome" else f">{inp} region={reg}",
                        "length": len(seq),
                        "sequence": seq,
                    })

            truncated = total_len > 1_000_000
            download_url = None
            if truncated:
                tmp = f"{settings.RUNTIME_DIR}/fance-seq-{uuid.uuid4().hex}.fasta"
                with open(tmp, "w") as fh:
                    for r in results:
                        if r.get("sequence"):
                            fh.write(f"{r['header']}\n{r['sequence']}\n")
                download_url = f"/api/v1/public/dataset/sequence/download?file={os.path.basename(tmp)}"
                for r in results:
                    r["sequence"] = None

            return {
                "sequences": results,
                "total_length": total_len,
                "truncated": truncated,
                "download_url": download_url,
            }
        finally:
            db.close()


dataset_domain_service = DatasetDomainService()
