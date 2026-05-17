import os
import time


class TestIndexStaleness:
    def test_stale_index_is_detected(self, tmp_path):
        source = tmp_path / "test.vcf.gz"
        source.write_text("mock vcf data")
        index = tmp_path / "test.vcf.gz.tbi"
        index.write_text("mock tbi index")
        old_time = time.time() - 3600
        os.utime(index, (old_time, old_time))

        from modules.datasets.adapters.base import DatasetQueryAdapter
        is_stale = DatasetQueryAdapter._is_index_stale(
            source_path=str(source), index_path=str(index),
        )
        assert is_stale is True

    def test_fresh_index_passes(self, tmp_path):
        source = tmp_path / "test.vcf.gz"
        source.write_text("mock vcf data")
        index = tmp_path / "test.vcf.gz.tbi"
        index.write_text("mock tbi index")
        new_time = time.time() + 3600
        os.utime(index, (new_time, new_time))

        from modules.datasets.adapters.base import DatasetQueryAdapter
        is_stale = DatasetQueryAdapter._is_index_stale(
            source_path=str(source), index_path=str(index),
        )
        assert is_stale is False
