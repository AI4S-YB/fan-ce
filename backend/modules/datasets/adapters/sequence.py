import os
import uuid
from typing import Any, Dict, List

from fastapi import HTTPException

from omics.core.file_utils import compress_file_to_gzip, generate_download_url
from omics.core.samtools_utils import extract_batch_sequences, extract_sequence

from .base import DatasetQueryAdapter


MAX_INLINE_SIZE = 1_000_000


class SequenceAdapter(DatasetQueryAdapter):
    adapter_name = "sequence"
    display_name = "FASTA Sequence Adapter"
    supported_dataset_types = ["sequence", "fasta", "genome", "genome_sequence"]
    supported_file_formats = ["fa", "fa.gz", "fasta", "fasta.gz", "fna", "fna.gz"]

    def supports(self, dataset_payload: Dict[str, Any]) -> bool:
        asset = self.get_query_entry_asset(dataset_payload) or {}
        asset_type = str(asset.get("asset_type") or "").lower()
        query_engine = str(asset.get("query_engine") or dataset_payload.get("query_profile", {}).get("query_engine") or "").lower()
        file_format = str(dataset_payload.get("query_profile", {}).get("file_format") or "").lower()
        dataset_type = str(dataset_payload.get("dataset_type") or "").lower()

        if asset_type or query_engine:
            return (
                asset_type in {"reference_fasta", "genome_sequence"}
                or query_engine in {"samtools/faidx", "faidx", "samtools"}
                or file_format in self.supported_file_formats
            )

        return dataset_type in self.supported_dataset_types or file_format in self.supported_file_formats

    def _ensure_query_ready(self, dataset_payload: Dict[str, Any], file_path: str):
        self.ensure_sidecar_index_files(dataset_payload, [".fai"])
        if not os.path.exists(f"{file_path}.fai"):
            raise HTTPException(
                status_code=409,
                detail="sequence dataset is not indexed yet; run dataset ingest index before querying",
            )

    def _resolve_example_seq_id(self, file_path: str) -> str:
        fai_path = f"{file_path}.fai"
        if os.path.exists(fai_path):
            with open(fai_path, "r", encoding="utf-8") as handle:
                first_line = handle.readline().strip()
            if first_line:
                return first_line.split("\t", 1)[0]

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line.startswith(">"):
                        return line[1:].split()[0]
        return "chr1"

    def describe(self, dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self.require_file_path(dataset_payload)
        example_seq_id = self._resolve_example_seq_id(file_path)
        return {
            "adapter": self.adapter_name,
            "display_name": self.display_name,
            "dataset_type": dataset_payload.get("dataset_type"),
            "file_format": dataset_payload.get("query_profile", {}).get("file_format"),
            "supported_operations": ["fetch", "batch_fetch"],
            "query_entrypoints": ["/api/v1/dataset/query/execute"],
            "examples": {
                "fetch": {"operation": "fetch", "params": {"seq_id": example_seq_id, "start": 1, "end": 100}},
                "batch_fetch": {
                    "operation": "batch_fetch",
                    "params": {"regions": [{"seq_id": example_seq_id, "start": 1, "end": 100}]},
                },
            },
        }

    def execute(self, dataset_payload: Dict[str, Any], operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self.require_file_path(dataset_payload)
        self._ensure_query_ready(dataset_payload, file_path)

        if operation == "fetch":
            seq_id = params.get("seq_id")
            start = params.get("start")
            end = params.get("end")
            if not seq_id:
                raise HTTPException(status_code=400, detail="seq_id is required")
            sequence_text = extract_sequence(file_path, seq_id, start, end)
            sequence_lines = sequence_text.strip().split("\n")
            sequence_str = "".join(sequence_lines[1:])
            if len(sequence_str) > MAX_INLINE_SIZE:
                temp_fasta = f"{settings.DOWNLOAD_DIR}/{seq_id}_{uuid.uuid4().hex}.fasta"
                with open(temp_fasta, "w", encoding="utf-8") as handle:
                    handle.write(sequence_text)
                gzip_path = compress_file_to_gzip(temp_fasta)
                return {
                    "adapter": self.adapter_name,
                    "operation": operation,
                    "dataset_id": dataset_payload["id"],
                    "data": {
                        "seq_id": seq_id,
                        "sequence": None,
                        "length": len(sequence_str),
                        "download_url": generate_download_url(gzip_path),
                    },
                }
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {
                    "seq_id": seq_id,
                    "start": start,
                    "end": end,
                    "sequence": sequence_str,
                    "length": len(sequence_str),
                },
            }

        if operation == "batch_fetch":
            regions: List[Dict[str, Any]] = params.get("regions") or []
            if not regions:
                raise HTTPException(status_code=400, detail="regions is required")
            region_strings = [
                f"{item['seq_id']}:{item['start']}-{item['end']}" if item.get("start") and item.get("end") else item["seq_id"]
                for item in regions
            ]
            output_path = extract_batch_sequences(file_path, region_strings)
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {
                    "output_path": output_path,
                    "regions": region_strings,
                },
            }

        raise HTTPException(status_code=400, detail=f"Unsupported operation for sequence adapter: {operation}")
