import gzip
import os
import subprocess
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from omics.core.sqlite_utils import query_sqlite

from .base import DatasetQueryAdapter


class AnnotationAdapter(DatasetQueryAdapter):
    adapter_name = "annotation"
    display_name = "Annotation Adapter"
    supported_dataset_types = ["annotation", "genome", "sequence"]
    supported_file_formats = ["db", "gff", "gff.gz", "gff3", "gff3.gz", "gtf", "gtf.gz", "sqlite"]

    def supports(self, dataset_payload: Dict[str, Any]) -> bool:
        asset = self.get_query_entry_asset(dataset_payload) or {}
        asset_type = str(asset.get("asset_type") or "").lower()
        query_engine = str(asset.get("query_engine") or dataset_payload.get("query_profile", {}).get("query_engine") or "").lower()
        file_format = str(dataset_payload.get("query_profile", {}).get("file_format") or "").lower()
        dataset_type = str(dataset_payload.get("dataset_type") or "").lower()

        if asset_type or query_engine:
            return (
                asset_type == "gene_annotation"
                or query_engine in {"annotation", "tabix/gff", "tabix/gtf"}
                or file_format in self.supported_file_formats
            )

        return dataset_type in self.supported_dataset_types or file_format in self.supported_file_formats

    def _is_sqlite_file(self, file_path: str) -> bool:
        return file_path.endswith(".sqlite") or file_path.endswith(".db")

    def _list_sqlite_tables(self, file_path: str) -> List[str]:
        rows = query_sqlite(file_path, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [str(item["name"]) for item in rows if item.get("name")]

    def _resolve_sqlite_table(self, tables: List[str], feature_type: Optional[str]) -> str:
        normalized = (feature_type or "gene").lower()
        if normalized in {"gene", "genes"} and "hse_genes" in tables:
            return "hse_genes"
        if normalized in {"transcript", "transcripts", "mrna"} and "hse_transcripts" in tables:
            return "hse_transcripts"
        if normalized in {"exon", "exons", "cds", "utr"} and "hse_exons" in tables:
            return "hse_exons"
        if "hse_genes" in tables:
            return "hse_genes"
        raise HTTPException(status_code=400, detail="annotation sqlite schema is not supported yet")

    def _get_sqlite_column_names(self, file_path: str, table_name: str) -> List[str]:
        rows = query_sqlite(file_path, f"PRAGMA table_info({table_name})")
        return [str(item["name"]) for item in rows if item.get("name")]

    def _query_sqlite_region(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        seq_id = params.get("seq_id") or params.get("chrom")
        start = params.get("start")
        end = params.get("end")
        feature_type = params.get("feature_type")
        limit = int(params.get("limit") or 100)
        if not seq_id or start is None or end is None:
            raise HTTPException(status_code=400, detail="seq_id/chrom, start and end are required")

        tables = self._list_sqlite_tables(file_path)
        table_name = self._resolve_sqlite_table(tables, feature_type)
        columns = self._get_sqlite_column_names(file_path, table_name)
        select_columns = [item for item in ["gene_id", "transcript_id", "chrom", "start", "stop", "strand", "description", "feature_type"] if item in columns]
        if not select_columns:
            select_columns = ["*"]
        rows = query_sqlite(
            file_path,
            f"""
            SELECT {", ".join(select_columns)}
            FROM {table_name}
            WHERE chrom = ?
              AND start <= ?
              AND stop >= ?
            ORDER BY start ASC
            LIMIT ?
            """,
            (seq_id, end, start, limit),
        )
        return {
            "source": "sqlite",
            "table": table_name,
            "items": rows,
            "count": len(rows),
        }

    def _query_sqlite_gene(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        gene_id = params.get("gene_id")
        if not gene_id:
            raise HTTPException(status_code=400, detail="gene_id is required")
        tables = self._list_sqlite_tables(file_path)
        if "hse_genes" not in tables:
            raise HTTPException(status_code=400, detail="annotation sqlite does not contain hse_genes")
        gene_rows = query_sqlite(
            file_path,
            """
            SELECT gene_id, chrom, start, stop, strand, description, canonical_transcript, family
            FROM hse_genes
            WHERE gene_id = ?
            LIMIT 1
            """,
            (gene_id,),
        )
        if not gene_rows:
            raise HTTPException(status_code=404, detail=f"gene not found: {gene_id}")

        transcript_rows = []
        if "hse_transcripts" in tables:
            transcript_rows = query_sqlite(
                file_path,
                """
                SELECT transcript_id, gene_id, chrom, start, stop, strand, description
                FROM hse_transcripts
                WHERE gene_id = ?
                ORDER BY start ASC
                LIMIT 200
                """,
                (gene_id,),
            )
        return {
            "source": "sqlite",
            "gene": gene_rows[0],
            "transcripts": transcript_rows,
            "transcript_count": len(transcript_rows),
        }

    def _parse_attributes(self, raw_attributes: str) -> Dict[str, str]:
        raw_attributes = raw_attributes or ""
        attributes: Dict[str, str] = {}
        for chunk in raw_attributes.split(";"):
            item = chunk.strip()
            if not item:
                continue
            if "=" in item:
                key, value = item.split("=", 1)
            elif " " in item:
                key, value = item.split(" ", 1)
                value = value.strip().strip('"')
            else:
                continue
            attributes[key.strip()] = value.strip()
        return attributes

    def _iter_annotation_lines(self, file_path: str):
        opener = gzip.open if file_path.endswith(".gz") else open
        with opener(file_path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if not line or line.startswith("#"):
                    continue
                fields = line.rstrip("\n").split("\t")
                if len(fields) < 9:
                    continue
                yield fields

    def _build_feature_payload(self, fields: List[str], attributes: Dict[str, str]) -> Dict[str, Any]:
        feature_type = fields[2].lower()
        feature_id = attributes.get("ID")
        if not feature_id and feature_type in {"mrna", "transcript"}:
            feature_id = attributes.get("transcript_id")
        if not feature_id:
            feature_id = attributes.get("gene_id")
        feature_name = attributes.get("Name")
        if not feature_name and feature_type in {"mrna", "transcript"}:
            feature_name = attributes.get("transcript_name")
        if not feature_name:
            feature_name = attributes.get("gene_name")
        return {
            "seq_id": fields[0],
            "source": fields[1],
            "feature_type": fields[2],
            "start": int(fields[3]),
            "end": int(fields[4]),
            "score": fields[5],
            "strand": fields[6],
            "phase": fields[7],
            "attributes": attributes,
            "id": feature_id,
            "name": feature_name,
        }

    def _query_gff_gene(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        gene_id = params.get("gene_id")
        if not gene_id:
            raise HTTPException(status_code=400, detail="gene_id is required")

        gene_item: Optional[Dict[str, Any]] = None
        gene_primary_id: Optional[str] = None
        transcripts: List[Dict[str, Any]] = []
        transcript_limit = int(params.get("limit") or 200)

        for fields in self._iter_annotation_lines(file_path):
            attributes = self._parse_attributes(fields[8])
            feature_type = fields[2].lower()
            candidate_ids = {
                attributes.get("gene_id"),
                attributes.get("ID"),
                attributes.get("Name"),
                attributes.get("gene_name"),
            }
            candidate_ids = {item for item in candidate_ids if item}

            if gene_item is None and gene_id in candidate_ids and feature_type in {"gene", "pseudogene"}:
                gene_item = self._build_feature_payload(fields, attributes)
                gene_primary_id = gene_item["id"] or attributes.get("gene_id") or gene_id
                continue

            if len(transcripts) >= transcript_limit:
                continue

            if feature_type not in {"mrna", "transcript"}:
                continue

            parent_id = attributes.get("Parent")
            transcript_gene_id = attributes.get("gene_id") or attributes.get("gene_name")
            if gene_id == transcript_gene_id or (gene_primary_id and parent_id == gene_primary_id):
                transcripts.append(self._build_feature_payload(fields, attributes))

        if gene_item is None:
            raise HTTPException(status_code=404, detail=f"gene not found: {gene_id}")

        return {
            "source": "gff",
            "gene": gene_item,
            "transcripts": transcripts,
            "transcript_count": len(transcripts),
        }

    def _query_tabix_region(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        seq_id = params.get("seq_id") or params.get("chrom")
        start = params.get("start")
        end = params.get("end")
        feature_type = params.get("feature_type")
        limit = int(params.get("limit") or 100)
        if not seq_id or start is None or end is None:
            raise HTTPException(status_code=400, detail="seq_id/chrom, start and end are required")

        items = []
        region = f"{seq_id}:{start}-{end}"
        if os.path.exists(f"{file_path}.tbi") or os.path.exists(f"{file_path}.csi"):
            self.require_binary("tabix")
            result = subprocess.run(["tabix", file_path, region], capture_output=True, text=True, check=True)
            lines = result.stdout.splitlines()
            field_rows = [line.split("\t") for line in lines if line and not line.startswith("#")]
        else:
            field_rows = list(self._iter_annotation_lines(file_path))

        for fields in field_rows:
            try:
                item_seq_id = fields[0]
                item_feature_type = fields[2]
                item_start = int(fields[3])
                item_end = int(fields[4])
            except (IndexError, ValueError):
                continue
            if item_seq_id != seq_id:
                continue
            if item_start > end or item_end < start:
                continue
            if feature_type and item_feature_type != feature_type:
                continue
            attributes = self._parse_attributes(fields[8])
            items.append(self._build_feature_payload(fields, attributes))
            if len(items) >= limit:
                break
        return {
            "source": "gff",
            "region": region,
            "items": items,
            "count": len(items),
        }

    def _resolve_example_gene(self, file_path: str) -> tuple:
        """Extract a real gene_id and chromosome from the annotation file."""
        if self._is_sqlite_file(file_path):
            rows = query_sqlite(file_path, "SELECT gene_id, chrom FROM hse_genes LIMIT 1")
            if rows:
                row = rows[0]
                return str(row.get("gene_id") or ""), str(row.get("chrom") or "")

        for fields in self._iter_annotation_lines(file_path):
            feature_type = fields[2].lower()
            if feature_type == "gene":
                attributes = self._parse_attributes(fields[8])
                gene_id = attributes.get("ID", "")
                chrom = fields[0] or ""
                if gene_id:
                    return gene_id, chrom

        return "", ""

    def describe(self, dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self.require_file_path(dataset_payload)
        operations = ["gene_lookup", "region_features"]
        if self._is_sqlite_file(file_path):
            operations = ["table_stats", "gene_lookup", "region_features"]

        example_gene_id, example_chrom = self._resolve_example_gene(file_path)
        if not example_gene_id:
            example_gene_id = "unknown"
        if not example_chrom:
            example_chrom = "chr1"

        return {
            "adapter": self.adapter_name,
            "display_name": self.display_name,
            "dataset_type": dataset_payload.get("dataset_type"),
            "file_format": dataset_payload.get("query_profile", {}).get("file_format"),
            "supported_operations": operations,
            "query_entrypoints": ["/api/v1/dataset/query/execute"],
            "examples": {
                "region_features": {
                    "operation": "region_features",
                    "params": {"seq_id": example_chrom, "start": 1, "end": 10000, "feature_type": "gene"},
                },
                "gene_lookup": {
                    "operation": "gene_lookup",
                    "params": {"gene_id": example_gene_id},
                },
            },
        }

    def execute(self, dataset_payload: Dict[str, Any], operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self.require_file_path(dataset_payload)

        if operation == "table_stats":
            if not self._is_sqlite_file(file_path):
                raise HTTPException(status_code=400, detail="table_stats is only supported for sqlite-backed annotations")
            tables = self._list_sqlite_tables(file_path)
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {"tables": tables, "count": len(tables)},
            }

        if operation == "gene_lookup":
            if self._is_sqlite_file(file_path):
                data = self._query_sqlite_gene(file_path, params)
            else:
                data = self._query_gff_gene(file_path, params)
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": data,
            }

        if operation == "region_features":
            if self._is_sqlite_file(file_path):
                data = self._query_sqlite_region(file_path, params)
            else:
                data = self._query_tabix_region(file_path, params)
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": data,
            }

        raise HTTPException(status_code=400, detail=f"Unsupported operation for annotation adapter: {operation}")
