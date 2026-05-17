from typing import Any, Dict

from fastapi import HTTPException

from basis.core.expression_utils import extract_expression_matrix, load_gene_sample_names

from .base import DatasetQueryAdapter


class ExpressionAdapter(DatasetQueryAdapter):
    adapter_name = "expression"
    display_name = "HDF5 Expression Adapter"
    supported_dataset_types = ["expression", "rnaseq", "transcriptome"]
    supported_file_formats = ["h5", "hdf5", "tsv", "csv", "txt", "mtx", "mtx.gz"]

    def supports(self, dataset_payload: Dict[str, Any]) -> bool:
        asset = self.get_query_entry_asset(dataset_payload) or {}
        asset_type = str(asset.get("asset_type") or "").lower()
        query_engine = str(asset.get("query_engine") or dataset_payload.get("query_profile", {}).get("query_engine") or "").lower()
        file_format = str(dataset_payload.get("query_profile", {}).get("file_format") or "").lower()
        dataset_type = str(dataset_payload.get("dataset_type") or "").lower()

        if asset_type or query_engine:
            return (
                asset_type == "expression_matrix"
                or query_engine in {"expression", "hdf5"}
                or file_format in self.supported_file_formats
            )

        return dataset_type in self.supported_dataset_types or file_format in self.supported_file_formats

    def describe(self, dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self.require_file_path(dataset_payload)
        example_genes: list = []
        example_samples: list = []

        fmt = str(dataset_payload.get("query_profile", {}).get("file_format") or "").lower()
        if fmt in ("tsv", "csv", "txt"):
            try:
                import pandas as pd
                sep = "\t" if file_path.endswith((".tsv", ".txt")) else ","
                df = pd.read_csv(file_path, sep=sep, index_col=0, nrows=100)
                example_genes = df.index.tolist()[:5]
                example_samples = df.columns.tolist()[:5]
            except Exception:
                pass
        else:
            try:
                example_genes, example_samples = load_gene_sample_names(file_path, max_records=5)
            except Exception:
                pass

        return {
            "adapter": self.adapter_name,
            "display_name": self.display_name,
            "dataset_type": dataset_payload.get("dataset_type"),
            "file_format": dataset_payload.get("query_profile", {}).get("file_format"),
            "supported_operations": ["genes_list", "samples_list", "matrix_slice"],
            "query_entrypoints": ["/api/v1/dataset/query/execute"],
            "examples": {
                "genes_list": {"operation": "genes_list", "params": {"max_records": 20}},
                "samples_list": {"operation": "samples_list", "params": {"max_records": 20}},
                "matrix_slice": {
                    "operation": "matrix_slice",
                    "params": {
                        "data_type": "count",
                        "genes": example_genes,
                        "samples": example_samples,
                    },
                },
            },
        }

    def execute(self, dataset_payload: Dict[str, Any], operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self.require_file_path(dataset_payload)
        fmt = str(dataset_payload.get("query_profile", {}).get("file_format") or "").lower()

        if fmt in ("tsv", "csv", "txt"):
            return self._execute_tsv(file_path, operation, params)

        if operation == "genes_list":
            max_records = int(params.get("max_records") or 100)
            genes, _ = load_gene_sample_names(file_path, max_records=max_records)
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {"genes": genes, "count": len(genes)},
            }

        if operation == "samples_list":
            max_records = int(params.get("max_records") or 100)
            _, samples = load_gene_sample_names(file_path, max_records=max_records)
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {"samples": samples, "count": len(samples)},
            }

        if operation == "matrix_slice":
            data_type = params.get("data_type") or "count"
            genes = params.get("genes")
            samples = params.get("samples")
            matrix, sub_genes, sub_samples, download_path = extract_expression_matrix(
                file_path=file_path,
                data_type=data_type,
                genes=genes,
                samples=samples,
            )
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "dataset_id": dataset_payload["id"],
                "data": {
                    "data_type": data_type,
                    "genes": sub_genes,
                    "samples": sub_samples,
                    "matrix": matrix,
                    "download_path": download_path,
                },
            }

        raise HTTPException(status_code=400, detail=f"Unsupported operation for expression adapter: {operation}")

    def _execute_tsv(self, file_path, operation, params):
        import pandas as pd

        sep = "\t" if file_path.endswith((".tsv", ".txt")) else ","
        df = pd.read_csv(file_path, sep=sep, index_col=0, nrows=1000)

        if operation == "genes_list":
            genes = df.index.tolist()
            max_records = int(params.get("max_records") or 100)
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "data": {"genes": genes[:max_records], "count": len(genes)},
            }

        if operation == "samples_list":
            samples = df.columns.tolist()
            max_records = int(params.get("max_records") or 100)
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "data": {"samples": samples[:max_records], "count": len(samples)},
            }

        if operation == "matrix_slice":
            genes = params.get("genes")
            samples = params.get("samples")
            sub = df
            if genes:
                sub = sub.loc[sub.index.isin(genes)]
            if samples:
                sub = sub[[s for s in samples if s in sub.columns]]
            return {
                "adapter": self.adapter_name,
                "operation": operation,
                "data": {
                    "genes": sub.index.tolist(),
                    "samples": sub.columns.tolist(),
                    "matrix": sub.values.tolist(),
                },
            }

        raise HTTPException(status_code=400, detail=f"Unsupported operation: {operation}")
