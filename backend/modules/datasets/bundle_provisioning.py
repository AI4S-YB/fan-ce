from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import HTTPException

from .crud import dataset_lineage_edge_db, dataset_registry_db
from .services import dataset_domain_service, dataset_legacy_bridge


REFERENCE_FASTA_CANDIDATES = (
    "genome.fa.gz",
    "genome.fa",
    "genome.fasta.gz",
    "genome.fasta",
    "reference.fa.gz",
    "reference.fa",
    "reference.fasta.gz",
    "reference.fasta",
)

GENE_ANNOTATION_CANDIDATES = (
    "gene_model_sorted.gff3.gz",
    "gene_model.gff3.gz",
    "gene_model.gtf.gz",
    "gene_model.gff3",
    "gene_model.gtf",
    "gene_model.gff",
    "annotation.gff3.gz",
    "annotation.gtf.gz",
    "annotation.gff3",
    "annotation.gtf",
)

FUNCTIONAL_ANNOTATION_CANDIDATES = (
    "genome.db",
    "functional_annotation.db",
    "annotation.db",
)

TRANSCRIPT_SEQUENCE_CANDIDATES = (
    "mRNA.fa.gz",
    "mRNA.fa",
    "mrna.fa.gz",
    "mrna.fa",
    "transcript.fa.gz",
    "transcript.fa",
    "transcripts.fa.gz",
    "transcripts.fa",
)

PROTEIN_SEQUENCE_CANDIDATES = (
    "protein.fa.gz",
    "protein.fa",
    "proteins.fa.gz",
    "proteins.fa",
    "protein.faa.gz",
    "protein.faa",
)

EXPRESSION_METADATA_CANDIDATES = (
    "meta.json",
    "metadata.json",
)

VARIOME_PRIMARY_SUFFIXES = (
    ".vcf.gz",
    ".bcf",
    ".vcf",
)

READY_TRANSITION_PATH = ("draft", "uploaded", "validating", "validated", "indexing", "ready")


@dataclass
class BundleFilePlan:
    file_role: str
    local_path: str
    file_format: str | None = None
    asset_file_type_code: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class BundleAssetPlan:
    asset_code: str
    asset_name: str
    asset_type: str
    file_format: str
    query_engine: str
    local_path: str
    primary_asset_file_type_code: str | None = None
    primary_file_meta: dict[str, Any] = field(default_factory=dict)
    is_query_entry: bool = False
    display_order: int = 0
    meta: dict[str, Any] = field(default_factory=dict)
    companion_files: list[BundleFilePlan] = field(default_factory=list)


@dataclass
class SequenceBundlePlan:
    bundle_dir: str
    dataset_title: str
    version: str
    dataset_type: str
    primary_file_path: str
    organism: str | None = None
    assets: list[BundleAssetPlan] = field(default_factory=list)
    bundle_meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _guess_file_format(file_path: Path) -> str:
    return dataset_domain_service._guess_file_suffix(str(file_path)) or file_path.suffix.lstrip(".")


def _pick_first_existing(bundle_path: Path, candidates: tuple[str, ...]) -> Path | None:
    for relative_path in candidates:
        candidate = bundle_path / relative_path
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _pick_expression_matrix(bundle_path: Path) -> Path | None:
    candidates = sorted(
        item
        for item in bundle_path.iterdir()
        if item.is_file() and _guess_file_format(item) in {"h5", "hdf5"}
    )
    return candidates[0] if candidates else None


def _pick_expression_metadata(bundle_path: Path, matrix_path: Path) -> Path | None:
    sidecar = Path(f"{matrix_path}.json")
    if sidecar.exists() and sidecar.is_file():
        return sidecar
    fallback = _pick_first_existing(bundle_path, EXPRESSION_METADATA_CANDIDATES)
    if fallback is not None:
        return fallback
    candidates = sorted(
        item
        for item in bundle_path.iterdir()
        if item.is_file() and item.suffix.lower() == ".json"
    )
    return candidates[0] if candidates else None


def _read_json_if_exists(file_path: Path | None) -> dict[str, Any]:
    if file_path is None or not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _detect_expression_metric(file_path: Path) -> str | None:
    lower_name = file_path.name.lower()
    for metric in ("count", "fpkm", "tpm"):
        if metric in lower_name:
            return metric
    return None


def _sanitize_asset_code(value: str) -> str:
    normalized = []
    last_was_sep = False
    for char in value.lower():
        if char.isalnum():
            normalized.append(char)
            last_was_sep = False
            continue
        if not last_was_sep:
            normalized.append("_")
            last_was_sep = True
    code = "".join(normalized).strip("_")
    return code or "asset"


def _discover_expression_support_files(bundle_path: Path, matrix_path: Path, metadata_path: Path | None) -> list[tuple[str, Path]]:
    matches: list[tuple[str, Path]] = []
    for candidate in sorted(bundle_path.iterdir()):
        if not candidate.is_file():
            continue
        if candidate == matrix_path or candidate == metadata_path:
            continue
        metric = _detect_expression_metric(candidate)
        if metric is None:
            continue
        matches.append((metric, candidate))
    return matches


