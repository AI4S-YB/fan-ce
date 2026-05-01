from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.datasets.adapters import dataset_adapter_registry


def _build_payload(*, dataset_type, asset_type, query_engine, file_format):
    return {
        "id": 1,
        "dataset_type": dataset_type,
        "query_profile": {
            "file_format": file_format,
            "query_engine": query_engine,
        },
        "query_entry_asset": {
            "id": 11,
            "asset_type": asset_type,
            "query_engine": query_engine,
            "files": [],
        },
        "assets": [],
    }


def test_genome_gene_annotation_asset_resolves_annotation_adapter():
    payload = _build_payload(
        dataset_type="genome",
        asset_type="gene_annotation",
        query_engine="tabix/gff",
        file_format="gff3.gz",
    )

    adapter = dataset_adapter_registry.resolve(payload)

    assert adapter.adapter_name == "annotation"


def test_transcriptome_metadata_asset_does_not_resolve_expression_adapter():
    payload = _build_payload(
        dataset_type="transcriptome",
        asset_type="metadata_table",
        query_engine="file",
        file_format="json",
    )

    adapter = dataset_adapter_registry.resolve(payload)

    assert adapter.adapter_name == "generic"


def test_variant_asset_on_genome_dataset_resolves_variant_adapter():
    payload = _build_payload(
        dataset_type="genome",
        asset_type="variant_vcf",
        query_engine="tabix/bcftools",
        file_format="vcf.gz",
    )

    adapter = dataset_adapter_registry.resolve(payload)

    assert adapter.adapter_name == "variant"
