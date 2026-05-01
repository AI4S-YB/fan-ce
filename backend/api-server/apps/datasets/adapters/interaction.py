import gzip
import os
import subprocess
from typing import Any, Dict, List

from fastapi import HTTPException

from apps.datasets.interaction_matrix import (
    inspect_interaction_matrix,
    list_interaction_resolutions,
    query_interaction_matrix_slice,
)

from .base import DatasetQueryAdapter


class InteractionAdapter(DatasetQueryAdapter):
    adapter_name = "interaction"
    display_name = "Interaction Matrix Adapter"
    supported_dataset_types = ["interaction"]
    supported_file_formats = ["bedpe", "bedpe.gz", "pairs", "pairs.gz", "cool", "mcool"]

    def _get_file_format(self, dataset_payload: Dict[str, Any]) -> str:
        return str(dataset_payload.get("query_profile", {}).get("file_format") or "").lower()

    def _iter_rows(self, file_path: str):
        opener = gzip.open if file_path.endswith(".gz") else open
        with opener(file_path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if not line or line.startswith("#") or not line.strip():
                    continue
                fields = line.rstrip("\n").split("\t")
                if len(fields) < 6:
                    continue
                yield fields

    def _build_item(self, fields: List[str]) -> Dict[str, Any]:
        item: Dict[str, Any] = {
            "chrom1": fields[0],
            "start1": int(fields[1]),
            "end1": int(fields[2]),
            "chrom2": fields[3],
            "start2": int(fields[4]),
            "end2": int(fields[5]),
        }
        if len(fields) > 6:
            item["name"] = fields[6]
        if len(fields) > 7:
            item["score"] = fields[7]
        if len(fields) > 8:
            item["strand1"] = fields[8]
        if len(fields) > 9:
            item["strand2"] = fields[9]
        if len(fields) > 10:
            item["extra_fields"] = fields[10:]
        return item

    def _query_region_contacts(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        seq_id = params.get("seq_id") or params.get("chrom")
        start = params.get("start")
        end = params.get("end")
        target_chrom = params.get("target_chrom")
        target_start = params.get("target_start")
        target_end = params.get("target_end")
        limit = int(params.get("limit") or 100)
        if not seq_id or start is None or end is None:
            raise HTTPException(status_code=400, detail="seq_id/chrom, start and end are required")

        items = []
        region = f"{seq_id}:{start}-{end}"
        if os.path.exists(f"{file_path}.tbi") or os.path.exists(f"{file_path}.csi"):
            self.require_binary("tabix")
            result = subprocess.run(["tabix", file_path, region], capture_output=True, text=True, check=True)
            field_rows = [line.split("\t") for line in result.stdout.splitlines() if line and not line.startswith("#")]
        else:
            field_rows = list(self._iter_rows(file_path))

        for fields in field_rows:
            try:
                chrom1 = fields[0]
                start1 = int(fields[1])
                end1 = int(fields[2])
                chrom2 = fields[3]
                start2 = int(fields[4])
                end2 = int(fields[5])
            except (IndexError, ValueError):
                continue
            if chrom1 != seq_id:
                continue
            if start1 > end or end1 < start:
                continue
            if target_chrom and chrom2 != target_chrom:
                continue
            if target_start is not None and end2 < int(target_start):
                continue
            if target_end is not None and start2 > int(target_end):
                continue
            items.append(self._build_item(fields))
            if len(items) >= limit:
                break

        return {
            "source": "bedpe",
            "anchor_region": region,
            "target_region": (
                f"{target_chrom}:{target_start}-{target_end}"
                if target_chrom and target_start is not None and target_end is not None
                else None
            ),
            "items": items,
            "count": len(items),
        }

    def describe(self, dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
        file_format = self._get_file_format(dataset_payload)
        operations: List[str]
        examples: Dict[str, Dict[str, Any]]
        if file_format in {"cool", "mcool"}:
            operations = ["matrix_meta", "matrix_slice"]
            examples = {
                "matrix_meta": {"operation": "matrix_meta", "params": {}},
                "matrix_slice": {
                    "operation": "matrix_slice",
                    "params": {"chrom": "chr1", "start": 0, "end": 100000, "limit_bins": 25},
                },
            }
            if file_format == "mcool":
                operations.append("resolutions_list")
                examples["resolutions_list"] = {"operation": "resolutions_list", "params": {}}
                examples["matrix_slice"]["params"]["resolution"] = 10000
        else:
            operations = ["region_contacts"]
            examples = {
                "region_contacts": {
                    "operation": "region_contacts",
                    "params": {"seq_id": "chr1", "start": 1, "end": 100000, "target_chrom": "chr1", "limit": 50},
                }
            }
        return {
            "adapter": self.adapter_name,
            "display_name": self.display_name,
            "dataset_type": dataset_payload.get("dataset_type"),
            "file_format": dataset_payload.get("query_profile", {}).get("file_format"),
            "supported_operations": operations,
            "query_entrypoints": ["/api/v1/dataset/query/execute"],
            "examples": examples,
        }

    def execute(self, dataset_payload: Dict[str, Any], operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self.require_file_path(dataset_payload)
        file_format = self._get_file_format(dataset_payload)

        if operation == "region_contacts":
            if file_format in {"cool", "mcool"}:
                raise HTTPException(status_code=400, detail="region_contacts is supported for BEDPE/pairs interaction assets only")
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": self._query_region_contacts(file_path, params),
            }

        if operation == "matrix_meta":
            if file_format not in {"cool", "mcool"}:
                raise HTTPException(status_code=400, detail="matrix_meta is supported for cool/mcool interaction assets only")
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": inspect_interaction_matrix(file_path, requested_resolution=params.get("resolution")),
            }

        if operation == "resolutions_list":
            if file_format != "mcool":
                raise HTTPException(status_code=400, detail="resolutions_list is supported for mcool interaction assets only")
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": list_interaction_resolutions(file_path),
            }

        if operation == "matrix_slice":
            if file_format not in {"cool", "mcool"}:
                raise HTTPException(status_code=400, detail="matrix_slice is supported for cool/mcool interaction assets only")
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": query_interaction_matrix_slice(file_path, params),
            }
        raise HTTPException(status_code=400, detail=f"Unsupported operation for interaction adapter: {operation}")