def _build_index_companions(file_path: Path, dataset_type: str, asset_file_type_code: str | None = None) -> list[BundleFilePlan]:
    dataset_type = dataset_domain_service._canonical_dataset_type(dataset_type)
    companions: list[BundleFilePlan] = []
    if dataset_type == "genome":
        for suffix in (".fai", ".gzi"):
            candidate = Path(f"{file_path}{suffix}")
            if candidate.exists():
                companions.append(
                    BundleFilePlan(
                        file_role="index",
                        local_path=str(candidate.resolve()),
                        file_format=_guess_file_format(candidate),
                        asset_file_type_code=asset_file_type_code,
                    )
                )
        return companions
    if dataset_type == "variome":
        candidates: list[Path] = []
        if str(file_path).endswith(".vcf.gz"):
            candidates.extend([Path(f"{file_path}.tbi"), Path(f"{file_path}.csi")])
        elif str(file_path).endswith(".bcf"):
            candidates.append(Path(f"{file_path}.csi"))
        for candidate in candidates:
            if candidate.exists():
                companions.append(
                    BundleFilePlan(
                        file_role="index",
                        local_path=str(candidate.resolve()),
                        file_format=_guess_file_format(candidate),
                        asset_file_type_code=asset_file_type_code,
                    )
                )
        return companions
    if dataset_type == "annotation":
        for suffix in (".tbi", ".csi"):
            candidate = Path(f"{file_path}{suffix}")
            if candidate.exists():
                companions.append(
                    BundleFilePlan(
                        file_role="index",
                        local_path=str(candidate.resolve()),
                        file_format=_guess_file_format(candidate),
                        asset_file_type_code=asset_file_type_code,
                    )
                )
        return companions
    return companions


def discover_sequence_bundle(
    bundle_dir: str | Path,
    *,
    dataset_title: str | None = None,
    version: str = "v1",
    organism: str | None = None,
) -> SequenceBundlePlan:
    bundle_path = Path(bundle_dir).expanduser().resolve()
    if not bundle_path.exists():
        raise HTTPException(status_code=404, detail=f"bundle directory not found: {bundle_path}")
    if not bundle_path.is_dir():
        raise HTTPException(status_code=400, detail=f"bundle path is not a directory: {bundle_path}")

    reference_fasta = _pick_first_existing(bundle_path, REFERENCE_FASTA_CANDIDATES)
    if reference_fasta is None:
        raise HTTPException(status_code=400, detail=f"reference fasta not found in bundle: {bundle_path}")

    gene_annotation = _pick_first_existing(bundle_path, GENE_ANNOTATION_CANDIDATES)
    functional_annotation = _pick_first_existing(bundle_path, FUNCTIONAL_ANNOTATION_CANDIDATES)
    transcript_sequence = _pick_first_existing(bundle_path, TRANSCRIPT_SEQUENCE_CANDIDATES)
    protein_sequence = _pick_first_existing(bundle_path, PROTEIN_SEQUENCE_CANDIDATES)

    func_source_dir = bundle_path / "func_anno"
    meta_path = bundle_path / "meta.json"

    assets: list[BundleAssetPlan] = [
        BundleAssetPlan(
            asset_code="reference_fasta",
            asset_name="Reference FASTA",
            asset_type="reference_fasta",
            file_format=_guess_file_format(reference_fasta),
            query_engine="samtools/faidx",
            local_path=str(reference_fasta.resolve()),
            primary_asset_file_type_code="genome_sequence",
            is_query_entry=True,
            display_order=0,
            meta={
                "bundle_dir": str(bundle_path),
                "bundle_role": "reference_fasta",
            },
            companion_files=_build_index_companions(
                reference_fasta,
                "genome",
                asset_file_type_code="genome_sequence_index",
            ),
        )
    ]

    if gene_annotation is not None:
        gene_annotation_companions = _build_index_companions(
            gene_annotation,
            "annotation",
            asset_file_type_code="gene_models_index",
        )
        if transcript_sequence is not None:
            gene_annotation_companions.append(
                BundleFilePlan(
                    file_role="primary",
                    local_path=str(transcript_sequence.resolve()),
                    file_format=_guess_file_format(transcript_sequence),
                    asset_file_type_code="transcript_sequence",
                )
            )
        if protein_sequence is not None:
            gene_annotation_companions.append(
                BundleFilePlan(
                    file_role="primary",
                    local_path=str(protein_sequence.resolve()),
                    file_format=_guess_file_format(protein_sequence),
                    asset_file_type_code="protein_sequence",
                )
            )
        assets.append(
            BundleAssetPlan(
                asset_code="gene_annotation",
                asset_name="Gene Annotation",
                asset_type="gene_annotation",
                file_format=_guess_file_format(gene_annotation),
                query_engine="tabix/gff",
                local_path=str(gene_annotation.resolve()),
                primary_asset_file_type_code="gene_models",
                display_order=10,
                meta={
                    "bundle_dir": str(bundle_path),
                    "bundle_role": "gene_annotation",
                },
                companion_files=gene_annotation_companions,
            )
        )

    if functional_annotation is not None:
        functional_meta: dict[str, Any] = {
            "bundle_dir": str(bundle_path),
            "bundle_role": "functional_annotation",
        }
        if func_source_dir.exists() and func_source_dir.is_dir():
            functional_meta["source_dir"] = str(func_source_dir.resolve())
        assets.append(
            BundleAssetPlan(
                asset_code="functional_annotation",
                asset_name="Functional Annotation",
                asset_type="functional_annotation",
                file_format=_guess_file_format(functional_annotation),
                query_engine="functional_annotation",
                local_path=str(functional_annotation.resolve()),
                primary_asset_file_type_code="functional_annotation_db",
                display_order=20,
                meta=functional_meta,
            )
        )

    bundle_meta = {
        "bundle_dir": str(bundle_path),
        "has_meta_json": meta_path.exists(),
        "has_func_anno_dir": func_source_dir.exists() and func_source_dir.is_dir(),
        "detected_assets": [item.asset_code for item in assets],
    }
    if meta_path.exists():
        bundle_meta["meta_json_path"] = str(meta_path.resolve())

    return SequenceBundlePlan(
        bundle_dir=str(bundle_path),
        dataset_title=dataset_title or bundle_path.name,
        version=version,
        dataset_type="genome",
        primary_file_path=str(reference_fasta.resolve()),
        organism=organism,
        
        assets=assets,
        bundle_meta=bundle_meta,
    )


