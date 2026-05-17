import os
import json
import uuid
from datetime import date, datetime

from fastapi.encoders import jsonable_encoder
from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import aliased

from .crud import (
    breeding_assay_db,
    breeding_biosample_db,
    breeding_data_file_db,
    breeding_dataset_assay_link_db,
    breeding_dataset_subject_link_db,
    breeding_material_db,
    breeding_observation_db,
    breeding_phenotype_subject_map_db,
    breeding_plot_db,
    breeding_program_db,
    breeding_trial_db,
    breeding_variant_sample_map_db,
)
from .germplasm_import import (
    load_validation_bundle,
    normalize_template_profile,
    update_validation_bundle,
    validate_germplasm_file,
    write_validation_bundle,
)
from .models import (
    BreedingAssay,
    BreedingBioSample,
    BreedingDataFile,
    BreedingDatasetAssayLink,
    BreedingDatasetSubjectLink,
    BreedingGermplasm,
    BreedingGermplasmImportBatch,
    BreedingGermplasmLineage,
    BreedingMaterial,
    BreedingObservation,
    BreedingPhenotypeSubjectMap,
    BreedingPlot,
    BreedingProgram,
    BreedingTaxonomyName,
    BreedingTaxonomyNode,
    BreedingTrial,
    BreedingVariantSampleMap,
)
from .ncbi_taxonomy import ncbi_taxonomy_client


