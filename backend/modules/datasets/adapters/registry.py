from typing import Any, Dict, List

from fastapi import HTTPException

from .annotation import AnnotationAdapter
from .expression import ExpressionAdapter
from .functional_annotation import FunctionalAnnotationAdapter
from .generic import GenericFileAdapter
from .interaction import InteractionAdapter
from .phenome import PhenomeAdapter
from .sequence import SequenceAdapter
from .signal import SignalAdapter
from .variant import VariantAdapter


class DatasetAdapterRegistry:
    def __init__(self):
        self.adapters = [
            FunctionalAnnotationAdapter(),
            SequenceAdapter(),
            PhenomeAdapter(),
            AnnotationAdapter(),
            SignalAdapter(),
            VariantAdapter(),
            ExpressionAdapter(),
            InteractionAdapter(),
            GenericFileAdapter(),
        ]

    def resolve(self, dataset_payload: Dict[str, Any]):
        for adapter in self.adapters:
            if adapter.supports(dataset_payload):
                return adapter
        return GenericFileAdapter()

    def resolve_all(self, dataset_payload: Dict[str, Any]):
        matching = [a for a in self.adapters if not isinstance(a, GenericFileAdapter) and a.supports(dataset_payload)]
        if not matching:
            matching.append(GenericFileAdapter())
        return matching

    def _iter_asset_payloads(self, dataset_payload: Dict[str, Any]):
        """Yield per-asset dataset payloads with query_profile reflecting each asset."""
        assets = dataset_payload.get("assets") or []
        if not assets:
            yield dataset_payload
            return
        for asset in assets:
            primary_file = None
            files = asset.get("files") or []
            for f in files:
                if f.get("file_role") == "primary":
                    primary_file = f
                    break
            if not primary_file and files:
                primary_file = files[0]

            asset_payload = {**dataset_payload, "query_entry_asset": asset}
            asset_payload["query_profile"] = {
                **(dataset_payload.get("query_profile") or {}),
                "file_format": asset.get("file_format") or (primary_file or {}).get("file_format") or "",
                
            }
            yield asset_payload

    def describe(self, dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
        merged_ops: List[str] = []
        merged_examples: Dict[str, Any] = {}
        adapter_names: List[str] = []
        display_names: List[str] = []
        primary: Dict[str, Any] = {}

        for asset_payload in self._iter_asset_payloads(dataset_payload):
            for adapter in self.resolve_all(asset_payload):
                try:
                    desc = adapter.describe(asset_payload)
                except HTTPException as e:
                    # 404 = file missing — let it propagate so list skips this dataset
                    if e.status_code == 404:
                        raise
                    # Other HTTP errors = format mismatch — skip this adapter
                    continue
                except Exception:
                    # Unexpected errors — skip this adapter
                    continue
                if not primary:
                    primary = desc
                for op in desc.get("supported_operations", []):
                    if op not in merged_ops:
                        merged_ops.append(op)
                merged_examples.update(desc.get("examples", {}))
                if adapter.adapter_name not in adapter_names:
                    adapter_names.append(adapter.adapter_name)
                    display_names.append(adapter.display_name)

        if not primary:
            return GenericFileAdapter().describe(dataset_payload)

        return {
            **primary,
            "adapter": "+".join(adapter_names),
            "display_name": " + ".join(display_names),
            "supported_operations": merged_ops,
            "examples": merged_examples,
        }

    def execute(self, dataset_payload: Dict[str, Any], operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        for asset_payload in self._iter_asset_payloads(dataset_payload):
            for adapter in self.resolve_all(asset_payload):
                try:
                    desc = adapter.describe(asset_payload)
                except Exception:
                    continue
                if operation in desc.get("supported_operations", []):
                    return adapter.execute(asset_payload, operation, params)
        raise HTTPException(status_code=400, detail=f"No adapter supports operation: {operation}")

    def list_adapters(self) -> List[Dict[str, Any]]:
        return [
            {
                "adapter": adapter.adapter_name,
                "display_name": adapter.display_name,
                "supported_dataset_types": sorted(adapter.supported_dataset_types),
                "supported_file_formats": sorted(adapter.supported_file_formats),
            }
            for adapter in self.adapters
        ]


dataset_adapter_registry = DatasetAdapterRegistry()