def discover_expression_bundle(
    bundle_dir: str | Path,
    *,
    dataset_title: str | None = None,
    version: str = "v1",
    organism: str | None = None,
) -> SequenceBundlePlan:
    bundle_path = Path(bundle_dir).expanduser().resolve()
    if not bundle_path.exists():
        raise HTTPException(status_code=404, detail=f"bundle directory not found: {bundle_path}")
    if not bundle_path.is_dir():
        raise HTTPException(status_code=400, detail=f"bundle path is not a directory: {bundle_path}")

    matrix_path = _pick_expression_matrix(bundle_path)
    if matrix_path is None:
        raise HTTPException(status_code=400, detail=f"expression matrix not found in bundle: {bundle_path}")

    metadata_path = _pick_expression_metadata(bundle_path, matrix_path)
    metadata_payload = _read_json_if_exists(metadata_path)
    dataset_info = metadata_payload.get("dataset_info") if isinstance(metadata_payload.get("dataset_info"), dict) else {}
    assets: list[BundleAssetPlan] = [
        BundleAssetPlan(
            asset_code="expression_matrix",
            asset_name="Expression Matrix",
            asset_type="expression_matrix",
            file_format=_guess_file_format(matrix_path),
            query_engine="hdf5",
            local_path=str(matrix_path.resolve()),
            primary_asset_file_type_code="expression_matrix_store",
            is_query_entry=True,
            display_order=0,
            meta={
                "bundle_dir": str(bundle_path),
                "bundle_role": "expression_matrix",
            },
        )
    ]

    if metadata_path is not None:
        assets.append(
            BundleAssetPlan(
                asset_code="sample_metadata",
                asset_name="Sample Metadata",
                asset_type="metadata_table",
                file_format=_guess_file_format(metadata_path),
                query_engine="file",
                local_path=str(metadata_path.resolve()),
                display_order=10,
                meta={
                    "bundle_dir": str(bundle_path),
                    "bundle_role": "sample_metadata",
                },
            )
        )

    metric_counts: dict[str, int] = {}
    for metric, file_path in _discover_expression_support_files(bundle_path, matrix_path, metadata_path):
        metric_counts[metric] = metric_counts.get(metric, 0) + 1
        suffix = "" if metric_counts[metric] == 1 else f"_{metric_counts[metric]}"
        asset_code = _sanitize_asset_code(f"{metric}_matrix_raw{suffix}")
        assets.append(
            BundleAssetPlan(
                asset_code=asset_code,
                asset_name=f"{metric.upper()} Raw Matrix",
                asset_type="metadata_table",
                file_format=_guess_file_format(file_path),
                query_engine="file",
                local_path=str(file_path.resolve()),
                display_order=20 + len(assets) * 10,
                meta={
                    "bundle_dir": str(bundle_path),
                    "bundle_role": "raw_matrix",
                    "metric": metric,
                },
            )
        )

    bundle_meta: dict[str, Any] = {
        "bundle_dir": str(bundle_path),
        "detected_assets": [item.asset_code for item in assets],
        "matrix_file_path": str(matrix_path.resolve()),
        "has_metadata_json": metadata_path is not None,
    }
    if metadata_path is not None:
        bundle_meta["metadata_json_path"] = str(metadata_path.resolve())
    if dataset_info:
        bundle_meta["dataset_info"] = dataset_info
    if metadata_payload.get("samples") is not None and isinstance(metadata_payload.get("samples"), list):
        bundle_meta["sample_count"] = len(metadata_payload["samples"])

    return SequenceBundlePlan(
        bundle_dir=str(bundle_path),
        dataset_title=dataset_title or dataset_info.get("title") or bundle_path.name,
        version=version,
        dataset_type="transcriptome",
        primary_file_path=str(matrix_path.resolve()),
        organism=organism or dataset_info.get("organism"),
        
        assets=assets,
        bundle_meta=bundle_meta,
    )


def _resolve_bundle_primary_file(bundle_path: Path, primary_file: str | Path | None) -> Path | None:
    if primary_file is None:
        return None
    candidate = Path(primary_file).expanduser()
    if not candidate.is_absolute():
        candidate = bundle_path / candidate
    candidate = candidate.resolve()
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail=f"bundle primary file not found: {candidate}")
    return candidate


