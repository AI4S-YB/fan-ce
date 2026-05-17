import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import and_, desc, distinct, func, or_

from basis.core.sqlite_utils import query_sqlite
from db.database import mydb

from apps.datasets.functional_indexing import rebuild_functional_annotation_index
from apps.datasets.models import FunctionalGene, FunctionalTerm, FunctionalTermAssignment

from .base import DatasetQueryAdapter


class FunctionalAnnotationAdapter(DatasetQueryAdapter):
    adapter_name = "functional_annotation"
    display_name = "Functional Annotation Adapter"
    supported_dataset_types = ["annotation", "genome", "sequence"]
    supported_file_formats = ["db", "sqlite"]

    def supports(self, dataset_payload: Dict[str, Any]) -> bool:
        asset = self.get_query_entry_asset(dataset_payload) or {}
        asset_type = str(asset.get("asset_type") or "").lower()
        query_engine = str(asset.get("query_engine") or dataset_payload.get("query_profile", {}).get("query_engine") or "").lower()
        file_format = str(dataset_payload.get("query_profile", {}).get("file_format") or "").lower()
        dataset_type = str(dataset_payload.get("dataset_type") or "").lower()

        if asset_type or query_engine:
            return (
                asset_type == "functional_annotation"
                or query_engine == "functional_annotation"
                or (asset_type == "functional_annotation" and file_format in self.supported_file_formats)
            )

        return dataset_type in self.supported_dataset_types or file_format in self.supported_file_formats

    def _is_sqlite_file(self, file_path: str) -> bool:
        return file_path.endswith(".sqlite") or file_path.endswith(".db")

    def _parse_json_value(self, raw_value: Any) -> Any:
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

    def _get_sqlite_tables(self, file_path: str) -> List[str]:
        rows = query_sqlite(file_path, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [str(item["name"]) for item in rows if item.get("name")]

    def _require_functional_schema(self, file_path: str) -> List[str]:
        if not self._is_sqlite_file(file_path):
            raise HTTPException(status_code=400, detail="functional_annotation currently only supports sqlite-backed assets")
        tables = self._get_sqlite_tables(file_path)
        if "hse_genes" not in tables or "hse_transcripts" not in tables:
            raise HTTPException(status_code=400, detail="functional annotation sqlite schema is not supported yet")
        return tables

    def _search_genes(self, file_path: str, keyword: str = None, chrom: str = None,
                     start: int = None, end: int = None, strand: str = None,
                     family: str = None, page: int = 1, size: int = 20) -> Dict[str, Any]:
        where_clauses: List[str] = []
        params_list: List[Any] = []

        if keyword:
            kw = f"%{keyword}%"
            where_clauses.append("(gene_id LIKE ? OR description LIKE ?)")
            params_list.extend([kw, kw])
        if chrom:
            where_clauses.append("chrom = ?")
            params_list.append(chrom)
        if start is not None:
            where_clauses.append("stop >= ?")
            params_list.append(start)
        if end is not None:
            where_clauses.append("start <= ?")
            params_list.append(end)
        if strand:
            where_clauses.append("strand = ?")
            params_list.append(strand)
        if family:
            where_clauses.append("family LIKE ?")
            params_list.append(f"%{family}%")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        count_rows = query_sqlite(
            file_path,
            f"SELECT COUNT(*) AS cnt FROM hse_genes WHERE {where_sql}",
            tuple(params_list),
        )
        total = count_rows[0]["cnt"] if count_rows else 0

        offset = (page - 1) * size
        rows = query_sqlite(
            file_path,
            f"""SELECT gene_id, chrom, start, stop, strand, description, canonical_transcript, family
                FROM hse_genes WHERE {where_sql}
                ORDER BY chrom ASC, start ASC
                LIMIT ? OFFSET ?""",
            tuple(params_list + [size, offset]),
        )
        items = []
        for row in rows:
            row_dict = dict(row)
            row_dict["family"] = self._parse_json_value(row_dict.get("family"))
            items.append(row_dict)

        return {"items": items, "total": total, "page": page, "size": size}

    def _query_gene_row(self, file_path: str, gene_id: str) -> Dict[str, Any]:
        rows = query_sqlite(
            file_path,
            """
            SELECT gene_id, chrom, start, stop, strand, description, canonical_transcript, family
            FROM hse_genes
            WHERE gene_id = ?
            LIMIT 1
            """,
            (gene_id,),
        )
        if not rows:
            raise HTTPException(status_code=404, detail=f"gene not found: {gene_id}")
        row = dict(rows[0])
        row["family"] = self._parse_json_value(row.get("family"))
        return row

    def _query_transcript_row(self, file_path: str, transcript_id: str) -> Dict[str, Any]:
        rows = query_sqlite(
            file_path,
            """
            SELECT transcript_id, gene_id, chrom, start, stop, strand, description,
                   blast_TAIR, blast_nr, blast_Swiss_Prot, blast_TrEMBL,
                   InterPro, GO, KEGG, family
            FROM hse_transcripts
            WHERE transcript_id = ?
            LIMIT 1
            """,
            (transcript_id,),
        )
        if not rows:
            raise HTTPException(status_code=404, detail=f"transcript not found: {transcript_id}")
        return self._serialize_transcript_row(dict(rows[0]))

    def _query_transcript_rows_by_gene(self, file_path: str, gene_id: str, limit: int = 500) -> List[Dict[str, Any]]:
        rows = query_sqlite(
            file_path,
            """
            SELECT transcript_id, gene_id, chrom, start, stop, strand, description,
                   blast_TAIR, blast_nr, blast_Swiss_Prot, blast_TrEMBL,
                   InterPro, GO, KEGG, family
            FROM hse_transcripts
            WHERE gene_id = ?
            ORDER BY start ASC
            LIMIT ?
            """,
            (gene_id, limit),
        )
        return [self._serialize_transcript_row(dict(row)) for row in rows]

    def _query_exons(self, file_path: str, gene_id: str) -> list:
        rows = query_sqlite(
            file_path,
            "SELECT feature_type, start, stop, strand, transcript_id "
            "FROM hse_exons WHERE gene_id=? ORDER BY start",
            (gene_id,),
        )
        return [
            {
                "feature_type": r["feature_type"],
                "start": r["start"],
                "stop": r["stop"],
                "strand": r["strand"],
                "transcript_id": r["transcript_id"],
            }
            for r in rows
        ]

    def _serialize_transcript_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        annotations = {
            "go": self._parse_json_value(row.pop("GO", None)) or [],
            "kegg": self._parse_json_value(row.pop("KEGG", None)) or [],
            "interpro": self._parse_json_value(row.pop("InterPro", None)),
            "family": self._parse_json_value(row.pop("family", None)) or [],
            "blast": {
                "tair": self._parse_json_value(row.pop("blast_TAIR", None)),
                "nr": self._parse_json_value(row.pop("blast_nr", None)),
                "swiss_prot": self._parse_json_value(row.pop("blast_Swiss_Prot", None)),
                "trembl": self._parse_json_value(row.pop("blast_TrEMBL", None)),
            },
        }
        annotations["blast"] = {
            key: value for key, value in annotations["blast"].items() if value not in (None, "", [], {})
        }
        return {
            **row,
            "annotation_counts": self._build_annotation_counts(annotations),
            "annotations": annotations,
        }

    def _build_annotation_counts(self, annotations: Dict[str, Any]) -> Dict[str, int]:
        interpro = annotations.get("interpro")
        interpro_count = 0
        if isinstance(interpro, dict):
            for key in ["matches", "matches_format", "annotated_domains", "entries", "domains"]:
                value = interpro.get(key)
                if isinstance(value, list):
                    interpro_count = len(value)
                    break
        elif isinstance(interpro, list):
            interpro_count = len(interpro)
        blast_payload = annotations.get("blast") or {}
        return {
            "go": len(annotations.get("go") or []),
            "kegg": len(annotations.get("kegg") or []),
            "interpro": interpro_count,
            "family": len(annotations.get("family") or []),
            "blast_sources": len(blast_payload),
        }

    def _pick_canonical_transcript(self, gene: Dict[str, Any], transcripts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        canonical_id = gene.get("canonical_transcript")
        if canonical_id:
            match = next((item for item in transcripts if item.get("transcript_id") == canonical_id), None)
            if match:
                return match
        return transcripts[0] if transcripts else None

    def _resolve_index_scope(self, dataset_payload: Dict[str, Any]) -> Dict[str, int]:
        asset = self.get_query_entry_asset(dataset_payload) or {}
        dataset_id = int(dataset_payload.get("id") or 0)
        version_id = int(
            asset.get("version_id")
            or (dataset_payload.get("selected_version") or {}).get("id")
            or (dataset_payload.get("published_version") or {}).get("id")
            or 0
        )
        asset_id = int(asset.get("id") or 0)
        if not dataset_id or not version_id or not asset_id:
            raise HTTPException(status_code=400, detail="functional annotation index scope is incomplete")
        return {
            "dataset_id": dataset_id,
            "version_id": version_id,
            "asset_id": asset_id,
        }

    def _get_runtime_db(self, dataset_payload: Dict[str, Any]):
        runtime_context = dataset_payload.get("_runtime_context") or {}
        db = runtime_context.get("db")
        if db is not None:
            return db, False
        return mydb.get_dbs(), True

    def _serialize_term_row(self, row: FunctionalTerm) -> Dict[str, Any]:
        return {
            "term_source": row.term_source,
            "term_id": row.term_id,
            "term_name": row.term_name,
            "term_type": row.term_type,
            "description": row.description,
            "assignment_count": row.assignment_count,
            "gene_count": row.gene_count,
            "extra_json": self._parse_json_value(row.extra_json),
        }

    def _serialize_gene_index_row(self, row: FunctionalGene) -> Dict[str, Any]:
        return {
            "gene_id": row.gene_id,
            "canonical_transcript_id": row.canonical_transcript_id,
            "chrom": row.chrom,
            "start": row.start,
            "end": row.end,
            "strand": row.strand,
            "description": row.description,
            "family": self._parse_json_value(row.family),
            "extra_json": self._parse_json_value(row.extra_json),
        }

    def _ensure_term_index(self, db, dataset_payload: Dict[str, Any], file_path: str) -> Dict[str, int]:
        scope = self._resolve_index_scope(dataset_payload)
        exists = db.query(FunctionalTerm.id).filter_by(**scope).first()
        if exists:
            return scope
        rebuild_functional_annotation_index(db=db, file_path=file_path, **scope)
        return scope

    def describe(self, dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self.require_file_path(dataset_payload)

        example_gene_id = ""
        example_transcript_id = ""
        if self._is_sqlite_file(file_path):
            try:
                rows = query_sqlite(file_path, "SELECT gene_id FROM hse_genes LIMIT 1")
                if rows:
                    example_gene_id = str(rows[0].get("gene_id") or "")
            except Exception:
                pass
            try:
                rows = query_sqlite(file_path, "SELECT transcript_id FROM hse_transcripts LIMIT 1")
                if rows:
                    example_transcript_id = str(rows[0].get("transcript_id") or "")
            except Exception:
                pass

        if not example_gene_id:
            example_gene_id = "unknown"
        if not example_transcript_id:
            example_transcript_id = "unknown"

        return {
            "adapter": self.adapter_name,
            "display_name": self.display_name,
            "dataset_type": dataset_payload.get("dataset_type"),
            "file_format": dataset_payload.get("query_profile", {}).get("file_format"),
            "supported_operations": [
                "search_genes",
                "list_genes",
                "list_families",
                "gene_detail",
                "transcript_detail",
                "gene_function_summary",
                "gene_descriptions",
                "term_lookup",
                "term_gene_list",
                "term_aggregation",
            ],
            "query_entrypoints": ["/api/v1/dataset/query/execute"],
            "examples": {
                "search_genes": {
                    "operation": "search_genes",
                    "params": {"keyword": "BRCA1", "page": 1, "size": 20},
                },
                "list_genes": {
                    "operation": "list_genes",
                    "params": {"page": 1, "size": 20},
                },
                "gene_detail": {
                    "operation": "gene_detail",
                    "params": {"gene_id": example_gene_id},
                },
                "transcript_detail": {
                    "operation": "transcript_detail",
                    "params": {"transcript_id": example_transcript_id},
                },
                "gene_function_summary": {
                    "operation": "gene_function_summary",
                    "params": {"gene_id": example_gene_id},
                },
                "term_lookup": {
                    "operation": "term_lookup",
                    "params": {"term_source": "go", "keyword": "transcription", "limit": 20},
                },
                "term_gene_list": {
                    "operation": "term_gene_list",
                    "params": {"term_source": "go", "term_id": "GO:0006355", "page": 1, "size": 20},
                },
                "term_aggregation": {
                    "operation": "term_aggregation",
                    "params": {"term_source": "interpro", "limit": 10},
                },
            },
        }

    def execute(self, dataset_payload: Dict[str, Any], operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self.require_file_path(dataset_payload)
        self._require_functional_schema(file_path)

        if operation == "search_genes":
            keyword = str(params.get("keyword") or params.get("gene_keyword") or "").strip() or None
            chrom = str(params.get("chrom") or "").strip() or None
            start = params.get("start")
            end = params.get("end")
            strand = str(params.get("strand") or "").strip() or None
            family = str(params.get("family") or "").strip() or None
            page = max(int(params.get("page") or 1), 1)
            size = min(max(int(params.get("size") or 20), 1), 200)
            result = self._search_genes(file_path, keyword=keyword, chrom=chrom,
                                       start=start, end=end, strand=strand,
                                       family=family, page=page, size=size)
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {"source": "sqlite", **result},
            }

        if operation == "list_genes":
            page = max(int(params.get("page") or 1), 1)
            size = min(max(int(params.get("size") or 20), 1), 200)
            result = self._search_genes(file_path, page=page, size=size)
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {"source": "sqlite", **result},
            }

        if operation == "gene_descriptions":
            gene_ids = params.get("gene_ids") or []
            if not gene_ids:
                return {"adapter": self.adapter_name, "operation": operation, "dataset_id": dataset_payload["id"], "data": {"descriptions": {}}}
            # Build IN clause for batch query
            placeholders = ",".join(["?" for _ in gene_ids])
            rows = query_sqlite(file_path, f"SELECT gene_id, description FROM hse_genes WHERE gene_id IN ({placeholders})", tuple(gene_ids))
            descriptions = {r["gene_id"]: r.get("description") or "" for r in rows}
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {"descriptions": descriptions},
            }

        if operation == "list_families":
            rows = query_sqlite(
                file_path,
                "SELECT DISTINCT family FROM hse_genes WHERE family IS NOT NULL AND family != '' ORDER BY family",
                (),
            )
            families = []
            seen = set()
            for r in rows:
                parsed = self._parse_json_value(r["family"])
                items = parsed if isinstance(parsed, list) else [parsed] if parsed else []
                for item in items:
                    key = str(item)
                    if key not in seen:
                        seen.add(key)
                        families.append(item)
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {"source": "sqlite", "families": families},
            }

        if operation == "gene_detail":
            gene_id = str(params.get("gene_id") or "").strip()
            if not gene_id:
                raise HTTPException(status_code=400, detail="gene_id is required")
            gene = self._query_gene_row(file_path, gene_id)
            transcripts = self._query_transcript_rows_by_gene(file_path, gene_id)
            canonical_transcript = self._pick_canonical_transcript(gene, transcripts)
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {
                    "source": "sqlite",
                    "gene": gene,
                    "transcripts": transcripts,
                    "transcript_count": len(transcripts),
                    "canonical_transcript": canonical_transcript,
                },
            }

        if operation == "transcript_detail":
            transcript_id = str(params.get("transcript_id") or "").strip()
            if not transcript_id:
                raise HTTPException(status_code=400, detail="transcript_id is required")
            transcript = self._query_transcript_row(file_path, transcript_id)
            gene = self._query_gene_row(file_path, str(transcript.get("gene_id") or ""))
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {
                    "source": "sqlite",
                    "gene": gene,
                    "transcript": transcript,
                },
            }

        if operation == "gene_function_summary":
            gene_id = str(params.get("gene_id") or "").strip()
            if not gene_id:
                raise HTTPException(status_code=400, detail="gene_id is required")
            gene = self._query_gene_row(file_path, gene_id)
            transcripts = self._query_transcript_rows_by_gene(file_path, gene_id)
            canonical_transcript = self._pick_canonical_transcript(gene, transcripts)
            annotations = canonical_transcript.get("annotations") if canonical_transcript else {
                "go": [],
                "kegg": [],
                "interpro": None,
                "family": [],
                "blast": {},
            }
            exons = self._query_exons(file_path, gene_id)
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {
                    "source": "sqlite",
                    "gene": gene,
                    "canonical_transcript_id": gene.get("canonical_transcript"),
                    "transcript_count": len(transcripts),
                    "annotation_counts": self._build_annotation_counts(annotations),
                    "annotations": annotations,
                    "exons": exons,
                },
            }

        if operation in {"term_lookup", "term_gene_list", "term_aggregation"}:
            db, should_close = self._get_runtime_db(dataset_payload)
            try:
                scope = self._ensure_term_index(db=db, dataset_payload=dataset_payload, file_path=file_path)

                if operation == "term_lookup":
                    term_source = str(params.get("term_source") or "").strip().lower()
                    keyword = str(params.get("keyword") or "").strip()
                    term_id = str(params.get("term_id") or "").strip()
                    limit = min(max(int(params.get("limit") or 20), 1), 200)

                    query = db.query(FunctionalTerm).filter_by(**scope)
                    if term_source:
                        query = query.filter(func.lower(FunctionalTerm.term_source) == term_source)
                    if term_id:
                        query = query.filter(FunctionalTerm.term_id == term_id)
                    if keyword:
                        keyword_like = f"%{keyword.lower()}%"
                        query = query.filter(
                            or_(
                                func.lower(func.coalesce(FunctionalTerm.term_id, "")).like(keyword_like),
                                func.lower(func.coalesce(FunctionalTerm.term_name, "")).like(keyword_like),
                                func.lower(func.coalesce(FunctionalTerm.description, "")).like(keyword_like),
                            )
                        )
                    total = query.count()
                    rows = (
                        query.order_by(
                            desc(FunctionalTerm.gene_count),
                            desc(FunctionalTerm.assignment_count),
                            FunctionalTerm.term_source.asc(),
                            FunctionalTerm.term_id.asc(),
                        )
                        .limit(limit)
                        .all()
                    )
                    return {
                        "adapter": self.adapter_name,
                        "operation": operation,
                        "dataset_id": dataset_payload["id"],
                        "data": {
                            "source": "postgresql_index",
                            "scope": scope,
                            "filters": {
                                "term_source": term_source or None,
                                "term_id": term_id or None,
                                "keyword": keyword or None,
                                "limit": limit,
                            },
                            "total": total,
                            "items": [self._serialize_term_row(row) for row in rows],
                        },
                    }

                if operation == "term_gene_list":
                    term_source = str(params.get("term_source") or "").strip().lower()
                    term_id = str(params.get("term_id") or "").strip()
                    if not term_source:
                        raise HTTPException(status_code=400, detail="term_source is required")
                    if not term_id:
                        raise HTTPException(status_code=400, detail="term_id is required")
                    page = max(int(params.get("page") or 1), 1)
                    size = min(max(int(params.get("size") or 20), 1), 200)

                    assignment_filters = and_(
                        FunctionalTermAssignment.dataset_id == scope["dataset_id"],
                        FunctionalTermAssignment.version_id == scope["version_id"],
                        FunctionalTermAssignment.asset_id == scope["asset_id"],
                        func.lower(FunctionalTermAssignment.term_source) == term_source,
                        FunctionalTermAssignment.term_id == term_id,
                    )

                    total = db.query(func.count(distinct(FunctionalTermAssignment.gene_id))).filter(assignment_filters).scalar() or 0
                    rows = (
                        db.query(
                            FunctionalGene,
                            func.count(FunctionalTermAssignment.id).label("assignment_hits"),
                        )
                        .join(
                            FunctionalTermAssignment,
                            and_(
                                FunctionalTermAssignment.dataset_id == FunctionalGene.dataset_id,
                                FunctionalTermAssignment.version_id == FunctionalGene.version_id,
                                FunctionalTermAssignment.asset_id == FunctionalGene.asset_id,
                                FunctionalTermAssignment.gene_id == FunctionalGene.gene_id,
                            ),
                        )
                        .filter(
                            FunctionalGene.dataset_id == scope["dataset_id"],
                            FunctionalGene.version_id == scope["version_id"],
                            FunctionalGene.asset_id == scope["asset_id"],
                            func.lower(FunctionalTermAssignment.term_source) == term_source,
                            FunctionalTermAssignment.term_id == term_id,
                        )
                        .group_by(FunctionalGene.id)
                        .order_by(FunctionalGene.gene_id.asc())
                        .offset((page - 1) * size)
                        .limit(size)
                        .all()
                    )

                    return {
                        "adapter": self.adapter_name,
                        "operation": operation,
                        "dataset_id": dataset_payload["id"],
                        "data": {
                            "source": "postgresql_index",
                            "scope": scope,
                            "term_source": term_source,
                            "term_id": term_id,
                            "page": page,
                            "size": size,
                            "total": total,
                            "items": [
                                {
                                    "gene": self._serialize_gene_index_row(gene_row),
                                    "assignment_hits": assignment_hits,
                                }
                                for gene_row, assignment_hits in rows
                            ],
                        },
                    }

                term_source = str(params.get("term_source") or "").strip().lower()
                limit = min(max(int(params.get("limit") or 20), 1), 200)
                by_source_query = db.query(
                    FunctionalTerm.term_source,
                    func.count(FunctionalTerm.id).label("term_count"),
                    func.sum(FunctionalTerm.gene_count).label("gene_hits"),
                    func.sum(FunctionalTerm.assignment_count).label("assignment_hits"),
                ).filter_by(**scope)
                by_source_rows = (
                    by_source_query.group_by(FunctionalTerm.term_source)
                    .order_by(FunctionalTerm.term_source.asc())
                    .all()
                )

                top_query = db.query(FunctionalTerm).filter_by(**scope)
                if term_source:
                    top_query = top_query.filter(func.lower(FunctionalTerm.term_source) == term_source)
                top_terms = (
                    top_query.order_by(
                        desc(FunctionalTerm.gene_count),
                        desc(FunctionalTerm.assignment_count),
                        FunctionalTerm.term_id.asc(),
                    )
                    .limit(limit)
                    .all()
                )
                return {
                    "adapter": self.adapter_name,
                    "operation": operation,
                    "dataset_id": dataset_payload["id"],
                    "data": {
                        "source": "postgresql_index",
                        "scope": scope,
                        "term_source": term_source or None,
                        "limit": limit,
                        "by_source": [
                            {
                                "term_source": row.term_source,
                                "term_count": row.term_count,
                                "gene_hits": row.gene_hits or 0,
                                "assignment_hits": row.assignment_hits or 0,
                            }
                            for row in by_source_rows
                        ],
                        "top_terms": [self._serialize_term_row(row) for row in top_terms],
                    },
                }
            finally:
                if should_close:
                    db.close()

        raise HTTPException(status_code=400, detail=f"Unsupported operation for functional annotation adapter: {operation}")
