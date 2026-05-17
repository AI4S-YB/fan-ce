from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.datasets.services import dataset_domain_service


def test_validate_annotation_gtf_detects_index_state(tmp_path):
    file_path = tmp_path / "genes.gtf"
    file_path.write_text(
        'chr1\tsrc\tgene\t10\t90\t.\t+\t.\tgene_id "Gene001"; gene_name "Gene001";\n',
        encoding="utf-8",
    )

    result_without_index = dataset_domain_service._validate_by_dataset_type(str(file_path), "annotation")
    index_path = tmp_path / "genes.gtf.tbi"
    index_path.write_text("tabix-index\n", encoding="utf-8")
    result_with_index = dataset_domain_service._validate_by_dataset_type(str(file_path), "annotation")

    assert result_without_index == {
        "format": "gtf",
        "validated_path": str(file_path),
        "indexed": False,
    }
    assert result_with_index == {
        "format": "gtf",
        "validated_path": str(file_path),
        "indexed": True,
    }


def test_index_annotation_gtf_creates_bgzip_and_tabix_outputs(monkeypatch, tmp_path):
    file_path = tmp_path / "genes.gtf"
    file_path.write_text(
        'chr1\tsrc\tgene\t10\t90\t.\t+\t.\tgene_id "Gene001"; gene_name "Gene001";\n',
        encoding="utf-8",
    )

    def fake_require_binary(_binary_name):
        return None

    def fake_run(cmd, stdout=None, check=None, **_kwargs):
        if cmd[:2] == ["bgzip", "-c"]:
            stdout.write(file_path.read_bytes())
            return None
        if cmd[:2] == ["tabix", "-p"]:
            Path(f"{cmd[-1]}.tbi").write_text("tabix-index\n", encoding="utf-8")
            return None
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(dataset_domain_service, "_require_binary", fake_require_binary)
    monkeypatch.setattr("apps.datasets.services.subprocess.run", fake_run)

    result = dataset_domain_service._index_by_dataset_type(str(file_path), "annotation")

    indexed_path = tmp_path / "genes.gtf.gz"
    index_path = tmp_path / "genes.gtf.gz.tbi"

    assert result == {
        "indexed_path": str(indexed_path),
        "index_files": [str(index_path)],
        "operation": "tabix-gff",
    }
    assert indexed_path.exists() is True
    assert index_path.exists() is True
    assert indexed_path.read_text(encoding="utf-8") == file_path.read_text(encoding="utf-8")


def test_index_annotation_sqlite_keeps_original_file(tmp_path):
    file_path = tmp_path / "genes.db"
    file_path.write_bytes(b"SQLite format 3\x00dummy")

    result = dataset_domain_service._index_by_dataset_type(str(file_path), "annotation")

    assert result == {
        "indexed_path": str(file_path),
        "index_files": [],
        "operation": "sqlite-ready",
    }