def _pick_variome_primary(bundle_path: Path, primary_file: str | Path | None = None) -> Path | None:
    resolved = _resolve_bundle_primary_file(bundle_path, primary_file)
    if resolved is not None:
        return resolved

    candidates = sorted(item for item in bundle_path.iterdir() if item.is_file())
    preferred: list[Path] = []
    fallback: list[Path] = []
    for suffix in VARIOME_PRIMARY_SUFFIXES:
        for candidate in candidates:
            if not candidate.name.endswith(suffix):
                continue
            fallback.append(candidate)
            companion_files = _build_index_companions(candidate, "variome")
            if companion_files:
                preferred.append(candidate)
        if preferred:
            return preferred[0]
    return fallback[0] if fallback else None


def discover_variome_bundle(
    bundle_dir: str | Path,
    *,
    dataset_title: str | None = None,
    version: str = "v1",
    organism: str | None = None,
    primary_file: str | Path | None = None,
) -> SequenceBundlePlan:
    bundle_path = Path(bundle_dir).expanduser().resolve()
    if not bundle_path.exists():
        raise HTTPException(status_code=404, detail=f"bundle directory not found: {bundle_path}")
    if not bundle_path.is_dir():
        raise HTTPException(status_code=400, detail=f"bundle path is not a directory: {bundle_path}")

    variant_path = _pick_variome_primary(bundle_path, primary_file=primary_file)
    if variant_path is None:
        raise HTTPException(status_code=400, detail=f"variome primary file not found in bundle: {bundle_path}")

    bundle_meta: dict[str, Any] = {
        "bundle_dir": str(bundle_path),
        "primary_file_path": str(variant_path.resolve()),
        "detected_assets": ["variant_calls"],
        "has_index": bool(_build_index_companions(variant_path, "variome")),
    }
    if primary_file is not None:
        bundle_meta["requested_primary_file"] = str(primary_file)

    assets = [
        BundleAssetPlan(
            asset_code="variant_calls",
            asset_name="Variant Calls",
            asset_type="variant_vcf",
            file_format=_guess_file_format(variant_path),
            query_engine="tabix/bcftools",
            local_path=str(variant_path.resolve()),
            primary_asset_file_type_code="variant_calls",
            is_query_entry=True,
            display_order=0,
            meta={
                "bundle_dir": str(bundle_path),
                "bundle_role": "variant_calls",
            },
            companion_files=_build_index_companions(
                variant_path,
                "variome",
                asset_file_type_code="variant_calls_index",
            ),
        )
    ]

    return SequenceBundlePlan(
        bundle_dir=str(bundle_path),
        dataset_title=dataset_title or variant_path.stem,
        version=version,
        dataset_type="variome",
        primary_file_path=str(variant_path.resolve()),
        organism=organism,
        
        assets=assets,
        bundle_meta=bundle_meta,
    )


def _find_dataset_id_by_title(db, dataset_title: str) -> int | None:
    rows = dataset_registry_db.get_data(db=db, filters={"title": dataset_title})
    dataset_ids = sorted({item.dataset_id for item in rows if item.dataset_id})
    if len(dataset_ids) > 1:
        raise HTTPException(status_code=400, detail=f"multiple datasets found with title: {dataset_title}")
    return dataset_ids[0] if dataset_ids else None


def _ensure_dataset_primary_file(db, dataset_id: int, primary_file_path: str, dataset_title: str, dataset_type: str):
    database_obj = db.query(DatasetRegistry).filter(DatasetRegistry.id == dataset_id).first()
    primary_file_obj = dataset_legacy_bridge.get_primary_file(db=db, dataset_id=dataset_id)
    file_suffix = _guess_file_format(Path(primary_file_path))
    now = datetime.now(timezone.utc)

    dataset_legacy_bridge.update_database(
        db=db,
        db_obj=database_obj,
        obj_in={
            "name": dataset_title,
            "type": dataset_type,
        },
    )

    if primary_file_obj:
        dataset_legacy_bridge.update_primary_file(
            db=db,
            db_obj=primary_file_obj,
            obj_in={
                "name": dataset_title,
                "file_name": Path(primary_file_path).stem,
                "path": primary_file_path,
                "type": f".{file_suffix}" if file_suffix else primary_file_obj.type,
                "data_type": dataset_type,
                "size": Path(primary_file_path).stat().st_size,
            },
        )
        return

    dataset_legacy_bridge.create_primary_file(
        db=db,
        obj_in={
            "uid": str(uuid.uuid4()),
            "size": Path(primary_file_path).stat().st_size,
            "name": dataset_title,
            "file_name": Path(primary_file_path).stem,
            "path": primary_file_path,
            "type": f".{file_suffix}" if file_suffix else Path(primary_file_path).suffix,
            "data_type": dataset_type,
            "dataset_id": dataset_id,
            "status": 1,
            "create_time": now,
        },
    )


def _ensure_dataset_ready(db, dataset_id: int, user, detail: str):
    dataset_payload = dataset_domain_service.get_dataset(db=db, dataset_id=dataset_id, user=user)
    current_state = dataset_payload["lifecycle_state"]
    if current_state in {"ready", "public"}:
        return dataset_payload
    if current_state not in READY_TRANSITION_PATH:
        raise HTTPException(status_code=400, detail=f"unsupported dataset lifecycle state for provisioning: {current_state}")

    current_index = READY_TRANSITION_PATH.index(current_state)
    for next_state in READY_TRANSITION_PATH[current_index + 1 :]:
        dataset_payload = dataset_domain_service.transition_state(
            db=db,
            dataset_id=dataset_id,
            request_data=SimpleNamespace(
                id=dataset_id,
                target_state=next_state,
                task_type="sync",
                status="success",
                detail=detail,
            ),
            user=user,
        )
    return dataset_payload


