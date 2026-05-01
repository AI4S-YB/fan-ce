from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.datasets.constants import DEFAULT_ASSET_TYPE_REGISTRY_ITEMS, DEFAULT_DATASET_KIND_REGISTRY_ITEMS
from apps.datasets.services import dataset_domain_service
from basis.core.variant_utils import check_vcf_file


def test_variome_is_registered_as_dataset_kind_and_variant_asset_target():
    dataset_kind_codes = {item["code"] for item in DEFAULT_DATASET_KIND_REGISTRY_ITEMS}
    assert "genome" in dataset_kind_codes
    assert "transcriptome" in dataset_kind_codes
    assert "variome" in dataset_kind_codes
    assert "phenome" in dataset_kind_codes

    reference_asset = next(item for item in DEFAULT_ASSET_TYPE_REGISTRY_ITEMS if item["code"] == "reference_fasta")
    expression_asset = next(item for item in DEFAULT_ASSET_TYPE_REGISTRY_ITEMS if item["code"] == "expression_matrix")
    variant_asset = next(item for item in DEFAULT_ASSET_TYPE_REGISTRY_ITEMS if item["code"] == "variant_vcf")
    phenotype_table_asset = next(item for item in DEFAULT_ASSET_TYPE_REGISTRY_ITEMS if item["code"] == "phenotype_table")
    phenotype_index_asset = next(item for item in DEFAULT_ASSET_TYPE_REGISTRY_ITEMS if item["code"] == "phenotype_index")
    assert "genome" in reference_asset["allowed_dataset_types"]
    assert "transcriptome" in expression_asset["allowed_dataset_types"]
    assert "variome" in variant_asset["allowed_dataset_types"]
    assert "phenome" in phenotype_table_asset["allowed_dataset_types"]
    assert "phenome" in phenotype_index_asset["allowed_dataset_types"]


def test_variome_uses_variant_internal_behavior_for_asset_and_index_detection(tmp_path):
    bcf_path = tmp_path / "example.bcf"
    csi_path = tmp_path / "example.bcf.csi"
    bcf_path.write_bytes(b"dummy")
    csi_path.write_bytes(b"idx")

    assert dataset_domain_service._default_asset_type("variome") == "variant_vcf"
    assert dataset_domain_service._detect_index_file_paths(str(bcf_path), "variome") == [str(csi_path)]


def test_check_vcf_file_accepts_csi_for_bgzip_vcf(tmp_path):
    vcf_path = tmp_path / "example.vcf.gz"
    csi_path = tmp_path / "example.vcf.gz.csi"
    vcf_path.write_bytes(b"dummy")
    csi_path.write_bytes(b"idx")

    assert check_vcf_file(str(vcf_path)) is True


def test_phenome_uses_phenotype_table_as_default_asset_type():
    assert dataset_domain_service._canonical_dataset_type("phenotype") == "phenome"
    assert dataset_domain_service._default_asset_type("phenome") == "phenotype_table"
    assert dataset_domain_service._resolve_dataset_type_from_path("/tmp/rose.xlsx") == "phenome"


def test_legacy_dataset_type_aliases_map_to_new_canonical_types():
    assert dataset_domain_service._canonical_dataset_type("sequence") == "genome"
    assert dataset_domain_service._canonical_dataset_type("expression") == "transcriptome"
    assert dataset_domain_service._canonical_dataset_type("variant") == "variome"

    genome_kind = next(item for item in DEFAULT_DATASET_KIND_REGISTRY_ITEMS if item["code"] == "genome")
    transcriptome_kind = next(item for item in DEFAULT_DATASET_KIND_REGISTRY_ITEMS if item["code"] == "transcriptome")
    dataset_kind_codes = {item["code"] for item in DEFAULT_DATASET_KIND_REGISTRY_ITEMS}

    assert genome_kind["name"] == "基因组"
    assert transcriptome_kind["name"] == "转录组"
    assert "sequence" not in dataset_kind_codes
    assert "expression" not in dataset_kind_codes
    assert "variant" not in dataset_kind_codes
