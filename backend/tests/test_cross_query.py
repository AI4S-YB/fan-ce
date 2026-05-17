class TestCrossDatasetQuery:
    def test_variant_annotation_overlap_query_builds_correctly(self, db_session):
        from modules.datasets.cross_query import CrossDatasetQueryService
        from modules.datasets.dataset_model import Dataset
        ds_var = Dataset(dataset_code="DS_JOIN_V", dataset_type="variome", assembly="IRGSP-1.0")
        ds_ann = Dataset(dataset_code="DS_JOIN_A", dataset_type="annotation", assembly="IRGSP-1.0")
        db_session.add_all([ds_var, ds_ann])
        db_session.commit()
        result = CrossDatasetQueryService.variant_annotation_overlap(
            db=db_session, variant_dataset_id=ds_var.id, annotation_dataset_id=ds_ann.id, region="Chr1:1000-5000",
        )
        assert "query_plan" in result
        assert result["query_plan"]["variant_step"]["operation"] == "batch_fetch"
        assert result["query_plan"]["annotation_step"]["operation"] == "region_features"

    def test_functional_expression_pathway_query(self, db_session):
        from modules.datasets.cross_query import CrossDatasetQueryService
        from modules.datasets.dataset_model import Dataset
        ds_func = Dataset(dataset_code="DS_FUNC", dataset_type="functional_annotation", assembly="IRGSP-1.0")
        ds_expr = Dataset(dataset_code="DS_EXPR", dataset_type="transcriptome", assembly="IRGSP-1.0")
        db_session.add_all([ds_func, ds_expr])
        db_session.commit()
        result = CrossDatasetQueryService.functional_expression_pathway(
            db=db_session, functional_dataset_id=ds_func.id, expression_dataset_id=ds_expr.id, term_id="GO:0008150",
        )
        assert "query_plan" in result
        assert result["query_plan"]["functional_step"]["operation"] == "term_gene_list"
        assert result["query_plan"]["expression_step"]["operation"] == "matrix_slice"
