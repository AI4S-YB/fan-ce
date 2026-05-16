import json
import os
import sqlite3
import time
from collections import defaultdict
from typing import Any

from fastapi import HTTPException

from .models import FunctionalGene, FunctionalTerm, FunctionalTermAssignment


FUNCTIONAL_INDEX_SOURCES = ("go", "kegg", "interpro", "itak", "family")
INTERPRO_ENTRY_KEYS = ("matches_format", "matches", "annotated_domains", "entries", "domains")


def _parse_json_value(raw_value: Any) -> Any:
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, (dict, list)):
        return raw_value
    if isinstance(raw_value, (int, float, bool)):
        return raw_value
    text = str(raw_value).strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _normalize_term_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_go_terms(raw_value: Any) -> list[dict[str, Any]]:
    payload = _parse_json_value(raw_value)
    items = payload if isinstance(payload, list) else [payload] if payload else []
    terms = []
    for item in items:
        if isinstance(item, dict):
            term_id = _normalize_term_text(item.get("term") or item.get("go_id") or item.get("id") or item.get("accession"))
            if not term_id:
                continue
            term_name = _normalize_term_text(item.get("name") or item.get("description") or item.get("term_name"))
            term_type = _normalize_term_text(item.get("namespace") or item.get("type") or item.get("category"))
            terms.append(
                {
                    "term_source": "go",
                    "term_id": term_id,
                    "term_name": term_name,
                    "term_type": term_type,
                    "description": term_name,
                    "attributes": item,
                }
            )
            continue
        term_id = _normalize_term_text(item)
        if term_id:
            terms.append(
                {
                    "term_source": "go",
                    "term_id": term_id,
                    "term_name": None,
                    "term_type": None,
                    "description": None,
                    "attributes": {"value": term_id},
                }
            )
    return terms


def _normalize_kegg_terms(raw_value: Any) -> list[dict[str, Any]]:
    payload = _parse_json_value(raw_value)
    items = payload if isinstance(payload, list) else [payload] if payload else []
    terms = []
    for item in items:
        if isinstance(item, dict):
            term_id = _normalize_term_text(item.get("pathway") or item.get("term") or item.get("id") or item.get("ko"))
            if not term_id:
                continue
            term_name = _normalize_term_text(item.get("description") or item.get("name") or item.get("title"))
            term_type = _normalize_term_text(item.get("type") or "pathway")
            terms.append(
                {
                    "term_source": "kegg",
                    "term_id": term_id,
                    "term_name": term_name,
                    "term_type": term_type,
                    "description": term_name,
                    "attributes": item,
                }
            )
            continue
        term_id = _normalize_term_text(item)
        if term_id:
            terms.append(
                {
                    "term_source": "kegg",
                    "term_id": term_id,
                    "term_name": None,
                    "term_type": "pathway",
                    "description": None,
                    "attributes": {"value": term_id},
                }
            )
    return terms


def _normalize_interpro_terms(raw_value: Any) -> list[dict[str, Any]]:
    payload = _parse_json_value(raw_value)
    items = []
    if isinstance(payload, dict):
        for key in INTERPRO_ENTRY_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                items.extend(value)
    elif isinstance(payload, list):
        items = payload

    terms = []
    for item in items:
        if not isinstance(item, dict):
            term_id = _normalize_term_text(item)
            if not term_id:
                continue
            terms.append(
                {
                    "term_source": "interpro",
                    "term_id": term_id,
                    "term_name": None,
                    "term_type": None,
                    "description": None,
                    "attributes": {"value": term_id},
                }
            )
            continue

        term_id = _normalize_term_text(
            item.get("ipr_term")
            or item.get("interpro_id")
            or item.get("source_term")
            or item.get("entry_id")
            or item.get("id")
        )
        if not term_id:
            continue
        term_name = _normalize_term_text(
            item.get("ipr_desc")
            or item.get("source_name")
            or item.get("source_desc")
            or item.get("description")
            or item.get("name")
        )
        term_type = _normalize_term_text(item.get("source_lib") or item.get("type") or item.get("source_database"))
        description = _normalize_term_text(item.get("ipr_desc") or item.get("source_desc") or item.get("description"))
        terms.append(
            {
                "term_source": "interpro",
                "term_id": term_id,
                "term_name": term_name,
                "term_type": term_type,
                "description": description or term_name,
                "attributes": item,
            }
        )
    return terms


