class TestExpressionMultiFormat:
    def test_adapter_accepts_tsv_format(self):
        from apps.datasets.adapters.expression import ExpressionAdapter
        adapter = ExpressionAdapter()
        payload = {"id": 1, "dataset_type": "transcriptome", "query_profile": {"file_format": "tsv"}}
        assert adapter.supports(payload) is True

    def test_adapter_accepts_csv_format(self):
        from apps.datasets.adapters.expression import ExpressionAdapter
        adapter = ExpressionAdapter()
        payload = {"id": 1, "dataset_type": "transcriptome", "query_profile": {"file_format": "csv"}}
        assert adapter.supports(payload) is True

    def test_adapter_accepts_10x_mtx_format(self):
        from apps.datasets.adapters.expression import ExpressionAdapter
        adapter = ExpressionAdapter()
        payload = {"id": 1, "dataset_type": "transcriptome", "query_profile": {"file_format": "mtx"}}
        assert adapter.supports(payload) is True