class BreedingDomainService:
    @staticmethod
    def _paginate(query, page, size):
        total = query.count()
        if page and size:
            query = query.offset((page - 1) * size).limit(size)
        return total, query.all()

    @staticmethod
    def _serialize_rows(rows):
        return [jsonable_encoder(item) for item in rows]

    @staticmethod
    def _count(query):
        return query.scalar() or 0

    @staticmethod
    def _decode_json_object(raw_value, default):
        if not raw_value:
            return default
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            return default

    @classmethod
    def _apply_germplasm_field_schema(cls, attributes_json, field_schema_json):
        attributes = cls._decode_json_object(attributes_json, {})
        field_schema = cls._decode_json_object(field_schema_json, [])
        if not isinstance(attributes, dict):
            attributes = {}
        if not isinstance(field_schema, list) or not field_schema:
            return attributes, []

        label_map = {}
        for item in field_schema:
            if not isinstance(item, dict):
                continue
            if item.get("is_builtin"):
                continue
            field_key = item.get("field_key")
            field_label = item.get("field_label") or item.get("source_header") or field_key
            if field_key:
                label_map[field_key] = field_label

        display_attributes = {}
        for field_key, value in attributes.items():
            display_attributes[label_map.get(field_key, field_key)] = value
        return display_attributes, field_schema

    @staticmethod
    def _coerce_iso_date(value):
        if isinstance(value, date):
            return value
        if isinstance(value, str) and value:
            return date.fromisoformat(value)
        return value

    @staticmethod
    def _normalize_taxonomy_record(record):
        if not record:
            return None
        return {
            "tax_id": int(record["tax_id"]),
            "scientific_name": record.get("scientific_name"),
            "common_name": record.get("common_name"),
            "rank": record.get("rank"),
            "parent_tax_id": record.get("parent_tax_id"),
            "lineage": record.get("lineage"),
            "lineage_ids": [],  # NCBI sync cannot provide full lineage_ids
            "source": record.get("source") or "ncbi_sync",
            "is_active": int(record.get("is_active", 1) or 0),
            "ncbi_sync_time": record.get("last_sync_time") or datetime.utcnow(),
        }

    def _upsert_taxonomy_node_records(self, db, records):
        synced_items = []
        for record in records:
            normalized = self._normalize_taxonomy_record(record)
            if not normalized:
                continue
            row = db.query(BreedingTaxonomyNode).filter(BreedingTaxonomyNode.tax_id == normalized["tax_id"]).first()
            if row is None:
                row = BreedingTaxonomyNode(**normalized)
                db.add(row)
            else:
                for field, value in normalized.items():
                    if field == "lineage_ids" and not value:
                        continue
                    setattr(row, field, value)
                row.updated_at = datetime.utcnow()
                db.add(row)
            synced_items.append(
                {
                    "tax_id": normalized["tax_id"],
                    "scientific_name": normalized["scientific_name"],
                    "common_name": normalized["common_name"],
                    "rank": normalized["rank"],
                    "lineage": normalized["lineage"],
                    "source": normalized["source"],
                }
            )
        if synced_items:
            db.commit()
        return synced_items

    def _build_taxonomy_node_query(self, db, request_data):
        query = db.query(BreedingTaxonomyNode)
        if getattr(request_data, "active_only", 1):
            query = query.filter(BreedingTaxonomyNode.is_active == 1)
        if getattr(request_data, "tax_id", None):
            query = query.filter(BreedingTaxonomyNode.tax_id == int(request_data.tax_id))
        if getattr(request_data, "keyword", None):
            keyword = f"%{request_data.keyword}%"
            query = query.filter(
                or_(
                    BreedingTaxonomyNode.scientific_name.ilike(keyword),
                    BreedingTaxonomyNode.common_name.ilike(keyword),
                    cast(BreedingTaxonomyNode.tax_id, String).ilike(keyword),
                )
            )
        return query

    def _build_taxonomy_germplasm_count_map(self, db, tax_ids):
        if not tax_ids:
            return {}
        count_rows = (
            db.query(BreedingGermplasm.taxonomy_tax_id, func.count(BreedingGermplasm.id))
            .filter(BreedingGermplasm.taxonomy_tax_id.in_(tax_ids))
            .group_by(BreedingGermplasm.taxonomy_tax_id)
            .all()
        )
        return {tax_id: int(total or 0) for tax_id, total in count_rows}

    def _list_existing_germplasm_taxonomy_options(self, db, request_data, limit):
        query = (
            db.query(
                BreedingTaxonomyNode.tax_id,
                BreedingTaxonomyNode.scientific_name,
                BreedingTaxonomyNode.common_name,
                BreedingTaxonomyNode.rank,
                BreedingTaxonomyNode.lineage,
                BreedingTaxonomyNode.source,
                BreedingTaxonomyNode.ncbi_sync_time,
                func.count(BreedingGermplasm.id).label("germplasm_count"),
            )
            .join(BreedingGermplasm, BreedingGermplasm.taxonomy_tax_id == BreedingTaxonomyNode.tax_id)
            .filter(BreedingGermplasm.status == "active")
        )
        if getattr(request_data, "active_only", 1):
            query = query.filter(BreedingTaxonomyNode.is_active == 1)
        if getattr(request_data, "tax_id", None):
            query = query.filter(BreedingTaxonomyNode.tax_id == int(request_data.tax_id))
        if getattr(request_data, "keyword", None):
            keyword = f"%{request_data.keyword}%"
            query = query.filter(
                or_(
                    BreedingTaxonomyNode.scientific_name.ilike(keyword),
                    BreedingTaxonomyNode.common_name.ilike(keyword),
                    cast(BreedingTaxonomyNode.tax_id, String).ilike(keyword),
                )
            )
        rows = (
            query.group_by(
                BreedingTaxonomyNode.tax_id,
                BreedingTaxonomyNode.scientific_name,
                BreedingTaxonomyNode.common_name,
                BreedingTaxonomyNode.rank,
                BreedingTaxonomyNode.lineage,
                BreedingTaxonomyNode.source,
                BreedingTaxonomyNode.ncbi_sync_time,
            )
            .order_by(BreedingTaxonomyNode.scientific_name.asc())
            .limit(limit)
            .all()
        )
        items = []
        for row in rows:
            items.append(
                {
                    "tax_id": row.tax_id,
                    "scientific_name": row.scientific_name,
                    "common_name": row.common_name,
                    "rank": row.rank,
                    "lineage": row.lineage,
                    "source": row.source,
                    "ncbi_sync_time": row.ncbi_sync_time,
                    "germplasm_count": int(row.germplasm_count or 0),
                }
            )
        return {"items": items, "total": len(items), "source_mode": "germplasm"}

    @staticmethod
    def _compare_taxonomy_node_row(local_row, remote_record):
        compare_fields = [
            ("scientific_name", "scientific_name"),
            ("common_name", "common_name"),
            ("rank", "rank"),
            ("parent_tax_id", "parent_tax_id"),
            ("lineage", "lineage"),
        ]
        mismatches = []
        for local_field, remote_field in compare_fields:
            local_value = getattr(local_row, local_field, None)
            remote_value = remote_record.get(remote_field)
            if local_value != remote_value:
                mismatches.append(
                    {
                        "field": local_field,
                        "local_value": local_value,
                        "remote_value": remote_value,
                    }
                )
        return mismatches

    def _build_local_taxonomy_query(self, db, request_data):
        query = db.query(BreedingTaxonomyNode)
        if getattr(request_data, "active_only", 1):
            query = query.filter(BreedingTaxonomyNode.is_active == 1)
        if getattr(request_data, "tax_id", None):
            query = query.filter(BreedingTaxonomyNode.tax_id == int(request_data.tax_id))
        if getattr(request_data, "keyword", None):
            keyword = f"%{request_data.keyword}%"
            name_tax_ids = (
                db.query(BreedingTaxonomyName.tax_id)
                .filter(BreedingTaxonomyName.name_txt.ilike(keyword))
                .distinct()
            )
            query = query.filter(
                or_(
                    BreedingTaxonomyNode.scientific_name.ilike(keyword),
                    BreedingTaxonomyNode.common_name.ilike(keyword),
                    cast(BreedingTaxonomyNode.tax_id, String).ilike(keyword),
                    BreedingTaxonomyNode.tax_id.in_(name_tax_ids),
                )
            )
        return query

    def _search_local_taxonomy_rows(self, db, *, keyword, limit, active_only=1):
        text = str(keyword or "").strip()
        if not text:
            return []

        def node_base_query():
            query = db.query(BreedingTaxonomyNode)
            if active_only:
                query = query.filter(BreedingTaxonomyNode.is_active == 1)
            return query

        def name_tax_ids(pattern, *, exact=False):
            query = db.query(BreedingTaxonomyName.tax_id).distinct()
            if exact:
                query = query.filter(BreedingTaxonomyName.name_txt == pattern)
            else:
                query = query.filter(BreedingTaxonomyName.name_txt.ilike(pattern))
            return [row[0] for row in query.limit(limit).all()]

        found_ids = []
        seen = set()

        def extend_ids(tax_ids):
            for tax_id in tax_ids:
                if tax_id in seen:
                    continue
                seen.add(tax_id)
                found_ids.append(tax_id)
                if len(found_ids) >= limit:
                    break

        exact_ids = [
            row[0]
            for row in node_base_query()
            .with_entities(BreedingTaxonomyNode.tax_id)
            .filter(
                or_(
                    BreedingTaxonomyNode.scientific_name == text,
                    BreedingTaxonomyNode.common_name == text,
                    cast(BreedingTaxonomyNode.tax_id, String) == text,
                )
            )
            .limit(limit)
            .all()
        ]
        extend_ids(exact_ids)
        if len(found_ids) < limit:
            extend_ids(name_tax_ids(text, exact=True))

        if len(found_ids) < limit:
            prefix = f"{text}%"
            prefix_ids = [
                row[0]
                for row in node_base_query()
                .with_entities(BreedingTaxonomyNode.tax_id)
                .filter(
                    or_(
                        BreedingTaxonomyNode.scientific_name.ilike(prefix),
                        BreedingTaxonomyNode.common_name.ilike(prefix),
                    )
                )
                .limit(limit)
                .all()
            ]
            extend_ids(prefix_ids)
        if len(found_ids) < limit:
            extend_ids(name_tax_ids(f"{text}%", exact=False))

        if len(found_ids) < limit:
            contains = f"%{text}%"
            contains_ids = [
                row[0]
                for row in node_base_query()
                .with_entities(BreedingTaxonomyNode.tax_id)
                .filter(
                    or_(
                        BreedingTaxonomyNode.scientific_name.ilike(contains),
                        BreedingTaxonomyNode.common_name.ilike(contains),
                    )
                )
                .limit(limit)
                .all()
            ]
            extend_ids(contains_ids)
        if len(found_ids) < limit:
            extend_ids(name_tax_ids(f"%{text}%", exact=False))

        if not found_ids:
            return []

        rows = (
            node_base_query()
            .filter(BreedingTaxonomyNode.tax_id.in_(found_ids))
            .all()
        )
        row_map = {row.tax_id: row for row in rows}
        return [row_map[tax_id] for tax_id in found_ids if tax_id in row_map][:limit]

    def _serialize_local_taxonomy_row(self, row):
        return {
            "tax_id": row.tax_id,
            "scientific_name": row.scientific_name,
            "common_name": row.common_name,
            "rank": row.rank,
            "parent_tax_id": row.parent_tax_id,
            "lineage": row.lineage,
            "lineage_ids": row.lineage_ids or [],
            "source": row.source or "plant_dump",
            "is_active": row.is_active,
            "last_sync_time": getattr(row, "ncbi_sync_time", None),
        }

    def _ensure_taxonomy_node_from_local_row(self, db, row):
        return row

    def _ensure_taxonomy_node_from_local_rows(self, db, rows):
        return {row.tax_id: row for row in rows}

    def _resolve_taxonomy_node_row(self, db, tax_id):
        return db.query(BreedingTaxonomyNode).filter(BreedingTaxonomyNode.tax_id == tax_id).first()

    def sync_germplasm_taxonomy_cache(self, db, request_data):
        records = []
        tax_id = getattr(request_data, "tax_id", None)
        keyword = str(getattr(request_data, "keyword", "") or "").strip()
        limit = max(1, min(int(getattr(request_data, "limit", 20) or 20), 100))
        force_refresh = int(getattr(request_data, "force_refresh", 0) or 0)

        if tax_id:
            local_row = db.query(BreedingTaxonomyNode).filter(BreedingTaxonomyNode.tax_id == int(tax_id)).first()
            if local_row is not None:
                cache_row = self._ensure_taxonomy_node_from_local_row(db=db, row=local_row)
                return {
                    "items": [
                        {
                            "tax_id": cache_row.tax_id,
                            "scientific_name": cache_row.scientific_name,
                            "common_name": cache_row.common_name,
                            "rank": cache_row.rank,
                            "lineage": cache_row.lineage,
                            "source": "local_dump",
                        }
                    ],
                    "total": 1,
                    "source_mode": "local_dump",
                }
        elif keyword:
            local_rows = self._search_local_taxonomy_rows(
                db=db,
                keyword=keyword,
                limit=limit,
                active_only=getattr(request_data, "active_only", 1),
            )
            if local_rows:
                cache_rows = self._ensure_taxonomy_node_from_local_rows(db=db, rows=local_rows)
                synced_items = []
                for local_row in local_rows:
                    cache_row = cache_rows[local_row.tax_id]
                    synced_items.append(
                        {
                            "tax_id": cache_row.tax_id,
                            "scientific_name": cache_row.scientific_name,
                            "common_name": cache_row.common_name,
                            "rank": cache_row.rank,
                            "lineage": cache_row.lineage,
                            "source": "local_dump",
                        }
                    )
                return {
                    "items": synced_items,
                    "total": len(synced_items),
                    "source_mode": "local_dump",
                }

        if tax_id:
            existing = db.query(BreedingTaxonomyNode).filter(BreedingTaxonomyNode.tax_id == tax_id).first()
            if existing is not None and not force_refresh:
                return {
                    "items": [
                        {
                            "tax_id": existing.tax_id,
                            "scientific_name": existing.scientific_name,
                            "common_name": existing.common_name,
                            "rank": existing.rank,
                            "lineage": existing.lineage,
                            "source": existing.source,
                        }
                    ],
                    "total": 1,
                    "source_mode": "cache",
                }
            record = ncbi_taxonomy_client.fetch_taxon(int(tax_id))
            if record:
                records = [record]
        elif keyword:
            records = ncbi_taxonomy_client.search_taxa(keyword, limit=limit)
        else:
            raise ValueError("tax_id or keyword is required for taxonomy sync")

        synced_items = self._upsert_taxonomy_node_records(db=db, records=records)
        return {
            "items": synced_items,
            "total": len(synced_items),
            "source_mode": "ncbi_sync",
        }

    def audit_germplasm_taxonomy_cache(self, db, request_data):
        limit = max(1, min(int(getattr(request_data, "limit", 20) or 20), 100))
        rows = (
            self._build_taxonomy_node_query(db=db, request_data=request_data)
            .order_by(BreedingTaxonomyNode.scientific_name.asc())
            .limit(limit)
            .all()
        )
        tax_ids = [row.tax_id for row in rows]
        germplasm_counts = self._build_taxonomy_germplasm_count_map(db=db, tax_ids=tax_ids)

        items = []
        summary = {
            "matched": 0,
            "mismatch": 0,
            "not_found": 0,
            "error": 0,
        }
        for row in rows:
            try:
                remote_record = ncbi_taxonomy_client.fetch_taxon(int(row.tax_id))
            except Exception as exc:
                summary["error"] += 1
                items.append(
                    {
                        "tax_id": row.tax_id,
                        "status": "error",
                        "germplasm_count": germplasm_counts.get(row.tax_id, 0),
                        "local": {
                            "scientific_name": row.scientific_name,
                            "common_name": row.common_name,
                            "rank": row.rank,
                            "parent_tax_id": row.parent_tax_id,
                            "lineage": row.lineage,
                            "source": row.source,
                            "ncbi_sync_time": row.ncbi_sync_time,
                        },
                        "remote": None,
                        "mismatches": [],
                        "message": str(exc),
                    }
                )
                continue

            if remote_record is None:
                summary["not_found"] += 1
                items.append(
                    {
                        "tax_id": row.tax_id,
                        "status": "not_found",
                        "germplasm_count": germplasm_counts.get(row.tax_id, 0),
                        "local": {
                            "scientific_name": row.scientific_name,
                            "common_name": row.common_name,
                            "rank": row.rank,
                            "parent_tax_id": row.parent_tax_id,
                            "lineage": row.lineage,
                            "source": row.source,
                            "ncbi_sync_time": row.ncbi_sync_time,
                        },
                        "remote": None,
                        "mismatches": [],
                        "message": "Taxonomy not found in NCBI",
                    }
                )
                continue

            mismatches = self._compare_taxonomy_node_row(local_row=row, remote_record=remote_record)
            status = "matched" if not mismatches else "mismatch"
            summary[status] += 1
            items.append(
                {
                    "tax_id": row.tax_id,
                    "status": status,
                    "germplasm_count": germplasm_counts.get(row.tax_id, 0),
                    "local": {
                        "scientific_name": row.scientific_name,
                        "common_name": row.common_name,
                        "rank": row.rank,
                        "parent_tax_id": row.parent_tax_id,
                        "lineage": row.lineage,
                        "source": row.source,
                        "ncbi_sync_time": row.ncbi_sync_time,
                    },
                    "remote": {
                        "scientific_name": remote_record.get("scientific_name"),
                        "common_name": remote_record.get("common_name"),
                        "rank": remote_record.get("rank"),
                        "parent_tax_id": remote_record.get("parent_tax_id"),
                        "lineage": remote_record.get("lineage"),
                        "source": remote_record.get("source"),
                        "ncbi_sync_time": remote_record.get("ncbi_sync_time"),
                    },
                    "mismatches": mismatches,
                    "message": None if not mismatches else f"{len(mismatches)} fields differ from NCBI",
                }
            )

        return {
            "items": items,
            "total": len(items),
            "summary": summary,
            "source_mode": "audit",
        }

    def resolve_germplasm_import_scope(self, db, *, file_path):
        if not file_path:
            return None

        normalized_path = os.path.abspath(str(file_path))
        source_filename = os.path.basename(normalized_path)
        batch = (
            db.query(BreedingGermplasmImportBatch)
            .filter(BreedingGermplasmImportBatch.source_file_path == normalized_path)
            .order_by(BreedingGermplasmImportBatch.id.desc())
            .first()
        )
        if batch is None:
            batch = (
                db.query(BreedingGermplasmImportBatch)
                .filter(BreedingGermplasmImportBatch.source_filename == source_filename)
                .order_by(BreedingGermplasmImportBatch.id.desc())
                .first()
            )
        if batch is None:
            return None
        return {
            "batch_id": batch.id,
            "batch_code": batch.batch_code,
            "taxonomy_tax_id": batch.taxonomy_tax_id,
            "source_filename": batch.source_filename,
            "source_file_path": batch.source_file_path,
        }

    @staticmethod
    def _program_counts_template():
        return {
            "materials": 0,
            "trials": 0,
            "plots": 0,
            "observations": 0,
            "biosamples": 0,
            "assays": 0,
            "data_files": 0,
        }

    @staticmethod
    def _germplasm_usage_template():
        return {
            "breeding_material_count": 0,
            "breeding_program_count": 0,
            "breeding_program_ids": [],
            "breeding_material_codes": [],
            "breeding_material_names": [],
        }

    def _collect_germplasm_usage_map(self, db, accession_ids):
        if not accession_ids:
            return {}

        rows = (
            db.query(
                BreedingMaterial.germplasm_accession,
                BreedingMaterial.program_id,
                BreedingMaterial.material_code,
                BreedingMaterial.material_name,
            )
            .filter(BreedingMaterial.germplasm_accession.in_(accession_ids))
            .order_by(
                BreedingMaterial.germplasm_accession.asc(),
                BreedingMaterial.program_id.asc(),
                BreedingMaterial.id.asc(),
            )
            .all()
        )
        usage_map = {}
        for germplasm_accession, program_id, material_code, material_name in rows:
            if not germplasm_accession:
                continue
            target = usage_map.setdefault(
                germplasm_accession,
                self._germplasm_usage_template(),
            )
            target["breeding_material_count"] += 1
            if program_id is not None and program_id not in target["breeding_program_ids"]:
                target["breeding_program_ids"].append(program_id)
            if material_code and material_code not in target["breeding_material_codes"]:
                target["breeding_material_codes"].append(material_code)
            if material_name and material_name not in target["breeding_material_names"]:
                target["breeding_material_names"].append(material_name)

        for target in usage_map.values():
            target["breeding_program_count"] = len(target["breeding_program_ids"])
            target["breeding_material_codes"] = target["breeding_material_codes"][:5]
            target["breeding_material_names"] = target["breeding_material_names"][:5]
        return usage_map

    def _collect_program_counts(self, db, program_ids):
        if not program_ids:
            return {}

        counts_map = {
            program_id: self._program_counts_template()
            for program_id in program_ids
        }

        def merge_counts(rows, field_name):
            for program_id, total in rows:
                if program_id in counts_map:
                    counts_map[program_id][field_name] = int(total or 0)

        merge_counts(
            db.query(BreedingMaterial.program_id, func.count(BreedingMaterial.id))
            .filter(BreedingMaterial.program_id.in_(program_ids))
            .group_by(BreedingMaterial.program_id)
            .all(),
            "materials",
        )
        merge_counts(
            db.query(BreedingTrial.program_id, func.count(BreedingTrial.id))
            .filter(BreedingTrial.program_id.in_(program_ids))
            .group_by(BreedingTrial.program_id)
            .all(),
            "trials",
        )
        merge_counts(
            db.query(BreedingTrial.program_id, func.count(BreedingPlot.id))
            .join(BreedingPlot, BreedingPlot.trial_id == BreedingTrial.id)
            .filter(BreedingTrial.program_id.in_(program_ids))
            .group_by(BreedingTrial.program_id)
            .all(),
            "plots",
        )
        merge_counts(
            db.query(BreedingTrial.program_id, func.count(BreedingObservation.id))
            .join(BreedingObservation, BreedingObservation.trial_id == BreedingTrial.id)
            .filter(BreedingTrial.program_id.in_(program_ids))
            .group_by(BreedingTrial.program_id)
            .all(),
            "observations",
        )
        merge_counts(
            db.query(BreedingMaterial.program_id, func.count(BreedingBioSample.id))
            .join(BreedingBioSample, BreedingBioSample.material_id == BreedingMaterial.id)
            .filter(BreedingMaterial.program_id.in_(program_ids))
            .group_by(BreedingMaterial.program_id)
            .all(),
            "biosamples",
        )
        merge_counts(
            db.query(BreedingMaterial.program_id, func.count(BreedingAssay.id))
            .join(BreedingBioSample, BreedingBioSample.material_id == BreedingMaterial.id)
            .join(BreedingAssay, BreedingAssay.biosample_id == BreedingBioSample.id)
            .filter(BreedingMaterial.program_id.in_(program_ids))
            .group_by(BreedingMaterial.program_id)
            .all(),
            "assays",
        )
        merge_counts(
            db.query(BreedingMaterial.program_id, func.count(BreedingDataFile.id))
            .join(BreedingBioSample, BreedingBioSample.material_id == BreedingMaterial.id)
            .join(BreedingAssay, BreedingAssay.biosample_id == BreedingBioSample.id)
            .join(BreedingDataFile, BreedingDataFile.assay_id == BreedingAssay.id)
            .filter(BreedingMaterial.program_id.in_(program_ids))
            .group_by(BreedingMaterial.program_id)
            .all(),
            "data_files",
        )
        return counts_map

    def _collect_program_previews(self, db, program_ids):
        if not program_ids:
            return {}

        preview_map = {
            program_id: {
                "materials": [],
                "traits": [],
                "assay_types": [],
            }
            for program_id in program_ids
        }

        material_rows = (
            db.query(
                BreedingMaterial.program_id,
                BreedingMaterial.material_code,
                BreedingMaterial.material_name,
                BreedingMaterial.is_check,
            )
            .filter(BreedingMaterial.program_id.in_(program_ids))
            .order_by(BreedingMaterial.program_id.asc(), BreedingMaterial.is_check.desc(), BreedingMaterial.id.asc())
            .all()
        )
        for program_id, material_code, material_name, is_check in material_rows:
            target = preview_map.get(program_id)
            if target is None or len(target["materials"]) >= 3:
                continue
            target["materials"].append(
                {
                    "material_code": material_code,
                    "material_name": material_name,
                    "is_check": int(is_check or 0),
                }
            )

        trait_rows = (
            db.query(
                BreedingTrial.program_id,
                BreedingObservation.trait_code,
                BreedingObservation.trait_name,
                func.count(BreedingObservation.id).label("trait_count"),
            )
            .join(BreedingObservation, BreedingObservation.trial_id == BreedingTrial.id)
            .filter(BreedingTrial.program_id.in_(program_ids))
            .group_by(BreedingTrial.program_id, BreedingObservation.trait_code, BreedingObservation.trait_name)
            .order_by(BreedingTrial.program_id.asc(), func.count(BreedingObservation.id).desc(), BreedingObservation.trait_code.asc())
            .all()
        )
        for program_id, trait_code, trait_name, trait_count in trait_rows:
            target = preview_map.get(program_id)
            if target is None or len(target["traits"]) >= 3:
                continue
            target["traits"].append(
                {
                    "trait_code": trait_code,
                    "trait_name": trait_name or trait_code,
                    "count": int(trait_count or 0),
                }
            )

        assay_rows = (
            db.query(
                BreedingMaterial.program_id,
                BreedingAssay.assay_type,
                func.count(BreedingAssay.id).label("assay_count"),
            )
            .join(BreedingBioSample, BreedingBioSample.material_id == BreedingMaterial.id)
            .join(BreedingAssay, BreedingAssay.biosample_id == BreedingBioSample.id)
            .filter(BreedingMaterial.program_id.in_(program_ids))
            .group_by(BreedingMaterial.program_id, BreedingAssay.assay_type)
            .order_by(BreedingMaterial.program_id.asc(), func.count(BreedingAssay.id).desc(), BreedingAssay.assay_type.asc())
            .all()
        )
        for program_id, assay_type, assay_count in assay_rows:
            target = preview_map.get(program_id)
            if target is None or len(target["assay_types"]) >= 3:
                continue
            target["assay_types"].append(
                {
                    "assay_type": assay_type,
                    "count": int(assay_count or 0),
                }
            )

        return preview_map

    def list_programs(self, db, request_data):
        query = db.query(BreedingProgram)
        if request_data.status:
            query = query.filter(BreedingProgram.status == request_data.status)
        if request_data.species_name:
            query = query.filter(BreedingProgram.species_name == request_data.species_name)
        if request_data.keyword:
            keyword = f"%{request_data.keyword}%"
            query = query.filter(or_(BreedingProgram.code.ilike(keyword), BreedingProgram.name.ilike(keyword)))
        total, rows = self._paginate(query.order_by(BreedingProgram.id.desc()), request_data.page or 1, request_data.size or 10)
        items = self._serialize_rows(rows)
        counts_map = self._collect_program_counts(db=db, program_ids=[item["id"] for item in items])
        preview_map = self._collect_program_previews(db=db, program_ids=[item["id"] for item in items])
        for item in items:
            item["summary_counts"] = counts_map.get(item["id"], self._program_counts_template())
            item["preview_summary"] = preview_map.get(
                item["id"],
                {"materials": [], "traits": [], "assay_types": []},
            )
        return {"items": items, "total": total}

    def get_program(self, db, program_id):
        return jsonable_encoder(breeding_program_db.get(db=db, id=program_id))

    def get_program_overview(self, db, program_id):
        program = breeding_program_db.get(db=db, id=program_id)
        if not program:
            return None

        plot_trial = aliased(BreedingTrial)
        plot_subject = aliased(BreedingPlot)
        biosample_subject = aliased(BreedingBioSample)
        biosample_material = aliased(BreedingMaterial)

        material_count = self._count(
            db.query(func.count(BreedingMaterial.id)).filter(BreedingMaterial.program_id == program_id)
        )
        trial_count = self._count(
            db.query(func.count(BreedingTrial.id)).filter(BreedingTrial.program_id == program_id)
        )
        plot_count = self._count(
            db.query(func.count(BreedingPlot.id))
            .join(BreedingTrial, BreedingPlot.trial_id == BreedingTrial.id)
            .filter(BreedingTrial.program_id == program_id)
        )
        observation_count = self._count(
            db.query(func.count(BreedingObservation.id))
            .join(BreedingTrial, BreedingObservation.trial_id == BreedingTrial.id)
            .filter(BreedingTrial.program_id == program_id)
        )
        biosample_count = self._count(
            db.query(func.count(BreedingBioSample.id))
            .join(BreedingMaterial, BreedingBioSample.material_id == BreedingMaterial.id)
            .filter(BreedingMaterial.program_id == program_id)
        )
        assay_count = self._count(
            db.query(func.count(BreedingAssay.id))
            .join(BreedingBioSample, BreedingAssay.biosample_id == BreedingBioSample.id)
            .join(BreedingMaterial, BreedingBioSample.material_id == BreedingMaterial.id)
            .filter(BreedingMaterial.program_id == program_id)
        )
        data_file_count = self._count(
            db.query(func.count(BreedingDataFile.id))
            .join(BreedingAssay, BreedingDataFile.assay_id == BreedingAssay.id)
            .join(BreedingBioSample, BreedingAssay.biosample_id == BreedingBioSample.id)
            .join(BreedingMaterial, BreedingBioSample.material_id == BreedingMaterial.id)
            .filter(BreedingMaterial.program_id == program_id)
        )
        dataset_subject_link_count = self._count(
            db.query(func.count(func.distinct(BreedingDatasetSubjectLink.id)))
            .outerjoin(BreedingMaterial, BreedingDatasetSubjectLink.material_id == BreedingMaterial.id)
            .outerjoin(BreedingTrial, BreedingDatasetSubjectLink.trial_id == BreedingTrial.id)
            .outerjoin(plot_subject, BreedingDatasetSubjectLink.plot_id == plot_subject.id)
            .outerjoin(plot_trial, plot_subject.trial_id == plot_trial.id)
            .outerjoin(biosample_subject, BreedingDatasetSubjectLink.biosample_id == biosample_subject.id)
            .outerjoin(biosample_material, biosample_subject.material_id == biosample_material.id)
            .filter(
                or_(
                    BreedingDatasetSubjectLink.program_id == program_id,
                    BreedingMaterial.program_id == program_id,
                    BreedingTrial.program_id == program_id,
                    plot_trial.program_id == program_id,
                    biosample_material.program_id == program_id,
                )
            )
        )
        dataset_assay_link_count = self._count(
            db.query(func.count(func.distinct(BreedingDatasetAssayLink.id)))
            .join(BreedingAssay, BreedingDatasetAssayLink.assay_id == BreedingAssay.id)
            .join(BreedingBioSample, BreedingAssay.biosample_id == BreedingBioSample.id)
            .join(BreedingMaterial, BreedingBioSample.material_id == BreedingMaterial.id)
            .filter(BreedingMaterial.program_id == program_id)
        )

        return {
            "program": jsonable_encoder(program),
            "counts": {
                "materials": material_count,
                "trials": trial_count,
                "plots": plot_count,
                "observations": observation_count,
                "biosamples": biosample_count,
                "assays": assay_count,
                "data_files": data_file_count,
                "dataset_subject_links": dataset_subject_link_count,
                "dataset_assay_links": dataset_assay_link_count,
                "dataset_links": dataset_subject_link_count + dataset_assay_link_count,
            },
        }

    def get_program_analysis_readiness(self, db, program_id: int) -> dict:
        """Count materials in a breeding program that are analysis-ready
        (have both variant and phenotype data with matched mappings)."""
        from modules.breeding.models import (
            BreedingMaterial,
            BreedingVariantSampleMap,
            BreedingPhenotypeSubjectMap,
        )

        all_materials = (
            db.query(BreedingMaterial.id)
            .filter(BreedingMaterial.program_id == program_id)
            .all()
        )
        total = len(all_materials)
        all_ids = {r[0] for r in all_materials}

        variant_material_ids = set(
            r[0] for r in
            db.query(BreedingVariantSampleMap.material_id)
            .filter(
                BreedingVariantSampleMap.material_id.in_(all_ids),
                BreedingVariantSampleMap.mapping_status == "matched",
            )
            .distinct()
            .all()
        )

        pheno_material_ids = set(
            r[0] for r in
            db.query(BreedingPhenotypeSubjectMap.material_id)
            .filter(
                BreedingPhenotypeSubjectMap.material_id.in_(all_ids),
                BreedingPhenotypeSubjectMap.mapping_status == "matched",
            )
            .distinct()
            .all()
        )

        both = variant_material_ids & pheno_material_ids

        return {
            "program_id": program_id,
            "total_materials": total,
            "materials_with_variant": len(variant_material_ids),
            "materials_with_phenotype": len(pheno_material_ids),
            "materials_with_both": len(both),
            "ready_material_ids": sorted(both),
        }

    def create_program(self, db, request_data, user):
        payload = request_data.model_dump(exclude_none=True)
        payload["created_by"] = getattr(user, "id", None)
        payload["updated_by"] = getattr(user, "id", None)
        return jsonable_encoder(breeding_program_db.create_one(db=db, obj_in=payload))

    def update_program(self, db, program_id, request_data, user):
        obj = breeding_program_db.get(db=db, id=program_id)
        payload = request_data.model_dump(exclude_none=True, exclude={"id"})
        payload["updated_by"] = getattr(user, "id", None)
        payload["updated_at"] = datetime.utcnow()
        return jsonable_encoder(breeding_program_db.update_one(db=db, db_obj=obj, obj_in=payload))

    def list_materials(self, db, request_data):
        query = db.query(BreedingMaterial)
        if request_data.program_id:
            query = query.filter(BreedingMaterial.program_id == request_data.program_id)
        if request_data.material_type:
            query = query.filter(BreedingMaterial.material_type == request_data.material_type)
        if request_data.status:
            query = query.filter(BreedingMaterial.status == request_data.status)
        if request_data.keyword:
            keyword = f"%{request_data.keyword}%"
            query = query.filter(
                or_(
                    BreedingMaterial.material_code.ilike(keyword),
                    BreedingMaterial.material_name.ilike(keyword),
                    BreedingMaterial.germplasm_accession.ilike(keyword),
                    BreedingMaterial.germplasm_name.ilike(keyword),
                )
            )
        total, rows = self._paginate(query.order_by(BreedingMaterial.id.desc()), request_data.page or 1, request_data.size or 10)
        return {"items": self._serialize_rows(rows), "total": total}

    def get_material(self, db, material_id):
        return jsonable_encoder(breeding_material_db.get(db=db, id=material_id))

    def get_material_overview(self, db, material_id):
        from modules.datasets.dataset_model import Dataset

        material = breeding_material_db.get(db=db, id=material_id)
        if not material:
            return None

        base = jsonable_encoder(material)

        # Collect linked datasets from 4 link tables
        linked_datasets: list[dict] = []
        seen: set = set()

        # 1. variant_sample_map
        for vmap, ds in (
            db.query(BreedingVariantSampleMap, Dataset)
            .join(Dataset, Dataset.id == BreedingVariantSampleMap.dataset_id)
            .filter(BreedingVariantSampleMap.material_id == material_id)
            .all()
        ):
            if ds.id not in seen:
                seen.add(ds.id)
                linked_datasets.append({
                    "dataset_id": ds.id,
                    "dataset_code": ds.dataset_code,
                    "dataset_type": ds.dataset_type,
                    "role": "variant",
                    "link_type": "variant_sample_map",
                })

        # 2. phenotype_subject_map
        for pmap, ds in (
            db.query(BreedingPhenotypeSubjectMap, Dataset)
            .join(Dataset, Dataset.id == BreedingPhenotypeSubjectMap.dataset_id)
            .filter(BreedingPhenotypeSubjectMap.material_id == material_id)
            .all()
        ):
            if ds.id not in seen:
                seen.add(ds.id)
                linked_datasets.append({
                    "dataset_id": ds.id,
                    "dataset_code": ds.dataset_code,
                    "dataset_type": ds.dataset_type,
                    "role": "phenotype",
                    "link_type": "phenotype_subject_map",
                })

        # 3. dataset_subject_link
        for slink, ds in (
            db.query(BreedingDatasetSubjectLink, Dataset)
            .join(Dataset, Dataset.id == BreedingDatasetSubjectLink.dataset_id)
            .filter(BreedingDatasetSubjectLink.material_id == material_id)
            .all()
        ):
            if ds.id not in seen:
                seen.add(ds.id)
                linked_datasets.append({
                    "dataset_id": ds.id,
                    "dataset_code": ds.dataset_code,
                    "dataset_type": ds.dataset_type,
                    "role": slink.role or "subject",
                    "link_type": "dataset_subject_link",
                })

        # 4. dataset_assay_link (via biosample -> assay)
        biosample_ids = [
            r[0] for r in
            db.query(BreedingBioSample.id)
            .filter(BreedingBioSample.material_id == material_id)
            .all()
        ]
        if biosample_ids:
            assay_ids = [
                r[0] for r in
                db.query(BreedingAssay.id)
                .filter(BreedingAssay.biosample_id.in_(biosample_ids))
                .all()
            ]
            if assay_ids:
                for alink, ds in (
                    db.query(BreedingDatasetAssayLink, Dataset)
                    .join(Dataset, Dataset.id == BreedingDatasetAssayLink.dataset_id)
                    .filter(BreedingDatasetAssayLink.assay_id.in_(assay_ids))
                    .all()
                ):
                    if ds.id not in seen:
                        seen.add(ds.id)
                        linked_datasets.append({
                            "dataset_id": ds.id,
                            "dataset_code": ds.dataset_code,
                            "dataset_type": ds.dataset_type,
                            "role": alink.role or "expression",
                            "link_type": "dataset_assay_link",
                        })

        # Counts
        trial_count = (
            db.query(func.count(BreedingTrial.id))
            .join(BreedingPlot, BreedingPlot.trial_id == BreedingTrial.id)
            .join(BreedingBioSample, BreedingBioSample.plot_id == BreedingPlot.id)
            .filter(BreedingBioSample.material_id == material_id)
            .scalar()
        ) or 0

        observation_count = (
            db.query(func.count(BreedingObservation.id))
            .filter(BreedingObservation.material_id == material_id)
            .scalar()
        ) or 0

        biosample_count = (
            db.query(func.count(BreedingBioSample.id))
            .filter(BreedingBioSample.material_id == material_id)
            .scalar()
        ) or 0

        assay_count = (
            db.query(func.count(BreedingAssay.id))
            .join(BreedingBioSample, BreedingBioSample.id == BreedingAssay.biosample_id)
            .filter(BreedingBioSample.material_id == material_id)
            .scalar()
        ) or 0

        # Trials list (distinct trials this material is used in via plot -> biosample)
        trial_rows = (
            db.query(BreedingTrial)
            .join(BreedingPlot, BreedingPlot.trial_id == BreedingTrial.id)
            .join(BreedingBioSample, BreedingBioSample.plot_id == BreedingPlot.id)
            .filter(BreedingBioSample.material_id == material_id)
            .distinct()
            .all()
        )
        trial_list = [
            {"id": t.id, "trial_name": t.trial_name, "trial_type": t.trial_type}
            for t in trial_rows
        ]

        return {
            **base,
            "linked_dataset_count": len(linked_datasets),
            "linked_datasets": linked_datasets,
            "trial_count": trial_count,
            "trials": trial_list,
            "observation_count": observation_count,
            "biosample_count": biosample_count,
            "assay_count": assay_count,
        }

    def get_trial_overview(self, db, trial_id):
        trial = breeding_trial_db.get(db=db, id=trial_id)
        if not trial:
            return None

        base = jsonable_encoder(trial)

        plot_count = (
            db.query(func.count(BreedingPlot.id))
            .filter(BreedingPlot.trial_id == trial_id)
            .scalar()
        ) or 0

        observation_count = (
            db.query(func.count(BreedingObservation.id))
            .filter(BreedingObservation.trial_id == trial_id)
            .scalar()
        ) or 0

        material_count = (
            db.query(func.count(func.distinct(BreedingPlot.material_id)))
            .filter(BreedingPlot.trial_id == trial_id)
            .filter(BreedingPlot.material_id.isnot(None))
            .scalar()
        ) or 0

        trait_rows = (
            db.query(func.distinct(BreedingObservation.trait_code))
            .filter(BreedingObservation.trial_id == trial_id)
            .filter(BreedingObservation.trait_code.isnot(None))
            .all()
        )
        trait_codes = [r[0] for r in trait_rows if r[0]]

        # Linked datasets through material references in plots
        material_ids = [
            r[0] for r in
            db.query(BreedingPlot.material_id)
            .filter(BreedingPlot.trial_id == trial_id)
            .filter(BreedingPlot.material_id.isnot(None))
            .distinct()
            .all()
        ]

        linked_datasets: list[dict] = []
        seen: set = set()

        if material_ids:
            from modules.datasets.dataset_model import Dataset

            for vmap, ds in (
                db.query(BreedingVariantSampleMap, Dataset)
                .join(Dataset, Dataset.id == BreedingVariantSampleMap.dataset_id)
                .filter(BreedingVariantSampleMap.material_id.in_(material_ids))
                .all()
            ):
                if ds.id not in seen:
                    seen.add(ds.id)
                    linked_datasets.append({
                        "dataset_id": ds.id, "dataset_code": ds.dataset_code,
                        "dataset_type": ds.dataset_type, "role": "variant",
                        "link_type": "variant_sample_map",
                    })

            for pmap, ds in (
                db.query(BreedingPhenotypeSubjectMap, Dataset)
                .join(Dataset, Dataset.id == BreedingPhenotypeSubjectMap.dataset_id)
                .filter(BreedingPhenotypeSubjectMap.material_id.in_(material_ids))
                .all()
            ):
                if ds.id not in seen:
                    seen.add(ds.id)
                    linked_datasets.append({
                        "dataset_id": ds.id, "dataset_code": ds.dataset_code,
                        "dataset_type": ds.dataset_type, "role": "phenotype",
                        "link_type": "phenotype_subject_map",
                    })

        return {
            **base,
            "plot_count": plot_count,
            "observation_count": observation_count,
            "material_count": material_count,
            "trait_codes": trait_codes,
            "linked_dataset_count": len(linked_datasets),
            "linked_datasets": linked_datasets,
        }

    def create_material(self, db, request_data, user):
        payload = request_data.model_dump(exclude_none=True)
        payload["created_by"] = getattr(user, "id", None)
        payload["updated_by"] = getattr(user, "id", None)
        return jsonable_encoder(breeding_material_db.create_one(db=db, obj_in=payload))

    def update_material(self, db, material_id, request_data, user):
        obj = breeding_material_db.get(db=db, id=material_id)
        payload = request_data.model_dump(exclude_none=True, exclude={"id"})
        payload["updated_by"] = getattr(user, "id", None)
        payload["updated_at"] = datetime.utcnow()
        return jsonable_encoder(breeding_material_db.update_one(db=db, db_obj=obj, obj_in=payload))

    def validate_germplasm_import(
        self,
        db,
        *,
        template_profile,
        taxonomy_tax_id,
        source_path,
        source_filename,
        user,
        validation_token=None,
    ):
        template_profile = normalize_template_profile(template_profile)
        taxonomy = self._resolve_taxonomy_node_row(db=db, tax_id=taxonomy_tax_id)
        if taxonomy is None:
            raise ValueError(f"taxonomy_tax_id {taxonomy_tax_id} not found in local taxonomy reference or brd_taxonomy_node")

        existing_accessions = {
            row[0]
            for row in db.query(BreedingGermplasm.accession_id)
            .filter(BreedingGermplasm.taxonomy_tax_id == taxonomy_tax_id)
            .all()
            if row[0]
        }

        validation_result = validate_germplasm_file(
            template_profile,
            source_path,
            taxonomy_tax_id=taxonomy_tax_id,
            db_existing_accessions=existing_accessions,
        )
        token = validation_token or uuid.uuid4().hex
        payload = {
            "validation_token": token,
            "status": "validated" if validation_result["summary"]["passed"] else "invalid",
            "template_profile": template_profile,
            "taxonomy_tax_id": taxonomy_tax_id,
            "taxonomy_snapshot": {
                "tax_id": taxonomy.tax_id,
                "scientific_name": taxonomy.scientific_name,
                "common_name": taxonomy.common_name,
                "rank": taxonomy.rank,
                "lineage": taxonomy.lineage,
            },
            "source_filename": source_filename,
            "source_path": source_path,
            "validated_by": getattr(user, "id", None),
            "validated_at": datetime.utcnow().isoformat(),
            **validation_result,
        }
        write_validation_bundle(token, payload)
        return {
            "validation_token": token,
            "status": payload["status"],
            "template_profile": template_profile,
            "taxonomy": payload["taxonomy_snapshot"],
            "source_filename": source_filename,
            "summary": validation_result["summary"],
            "errors": validation_result["errors"],
            "warnings": validation_result["warnings"],
            "preview_rows": validation_result["preview_rows"],
            "builtin_fields": validation_result.get("builtin_fields", []),
            "dynamic_fields": validation_result.get("dynamic_fields", []),
            "field_schema_preview": validation_result.get("field_schema_preview", []),
        }

    def list_germplasm_taxonomy_options(self, db, request_data):
        limit = max(1, min(int(getattr(request_data, "limit", 20) or 20), 100))
        if getattr(request_data, "with_germplasm_only", 0):
            return self._list_existing_germplasm_taxonomy_options(
                db=db,
                request_data=request_data,
                limit=limit,
            )
        if getattr(request_data, "keyword", None):
            local_rows = self._search_local_taxonomy_rows(
                db=db,
                keyword=request_data.keyword,
                limit=limit,
                active_only=getattr(request_data, "active_only", 1),
            )
        else:
            local_rows = (
                self._build_local_taxonomy_query(db=db, request_data=request_data)
                .order_by(BreedingTaxonomyNode.scientific_name.asc())
                .limit(limit)
                .all()
            )
        if local_rows:
            counts = self._build_taxonomy_germplasm_count_map(db=db, tax_ids=[row.tax_id for row in local_rows])
            cache_rows = self._ensure_taxonomy_node_from_local_rows(db=db, rows=local_rows)
            items = []
            for row in local_rows:
                cache_row = cache_rows[row.tax_id]
                items.append(
                    {
                        "tax_id": row.tax_id,
                        "scientific_name": row.scientific_name,
                        "common_name": row.common_name,
                        "rank": row.rank,
                        "lineage": row.lineage,
                        "source": cache_row.source,
                        "ncbi_sync_time": cache_row.ncbi_sync_time,
                        "germplasm_count": counts.get(row.tax_id, 0),
                    }
                )
            return {"items": items, "total": len(items), "source_mode": "local_dump"}

        rows = (
            self._build_taxonomy_node_query(db=db, request_data=request_data)
            .order_by(BreedingTaxonomyNode.scientific_name.asc())
            .limit(limit)
            .all()
        )
        tax_ids = [row.tax_id for row in rows]
        counts = self._build_taxonomy_germplasm_count_map(db=db, tax_ids=tax_ids)
        items = []
        for row in rows:
            items.append(
                {
                    "tax_id": row.tax_id,
                    "scientific_name": row.scientific_name,
                    "common_name": row.common_name,
                    "rank": row.rank,
                    "lineage": row.lineage,
                    "source": row.source,
                    "ncbi_sync_time": row.ncbi_sync_time,
                    "germplasm_count": counts.get(row.tax_id, 0),
                }
            )
        return {"items": items, "total": len(items), "source_mode": "cache"}

    def list_germplasm_import_batches(self, db, request_data):
        query = (
            db.query(
                BreedingGermplasmImportBatch,
                BreedingTaxonomyNode.scientific_name,
                BreedingTaxonomyNode.common_name,
                BreedingTaxonomyNode.rank,
            )
            .join(BreedingTaxonomyNode, BreedingGermplasmImportBatch.taxonomy_tax_id == BreedingTaxonomyNode.tax_id)
        )
        if request_data.taxonomy_tax_id is not None:
            query = query.filter(BreedingGermplasmImportBatch.taxonomy_tax_id == request_data.taxonomy_tax_id)
        if request_data.status:
            query = query.filter(BreedingGermplasmImportBatch.status == request_data.status)
        if request_data.keyword:
            keyword = f"%{request_data.keyword}%"
            query = query.filter(
                or_(
                    BreedingGermplasmImportBatch.batch_code.ilike(keyword),
                    BreedingGermplasmImportBatch.source_filename.ilike(keyword),
                    BreedingGermplasmImportBatch.template_profile.ilike(keyword),
                    BreedingTaxonomyNode.scientific_name.ilike(keyword),
                    BreedingTaxonomyNode.common_name.ilike(keyword),
                )
            )

        total = query.count()
        page = request_data.page or 1
        size = request_data.size or 10
        rows = (
            query.order_by(BreedingGermplasmImportBatch.id.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        items = []
        for batch, scientific_name, common_name, rank in rows:
            items.append(
                {
                    "id": batch.id,
                    "batch_code": batch.batch_code,
                    "template_profile": batch.template_profile,
                    "taxonomy_tax_id": batch.taxonomy_tax_id,
                    "taxonomy": {
                        "tax_id": batch.taxonomy_tax_id,
                        "scientific_name": scientific_name,
                        "common_name": common_name,
                        "rank": rank,
                    },
                    "source_filename": batch.source_filename,
                    "source_file_path": batch.source_file_path,
                    "status": batch.status,
                    "total_rows": batch.total_rows,
                    "valid_rows": batch.valid_rows,
                    "error_rows": batch.error_rows,
                    "warning_rows": batch.warning_rows,
                    "is_public": bool(batch.is_public),
                    "created_by": batch.created_by,
                    "updated_by": batch.updated_by,
                    "created_at": batch.created_at,
                    "updated_at": batch.updated_at,
                }
            )
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": size,
            "total_pages": (total + size - 1) // size if size else 1,
        }

    @staticmethod
    def _dedupe_accessions(values):
        items = []
        seen = set()
        for value in values or []:
            if not value:
                continue
            text = str(value).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            items.append(text)
        return items

    def _load_germplasm_record_map(self, db, taxonomy_tax_id, accession_ids):
        accession_ids = self._dedupe_accessions(accession_ids)
        if not accession_ids:
            return {}
        rows = (
            db.query(BreedingGermplasm)
            .filter(
                BreedingGermplasm.taxonomy_tax_id == taxonomy_tax_id,
                BreedingGermplasm.accession_id.in_(accession_ids),
            )
            .all()
        )
        record_map = {}
        for row in rows:
            attributes = {}
            if row.attributes_json:
                try:
                    attributes = json.loads(row.attributes_json)
                except json.JSONDecodeError:
                    attributes = {}
            record_map[row.accession_id] = {
                "record_id": row.id,
                "accession_id": row.accession_id,
                "display_name": row.display_name,
                "english_name": row.english_name,
                "father_accession": row.father_accession,
                "mother_accession": row.mother_accession,
                "status": row.status,
                "batch_id": row.batch_id,
                "source_row_no": row.source_row_no,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "attributes": attributes,
            }
        return record_map

    def _get_germplasm_scope_accessions(self, db, taxonomy_tax_id, batch_id=None, status="active"):
        query = db.query(BreedingGermplasm.accession_id).filter(BreedingGermplasm.taxonomy_tax_id == taxonomy_tax_id)
        if batch_id is not None:
            query = query.filter(BreedingGermplasm.batch_id == batch_id)
        if status:
            query = query.filter(BreedingGermplasm.status == status)
        return [row[0] for row in query.all() if row[0]]

    def _get_lineage_edges(self, db, taxonomy_tax_id, batch_id=None):
        query = db.query(BreedingGermplasmLineage).filter(BreedingGermplasmLineage.taxonomy_tax_id == taxonomy_tax_id)
        if batch_id is not None:
            query = query.filter(BreedingGermplasmLineage.batch_id == batch_id)
        return query.order_by(BreedingGermplasmLineage.id.asc()).all()

    def _build_germplasm_graph_payload(self, db, taxonomy_tax_id, accession_ids, lineage_edges, selected_nodes=None):
        node_ids = self._dedupe_accessions(
            list(accession_ids or [])
            + [edge.child_accession for edge in lineage_edges]
            + [edge.parent_accession for edge in lineage_edges]
        )
        selected_nodes = set(self._dedupe_accessions(selected_nodes or []))
        record_map = self._load_germplasm_record_map(db=db, taxonomy_tax_id=taxonomy_tax_id, accession_ids=node_ids)

        degree_map = {accession_id: 0 for accession_id in node_ids}
        edges = []
        for edge in lineage_edges:
            degree_map.setdefault(edge.parent_accession, 0)
            degree_map.setdefault(edge.child_accession, 0)
            degree_map[edge.parent_accession] += 1
            degree_map[edge.child_accession] += 1
            edges.append(
                {
                    "id": f"{edge.parent_accession}->{edge.child_accession}:{edge.parent_role}",
                    "source": edge.parent_accession,
                    "target": edge.child_accession,
                    "relationship_type": edge.parent_role,
                    "weight": 1,
                    "created_at": edge.created_at,
                }
            )

        nodes = []
        for accession_id in node_ids:
            record = record_map.get(accession_id)
            attributes = dict(record["attributes"]) if record else {}
            if record:
                attributes.setdefault("display_name", record["display_name"])
                attributes.setdefault("english_name", record["english_name"])
                attributes.setdefault("father_accession", record["father_accession"])
                attributes.setdefault("mother_accession", record["mother_accession"])
                attributes.setdefault("status", record["status"])
                attributes.setdefault("batch_id", record["batch_id"])
            attributes["is_placeholder"] = record is None
            nodes.append(
                {
                    "id": accession_id,
                    "label": (record or {}).get("display_name") or accession_id,
                    "degree": degree_map.get(accession_id, 0),
                    "selected": accession_id in selected_nodes,
                    "attributes": attributes,
                }
            )
        return {
            "nodes": nodes,
            "edges": edges,
        }

    def get_germplasm_import_batch(self, db, batch_id):
        row = (
            db.query(
                BreedingGermplasmImportBatch,
                BreedingTaxonomyNode.scientific_name,
                BreedingTaxonomyNode.common_name,
                BreedingTaxonomyNode.rank,
                BreedingTaxonomyNode.lineage,
            )
            .join(BreedingTaxonomyNode, BreedingGermplasmImportBatch.taxonomy_tax_id == BreedingTaxonomyNode.tax_id)
            .filter(BreedingGermplasmImportBatch.id == batch_id)
            .first()
        )
        if row is None:
            return None
        batch, scientific_name, common_name, rank, lineage = row
        report = {}
        field_schema = []
        if batch.validation_report_json:
            try:
                report = json.loads(batch.validation_report_json)
            except json.JSONDecodeError:
                report = {}
        if batch.field_schema_json:
            try:
                field_schema = json.loads(batch.field_schema_json)
            except json.JSONDecodeError:
                field_schema = []
        return {
            "id": batch.id,
            "batch_code": batch.batch_code,
            "template_profile": batch.template_profile,
            "taxonomy_tax_id": batch.taxonomy_tax_id,
            "taxonomy": {
                "tax_id": batch.taxonomy_tax_id,
                "scientific_name": scientific_name,
                "common_name": common_name,
                "rank": rank,
                "lineage": lineage,
            },
            "source_filename": batch.source_filename,
            "source_file_path": batch.source_file_path,
            "status": batch.status,
            "total_rows": batch.total_rows,
            "valid_rows": batch.valid_rows,
            "error_rows": batch.error_rows,
            "warning_rows": batch.warning_rows,
            "field_schema": field_schema,
            "validation_report": report,
            "created_by": batch.created_by,
            "updated_by": batch.updated_by,
            "created_at": batch.created_at,
            "updated_at": batch.updated_at,
        }

    def delete_germplasm_import_batch(self, db, *, batch_id, user):
        batch = db.query(BreedingGermplasmImportBatch).filter(BreedingGermplasmImportBatch.id == batch_id).first()
        if batch is None:
            raise ValueError(f"germplasm import batch {batch_id} not found")

        if batch.status == "deleted":
            return {
                "batch_id": batch.id,
                "batch_code": batch.batch_code,
                "deleted_germplasm_count": 0,
                "deleted_lineage_count": 0,
                "status": "deleted",
            }

        deleted_germplasm_count = (
            db.query(BreedingGermplasm)
            .filter(BreedingGermplasm.batch_id == batch.id)
            .count()
        )
        deleted_lineage_count = (
            db.query(BreedingGermplasmLineage)
            .filter(BreedingGermplasmLineage.batch_id == batch.id)
            .count()
        )

        db.query(BreedingGermplasmLineage).filter(BreedingGermplasmLineage.batch_id == batch.id).delete(synchronize_session=False)
        db.query(BreedingGermplasm).filter(BreedingGermplasm.batch_id == batch.id).delete(synchronize_session=False)
        batch.status = "deleted"
        batch.updated_by = getattr(user, "id", None)
        batch.updated_at = datetime.utcnow()
        db.commit()

        return {
            "batch_id": batch.id,
            "batch_code": batch.batch_code,
            "deleted_germplasm_count": deleted_germplasm_count,
            "deleted_lineage_count": deleted_lineage_count,
            "status": "deleted",
        }

    def list_germplasms(self, db, request_data, public_only=False):
        query = (
            db.query(
                BreedingGermplasm,
                BreedingGermplasmImportBatch.batch_code,
                BreedingGermplasmImportBatch.source_filename,
                BreedingGermplasmImportBatch.field_schema_json,
                BreedingTaxonomyNode.scientific_name,
                BreedingTaxonomyNode.common_name,
                BreedingTaxonomyNode.rank,
            )
            .join(BreedingGermplasmImportBatch, BreedingGermplasm.batch_id == BreedingGermplasmImportBatch.id)
            .join(BreedingTaxonomyNode, BreedingGermplasm.taxonomy_tax_id == BreedingTaxonomyNode.tax_id)
        )
        if public_only:
            query = query.filter(BreedingGermplasmImportBatch.is_public == 1)
            query = query.filter(BreedingGermplasm.is_public == 1)
        if request_data.taxonomy_tax_id is not None:
            query = query.filter(BreedingGermplasm.taxonomy_tax_id == request_data.taxonomy_tax_id)
        if request_data.batch_id is not None:
            query = query.filter(BreedingGermplasm.batch_id == request_data.batch_id)
        if request_data.status:
            query = query.filter(BreedingGermplasm.status == request_data.status)
        if request_data.keyword:
            keyword = f"%{request_data.keyword}%"
            query = query.filter(
                or_(
                    BreedingGermplasm.accession_id.ilike(keyword),
                    BreedingGermplasm.display_name.ilike(keyword),
                    BreedingGermplasm.english_name.ilike(keyword),
                    BreedingGermplasm.father_accession.ilike(keyword),
                    BreedingGermplasm.mother_accession.ilike(keyword),
                    BreedingGermplasm.search_text.ilike(keyword),
                )
            )

        total = query.count()
        page = request_data.page or 1
        size = request_data.size or 10
        rows = (
            query.order_by(BreedingGermplasm.id.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        accession_ids = [row[0].accession_id for row in rows]
        usage_map = self._collect_germplasm_usage_map(db=db, accession_ids=accession_ids)
        items = []
        for germplasm, batch_code, source_filename, field_schema_json, scientific_name, common_name, rank in rows:
            attributes, field_schema = self._apply_germplasm_field_schema(
                germplasm.attributes_json,
                field_schema_json,
            )
            items.append(
                {
                    "id": germplasm.accession_id,
                    "record_id": germplasm.id,
                    "accession_id": germplasm.accession_id,
                    "display_name": germplasm.display_name,
                    "english_name": germplasm.english_name,
                    "taxonomy_tax_id": germplasm.taxonomy_tax_id,
                    "father_accession": germplasm.father_accession,
                    "mother_accession": germplasm.mother_accession,
                    "status": germplasm.status,
                    "is_public": bool(germplasm.is_public),
                    "batch_id": germplasm.batch_id,
                    "batch_code": batch_code,
                    "source_filename": source_filename,
                    "taxonomy": {
                        "tax_id": germplasm.taxonomy_tax_id,
                        "scientific_name": scientific_name,
                        "common_name": common_name,
                        "rank": rank,
                    },
                    "attributes": attributes,
                    "field_schema": field_schema,
                    "breeding_summary": usage_map.get(germplasm.accession_id, self._germplasm_usage_template()),
                    "created_at": germplasm.created_at,
                    "updated_at": germplasm.updated_at,
                }
            )
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": size,
            "total_pages": (total + size - 1) // size if size else 1,
        }

    def get_germplasm_statistics(self, db, request_data):
        taxonomy = db.query(BreedingTaxonomyNode).filter(BreedingTaxonomyNode.tax_id == request_data.taxonomy_tax_id).first()
        scope_accessions = self._get_germplasm_scope_accessions(
            db=db,
            taxonomy_tax_id=request_data.taxonomy_tax_id,
            batch_id=request_data.batch_id,
            status=request_data.status,
        )
        lineage_edges = self._get_lineage_edges(
            db=db,
            taxonomy_tax_id=request_data.taxonomy_tax_id,
            batch_id=request_data.batch_id,
        )
        graph_payload = self._build_germplasm_graph_payload(
            db=db,
            taxonomy_tax_id=request_data.taxonomy_tax_id,
            accession_ids=scope_accessions,
            lineage_edges=lineage_edges,
        )
        node_ids = [node["id"] for node in graph_payload["nodes"]]
        adjacency = {node_id: set() for node_id in node_ids}
        degree_map = {node_id: 0 for node_id in node_ids}
        role_counts = {"father": 0, "mother": 0, "other": 0}
        for edge in graph_payload["edges"]:
            source = edge["source"]
            target = edge["target"]
            adjacency.setdefault(source, set()).add(target)
            adjacency.setdefault(target, set()).add(source)
            degree_map[source] = degree_map.get(source, 0) + 1
            degree_map[target] = degree_map.get(target, 0) + 1
            role = edge["relationship_type"]
            if role in role_counts:
                role_counts[role] += 1
            else:
                role_counts["other"] += 1

        components = 0
        visited = set()
        for node_id in node_ids:
            if node_id in visited:
                continue
            components += 1
            stack = [node_id]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                stack.extend(neighbor for neighbor in adjacency.get(current, set()) if neighbor not in visited)

        degrees = [degree_map.get(node_id, 0) for node_id in node_ids]
        average_degree = round(sum(degrees) / len(degrees), 2) if degrees else 0.0
        max_degree = max(degrees) if degrees else 0
        min_degree = min(degrees) if degrees else 0
        record_map = self._load_germplasm_record_map(db=db, taxonomy_tax_id=request_data.taxonomy_tax_id, accession_ids=node_ids)
        top_hubs = sorted(
            (
                {
                    "accession_id": node_id,
                    "display_name": (record_map.get(node_id) or {}).get("display_name"),
                    "degree": degree_map.get(node_id, 0),
                }
                for node_id in node_ids
            ),
            key=lambda item: (-item["degree"], item["accession_id"]),
        )[:10]

        batch_meta = None
        if request_data.batch_id is not None:
            batch = db.query(BreedingGermplasmImportBatch).filter(BreedingGermplasmImportBatch.id == request_data.batch_id).first()
            if batch:
                batch_meta = {
                    "id": batch.id,
                    "batch_code": batch.batch_code,
                    "source_filename": batch.source_filename,
                    "created_at": batch.created_at,
                    "updated_at": batch.updated_at,
                }

        return {
            "taxonomy_tax_id": request_data.taxonomy_tax_id,
            "batch_id": request_data.batch_id,
            "node_count": len(node_ids),
            "edge_count": len(graph_payload["edges"]),
            "germplasm_record_count": len(scope_accessions),
            "connected_components": components,
            "is_connected": len(node_ids) > 0 and components <= 1,
            "average_degree": average_degree,
            "max_degree": max_degree,
            "min_degree": min_degree,
            "role_counts": role_counts,
            "top_hubs": top_hubs,
            "metadata": {
                "source_model": "breeding:germplasm_lineage",
                "generated_at": datetime.utcnow().isoformat(),
                "taxonomy": {
                    "tax_id": getattr(taxonomy, "tax_id", request_data.taxonomy_tax_id),
                    "scientific_name": getattr(taxonomy, "scientific_name", None),
                    "common_name": getattr(taxonomy, "common_name", None),
                    "rank": getattr(taxonomy, "rank", None),
                },
                "batch": batch_meta,
            },
        }

    def get_germplasm_relationship(self, db, request_data):
        accession_id_1 = str(request_data.accession_id_1).strip()
        accession_id_2 = str(request_data.accession_id_2).strip()
        lineage_edges = self._get_lineage_edges(
            db=db,
            taxonomy_tax_id=request_data.taxonomy_tax_id,
            batch_id=request_data.batch_id,
        )
        record_map = self._load_germplasm_record_map(
            db=db,
            taxonomy_tax_id=request_data.taxonomy_tax_id,
            accession_ids=[accession_id_1, accession_id_2],
        )

        direct_edges = []
        parent_map = {}
        child_map = {}
        for edge in lineage_edges:
            parent_map.setdefault(edge.child_accession, []).append(edge)
            child_map.setdefault(edge.parent_accession, []).append(edge)
            if (
                edge.child_accession == accession_id_1
                and edge.parent_accession == accession_id_2
            ) or (
                edge.child_accession == accession_id_2
                and edge.parent_accession == accession_id_1
            ):
                direct_edges.append(
                    {
                        "parent_accession": edge.parent_accession,
                        "child_accession": edge.child_accession,
                        "parent_role": edge.parent_role,
                        "created_at": edge.created_at,
                    }
                )

        parents_1 = parent_map.get(accession_id_1, [])
        parents_2 = parent_map.get(accession_id_2, [])
        shared_parent_ids = sorted(
            {edge.parent_accession for edge in parents_1}.intersection({edge.parent_accession for edge in parents_2})
        )
        shared_parents = []
        for parent_accession in shared_parent_ids:
            roles = sorted(
                {
                    edge.parent_role
                    for edge in parents_1 + parents_2
                    if edge.parent_accession == parent_accession
                }
            )
            shared_parents.append(
                {
                    "parent_accession": parent_accession,
                    "roles": roles,
                }
            )

        children_1 = child_map.get(accession_id_1, [])
        children_2 = child_map.get(accession_id_2, [])
        shared_child_ids = sorted(
            {edge.child_accession for edge in children_1}.intersection({edge.child_accession for edge in children_2})
        )
        shared_children = [
            {
                "child_accession": child_accession,
            }
            for child_accession in shared_child_ids
        ]

        directed_adjacency = {}
        for edge in lineage_edges:
            directed_adjacency.setdefault(edge.parent_accession, []).append(edge.child_accession)

        def find_directed_path(start_node, target_node):
            if start_node == target_node:
                return [start_node]
            queue = [(start_node, [start_node])]
            visited = {start_node}
            while queue:
                current, path = queue.pop(0)
                for neighbor in directed_adjacency.get(current, []):
                    if neighbor in visited:
                        continue
                    next_path = path + [neighbor]
                    if neighbor == target_node:
                        return next_path
                    visited.add(neighbor)
                    queue.append((neighbor, next_path))
            return None

        relationship_type = "none"
        relationship_direction = None
        path_nodes = None
        if accession_id_1 == accession_id_2:
            relationship_type = "self"
            path_nodes = [accession_id_1]
        elif direct_edges:
            relationship_type = "parent-child"
            edge = direct_edges[0]
            relationship_direction = f"{edge['parent_accession']} -> {edge['child_accession']}"
            path_nodes = [edge["parent_accession"], edge["child_accession"]]
        elif shared_parents:
            relationship_type = "siblings"
        elif shared_children:
            relationship_type = "co-parent"
        else:
            path_forward = find_directed_path(accession_id_1, accession_id_2)
            path_reverse = find_directed_path(accession_id_2, accession_id_1)
            if path_forward:
                relationship_type = "ancestor-descendant"
                relationship_direction = f"{accession_id_1} -> {accession_id_2}"
                path_nodes = path_forward
            elif path_reverse:
                relationship_type = "ancestor-descendant"
                relationship_direction = f"{accession_id_2} -> {accession_id_1}"
                path_nodes = path_reverse

        return {
            "node1": accession_id_1,
            "node2": accession_id_2,
            "exists": relationship_type != "none",
            "relationship_type": relationship_type,
            "relationship_direction": relationship_direction,
            "weight": len(direct_edges) or (1 if relationship_type != "none" else 0),
            "path_nodes": path_nodes,
            "shared_parents": shared_parents,
            "shared_children": shared_children,
            "direct_edges": direct_edges,
            "node_snapshots": {
                accession_id_1: {
                    "display_name": (record_map.get(accession_id_1) or {}).get("display_name"),
                    "english_name": (record_map.get(accession_id_1) or {}).get("english_name"),
                },
                accession_id_2: {
                    "display_name": (record_map.get(accession_id_2) or {}).get("display_name"),
                    "english_name": (record_map.get(accession_id_2) or {}).get("english_name"),
                },
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_germplasm_batch_relationships(self, db, request_data):
        selected_nodes = self._dedupe_accessions(request_data.selected_nodes)
        if not selected_nodes:
            return {"nodes": [], "edges": [], "summary": {"selected_nodes": [], "edge_count": 0}}

        lineage_edges = self._get_lineage_edges(
            db=db,
            taxonomy_tax_id=request_data.taxonomy_tax_id,
            batch_id=request_data.batch_id,
        )
        selected_node_set = set(selected_nodes)
        max_connections = max(1, min(int(request_data.max_connections_per_node or 30), 200))
        external_connection_counts = {node_id: 0 for node_id in selected_nodes}
        filtered_edges = []
        seen_edges = set()

        for edge in lineage_edges:
            parent_selected = edge.parent_accession in selected_node_set
            child_selected = edge.child_accession in selected_node_set
            edge_id = (edge.parent_accession, edge.child_accession, edge.parent_role)

            if parent_selected and child_selected:
                if request_data.include_internal and edge_id not in seen_edges:
                    filtered_edges.append(edge)
                    seen_edges.add(edge_id)
                continue

            if not request_data.include_external:
                continue

            pivot = None
            if parent_selected:
                pivot = edge.parent_accession
            elif child_selected:
                pivot = edge.child_accession
            if pivot is None:
                continue
            if external_connection_counts[pivot] >= max_connections:
                continue
            if edge_id in seen_edges:
                continue
            filtered_edges.append(edge)
            seen_edges.add(edge_id)
            external_connection_counts[pivot] += 1

        graph_payload = self._build_germplasm_graph_payload(
            db=db,
            taxonomy_tax_id=request_data.taxonomy_tax_id,
            accession_ids=selected_nodes,
            lineage_edges=filtered_edges,
            selected_nodes=selected_nodes,
        )
        return {
            **graph_payload,
            "summary": {
                "selected_nodes": selected_nodes,
                "selected_node_count": len(selected_nodes),
                "node_count": len(graph_payload["nodes"]),
                "edge_count": len(graph_payload["edges"]),
                "include_internal": bool(request_data.include_internal),
                "include_external": bool(request_data.include_external),
                "max_connections_per_node": max_connections,
            },
        }

    def set_germplasm_public(self, db, accession_id, taxonomy_tax_id, is_public):
        germplasm = (
            db.query(BreedingGermplasm)
            .filter(
                BreedingGermplasm.accession_id == accession_id,
                BreedingGermplasm.taxonomy_tax_id == taxonomy_tax_id,
            )
            .first()
        )
        if germplasm is None:
            raise HTTPException(status_code=404, detail="Germplasm not found")
        germplasm.is_public = 1 if is_public else 0
        germplasm.updated_at = func.now()
        db.add(germplasm)
        db.commit()
        return {"ok": True}

    def set_germplasm_batch_public(self, db, batch_id, is_public):
        batch = (
            db.query(BreedingGermplasmImportBatch)
            .filter(BreedingGermplasmImportBatch.id == batch_id)
            .first()
        )
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        batch.is_public = 1 if is_public else 0
        batch.updated_at = func.now()
        db.add(batch)
        db.commit()
        return {"ok": True}

    def get_germplasm(self, db, accession_id, taxonomy_tax_id, public_only=False):
        query = (
            db.query(
                BreedingGermplasm,
                BreedingGermplasmImportBatch.batch_code,
                BreedingGermplasmImportBatch.source_filename,
                BreedingGermplasmImportBatch.source_file_path,
                BreedingGermplasmImportBatch.field_schema_json,
                BreedingTaxonomyNode.scientific_name,
                BreedingTaxonomyNode.common_name,
                BreedingTaxonomyNode.rank,
                BreedingTaxonomyNode.lineage,
            )
            .join(BreedingGermplasmImportBatch, BreedingGermplasm.batch_id == BreedingGermplasmImportBatch.id)
            .join(BreedingTaxonomyNode, BreedingGermplasm.taxonomy_tax_id == BreedingTaxonomyNode.tax_id)
            .filter(
                BreedingGermplasm.accession_id == accession_id,
                BreedingGermplasm.taxonomy_tax_id == taxonomy_tax_id,
            )
        )
        if public_only:
            query = query.filter(BreedingGermplasmImportBatch.is_public == 1)
            query = query.filter(BreedingGermplasm.is_public == 1)
        row = query.first()
        if row is None:
            return None
        (
            germplasm,
            batch_code,
            source_filename,
            source_file_path,
            field_schema_json,
            scientific_name,
            common_name,
            rank,
            lineage,
        ) = row
        parent_edges = (
            db.query(BreedingGermplasmLineage)
            .filter(
                BreedingGermplasmLineage.taxonomy_tax_id == taxonomy_tax_id,
                BreedingGermplasmLineage.child_accession == accession_id,
            )
            .order_by(BreedingGermplasmLineage.parent_role.asc(), BreedingGermplasmLineage.parent_accession.asc())
            .all()
        )
        child_edges = (
            db.query(BreedingGermplasmLineage)
            .filter(
                BreedingGermplasmLineage.taxonomy_tax_id == taxonomy_tax_id,
                BreedingGermplasmLineage.parent_accession == accession_id,
            )
            .order_by(BreedingGermplasmLineage.child_accession.asc())
            .all()
        )
        usage = self._collect_germplasm_usage_map(db=db, accession_ids=[accession_id]).get(
            accession_id,
            self._germplasm_usage_template(),
        )
        attributes, field_schema = self._apply_germplasm_field_schema(
            germplasm.attributes_json,
            field_schema_json,
        )
        return {
            "id": accession_id,
            "record_id": germplasm.id,
            "accession_id": accession_id,
            "display_name": germplasm.display_name,
            "english_name": germplasm.english_name,
            "father_accession": germplasm.father_accession,
            "mother_accession": germplasm.mother_accession,
            "father_name_snapshot": germplasm.father_name_snapshot,
            "mother_name_snapshot": germplasm.mother_name_snapshot,
            "status": germplasm.status,
            "taxonomy": {
                "tax_id": germplasm.taxonomy_tax_id,
                "scientific_name": scientific_name,
                "common_name": common_name,
                "rank": rank,
                "lineage": lineage,
            },
            "attributes": attributes,
            "field_schema": field_schema,
            "lineage_summary": {
                "parents": [
                    {
                        "parent_accession": edge.parent_accession,
                        "parent_role": edge.parent_role,
                    }
                    for edge in parent_edges
                ],
                "children": [
                    {
                        "child_accession": edge.child_accession,
                        "parent_role": edge.parent_role,
                    }
                    for edge in child_edges[:20]
                ],
                "child_count": len(child_edges),
                "parent_count": len(parent_edges),
            },
            "breeding_usage": usage,
            "audit": {
                "batch_id": germplasm.batch_id,
                "batch_code": batch_code,
                "source_filename": source_filename,
                "source_file_path": source_file_path,
                "source_row_no": germplasm.source_row_no,
                "created_at": germplasm.created_at,
                "updated_at": germplasm.updated_at,
            },
        }

    def commit_germplasm_import(self, db, *, validation_token, user):
        bundle = load_validation_bundle(validation_token)
        if bundle.get("status") == "imported" and bundle.get("batch_id") is not None:
            return {
                "batch_id": bundle["batch_id"],
                "batch_code": bundle.get("batch_code"),
                "imported_count": bundle.get("summary", {}).get("valid_rows", 0),
                "validation_token": validation_token,
                "status": "imported",
            }
        if not bundle.get("summary", {}).get("passed"):
            raise ValueError("validation has errors, cannot commit import")

        taxonomy_tax_id = int(bundle["taxonomy_tax_id"])
        taxonomy = self._resolve_taxonomy_node_row(db=db, tax_id=taxonomy_tax_id)
        if taxonomy is None:
            raise ValueError(f"taxonomy_tax_id {taxonomy_tax_id} not found in local taxonomy reference or brd_taxonomy_node")

        normalized_rows = bundle.get("normalized_rows") or []
        if not normalized_rows:
            raise ValueError("no valid germplasm rows found in validation bundle")

        existing_accessions = {
            row[0]
            for row in db.query(BreedingGermplasm.accession_id)
            .filter(BreedingGermplasm.taxonomy_tax_id == taxonomy_tax_id)
            .all()
            if row[0]
        }
        duplicate_accessions = sorted(
            {
                row["accession_id"]
                for row in normalized_rows
                if row.get("accession_id") and row["accession_id"] in existing_accessions
            }
        )
        if duplicate_accessions:
            raise ValueError(f"existing accessions found during commit: {', '.join(duplicate_accessions)}")

        batch_code = f"GIP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{validation_token[:6]}"
        batch = BreedingGermplasmImportBatch(
            batch_code=batch_code,
            template_profile=bundle["template_profile"],
            taxonomy_tax_id=taxonomy_tax_id,
            taxonomy_name_snapshot=taxonomy.scientific_name,
            source_filename=bundle.get("source_filename") or "uploaded.xlsx",
            source_file_path=bundle.get("source_path"),
            status="imported",
            total_rows=int(bundle["summary"].get("total_rows") or 0),
            valid_rows=int(bundle["summary"].get("valid_rows") or 0),
            error_rows=int(bundle["summary"].get("error_rows") or 0),
            warning_rows=int(bundle["summary"].get("warning_rows") or 0),
            field_schema_json=json.dumps(bundle.get("field_schema_preview") or [], ensure_ascii=False),
            validation_report_json=json.dumps(
                {
                    "summary": bundle.get("summary", {}),
                    "errors": bundle.get("errors", []),
                    "warnings": bundle.get("warnings", []),
                },
                ensure_ascii=False,
            ),
            created_by=getattr(user, "id", None),
            updated_by=getattr(user, "id", None),
        )
        db.add(batch)
        db.flush()

        lineage_edges = []
        for row in normalized_rows:
            germplasm = BreedingGermplasm(
                batch_id=batch.id,
                taxonomy_tax_id=taxonomy_tax_id,
                accession_id=row["accession_id"],
                display_name=row["display_name"],
                scientific_name_snapshot=taxonomy.scientific_name,
                common_name_snapshot=taxonomy.common_name,
                english_name=row.get("english_name"),
                father_accession=row.get("father_accession"),
                mother_accession=row.get("mother_accession"),
                father_name_snapshot=row.get("father_name_snapshot"),
                mother_name_snapshot=row.get("mother_name_snapshot"),
                source_row_no=row.get("source_row_no"),
                status="active",
                attributes_json=json.dumps(row.get("attributes_json") or {}, ensure_ascii=False),
                search_text=row.get("search_text"),
            )
            db.add(germplasm)
            if row.get("father_accession"):
                lineage_edges.append(
                    BreedingGermplasmLineage(
                        taxonomy_tax_id=taxonomy_tax_id,
                        child_accession=row["accession_id"],
                        parent_accession=row["father_accession"],
                        parent_role="father",
                        batch_id=batch.id,
                        source_row_no=row.get("source_row_no"),
                    )
                )
            if row.get("mother_accession"):
                lineage_edges.append(
                    BreedingGermplasmLineage(
                        taxonomy_tax_id=taxonomy_tax_id,
                        child_accession=row["accession_id"],
                        parent_accession=row["mother_accession"],
                        parent_role="mother",
                        batch_id=batch.id,
                        source_row_no=row.get("source_row_no"),
                    )
                )

        for lineage in lineage_edges:
            db.add(lineage)
        db.commit()

        update_validation_bundle(
            validation_token,
            {
                "status": "imported",
                "batch_id": batch.id,
                "batch_code": batch_code,
                "committed_by": getattr(user, "id", None),
                "committed_at": datetime.utcnow().isoformat(),
            },
        )
        return {
            "batch_id": batch.id,
            "batch_code": batch_code,
            "imported_count": len(normalized_rows),
            "lineage_edge_count": len(lineage_edges),
            "validation_token": validation_token,
            "status": "imported",
        }

    def list_trials(self, db, request_data):
        query = db.query(BreedingTrial)
        if request_data.program_id:
            query = query.filter(BreedingTrial.program_id == request_data.program_id)
        if request_data.trial_type:
            query = query.filter(BreedingTrial.trial_type == request_data.trial_type)
        if request_data.location_name:
            query = query.filter(BreedingTrial.location_name == request_data.location_name)
        if request_data.season_label:
            query = query.filter(BreedingTrial.season_label == request_data.season_label)
        if request_data.status:
            query = query.filter(BreedingTrial.status == request_data.status)
        if request_data.keyword:
            keyword = f"%{request_data.keyword}%"
            query = query.filter(or_(BreedingTrial.trial_code.ilike(keyword), BreedingTrial.trial_name.ilike(keyword)))
        total, rows = self._paginate(query.order_by(BreedingTrial.id.desc()), request_data.page or 1, request_data.size or 10)
        return {"items": self._serialize_rows(rows), "total": total}

    def get_trial(self, db, trial_id):
        return jsonable_encoder(breeding_trial_db.get(db=db, id=trial_id))

    def create_trial(self, db, request_data, user):
        payload = request_data.model_dump(exclude_none=True)
        for field in ("sowing_date", "harvest_date"):
            payload[field] = self._coerce_iso_date(payload.get(field))
        payload["created_by"] = getattr(user, "id", None)
        payload["updated_by"] = getattr(user, "id", None)
        return jsonable_encoder(breeding_trial_db.create_one(db=db, obj_in=payload))

    def update_trial(self, db, trial_id, request_data, user):
        obj = breeding_trial_db.get(db=db, id=trial_id)
        payload = request_data.model_dump(exclude_none=True, exclude={"id"})
        for field in ("sowing_date", "harvest_date"):
            payload[field] = self._coerce_iso_date(payload.get(field))
        payload["updated_by"] = getattr(user, "id", None)
        payload["updated_at"] = datetime.utcnow()
        return jsonable_encoder(breeding_trial_db.update_one(db=db, db_obj=obj, obj_in=payload))

    def list_plots(self, db, request_data):
        query = db.query(BreedingPlot)
        program_id = getattr(request_data, "program_id", None)
        if program_id:
            query = query.join(BreedingTrial, BreedingPlot.trial_id == BreedingTrial.id).filter(BreedingTrial.program_id == program_id)
        if request_data.trial_id:
            query = query.filter(BreedingPlot.trial_id == request_data.trial_id)
        if request_data.material_id:
            query = query.filter(BreedingPlot.material_id == request_data.material_id)
        if request_data.replicate_no is not None:
            query = query.filter(BreedingPlot.replicate_no == request_data.replicate_no)
        if request_data.block_no is not None:
            query = query.filter(BreedingPlot.block_no == request_data.block_no)
        if request_data.status:
            query = query.filter(BreedingPlot.status == request_data.status)
        if request_data.keyword:
            keyword = f"%{request_data.keyword}%"
            query = query.filter(BreedingPlot.plot_code.ilike(keyword))
        total, rows = self._paginate(query.order_by(BreedingPlot.id.desc()), request_data.page or 1, request_data.size or 10)
        return {"items": self._serialize_rows(rows), "total": total}

    def get_plot(self, db, plot_id):
        return jsonable_encoder(breeding_plot_db.get(db=db, id=plot_id))

    def create_plot(self, db, request_data, user):
        payload = request_data.model_dump(exclude_none=True)
        payload["created_by"] = getattr(user, "id", None)
        payload["updated_by"] = getattr(user, "id", None)
        return jsonable_encoder(breeding_plot_db.create_one(db=db, obj_in=payload))

    def update_plot(self, db, plot_id, request_data, user):
        obj = breeding_plot_db.get(db=db, id=plot_id)
        payload = request_data.model_dump(exclude_none=True, exclude={"id"})
        payload["updated_by"] = getattr(user, "id", None)
        payload["updated_at"] = datetime.utcnow()
        return jsonable_encoder(breeding_plot_db.update_one(db=db, db_obj=obj, obj_in=payload))

    def list_observations(self, db, request_data):
        query = db.query(BreedingObservation)
        program_id = getattr(request_data, "program_id", None)
        if program_id:
            query = query.join(BreedingTrial, BreedingObservation.trial_id == BreedingTrial.id).filter(BreedingTrial.program_id == program_id)
        if request_data.trial_id:
            query = query.filter(BreedingObservation.trial_id == request_data.trial_id)
        if request_data.plot_id:
            query = query.filter(BreedingObservation.plot_id == request_data.plot_id)
        if request_data.material_id:
            query = query.filter(BreedingObservation.material_id == request_data.material_id)
        if request_data.trait_code:
            query = query.filter(BreedingObservation.trait_code == request_data.trait_code)
        if request_data.qc_status:
            query = query.filter(BreedingObservation.qc_status == request_data.qc_status)
        if request_data.keyword:
            keyword = f"%{request_data.keyword}%"
            query = query.filter(
                or_(
                    BreedingObservation.trait_code.ilike(keyword),
                    BreedingObservation.trait_name.ilike(keyword),
                    BreedingObservation.source_row_key.ilike(keyword),
                    BreedingObservation.observer.ilike(keyword),
                )
            )
        total, rows = self._paginate(query.order_by(BreedingObservation.id.desc()), request_data.page or 1, request_data.size or 10)
        return {"items": self._serialize_rows(rows), "total": total}

    def get_observation(self, db, observation_id):
        return jsonable_encoder(breeding_observation_db.get(db=db, id=observation_id))

    def create_observation(self, db, request_data, user):
        payload = request_data.model_dump(exclude_none=True)
        payload["obs_date"] = self._coerce_iso_date(payload.get("obs_date"))
        payload["created_by"] = getattr(user, "id", None)
        payload["updated_by"] = getattr(user, "id", None)
        return jsonable_encoder(breeding_observation_db.create_one(db=db, obj_in=payload))

    def update_observation(self, db, observation_id, request_data, user):
        obj = breeding_observation_db.get(db=db, id=observation_id)
        payload = request_data.model_dump(exclude_none=True, exclude={"id"})
        payload["obs_date"] = self._coerce_iso_date(payload.get("obs_date"))
        payload["updated_by"] = getattr(user, "id", None)
        payload["updated_at"] = datetime.utcnow()
        return jsonable_encoder(breeding_observation_db.update_one(db=db, db_obj=obj, obj_in=payload))

    def list_biosamples(self, db, request_data):
        query = db.query(BreedingBioSample)
        program_id = getattr(request_data, "program_id", None)
        if program_id:
            query = query.join(BreedingMaterial, BreedingBioSample.material_id == BreedingMaterial.id).filter(BreedingMaterial.program_id == program_id)
        if request_data.material_id:
            query = query.filter(BreedingBioSample.material_id == request_data.material_id)
        if request_data.plot_id:
            query = query.filter(BreedingBioSample.plot_id == request_data.plot_id)
        if request_data.sample_type:
            query = query.filter(BreedingBioSample.sample_type == request_data.sample_type)
        if request_data.organism:
            query = query.filter(BreedingBioSample.organism == request_data.organism)
        if request_data.status:
            query = query.filter(BreedingBioSample.status == request_data.status)
        if request_data.keyword:
            keyword = f"%{request_data.keyword}%"
            query = query.filter(BreedingBioSample.sample_code.ilike(keyword))
        total, rows = self._paginate(query.order_by(BreedingBioSample.id.desc()), request_data.page or 1, request_data.size or 10)
        return {"items": self._serialize_rows(rows), "total": total}

    def get_biosample(self, db, biosample_id):
        return jsonable_encoder(breeding_biosample_db.get(db=db, id=biosample_id))

    def create_biosample(self, db, request_data, user):
        payload = request_data.model_dump(exclude_none=True)
        payload["collection_date"] = self._coerce_iso_date(payload.get("collection_date"))
        payload["created_by"] = getattr(user, "id", None)
        payload["updated_by"] = getattr(user, "id", None)
        return jsonable_encoder(breeding_biosample_db.create_one(db=db, obj_in=payload))

    def update_biosample(self, db, biosample_id, request_data, user):
        obj = breeding_biosample_db.get(db=db, id=biosample_id)
        payload = request_data.model_dump(exclude_none=True, exclude={"id"})
        payload["collection_date"] = self._coerce_iso_date(payload.get("collection_date"))
        payload["updated_by"] = getattr(user, "id", None)
        payload["updated_at"] = datetime.utcnow()
        return jsonable_encoder(breeding_biosample_db.update_one(db=db, db_obj=obj, obj_in=payload))

    def list_assays(self, db, request_data):
        query = db.query(BreedingAssay)
        program_id = getattr(request_data, "program_id", None)
        if program_id:
            query = (
                query.join(BreedingBioSample, BreedingAssay.biosample_id == BreedingBioSample.id)
                .join(BreedingMaterial, BreedingBioSample.material_id == BreedingMaterial.id)
                .filter(BreedingMaterial.program_id == program_id)
            )
        if request_data.biosample_id:
            query = query.filter(BreedingAssay.biosample_id == request_data.biosample_id)
        if request_data.assay_type:
            query = query.filter(BreedingAssay.assay_type == request_data.assay_type)
        if request_data.platform:
            query = query.filter(BreedingAssay.platform == request_data.platform)
        if request_data.library_strategy:
            query = query.filter(BreedingAssay.library_strategy == request_data.library_strategy)
        if request_data.instrument_model:
            query = query.filter(BreedingAssay.instrument_model == request_data.instrument_model)
        if request_data.status:
            query = query.filter(BreedingAssay.status == request_data.status)
        if request_data.keyword:
            keyword = f"%{request_data.keyword}%"
            query = query.filter(BreedingAssay.assay_code.ilike(keyword))
        total, rows = self._paginate(query.order_by(BreedingAssay.id.desc()), request_data.page or 1, request_data.size or 10)
        return {"items": self._serialize_rows(rows), "total": total}

    def get_assay(self, db, assay_id):
        return jsonable_encoder(breeding_assay_db.get(db=db, id=assay_id))

    def create_assay(self, db, request_data, user):
        payload = request_data.model_dump(exclude_none=True)
        payload["run_date"] = self._coerce_iso_date(payload.get("run_date"))
        payload["created_by"] = getattr(user, "id", None)
        payload["updated_by"] = getattr(user, "id", None)
        return jsonable_encoder(breeding_assay_db.create_one(db=db, obj_in=payload))

    def update_assay(self, db, assay_id, request_data, user):
        obj = breeding_assay_db.get(db=db, id=assay_id)
        payload = request_data.model_dump(exclude_none=True, exclude={"id"})
        payload["run_date"] = self._coerce_iso_date(payload.get("run_date"))
        payload["updated_by"] = getattr(user, "id", None)
        payload["updated_at"] = datetime.utcnow()
        return jsonable_encoder(breeding_assay_db.update_one(db=db, db_obj=obj, obj_in=payload))

    def list_data_files(self, db, request_data):
        query = db.query(BreedingDataFile)
        program_id = getattr(request_data, "program_id", None)
        if program_id:
            query = (
                query.join(BreedingAssay, BreedingDataFile.assay_id == BreedingAssay.id)
                .join(BreedingBioSample, BreedingAssay.biosample_id == BreedingBioSample.id)
                .join(BreedingMaterial, BreedingBioSample.material_id == BreedingMaterial.id)
                .filter(BreedingMaterial.program_id == program_id)
            )
        if request_data.assay_id:
            query = query.filter(BreedingDataFile.assay_id == request_data.assay_id)
        if request_data.dataset_id:
            query = query.filter(BreedingDataFile.dataset_id == request_data.dataset_id)
        if request_data.version_id:
            query = query.filter(BreedingDataFile.version_id == request_data.version_id)
        if request_data.asset_id:
            query = query.filter(BreedingDataFile.asset_id == request_data.asset_id)
        if request_data.source_mode:
            query = query.filter(BreedingDataFile.source_mode == request_data.source_mode)
        if request_data.file_role:
            query = query.filter(BreedingDataFile.file_role == request_data.file_role)
        if request_data.status:
            query = query.filter(BreedingDataFile.status == request_data.status)
        if request_data.keyword:
            keyword = f"%{request_data.keyword}%"
            query = query.filter(or_(BreedingDataFile.file_name.ilike(keyword), BreedingDataFile.uri_snapshot.ilike(keyword)))
        total, rows = self._paginate(query.order_by(BreedingDataFile.id.desc()), request_data.page or 1, request_data.size or 10)
        return {"items": self._serialize_rows(rows), "total": total}

    def get_data_file(self, db, data_file_id):
        return jsonable_encoder(breeding_data_file_db.get(db=db, id=data_file_id))

    def create_data_file(self, db, request_data, user):
        payload = request_data.model_dump(exclude_none=True)
        payload["created_by"] = getattr(user, "id", None)
        payload["updated_by"] = getattr(user, "id", None)
        return jsonable_encoder(breeding_data_file_db.create_one(db=db, obj_in=payload))

    def update_data_file(self, db, data_file_id, request_data, user):
        obj = breeding_data_file_db.get(db=db, id=data_file_id)
        payload = request_data.model_dump(exclude_none=True, exclude={"id"})
        payload["updated_by"] = getattr(user, "id", None)
        payload["updated_at"] = datetime.utcnow()
        return jsonable_encoder(breeding_data_file_db.update_one(db=db, db_obj=obj, obj_in=payload))

    def list_dataset_subject_links(self, db, request_data):
        query = db.query(BreedingDatasetSubjectLink)
        for field in ("dataset_id", "version_id", "asset_id", "material_id", "plot_id", "biosample_id", "role", "mapping_status"):
            value = getattr(request_data, field, None)
            if value is not None:
                query = query.filter(getattr(BreedingDatasetSubjectLink, field) == value)
        total, rows = self._paginate(query.order_by(BreedingDatasetSubjectLink.id.desc()), request_data.page or 1, request_data.size or 10)
        return {"items": self._serialize_rows(rows), "total": total}

    def get_dataset_subject_link(self, db, link_id):
        return jsonable_encoder(breeding_dataset_subject_link_db.get(db=db, id=link_id))

    def create_dataset_subject_link(self, db, request_data, user):
        payload = request_data.model_dump(exclude_none=True)
        payload["created_by"] = getattr(user, "id", None)
        payload["updated_by"] = getattr(user, "id", None)
        return jsonable_encoder(breeding_dataset_subject_link_db.create_one(db=db, obj_in=payload))

    def update_dataset_subject_link(self, db, link_id, request_data, user):
        obj = breeding_dataset_subject_link_db.get(db=db, id=link_id)
        payload = request_data.model_dump(exclude_none=True, exclude={"id"})
        payload["updated_by"] = getattr(user, "id", None)
        payload["updated_at"] = datetime.utcnow()
        return jsonable_encoder(breeding_dataset_subject_link_db.update_one(db=db, db_obj=obj, obj_in=payload))

    def list_dataset_assay_links(self, db, request_data):
        query = db.query(BreedingDatasetAssayLink)
        for field in ("dataset_id", "version_id", "asset_id", "assay_id", "role", "mapping_status"):
            value = getattr(request_data, field, None)
            if value is not None:
                query = query.filter(getattr(BreedingDatasetAssayLink, field) == value)
        total, rows = self._paginate(query.order_by(BreedingDatasetAssayLink.id.desc()), request_data.page or 1, request_data.size or 10)
        return {"items": self._serialize_rows(rows), "total": total}

    def get_dataset_assay_link(self, db, link_id):
        return jsonable_encoder(breeding_dataset_assay_link_db.get(db=db, id=link_id))

    def create_dataset_assay_link(self, db, request_data, user):
        payload = request_data.model_dump(exclude_none=True)
        payload["created_by"] = getattr(user, "id", None)
        payload["updated_by"] = getattr(user, "id", None)
        return jsonable_encoder(breeding_dataset_assay_link_db.create_one(db=db, obj_in=payload))

    def update_dataset_assay_link(self, db, link_id, request_data, user):
        obj = breeding_dataset_assay_link_db.get(db=db, id=link_id)
        payload = request_data.model_dump(exclude_none=True, exclude={"id"})
        payload["updated_by"] = getattr(user, "id", None)
        payload["updated_at"] = datetime.utcnow()
        return jsonable_encoder(breeding_dataset_assay_link_db.update_one(db=db, db_obj=obj, obj_in=payload))

    def list_variant_sample_maps(self, db, request_data):
        query = db.query(BreedingVariantSampleMap)
        for field in ("dataset_id", "version_id", "asset_id", "material_id", "biosample_id", "plot_id", "mapping_status"):
            value = getattr(request_data, field, None)
            if value is not None:
                query = query.filter(getattr(BreedingVariantSampleMap, field) == value)
        if request_data.keyword:
            keyword = f"%{request_data.keyword}%"
            query = query.filter(
                or_(
                    BreedingVariantSampleMap.vcf_sample_name.ilike(keyword),
                    BreedingVariantSampleMap.normalized_sample_name.ilike(keyword),
                    BreedingVariantSampleMap.sample_alias.ilike(keyword),
                )
            )
        total, rows = self._paginate(query.order_by(BreedingVariantSampleMap.id.desc()), request_data.page or 1, request_data.size or 10)
        return {"items": self._serialize_rows(rows), "total": total}

    def get_variant_sample_map(self, db, map_id):
        return jsonable_encoder(breeding_variant_sample_map_db.get(db=db, id=map_id))

    def create_variant_sample_map(self, db, request_data, user):
        payload = request_data.model_dump(exclude_none=True)
        payload["created_by"] = getattr(user, "id", None)
        payload["updated_by"] = getattr(user, "id", None)
        return jsonable_encoder(breeding_variant_sample_map_db.create_one(db=db, obj_in=payload))

    def update_variant_sample_map(self, db, map_id, request_data, user):
        obj = breeding_variant_sample_map_db.get(db=db, id=map_id)
        payload = request_data.model_dump(exclude_none=True, exclude={"id"})
        payload["updated_by"] = getattr(user, "id", None)
        payload["updated_at"] = datetime.utcnow()
        return jsonable_encoder(breeding_variant_sample_map_db.update_one(db=db, db_obj=obj, obj_in=payload))

    def list_phenotype_subject_maps(self, db, request_data):
        query = db.query(BreedingPhenotypeSubjectMap)
        for field in ("dataset_id", "version_id", "asset_id", "trial_id", "plot_id", "material_id", "trait_code", "mapping_status"):
            value = getattr(request_data, field, None)
            if value is not None:
                query = query.filter(getattr(BreedingPhenotypeSubjectMap, field) == value)
        if request_data.keyword:
            keyword = f"%{request_data.keyword}%"
            query = query.filter(BreedingPhenotypeSubjectMap.row_key.ilike(keyword))
        total, rows = self._paginate(query.order_by(BreedingPhenotypeSubjectMap.id.desc()), request_data.page or 1, request_data.size or 10)
        return {"items": self._serialize_rows(rows), "total": total}

    def get_phenotype_subject_map(self, db, map_id):
        return jsonable_encoder(breeding_phenotype_subject_map_db.get(db=db, id=map_id))

    def create_phenotype_subject_map(self, db, request_data, user):
        payload = request_data.model_dump(exclude_none=True)
        payload["created_by"] = getattr(user, "id", None)
        payload["updated_by"] = getattr(user, "id", None)
        return jsonable_encoder(breeding_phenotype_subject_map_db.create_one(db=db, obj_in=payload))

    def update_phenotype_subject_map(self, db, map_id, request_data, user):
        obj = breeding_phenotype_subject_map_db.get(db=db, id=map_id)
        payload = request_data.model_dump(exclude_none=True, exclude={"id"})
        payload["updated_by"] = getattr(user, "id", None)
        payload["updated_at"] = datetime.utcnow()
        return jsonable_encoder(breeding_phenotype_subject_map_db.update_one(db=db, db_obj=obj, obj_in=payload))

    def link_dataset_to_program(self, db, program_id, dataset_id, version_id=None, link_type="dataset_subject_link", role=None, material_id=None, note=None):
        from modules.datasets.dataset_model import Dataset
        from modules.datasets.models import DatasetVersion

        # Validate dataset exists
        dataset = db.query(Dataset).filter_by(id=dataset_id).first()
        if not dataset:
            return {"linked": False, "dataset_id": dataset_id, "link_type": link_type, "message": "Dataset not found"}

        # Auto-resolve latest version from DatasetVersion
        if version_id is None:
            latest_version = (
                db.query(DatasetVersion)
                .filter(DatasetVersion.dataset_id == dataset_id)
                .order_by(DatasetVersion.id.desc())
                .first()
            )
            if latest_version:
                version_id = latest_version.id
            else:
                return {"linked": False, "dataset_id": dataset_id, "link_type": link_type, "message": "No version found for dataset"}

        link_id = None
        if link_type == "dataset_subject_link":
            link = BreedingDatasetSubjectLink(
                dataset_id=dataset_id,
                version_id=version_id,
                program_id=program_id,
                material_id=material_id,
                role=role or "subject",
                mapping_status="draft",
                mapping_method="manual",
            )
            db.add(link)
            db.commit()
            link_id = link.id
        elif link_type == "dataset_assay_link":
            link = BreedingDatasetAssayLink(
                dataset_id=dataset_id,
                version_id=version_id,
                assay_id=material_id,  # caller passes assay_id as material_id
                role=role or "assay",
                mapping_status="draft",
                mapping_method="manual",
            )
            db.add(link)
            db.commit()
            link_id = link.id
        else:
            return {"linked": False, "dataset_id": dataset_id, "link_type": link_type, "message": f"Unsupported link_type: {link_type}"}

        return {"linked": True, "dataset_id": dataset_id, "link_type": link_type, "link_id": link_id}

    def sync_variant_samples_to_catalog(self, db, dataset_id, version_id, asset_id, sample_names):
        """Sync VCF sample names to BreedingVariantSampleMap table."""
        sample_names = list(sample_names or [])
        if not sample_names:
            return {"created": 0, "already_exist": 0, "total_in_vcf": 0}

        existing = (
            db.query(BreedingVariantSampleMap)
            .filter_by(dataset_id=dataset_id, version_id=version_id, asset_id=asset_id)
            .all()
        )
        existing_names = {e.vcf_sample_name for e in existing}

        created = 0
        for name in sample_names:
            if name in existing_names:
                continue
            vmap = BreedingVariantSampleMap(
                dataset_id=dataset_id,
                version_id=version_id,
                asset_id=asset_id,
                vcf_sample_name=name,
                mapping_status="draft",
                mapping_method="import",
            )
            db.add(vmap)
            created += 1

        if created:
            db.commit()

        return {
            "created": created,
            "already_exist": len([n for n in sample_names if n in existing_names]),
            "total_in_vcf": len(sample_names),
        }

    def map_expression_samples_to_biosamples(self, db, dataset_id, version_id, asset_id, sample_names):
        """Map expression matrix column names to BioSample records.

        Strategy: exact match on sample_code, then fuzzy (ILIKE %name%).
        """
        sample_names = list(sample_names or [])
        if not sample_names:
            return {"mapped": 0, "unmapped": 0, "total": 0, "matches": []}

        matches = []
        unmatched = []
        all_biosamples = db.query(BreedingBioSample).filter(
            BreedingBioSample.status == "active"
        ).all()

        biosample_by_code = {bs.sample_code: bs for bs in all_biosamples if bs.sample_code}

        for name in sample_names:
            if name in biosample_by_code:
                bs = biosample_by_code[name]
                matches.append({
                    "sample_name": name,
                    "biosample_id": bs.id,
                    "biosample_code": bs.sample_code,
                    "material_id": bs.material_id,
                    "confidence": "exact",
                })
                continue

            # Fuzzy match
            fuzzy = None
            for bs in all_biosamples:
                if not bs.sample_code:
                    continue
                if name.lower() in bs.sample_code.lower() or bs.sample_code.lower() in name.lower():
                    fuzzy = bs
                    break

            if fuzzy:
                matches.append({
                    "sample_name": name,
                    "biosample_id": fuzzy.id,
                    "biosample_code": fuzzy.sample_code,
                    "material_id": fuzzy.material_id,
                    "confidence": "fuzzy",
                })
            else:
                unmatched.append(name)

        return {
            "mapped": len(matches),
            "unmapped": len(unmatched),
            "total": len(sample_names),
            "matches": matches,
            "unmatched_names": unmatched,
        }


breeding_domain_service = BreedingDomainService()