def _ensure_version(db, dataset_id: int, plan: SequenceBundlePlan, user):
    primary_asset = next((item for item in plan.assets if item.is_query_entry), None) or (plan.assets[0] if plan.assets else None)
    update_payload = SimpleNamespace(
        id=dataset_id,
        title=plan.dataset_title,
        dataset_type=plan.dataset_type,
        version=plan.version,
        organism=plan.organism,
        
        file_format=_guess_file_format(Path(plan.primary_file_path)),
        query_engine=primary_asset.query_engine if primary_asset else "file",
        validation_summary=None,
        index_summary=None,
        meta_json=json.dumps(
            {
                "bundle": plan.bundle_meta,
                "provisioning": {
                    "mode": f"{plan.dataset_type}_bundle",
                    "primary_file_path": plan.primary_file_path,
                },
            },
            ensure_ascii=False,
        ),
    )
    dataset_domain_service.update_dataset(db=db, dataset_id=dataset_id, request_data=update_payload, user=user)
    version_obj = dataset_domain_service.sync_current_version_from_dataset_id(db=db, dataset_id=dataset_id)
    if not version_obj:
        raise HTTPException(status_code=500, detail=f"failed to create or sync dataset version for dataset={dataset_id}")
    return version_obj


def _build_asset_meta(plan: SequenceBundlePlan, asset_plan: BundleAssetPlan) -> str:
    payload = {
        "bundle_dir": plan.bundle_dir,
        "bundle_version": plan.version,
        "asset_code": asset_plan.asset_code,
        "asset_type": asset_plan.asset_type,
    }
    payload.update(asset_plan.meta)
    return json.dumps(payload, ensure_ascii=False)


def _find_query_entry_asset(db, version_id: int, user):
    asset_rows = dataset_domain_service.list_dataset_assets(db=db, version_id=version_id, user=user)["items"]
    if not asset_rows:
        return None
    return next((item for item in asset_rows if item["is_query_entry"]), asset_rows[0])


def _asset_preference_key(asset_payload: dict[str, Any]) -> tuple[int, int, int, int]:
    return (
        int(bool(asset_payload.get("is_query_entry"))),
        int(asset_payload.get("workflow_state") == "ready"),
        int(bool(asset_payload.get("meta_json"))),
        -(asset_payload.get("id") or 0),
    )


def _ensure_asset(db, version_id: int, plan: SequenceBundlePlan, asset_plan: BundleAssetPlan, user):
    existing_rows = dataset_domain_service.list_dataset_assets(db=db, version_id=version_id, user=user)["items"]
    existing = next((item for item in existing_rows if item["asset_code"] == asset_plan.asset_code), None)
    meta_json = _build_asset_meta(plan, asset_plan)

    if existing:
        asset_payload = dataset_domain_service.update_dataset_asset(
            db=db,
            asset_id=existing["id"],
            request_data=SimpleNamespace(
                id=existing["id"],
                asset_name=asset_plan.asset_name,
                asset_type=asset_plan.asset_type,
                file_format=asset_plan.file_format,
                query_engine=asset_plan.query_engine,
                storage_backend="local",
                workflow_state="ready",
                status="active",
                is_required=True,
                is_query_entry=asset_plan.is_query_entry,
                display_order=asset_plan.display_order,
                meta_json=meta_json,
            ),
            user=user,
        )
    else:
        asset_payload = dataset_domain_service.create_dataset_asset(
            db=db,
            request_data=SimpleNamespace(
                version_id=version_id,
                asset_code=asset_plan.asset_code,
                asset_name=asset_plan.asset_name,
                asset_type=asset_plan.asset_type,
                file_format=asset_plan.file_format,
                query_engine=asset_plan.query_engine,
                storage_backend="local",
                workflow_state="ready",
                status="active",
                is_required=True,
                is_query_entry=asset_plan.is_query_entry,
                display_order=asset_plan.display_order,
                meta_json=meta_json,
                local_path=None,
            ),
            user=user,
        )

    primary_file = dataset_domain_service.register_asset_file(
        db=db,
        request_data=SimpleNamespace(
            asset_id=asset_payload["id"],
            file_role="primary",
            asset_file_type_code=asset_plan.primary_asset_file_type_code,
            local_path=asset_plan.local_path,
            file_format=asset_plan.file_format,
            index_of_file_id=None,
            status="active",
            meta_json=json.dumps(asset_plan.primary_file_meta, ensure_ascii=False) if asset_plan.primary_file_meta else None,
        ),
        user=user,
    )

    for companion in asset_plan.companion_files:
        dataset_domain_service.register_asset_file(
            db=db,
                request_data=SimpleNamespace(
                    asset_id=asset_payload["id"],
                    file_role=companion.file_role,
                    asset_file_type_code=companion.asset_file_type_code,
                    local_path=companion.local_path,
                    file_format=companion.file_format,
                    index_of_file_id=primary_file["id"] if companion.file_role == "index" else None,
                    status="active",
                    meta_json=json.dumps(companion.meta, ensure_ascii=False) if companion.meta else None,
                ),
                user=user,
            )

    return dataset_domain_service.get_dataset_asset(db=db, asset_id=asset_payload["id"], user=user)


