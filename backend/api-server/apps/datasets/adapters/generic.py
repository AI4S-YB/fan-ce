from typing import Any, Dict

from fastapi import HTTPException

from .base import DatasetQueryAdapter


class GenericFileAdapter(DatasetQueryAdapter):
    adapter_name = "generic"
    display_name = "Generic File Adapter"

    def supports(self, dataset_payload: Dict[str, Any]) -> bool:
        return True

    def describe(self, dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "adapter": self.adapter_name,
            "display_name": self.display_name,
            "dataset_type": dataset_payload.get("dataset_type"),
            "file_format": dataset_payload.get("query_profile", {}).get("file_format"),
            "supported_operations": ["describe_file"],
            "query_entrypoints": [],
            "notes": [
                "No specialized omics adapter is mapped yet.",
                "This dataset can still be managed through workflow and publish APIs.",
            ],
        }

    def execute(self, dataset_payload: Dict[str, Any], operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation != "describe_file":
            raise HTTPException(status_code=400, detail=f"Unsupported operation for generic adapter: {operation}")
        return {
            "dataset_id": dataset_payload["id"],
            "adapter": self.adapter_name,
            "file": dataset_payload.get("file"),
            "query_profile": dataset_payload.get("query_profile"),
        }
