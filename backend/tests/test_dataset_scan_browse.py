import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import os
from unittest.mock import patch, MagicMock, Mock

from modules.datasets.services import DatasetDomainService


def test_phenome_sqlite_detected_via_directory_context():
    """phenome sqlite file in phenotype directory should be detected as phenome"""
    svc = DatasetDomainService()
    result = svc._resolve_dataset_type_from_path(
        "/data/phenotype/rose_phenotype.db", None
    )
    assert result == "phenome"


def test_sqlite_file_format_falls_back_to_generic():
    svc = DatasetDomainService()
    assert svc.FILE_FORMAT_TO_DATASET_TYPE.get("sqlite") is None
    assert svc.FILE_FORMAT_TO_DATASET_TYPE.get("db") is None


def test_sqlite_in_unknown_directory_falls_back_to_generic():
    """sqlite file in a directory without recognizable keywords should be generic"""
    svc = DatasetDomainService()
    result = svc._resolve_dataset_type_from_path(
        "/data/misc/mystery.db", None
    )
    assert result == "generic"


def test_genome_fasta_still_resolves_correctly():
    svc = DatasetDomainService()
    result = svc._resolve_dataset_type_from_path(
        "/data/genomes/rice_genome.fasta", None
    )
    assert result == "genome"


def test_iter_scan_files_yields_realpath():
    """_iter_scan_files should use realpath for consistent symlink handling"""
    svc = DatasetDomainService()
    with patch("os.walk") as mock_walk, patch("os.path.isfile", return_value=True), \
         patch("os.path.realpath", side_effect=lambda p: "/real_" + p):
        mock_walk.return_value = [
            ("/data/genomes", [], ["genome.fasta", "link_to_gff"]),
        ]
        results = list(svc._iter_scan_files("/data/genomes", scan_recursive=True))
        assert len(results) == 2
        for _count, path in results:
            assert "/real_" in path


def test_upsert_scan_staging_file_handles_permission_error():
    """unreadable files should be silently skipped, not crash the scan"""
    svc = DatasetDomainService()
    mock_db = MagicMock()
    mock_root = MagicMock()
    mock_root.root_path = "/data/genomes"
    mock_job = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 1

    with patch("os.stat", side_effect=PermissionError("permission denied")):
        result = svc._upsert_scan_staging_file(
            db=mock_db,
            root_obj=mock_root,
            job_obj=mock_job,
            absolute_path="/data/genomes/unreadable.fasta",
            user=mock_user,
        )
    # should return sentinel indicating skip, not raise
    assert result == (None, False, False, False)


def test_merge_meta_json_preserves_existing_keys():
    """_merge_meta_json should preserve existing keys while adding new ones"""
    existing = json.dumps({"custom_key": "custom_value", "old_field": "keep_me"})
    result = DatasetDomainService._merge_meta_json(existing, {"scan_root_code": "scan-abc"})
    parsed = json.loads(result)
    assert parsed["custom_key"] == "custom_value"
    assert parsed["old_field"] == "keep_me"
    assert parsed["scan_root_code"] == "scan-abc"


def test_merge_meta_json_handles_none_existing():
    """_merge_meta_json should work when existing is None"""
    result = DatasetDomainService._merge_meta_json(None, {"scan_root_code": "scan-xyz"})
    parsed = json.loads(result)
    assert parsed == {"scan_root_code": "scan-xyz"}


def test_merge_meta_json_handles_invalid_json():
    """_merge_meta_json should handle invalid JSON gracefully"""
    result = DatasetDomainService._merge_meta_json("not-valid-json{{{", {"scan_root_code": "scan-123"})
    parsed = json.loads(result)
    assert parsed["scan_root_code"] == "scan-123"


def test_browse_path_outside_root_is_rejected():
    """browse path outside browse_root should return 400"""
    svc = DatasetDomainService()
    with patch.object(svc, '_get_scan_browse_root', return_value="/data/genomes"):
        with patch("os.path.exists", return_value=True), patch("os.path.isdir", return_value=True):
            try:
                svc._resolve_scan_browse_path("/etc/passwd")
                assert False, "should have raised HTTPException"
            except Exception as e:
                assert getattr(e, "status_code", None) == 400
                assert "outside browse root" in str(e.detail)


def test_browse_scan_root_path_returns_files():
    """browse API should return files in current directory"""
    svc = DatasetDomainService()
    with patch.object(svc, '_get_scan_browse_root', return_value="/tmp/test_scan"):
        with patch("os.path.exists", return_value=True), patch("os.path.isdir", return_value=True), \
             patch("os.path.realpath", side_effect=lambda p: p):
            mock_dir = Mock()
            mock_dir.is_dir.return_value = True
            mock_dir.is_file.return_value = False
            mock_dir.name = "subdir"
            mock_dir.path = "/tmp/test_scan/subdir"
            mock_dir.stat.return_value.st_mtime = 12345

            mock_file = Mock()
            mock_file.is_dir.return_value = False
            mock_file.is_file.return_value = True
            mock_file.name = "genome.fasta"
            mock_file.path = "/tmp/test_scan/genome.fasta"
            mock_file.stat.return_value = Mock(st_size=1000, st_mtime=12345)

            with patch("os.scandir") as mock_scandir:
                mock_scandir.return_value.__enter__.return_value = [mock_dir, mock_file]
                result = svc.browse_scan_root_path(
                    db=Mock(),
                    request_data=Mock(path=None, show_hidden=False),
                    user=Mock(),
                )
            assert "files" in result
            assert len(result["files"]) == 1
            assert result["files"][0]["name"] == "genome.fasta"
            assert result["files"][0]["format"] == "fasta"
            assert len(result["entries"]) == 1
            assert result["entries"][0]["is_dir"] is True