def _dedupe_version_assets(db, version_id: int, user):
    asset_rows = dataset_domain_service.list_dataset_assets(db=db, version_id=version_id, user=user)["items"]
    by_code: dict[str, list[dict[str, Any]]] = {}
    for item in asset_rows:
        by_code.setdefault(item["asset_code"], []).append(item)
    for items in by_code.values():
        if len(items) <= 1:
            continue
        sorted_items = sorted(items, key=_asset_preference_key, reverse=True)
        keep = sorted_items[0]
        for duplicate in sorted_items[1:]:
            dataset_domain_service.delete_dataset_asset(db=db, asset_id=duplicate["id"], user=user)
    return dataset_domain_service.list_dataset_assets(db=db, version_id=version_id, user=user)["items"]


def _remove_bundle_bootstrap_assets(db, version_id: int, plan: SequenceBundlePlan, user):
    asset_rows = dataset_domain_service.list_dataset_assets(db=db, version_id=version_id, user=user)["items"]
    planned_codes = {item.asset_code for item in plan.assets}
    planned_signatures = {
        (item.asset_type, str(Path(item.local_path).resolve()))
        for item in plan.assets
    }
    for asset_payload in asset_rows:
        if asset_payload["asset_code"] in planned_codes:
            continue
        files = asset_payload.get("files") or []
        primary_file = next((item for item in files if item.get("file_role") == "primary"), None)
        if primary_file is None or not primary_file.get("local_path"):
            continue
        signature = (
            asset_payload.get("asset_type"),
            str(Path(primary_file["local_path"]).resolve()),
        )
        if signature not in planned_signatures:
            continue
        dataset_domain_service.delete_dataset_asset(db=db, asset_id=asset_payload["id"], user=user)
    return dataset_domain_service.list_dataset_assets(db=db, version_id=version_id, user=user)["items"]


def _apply_bundle_publish_policy(db, dataset_id: int, version_id: int, bundle_dir: str, publish: bool, user):
    dataset_payload = dataset_domain_service.get_dataset(db=db, dataset_id=dataset_id, user=user)
    version_payload = dataset_domain_service.get_dataset_version(db=db, version_id=version_id, user=user)

    if not publish:
        if dataset_payload.get("default_public_version_id"):
            dataset_domain_service.unpublish_dataset(
                db=db,
                dataset_id=dataset_id,
                request_data=SimpleNamespace(id=dataset_id, note=f"keep provisioned bundle private {bundle_dir}"),
                user=user,
            )
        if version_payload["release_state"] != "unreleased":
            dataset_domain_service.withdraw_dataset_version(
                db=db,
                version_id=version_id,
                request_data=SimpleNamespace(id=version_id, note=f"reset release state for private bundle {bundle_dir}"),
                user=user,
            )
        dataset_payload = dataset_domain_service.get_dataset(db=db, dataset_id=dataset_id, user=user)
        version_payload = dataset_domain_service.get_dataset_version(db=db, version_id=version_id, user=user)
        return dataset_payload, version_payload

    if dataset_payload["lifecycle_state"] == "ready":
        dataset_payload = dataset_domain_service.publish_dataset(
            db=db,
            dataset_id=dataset_id,
            request_data=SimpleNamespace(id=dataset_id, note=f"publish provisioned bundle {bundle_dir}"),
            user=user,
        )
        version_payload = dataset_domain_service.get_dataset_version(db=db, version_id=version_id, user=user)
    return dataset_payload, version_payload


def _ensure_version_lineage(
    db,
    *,
    src_version_id: int,
    dst_version_id: int,
    relation_type: str,
    user,
    src_asset_id: int | None = None,
    dst_asset_id: int | None = None,
    detail_json: str | None = None,
):
    existing_rows = dataset_domain_service.list_dataset_lineage(db=db, version_id=src_version_id, limit=200, user=user)["items"]
    for row in existing_rows:
        if row["src_version_id"] != src_version_id:
            continue
        if row["dst_version_id"] != dst_version_id:
            continue
        if row["relation_type"] != relation_type:
            continue
        if row["src_asset_id"] != src_asset_id:
            continue
        if row["dst_asset_id"] != dst_asset_id:
            continue
        return row

    return dataset_domain_service.create_dataset_lineage(
        db=db,
        request_data=SimpleNamespace(
            src_version_id=src_version_id,
            dst_version_id=dst_version_id,
            relation_type=relation_type,
            src_asset_id=src_asset_id,
            dst_asset_id=dst_asset_id,
            detail_json=detail_json,
        ),
        user=user,
    )


