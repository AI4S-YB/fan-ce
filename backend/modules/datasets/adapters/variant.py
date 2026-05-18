import os
import re
import shutil
import subprocess
import uuid
from typing import Any, Dict, List

from fastapi import HTTPException

from omics.core.variant_utils import check_vcf_file, extract_variants

from .base import DatasetQueryAdapter


from config.settings import settings; DOWNLOAD_DIR = settings.DOWNLOAD_DIR
DOWNLOAD_BASE_URL = "http://yourdomain.com/downloads"


class VariantAdapter(DatasetQueryAdapter):
    adapter_name = "variant"
    display_name = "VCF Variant Adapter"
    supported_dataset_types = ["variant", "vcf", "variome"]
    supported_file_formats = ["vcf", "vcf.gz", "bcf"]

    def _get_first_variant(self, file_path: str) -> tuple:
        """Return (chrom, pos) of the first variant, or (None, None)."""
        try:
            cmd = ["bash", "-c", f"bcftools view -H '{file_path}' | head -1"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return None, None
            first_variant = result.stdout.split("\n")[0]
            if not first_variant:
                return None, None
            fields = first_variant.split("\t")
            return fields[0], int(fields[1])
        except Exception:
            return None, None

    def _build_example_regions(self, chrom: str, pos: int) -> List[str]:
        return [
            f"{chrom}:{max(1, pos - 500)}-{pos + 499}",
            f"{chrom}:{pos + 500}-{pos + 999}",
        ]

    def _try_get_example_regions(self, file_path: str) -> List[str]:
        chrom, pos = self._get_first_variant(file_path)
        if chrom is None:
            return []
        return self._build_example_regions(chrom, pos)

    def supports(self, dataset_payload: Dict[str, Any]) -> bool:
        asset = self.get_query_entry_asset(dataset_payload) or {}
        asset_type = str(asset.get("asset_type") or "").lower()
        file_format = str(dataset_payload.get("query_profile", {}).get("file_format") or "").lower()
        dataset_type = str(dataset_payload.get("dataset_type") or "").lower()

        if asset_type:
            return (
                asset_type in {"variant_vcf", "variant_calls"}
                or True in {"variant", "bcftools", "tabix/bcftools", "tabix/vcf"}
                or file_format in self.supported_file_formats
            )

        return dataset_type in self.supported_dataset_types or file_format in self.supported_file_formats

    def describe(self, dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
        primary_file = self.get_primary_file(dataset_payload)
        file_path = self._resolve_file_payload_path(primary_file) if primary_file else ""
        query_regions = self._try_get_example_regions(file_path) or ["Chr1:1000-2000"]
        return {
            "adapter": self.adapter_name,
            "display_name": self.display_name,
            "dataset_type": dataset_payload.get("dataset_type"),
            "file_format": dataset_payload.get("query_profile", {}).get("file_format"),
            "supported_operations": ["region_example", "samples_list", "query", "query_by_id"],
            "query_entrypoints": ["/api/v1/dataset/query/execute"],
            "examples": {
                "region_example": {"operation": "region_example", "params": {}},
                "samples_list": {"operation": "samples_list", "params": {}},
                "query": {"operation": "query", "params": {"regions": query_regions}},
                "query_by_id": {"operation": "query_by_id", "params": {"variant_ids": ["example_variant_id"]}},
            },
        }

    def execute(self, dataset_payload: Dict[str, Any], operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self.require_file_path(dataset_payload)
        self.ensure_sidecar_index_files(dataset_payload, [".tbi", ".csi"])
        self.require_binary("bcftools")
        if not check_vcf_file(file_path):
            raise HTTPException(status_code=400, detail="dataset file is not a valid indexed variant file")

        if operation == "region_example":
            chrom, pos = self._get_first_variant(file_path)
            if chrom is None:
                raise HTTPException(status_code=400, detail="No variants found in file")
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {
                    "ref_id": chrom,
                    "variant_position": pos,
                    "example_regions": self._build_example_regions(chrom, pos),
                },
            }

        if operation == "samples_list":
            cmd = ["bcftools", "query", "-l", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise HTTPException(status_code=500, detail=f"Failed to list samples: {result.stderr}")
            samples = [sample for sample in result.stdout.strip().split("\n") if sample]
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {"samples": samples, "count": len(samples)},
            }

        if operation == "query":
            regions: List[str] = params.get("regions") or []
            include_samples = params.get("include_samples")
            exclude_samples = params.get("exclude_samples")
            if not regions:
                raise HTTPException(status_code=400, detail="regions is required")
            for region in regions:
                if not re.match(r"^([a-zA-Z0-9_]+)(?::(\d+)(?:-(\d+))?)?$", region):
                    raise HTTPException(status_code=400, detail=f"Invalid region format: {region}")
            result = extract_variants(
                vcf_path=file_path,
                regions=regions,
                include_samples=include_samples,
                exclude_samples=exclude_samples,
            )
            file_id = f"{uuid.uuid4()}.vcf.gz"
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            final_path = f"{DOWNLOAD_DIR}/{file_id}"
            shutil.copyfile(result["vcf_path"], final_path)
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {
                    "count": result["preview"].count("\n") if result["preview"] else 0,
                    "size": result["size"],
                    "preview": result["preview"] if result["size"] <= 1024 * 1024 else None,
                    "download_url": f"{DOWNLOAD_BASE_URL}/{file_id}",
                },
            }

        if operation == "query_by_id":
            variant_ids: List[str] = params.get("variant_ids") or []
            if not variant_ids:
                raise HTTPException(status_code=400, detail="variant_ids is required")
            id_filter = " || ".join(f'ID="{vid}"' for vid in variant_ids)
            cmd = ["bcftools", "view", "-i", id_filter, file_path]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if proc.returncode != 0:
                raise HTTPException(status_code=500, detail=f"bcftools query_by_id failed: {proc.stderr}")
            output = proc.stdout
            count = sum(1 for line in output.split("\n") if line and not line.startswith("#"))
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {
                    "count": count,
                    "size": len(output.encode()),
                    "preview": output if len(output.encode()) <= 1024 * 1024 else None,
                    "sample_count": len(output.strip().split("\t")) - 9 if "\t" in output else 0,
                },
            }

        raise HTTPException(status_code=400, detail=f"Unsupported operation for variant adapter: {operation}")
