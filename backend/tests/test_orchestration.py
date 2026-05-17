import pytest


class TestGwasAssembly:
    def test_check_analysis_readiness_returns_traffic_light(self, db_session):
        from modules.datasets.orchestration import AnalysisReadinessService
        from modules.datasets.models import DatasetRegistry as Dataset  # was dataset_model.Dataset

        ds_v = Dataset(dataset_code="DS_READY_V", dataset_type="variome", assembly="IRGSP-1.0")
        ds_p = Dataset(dataset_code="DS_READY_P", dataset_type="phenome", assembly="IRGSP-1.0")
        db_session.add_all([ds_v, ds_p])
        db_session.commit()

        result = AnalysisReadinessService.check_gwas_readiness(
            db=db_session,
            variant_dataset_id=ds_v.id,
            phenotype_dataset_id=ds_p.id,
        )
        assert "overall" in result
        assert result["overall"] in ("green", "yellow", "red")
        assert "checks" in result
        assert "assembly" in result["checks"]
        assert result["checks"]["assembly"]["passed"] is True

    def test_assemble_gwas_input_empty_when_no_samples(self, db_session):
        from modules.datasets.orchestration import GwasAssemblyService
        from modules.datasets.models import DatasetRegistry as Dataset  # was dataset_model.Dataset

        ds_v = Dataset(dataset_code="DS_GWAS_V", dataset_type="variome", assembly="IRGSP-1.0")
        ds_p = Dataset(dataset_code="DS_GWAS_P", dataset_type="phenome", assembly="IRGSP-1.0")
        db_session.add_all([ds_v, ds_p])
        db_session.commit()

        result = GwasAssemblyService.assemble_gwas_input(
            db=db_session,
            variant_dataset_id=ds_v.id,
            phenotype_dataset_id=ds_p.id,
        )
        assert "status" in result
        assert result["status"] == "not_ready"
        assert "reason" in result

    def test_check_analysis_readiness_red_when_assembly_mismatch(self, db_session):
        from modules.datasets.orchestration import AnalysisReadinessService
        from modules.datasets.models import DatasetRegistry as Dataset  # was dataset_model.Dataset

        ds_v = Dataset(dataset_code="DS_RED_V", dataset_type="variome", assembly="IRGSP-1.0")
        ds_p = Dataset(dataset_code="DS_RED_P", dataset_type="phenome", assembly="Os-Nipponbare-Reference-IRGSP-1.0")
        db_session.add_all([ds_v, ds_p])
        db_session.commit()

        result = AnalysisReadinessService.check_gwas_readiness(
            db=db_session, variant_dataset_id=ds_v.id, phenotype_dataset_id=ds_p.id,
        )
        assert result["checks"]["assembly"]["passed"] is False
        assert result["overall"] == "red"