def provision_sequence_bundle(
    db,
    *,
    bundle_dir: str | Path,
    user,
    dataset_title: str | None = None,
    version: str = "v1",
    dataset_id: int | None = None,
    project_id: int = 0,
    team_id: int = 0,
    organism: str | None = None,
    publish: bool = False,
) -> dict[str, Any]:
    plan = discover_sequence_bundle(
        bundle_dir,
        dataset_title=dataset_title,
        version=version,
        organism=organism,
        
    )

    target_dataset_id = dataset_id or _find_dataset_id_by_title(db=db, dataset_title=plan.dataset_title)

    if target_dataset_id is None:
        dataset_payload = dataset_domain_service.register_dataset_source(
            db=db,
            request_data=SimpleNamespace(
                file_path=plan.primary_file_path,
                name=plan.dataset_title,
                dataset_type="genome",
                remark="provisioned from sequence bundle",
                
                dry_run=False,
                project_id=project_id,
                team_id=team_id,
            ),
            user=user,
        )
        target_dataset_id = dataset_payload["id"]

    _ensure_dataset_primary_file(
        db=db,
        dataset_id=target_dataset_id,
        primary_file_path=plan.primary_file_path,
        dataset_title=plan.dataset_title,
        dataset_type=plan.dataset_type,
    )
    version_obj = _ensure_version(db=db, dataset_id=target_dataset_id, plan=plan, user=user)
    _ensure_dataset_ready(
        db=db,
        dataset_id=target_dataset_id,
        user=user,
        detail=f"provision sequence bundle {plan.bundle_dir}",
    )

    ensured_assets = [
        _ensure_asset(db=db, version_id=version_obj.id, plan=plan, asset_plan=asset_plan, user=user)
        for asset_plan in plan.assets
    ]
    _dedupe_version_assets(db=db, version_id=version_obj.id, user=user)
    _remove_bundle_bootstrap_assets(db=db, version_id=version_obj.id, plan=plan, user=user)
    refreshed_version_obj = _ensure_version(db=db, dataset_id=target_dataset_id, plan=plan, user=user)
    if refreshed_version_obj.id != version_obj.id:
        version_obj = refreshed_version_obj
        ensured_assets = [
            _ensure_asset(db=db, version_id=version_obj.id, plan=plan, asset_plan=asset_plan, user=user)
            for asset_plan in plan.assets
        ]
        _dedupe_version_assets(db=db, version_id=version_obj.id, user=user)
        _remove_bundle_bootstrap_assets(db=db, version_id=version_obj.id, plan=plan, user=user)
    else:
        version_obj = refreshed_version_obj
        ensured_assets = dataset_domain_service.list_dataset_assets(db=db, version_id=version_obj.id, user=user)["items"]

    dataset_payload, version_payload = _apply_bundle_publish_policy(
        db=db,
        dataset_id=target_dataset_id,
        version_id=version_obj.id,
        bundle_dir=plan.bundle_dir,
        publish=publish,
        user=user,
    )

    return {
        "dataset": dataset_payload,
        "version": version_payload,
        "plan": plan.to_dict(),
        "ensured_asset_codes": [item["asset_code"] for item in ensured_assets],
        "published": bool(publish),
    }


def provision_expression_bundle(
    db,
    *,
    bundle_dir: str | Path,
    user,
    dataset_title: str | None = None,
    version: str = "v1",
    dataset_id: int | None = None,
    project_id: int = 0,
    team_id: int = 0,
    organism: str | None = None,
    reference_version_id: int | None = None,
    publish: bool = False,
) -> dict[str, Any]:
    plan = discover_expression_bundle(
        bundle_dir,
        dataset_title=dataset_title,
        version=version,
        organism=organism,
        
    )

    target_dataset_id = dataset_id or _find_dataset_id_by_title(db=db, dataset_title=plan.dataset_title)

    if target_dataset_id is None:
        dataset_payload = dataset_domain_service.register_dataset_source(
            db=db,
            request_data=SimpleNamespace(
                file_path=plan.primary_file_path,
                name=plan.dataset_title,
                dataset_type="transcriptome",
                remark="provisioned from expression bundle",
                
                dry_run=False,
                project_id=project_id,
                team_id=team_id,
            ),
            user=user,
        )
        target_dataset_id = dataset_payload["id"]

    _ensure_dataset_primary_file(
        db=db,
        dataset_id=target_dataset_id,
        primary_file_path=plan.primary_file_path,
        dataset_title=plan.dataset_title,
        dataset_type=plan.dataset_type,
    )
    version_obj = _ensure_version(db=db, dataset_id=target_dataset_id, plan=plan, user=user)
    _ensure_dataset_ready(
        db=db,
        dataset_id=target_dataset_id,
        user=user,
        detail=f"provision expression bundle {plan.bundle_dir}",
    )

    ensured_assets = [
        _ensure_asset(db=db, version_id=version_obj.id, plan=plan, asset_plan=asset_plan, user=user)
        for asset_plan in plan.assets
    ]
    _dedupe_version_assets(db=db, version_id=version_obj.id, user=user)
    _remove_bundle_bootstrap_assets(db=db, version_id=version_obj.id, plan=plan, user=user)
    refreshed_version_obj = _ensure_version(db=db, dataset_id=target_dataset_id, plan=plan, user=user)
    if refreshed_version_obj.id != version_obj.id:
        version_obj = refreshed_version_obj
        ensured_assets = [
            _ensure_asset(db=db, version_id=version_obj.id, plan=plan, asset_plan=asset_plan, user=user)
            for asset_plan in plan.assets
        ]
        _dedupe_version_assets(db=db, version_id=version_obj.id, user=user)
        _remove_bundle_bootstrap_assets(db=db, version_id=version_obj.id, plan=plan, user=user)
    else:
        version_obj = refreshed_version_obj
        ensured_assets = dataset_domain_service.list_dataset_assets(db=db, version_id=version_obj.id, user=user)["items"]
    ensured_assets_by_code = {item["asset_code"]: item for item in ensured_assets}

    lineage_payload = None
    if reference_version_id is not None:
        source_asset = ensured_assets_by_code.get("expression_matrix")
        target_asset = _find_query_entry_asset(db=db, version_id=reference_version_id, user=user)
        lineage_payload = _ensure_version_lineage(
            db=db,
            src_version_id=version_obj.id,
            dst_version_id=reference_version_id,
            relation_type="quantified_against",
            user=user,
            src_asset_id=source_asset["id"] if source_asset else None,
            dst_asset_id=target_asset["id"] if target_asset else None,
            detail_json=json.dumps(
                {
                    "bundle_dir": plan.bundle_dir,
                    "mode": "expression_bundle",
                    "reference_version_id": reference_version_id,
                },
                ensure_ascii=False,
            ),
        )

    dataset_payload, version_payload = _apply_bundle_publish_policy(
        db=db,
        dataset_id=target_dataset_id,
        version_id=version_obj.id,
        bundle_dir=plan.bundle_dir,
        publish=publish,
        user=user,
    )

    result = {
        "dataset": dataset_payload,
        "version": version_payload,
        "plan": plan.to_dict(),
        "ensured_asset_codes": [item["asset_code"] for item in ensured_assets],
        "published": bool(publish),
    }
    if lineage_payload is not None:
        result["lineage"] = lineage_payload
    return result


