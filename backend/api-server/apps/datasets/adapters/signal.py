import gzip
import os
import subprocess
from typing import Any, Dict, List

from fastapi import HTTPException

from .base import DatasetQueryAdapter

try:
    import pyBigWig
except ImportError:  # pragma: no cover - exercised via runtime environment or monkeypatch in tests
    pyBigWig = None


class SignalAdapter(DatasetQueryAdapter):
    adapter_name = "signal"
    display_name = "Signal Track Adapter"
    supported_dataset_types = ["signal"]
    supported_file_formats = ["bed", "bed.gz", "bw", "bigwig"]

    def _iter_bed_rows(self, file_path: str):
        opener = gzip.open if file_path.endswith(".gz") else open
        with opener(file_path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if not line or line.startswith("#") or not line.strip():
                    continue
                fields = line.rstrip("\n").split("\t")
                if len(fields) < 3:
                    continue
                yield fields

    def _build_bed_item(self, fields: List[str]) -> Dict[str, Any]:
        item: Dict[str, Any] = {
            "chrom": fields[0],
            "start": int(fields[1]),
            "end": int(fields[2]),
        }
        if len(fields) > 3:
            item["name"] = fields[3]
        if len(fields) > 4:
            item["score"] = fields[4]
        if len(fields) > 5:
            item["strand"] = fields[5]
        if len(fields) > 6:
            item["extra_fields"] = fields[6:]
        return item

    def _query_bed_region(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        seq_id = params.get("seq_id") or params.get("chrom")
        start = params.get("start")
        end = params.get("end")
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
            field_rows = list(self._iter_bed_rows(file_path))

        for fields in field_rows:
            try:
                item_chrom = fields[0]
                item_start = int(fields[1])
                item_end = int(fields[2])
            except (IndexError, ValueError):
                continue
            if item_chrom != seq_id:
                continue
            if item_start > end or item_end < start:
                continue
            items.append(self._build_bed_item(fields))
            if len(items) >= limit:
                break

        return {
            "source": "bed",
            "region": region,
            "items": items,
            "count": len(items),
        }

    def _open_bigwig(self, file_path: str):
        if pyBigWig is None:
            raise HTTPException(status_code=503, detail="pyBigWig is required for BigWig querying")
        return pyBigWig.open(file_path)

    def _describe_bigwig(self, file_path: str) -> Dict[str, Any]:
        with self._open_bigwig(file_path) as handle:
            chroms = handle.chroms() or {}
            header = handle.header() or {}
        chromosomes = [{"chrom": chrom, "length": int(length)} for chrom, length in chroms.items()]
        return {
            "source": "bigwig",
            "file_path": file_path,
            "chromosome_count": len(chromosomes),
            "chromosomes": chromosomes,
            "header": header,
        }

    def _query_bigwig_region(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        seq_id = params.get("seq_id") or params.get("chrom")
        start = params.get("start")
        end = params.get("end")
        bins = int(params.get("bins") or 50)
        summary_type = str(params.get("summary_type") or params.get("stat") or "mean").lower()
        if not seq_id or start is None or end is None:
            raise HTTPException(status_code=400, detail="seq_id/chrom, start and end are required")
        if bins <= 0:
            raise HTTPException(status_code=400, detail="bins must be a positive integer")
        if summary_type not in {"coverage", "max", "mean", "min", "std"}:
            raise HTTPException(status_code=400, detail=f"unsupported BigWig summary_type: {summary_type}")

        region_start = int(start)
        region_end = int(end)
        if region_start < 0 or region_end <= region_start:
            raise HTTPException(status_code=400, detail="invalid region: require 0 <= start < end")

        with self._open_bigwig(file_path) as handle:
            chroms = handle.chroms() or {}
            chrom_length = chroms.get(seq_id)
            if chrom_length is None:
                raise HTTPException(status_code=404, detail=f"chromosome not found in BigWig: {seq_id}")
            clipped_end = min(region_end, int(chrom_length))
            if clipped_end <= region_start:
                raise HTTPException(status_code=400, detail="requested region is outside chromosome bounds")

            raw_values = handle.stats(
                seq_id,
                region_start,
                clipped_end,
                nBins=bins,
                type=summary_type,
                exact=True,
            ) or []
            overall_values = handle.stats(
                seq_id,
                region_start,
                clipped_end,
                nBins=1,
                type=summary_type,
                exact=True,
            ) or [None]

        bin_width = max(1, (clipped_end - region_start + bins - 1) // bins)
        items = []
        non_null_values = []
        for index, value in enumerate(raw_values):
            bin_start = region_start + index * bin_width
            if bin_start >= clipped_end:
                break
            bin_end = min(clipped_end, bin_start + bin_width)
            normalized_value = None if value is None else float(value)
            if normalized_value is not None:
                non_null_values.append(normalized_value)
            items.append(
                {
                    "chrom": seq_id,
                    "start": bin_start,
                    "end": bin_end,
                    "value": normalized_value,
                }
            )

        return {
            "source": "bigwig",
            "region": f"{seq_id}:{region_start}-{clipped_end}",
            "summary_type": summary_type,
            "requested_range": {"seq_id": seq_id, "start": region_start, "end": region_end},
            "bins": bins,
            "bin_width": bin_width,
            "items": items,
            "count": len(items),
            "non_null_count": len(non_null_values),
            "summary": {
                "value": None if overall_values[0] is None else float(overall_values[0]),
                "min": min(non_null_values) if non_null_values else None,
                "max": max(non_null_values) if non_null_values else None,
            },
        }

    def describe(self, dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self.require_file_path(dataset_payload)
        operations: List[str] = []
        examples: Dict[str, Dict[str, Any]] = {}
        if file_path.endswith(".bed") or file_path.endswith(".bed.gz"):
            operations = ["region_features"]
            examples["region_features"] = {
                "operation": "region_features",
                "params": {"seq_id": "chr1", "start": 1, "end": 1000, "limit": 50},
            }
        elif file_path.endswith(".bw") or file_path.endswith(".bigwig"):
            operations = ["region_signal", "describe_signal"]
            examples["region_signal"] = {
                "operation": "region_signal",
                "params": {"seq_id": "chr1", "start": 1, "end": 1000, "bins": 20, "summary_type": "mean"},
            }
            examples["describe_signal"] = {
                "operation": "describe_signal",
                "params": {},
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

        if operation == "describe_signal":
            if file_path.endswith(".bw") or file_path.endswith(".bigwig"):
                data = self._describe_bigwig(file_path)
                return {
                    "adapter": self.adapter_name,
                    "operation": operation,
                    "dataset_id": dataset_payload["id"],
                    "data": data,
                }
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {
                    "file_path": file_path,
                    "file_format": dataset_payload.get("query_profile", {}).get("file_format"),
                    "message": "specialized BigWig querying is not enabled yet",
                },
            }

        if operation == "region_signal":
            if not (file_path.endswith(".bw") or file_path.endswith(".bigwig")):
                raise HTTPException(status_code=400, detail="region_signal is currently supported for BigWig tracks only")
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": self._query_bigwig_region(file_path, params),
            }

        if operation == "region_features":
            if not (file_path.endswith(".bed") or file_path.endswith(".bed.gz")):
                raise HTTPException(status_code=400, detail="region_features is currently supported for BED/bed.gz signal tracks only")
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": self._query_bed_region(file_path, params),
            }

        raise HTTPException(status_code=400, detail=f"Unsupported operation for signal adapter: {operation}")