def test_browse_hidden_files_filtered_from_files():
    """hidden files should not appear in files list"""
    svc = DatasetDomainService()
    with patch.object(svc, '_get_scan_browse_root', return_value="/tmp/test_scan"):
        with patch("os.path.exists", return_value=True), patch("os.path.isdir", return_value=True), \
             patch("os.path.realpath", side_effect=lambda p: p):
            mock_hidden = Mock()
            mock_hidden.is_dir.return_value = False
            mock_hidden.is_file.return_value = True
            mock_hidden.name = ".secret"
            mock_hidden.path = "/tmp/test_scan/.secret"
            mock_hidden.stat.return_value = Mock(st_size=100, st_mtime=12345)

            with patch("os.scandir") as mock_scandir:
                mock_scandir.return_value.__enter__.return_value = [mock_hidden]
                result = svc.browse_scan_root_path(
                    db=Mock(),
                    request_data=Mock(path=None, show_hidden=False),
                    user=Mock(),
                )
            assert len(result["files"]) == 0


class MockStagingFile:
    """Minimal mock for staging file rows."""
    def __init__(self, id, local_path, scan_root_id, dataset_type, file_name):
        self.id = id
        self.local_path = local_path
        self.scan_root_id = scan_root_id
        self.dataset_type = dataset_type
        self.file_name = file_name
        self.file_format = "fasta"
        self.status = "discovered"
        self.staging_code = f"stg-{id}"
        self.relative_path = file_name
        self.file_size = 1000
        self.scan_job_id = 1
        self.linked_dataset_id = None
        self.last_seen_time = 12345
        self.create_user_id = 1
        self.meta_json = None
        self.create_time = 12345
        self.update_time = 12345
        self.source_name = file_name
        self.source_mode = "server_scan"


def test_build_directory_view_builds_tree():
    """directory view builds recursive tree from staging files"""
    svc = DatasetDomainService()

    items = [
        MockStagingFile(1, "/data/genomes/rice_v3/genome.fasta", 1, "genome", "genome.fasta"),
        MockStagingFile(2, "/data/genomes/rice_v3/gene.gff", 1, "annotation", "gene.gff"),
        MockStagingFile(3, "/data/genomes/wheat_cs/genome.fasta", 1, "genome", "genome.fasta"),
        MockStagingFile(4, "/data/genomes/orphan.fasta", 1, "genome", "orphan.fasta"),
    ]

    class MockRoot:
        def __init__(self, id, root_path):
            self.id = id
            self.root_path = root_path

    with patch.object(svc, '_normalize_local_path', side_effect=lambda p: p):
        with patch("os.path.realpath", side_effect=lambda p: p):
            with patch.object(svc, '_build_dataset_staging_payload', side_effect=lambda row: {"id": row.id, "file_name": row.file_name}):
                scan_roots = [MockRoot(1, "/data/genomes")]
                result = svc._build_directory_view(items, scan_roots)

    assert "trees" in result
    assert "orphan_files" in result
    assert len(result["trees"]) == 1  # one scan root tree
    tree = result["trees"][0]
    assert tree["scan_root_id"] == 1
    children = tree["children"]
    child_names = {c["name"] for c in children}
    assert child_names == {"rice_v3", "wheat_cs"}
    assert len(result["orphan_files"]) == 1  # orphan.fasta directly under /data/genomes


def test_validate_staging_files_checks_file_exists():
    """validate_staging_files should flag non-existent files"""
    svc = DatasetDomainService()
    errors = svc.validate_staging_files([
        {"local_path": "/nonexistent/file.fasta", "file_format": "fasta"},
    ])
    assert len(errors) > 0
    assert any("not found" in e.lower() for e in errors)


def test_validate_staging_files_checks_format_consistency():
    """validate_staging_files should warn when file format doesn't match declared type"""
    svc = DatasetDomainService()
    with patch("os.path.exists", return_value=True), patch("os.access", return_value=True):
        errors = svc.validate_staging_files(
            [{"local_path": "/data/test.fasta", "file_format": "fasta"}],
            declared_dataset_type="variome",
        )
    # fasta -> genome, declared as variome -> mismatch warning
    assert any("fasta" in e.lower() or "genome" in e.lower() or "mismatch" in e.lower() for e in errors)


def test_validate_staging_files_passes_for_valid_files():
    """validate_staging_files should return empty list when everything is valid"""
    svc = DatasetDomainService()
    with patch("os.path.exists", return_value=True), patch("os.access", return_value=True):
        errors = svc.validate_staging_files(
            [{"local_path": "/data/test.fasta", "file_format": "fasta"}],
            declared_dataset_type="genome",
        )
    # fasta -> genome matches declared genome -> no errors
    assert len(errors) == 0