def _normalize_family_terms(raw_value: Any) -> list[dict[str, Any]]:
    payload = _parse_json_value(raw_value)
    items = payload if isinstance(payload, list) else [payload] if payload else []
    terms = []
    for item in items:
        if isinstance(item, dict):
            term_source = str(item.get("database") or "family").strip().lower()
            if term_source not in FUNCTIONAL_INDEX_SOURCES:
                term_source = "family"
            term_id = _normalize_term_text(item.get("name") or item.get("family") or item.get("id"))
            if not term_id:
                continue
            term_type = _normalize_term_text(item.get("type") or item.get("class") or item.get("category"))
            terms.append(
                {
                    "term_source": term_source,
                    "term_id": term_id,
                    "term_name": term_id,
                    "term_type": term_type,
                    "description": term_id,
                    "attributes": item,
                }
            )
            continue
        term_id = _normalize_term_text(item)
        if term_id:
            terms.append(
                {
                    "term_source": "family",
                    "term_id": term_id,
                    "term_name": term_id,
                    "term_type": None,
                    "description": term_id,
                    "attributes": {"value": term_id},
                }
            )
    return terms


def _require_functional_schema(file_path: str):
    if not file_path.endswith(".db") and not file_path.endswith(".sqlite"):
        raise HTTPException(status_code=400, detail="functional annotation indexer currently supports sqlite-backed assets only")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"functional annotation file not found: {file_path}")
    conn = sqlite3.connect(file_path)
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {str(row[0]) for row in cursor.fetchall()}
    finally:
        conn.close()
    if "hse_genes" not in tables or "hse_transcripts" not in tables:
        raise HTTPException(status_code=400, detail="functional annotation sqlite schema is not supported yet")


def clear_functional_annotation_index(db, *, dataset_id: int, version_id: int, asset_id: int):
    scope = {
        "dataset_id": dataset_id,
        "version_id": version_id,
        "asset_id": asset_id,
    }
    db.query(FunctionalTermAssignment).filter_by(**scope).delete(synchronize_session=False)
    db.query(FunctionalTerm).filter_by(**scope).delete(synchronize_session=False)
    db.query(FunctionalGene).filter_by(**scope).delete(synchronize_session=False)
    db.commit()


