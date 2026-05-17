import pytest


class TestExpressionComparison:
    def test_comparison_plan_builds_correctly(self, db_session):
        from modules.datasets.expression_comparison import ExpressionComparisonService
        from modules.datasets.models import DatasetRegistry as Dataset  # was dataset_model.Dataset

        ds_a = Dataset(dataset_code="DS_EXPR_A", dataset_type="transcriptome", assembly="IRGSP-1.0")
        ds_b = Dataset(dataset_code="DS_EXPR_B", dataset_type="transcriptome", assembly="IRGSP-1.0")
        db_session.add_all([ds_a, ds_b])
        db_session.commit()

        result = ExpressionComparisonService.compare_expression(
            db=db_session, dataset_a_id=ds_a.id, dataset_b_id=ds_b.id,
            genes=["Os01g0100100", "Os01g0100200"],
        )
        assert result["query_type"] == "cross_dataset_expression_comparison"
        assert result["genes"] == ["Os01g0100100", "Os01g0100200"]
        assert result["query_plan"]["dataset_a"]["operation"] == "matrix_slice"
        assert result["query_plan"]["dataset_b"]["operation"] == "matrix_slice"

    def test_multi_dataset_profile_builds_correctly(self, db_session):
        from modules.datasets.expression_comparison import ExpressionComparisonService
        from modules.datasets.models import DatasetRegistry as Dataset  # was dataset_model.Dataset

        datasets = []
        for code in ["DS_PROF_1", "DS_PROF_2", "DS_PROF_3"]:
            ds = Dataset(dataset_code=code, dataset_type="transcriptome", assembly="IRGSP-1.0")
            db_session.add(ds)
            datasets.append(ds)
        db_session.commit()

        result = ExpressionComparisonService.multi_dataset_profile(
            db=db_session,
            dataset_ids=[ds.id for ds in datasets],
            gene="Os01g0100100",
        )
        assert result["query_type"] == "multi_dataset_expression_profile"
        assert result["gene"] == "Os01g0100100"
        assert len(result["datasets"]) == 3
