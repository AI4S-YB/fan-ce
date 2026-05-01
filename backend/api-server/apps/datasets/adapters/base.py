from typing import Any, Dict, List, Optional

from fastapi import HTTPException
import os
import shutil


class DatasetQueryAdapter:
    adapter_name = "generic"
    display_name = "Generic File Adapter"
    supported_dataset_types: List[str] = []
    supported_file_formats: List[str] = []

    def supports(self, dataset_payload: Dict[str, Any]) -> bool:
        dataset_type = (dataset_payload.get("dataset_type") or "").lower()
        file_format = (dataset_payload.get("query_profile", {}).get("file_format") or "").lower()
        return dataset_type in self.supported_dataset_types or file_format in self.supported_file_formats

    def describe(self, dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "adapter": self.adapter_name,
            "display_name": self.display_name,
            "dataset_type": dataset_payload.get("dataset_type"),
            "file_format": dataset_payload.get("query_profile", {}).get("file_format"),
            "supported_operations": [],
            "query_entrypoints": [],
        }

    def execute(self, dataset_payload: Dict[str, Any], operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def get_query_entry_asset(self, dataset_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        query_entry_asset = dataset_payload.get("query_entry_asset")
        if query_entry_asset:
            return query_entry_asset
        assets = dataset_payload.get("assets") or []
        return assets[0] if assets else None

    def get_legacy_dataset_file(self, dataset_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Legacy compatibility only. Main query paths should resolve from query_entry_asset/files.
        return dataset_payload.get("file")

    def get_primary_file(self, dataset_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        query_entry_asset = self.get_query_entry_asset(dataset_payload)
        if query_entry_asset:
            files = query_entry_asset.get("files") or []
            primary_file = next((item for item in files if item.get("file_role") == "primary"), None)
            if primary_file:
                return primary_file
            if files:
                return files[0]
        return self.get_legacy_dataset_file(dataset_payload)

    def get_asset_files(self, dataset_payload: Dict[str, Any], file_role: Optional[str] = None) -> List[Dict[str, Any]]:
        query_entry_asset = self.get_query_entry_asset(dataset_payload)
        if not query_entry_asset:
            return []
        files = query_entry_asset.get("files") or []
        if not file_role:
            return files
        return [item for item in files if item.get("file_role") == file_role]

    def _normalize_file_path(self, raw_path: Optional[str]) -> str:
        if not raw_path:
            return ""
        if raw_path.startswith("file://"):
            return raw_path[len("file://") :]
        return raw_path

    def _resolve_file_payload_path(self, file_payload: Optional[Dict[str, Any]]) -> str:
        file_payload = file_payload or {}
        return self._normalize_file_path(
            file_payload.get("local_path")
            or file_payload.get("path")
            or file_payload.get("storage_uri")
        )

    def require_binary(self, binary_name: str) -> str:
        resolved = shutil.which(binary_name)
        if resolved:
            return resolved
        raise HTTPException(status_code=503, detail=f"required system binary is not available: {binary_name}")

    def require_file_path(self, dataset_payload: Dict[str, Any]) -> str:
        primary_file = self.get_primary_file(dataset_payload)
        file_path = self._resolve_file_payload_path(primary_file)
        if not file_path:
            raise HTTPException(status_code=400, detail="dataset file path is missing")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"dataset file not found on server: {file_path}")
        return file_path

    @staticmethod
    def _is_index_stale(source_path: str, index_path: str) -> bool:
        """Return True if the index file is older than the source file."""
        try:
            source_mtime = os.path.getmtime(source_path)
            index_mtime = os.path.getmtime(index_path)
            return index_mtime < source_mtime
        except OSError:
            return True  # Can't stat = treat as stale

    def ensure_sidecar_index_files(self, dataset_payload: Dict[str, Any], suffixes: List[str]) -> str:
        file_path = self.require_file_path(dataset_payload)
        index_files = self.get_asset_files(dataset_payload, file_role="index")
        if not index_files or not suffixes:
            return file_path

        for suffix in suffixes:
            expected_path = f"{file_path}{suffix}"
            if os.path.exists(expected_path):
                if not self._is_index_stale(file_path, expected_path):
                    continue
                # Index is stale — log and rebuild below
            match = None
            for file_payload in index_files:
                source_path = self._resolve_file_payload_path(file_payload)
                if not source_path:
                    continue
                if file_payload.get("file_name") == os.path.basename(expected_path) or source_path.endswith(suffix):
                    match = source_path
                    break
            if not match or not os.path.exists(match):
                continue
            try:
                os.symlink(match, expected_path)
            except FileExistsError:
                continue
            except OSError:
                shutil.copyfile(match, expected_path)
        return file_path