def rebuild_functional_annotation_index(
    db,
    *,
    dataset_id: int,
    version_id: int,
    asset_id: int,
    file_path: str,
) -> dict[str, Any]:
    _require_functional_schema(file_path)

    now = int(time.time())
    clear_functional_annotation_index(db=db, dataset_id=dataset_id, version_id=version_id, asset_id=asset_id)

    conn = sqlite3.connect(file_path)
    conn.row_factory = sqlite3.Row
    try:
        gene_rows = conn.execute(
            """
            SELECT gene_id, chrom, start, stop, strand, description, canonical_transcript, family
            FROM hse_genes
            ORDER BY gene_id
            """
        ).fetchall()
        transcript_rows = conn.execute(
            """
            SELECT transcript_id, gene_id, chrom, start, stop, strand, description, InterPro, GO, KEGG, family
            FROM hse_transcripts
            ORDER BY gene_id, transcript_id
            """
        ).fetchall()
    finally:
        conn.close()

    gene_payloads = []
    gene_lookup: dict[str, dict[str, Any]] = {}
    assignment_payloads = []
    assignment_keys = set()
    term_stats: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "term_name": None,
            "term_type": None,
            "description": None,
            "assignment_count": 0,
            "gene_ids": set(),
            "attributes": None,
        }
    )

    def add_assignment(gene_id: str, transcript_id: str | None, term: dict[str, Any]):
        term_source = str(term.get("term_source") or "").strip().lower()
        term_id = _normalize_term_text(term.get("term_id"))
        if not term_source or not term_id:
            return
        normalized_transcript_id = _normalize_term_text(transcript_id) or ""
        assignment_key = (gene_id, normalized_transcript_id, term_source, term_id)
        if assignment_key in assignment_keys:
            return
        assignment_keys.add(assignment_key)
        assignment_payloads.append(
            {
                "dataset_id": dataset_id,
                "version_id": version_id,
                "asset_id": asset_id,
                "gene_id": gene_id,
                "transcript_id": normalized_transcript_id,
                "term_source": term_source,
                "term_id": term_id,
                "term_name": term.get("term_name"),
                "term_type": term.get("term_type"),
                "attributes_json": json.dumps(term.get("attributes"), ensure_ascii=False)
                if term.get("attributes") is not None
                else None,
                "create_time": now,
            }
        )
        stat = term_stats[(term_source, term_id)]
        stat["term_name"] = stat["term_name"] or term.get("term_name")
        stat["term_type"] = stat["term_type"] or term.get("term_type")
        stat["description"] = stat["description"] or term.get("description") or term.get("term_name")
        stat["assignment_count"] += 1
        stat["gene_ids"].add(gene_id)
        if stat["attributes"] is None and term.get("attributes") is not None:
            stat["attributes"] = term.get("attributes")

    for row in gene_rows:
        gene_id = str(row["gene_id"])
        family_value = _parse_json_value(row["family"])
        gene_payload = {
            "dataset_id": dataset_id,
            "version_id": version_id,
            "asset_id": asset_id,
            "gene_id": gene_id,
            "canonical_transcript_id": row["canonical_transcript"],
            "chrom": row["chrom"],
            "start": row["start"],
            "end": row["stop"],
            "strand": row["strand"],
            "description": row["description"],
            "family": json.dumps(family_value, ensure_ascii=False) if isinstance(family_value, (dict, list)) else _normalize_term_text(family_value),
            "extra_json": None,
            "create_time": now,
            "update_time": now,
        }
        gene_payloads.append(gene_payload)
        gene_lookup[gene_id] = gene_payload
        for term in _normalize_family_terms(family_value):
            add_assignment(gene_id=gene_id, transcript_id=None, term=term)

    for row in transcript_rows:
        gene_id = str(row["gene_id"])
        transcript_id = str(row["transcript_id"])
        for term in _normalize_go_terms(row["GO"]):
            add_assignment(gene_id=gene_id, transcript_id=transcript_id, term=term)
        for term in _normalize_kegg_terms(row["KEGG"]):
            add_assignment(gene_id=gene_id, transcript_id=transcript_id, term=term)
        for term in _normalize_interpro_terms(row["InterPro"]):
            add_assignment(gene_id=gene_id, transcript_id=transcript_id, term=term)
        for term in _normalize_family_terms(row["family"]):
            add_assignment(gene_id=gene_id, transcript_id=transcript_id, term=term)

    term_payloads = []
    for (term_source, term_id), stat in sorted(term_stats.items(), key=lambda item: (item[0][0], item[0][1])):
        term_payloads.append(
            {
                "dataset_id": dataset_id,
                "version_id": version_id,
                "asset_id": asset_id,
                "term_source": term_source,
                "term_id": term_id,
                "term_name": stat["term_name"],
                "term_type": stat["term_type"],
                "description": stat["description"],
                "assignment_count": stat["assignment_count"],
                "gene_count": len(stat["gene_ids"]),
                "extra_json": json.dumps(stat["attributes"], ensure_ascii=False) if stat["attributes"] is not None else None,
                "create_time": now,
                "update_time": now,
            }
        )

    if gene_payloads:
        db.execute(FunctionalGene.__table__.insert(), gene_payloads)
    if term_payloads:
        db.execute(FunctionalTerm.__table__.insert(), term_payloads)
    if assignment_payloads:
        db.execute(FunctionalTermAssignment.__table__.insert(), assignment_payloads)
    db.commit()

    return {
        "dataset_id": dataset_id,
        "version_id": version_id,
        "asset_id": asset_id,
        "gene_count": len(gene_payloads),
        "term_count": len(term_payloads),
        "assignment_count": len(assignment_payloads),
        "file_path": file_path,
    }