def provision_variome_bundle(
    db,
    *,
    bundle_dir: str | Path,
    user,
    dataset_title: str | None = None,
    version: str = "v1",
    dataset_id: int | None = None,
    project_id: int = 0,
    team_id: int = 0,
    organism: str | None = None,
    primary_file: str | Path | None = None,
    reference_version_id: int | None = None,
    publish: bool = False,
) -> dict[str, Any]:
    plan = discover_variome_bundle(
        bundle_dir,
        dataset_title=dataset_title,
        version=version,
        organism=organism,
        
        primary_file=primary_file,
    )

    target_dataset_id = dataset_id or _find_dataset_id_by_title(db=db, dataset_title=plan.dataset_title)

    if target_dataset_id is None:
        dataset_payload = dataset_domain_service.register_dataset_source(
            db=db,
            request_data=SimpleNamespace(
                file_path=plan.primary_file_path,
                name=plan.dataset_title,
                dataset_type="variome",
                remark="provisioned from variome bundle",
                
                dry_run=False,
                project_id=project_id,
                team_id=team_id,
            ),
            user=user,
        )
        target_dataset_id = dataset_payload["id"]

    _ensure_dataset_primary_file(
        db=db,
        dataset_id=target_dataset_id,
        primary_file_path=plan.primary_file_path,
        dataset_title=plan.dataset_title,
        dataset_type=plan.dataset_type,
    )
    version_obj = _ensure_version(db=db, dataset_id=target_dataset_id, plan=plan, user=user)
    _ensure_dataset_ready(
        db=db,
        dataset_id=target_dataset_id,
        user=user,
        detail=f"provision variome bundle {plan.bundle_dir}",
    )

    ensured_assets = [
        _ensure_asset(db=db, version_id=version_obj.id, plan=plan, asset_plan=asset_plan, user=user)
        for asset_plan in plan.assets
    ]
    _dedupe_version_assets(db=db, version_id=version_obj.id, user=user)
    _remove_bundle_bootstrap_assets(db=db, version_id=version_obj.id, plan=plan, user=user)
    refreshed_version_obj = _ensure_version(db=db, dataset_id=target_dataset_id, plan=plan, user=user)
    if refreshed_version_obj.id != version_obj.id:
        version_obj = refreshed_version_obj
        ensured_assets = [
            _ensure_asset(db=db, version_id=version_obj.id, plan=plan, asset_plan=asset_plan, user=user)
            for asset_plan in plan.assets
        ]
        _dedupe_version_assets(db=db, version_id=version_obj.id, user=user)
        _remove_bundle_bootstrap_assets(db=db, version_id=version_obj.id, plan=plan, user=user)
    else:
        version_obj = refreshed_version_obj
        ensured_assets = dataset_domain_service.list_dataset_assets(db=db, version_id=version_obj.id, user=user)["items"]
    ensured_assets_by_code = {item["asset_code"]: item for item in ensured_assets}

    lineage_payload = None
    if reference_version_id is not None:
        source_asset = ensured_assets_by_code.get("variant_calls")
        target_asset = _find_query_entry_asset(db=db, version_id=reference_version_id, user=user)
        lineage_payload = _ensure_version_lineage(
            db=db,
            src_version_id=version_obj.id,
            dst_version_id=reference_version_id,
            relation_type="called_against",
            user=user,
            src_asset_id=source_asset["id"] if source_asset else None,
            dst_asset_id=target_asset["id"] if target_asset else None,
            detail_json=json.dumps(
                {
                    "bundle_dir": plan.bundle_dir,
                    "mode": "variome_bundle",
                    "reference_version_id": reference_version_id,
                },
                ensure_ascii=False,
            ),
        )

    dataset_payload, version_payload = _apply_bundle_publish_policy(
        db=db,
        dataset_id=target_dataset_id,
        version_id=version_obj.id,
        bundle_dir=plan.bundle_dir,
        publish=publish,
        user=user,
    )

    result = {
        "dataset": dataset_payload,
        "version": version_payload,
        "plan": plan.to_dict(),
        "ensured_asset_codes": [item["asset_code"] for item in ensured_assets],
        "published": bool(publish),
    }
    if lineage_payload is not None:
        result["lineage"] = lineage_payload
    return result
