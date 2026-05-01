import pytest


class TestBreedingReadiness:
    def test_program_readiness_counts_materials_with_both_data_types(self, db_session):
        from apps.breeding.services import BreedingDomainService
        from apps.breeding.models import (
            BreedingProgram, BreedingMaterial,
            BreedingVariantSampleMap, BreedingPhenotypeSubjectMap,
        )
        from apps.datasets.dataset_model import Dataset

        program = BreedingProgram(code="P_READY", name="Readiness Program", status="active")
        db_session.add(program)
        db_session.commit()

        mat1 = BreedingMaterial(program_id=program.id, material_code="M_HAS_BOTH",
                                material_name="Has Both", material_type="line")
        mat2 = BreedingMaterial(program_id=program.id, material_code="M_VAR_ONLY",
                                material_name="Variant Only", material_type="line")
        mat3 = BreedingMaterial(program_id=program.id, material_code="M_NONE",
                                material_name="No Data", material_type="line")
        db_session.add_all([mat1, mat2, mat3])
        db_session.commit()

        ds_v = Dataset(dataset_code="DS_V_READY", dataset_type="variome", assembly="IRGSP-1.0")
        ds_p = Dataset(dataset_code="DS_P_READY", dataset_type="phenome", assembly="IRGSP-1.0")
        db_session.add_all([ds_v, ds_p])
        db_session.commit()

        # Mat1: has both variant and phenotype
        db_session.add(BreedingVariantSampleMap(
            dataset_id=ds_v.id, version_id=1, asset_id=1,
            vcf_sample_name="S1", material_id=mat1.id, mapping_status="matched"))
        db_session.add(BreedingPhenotypeSubjectMap(
            dataset_id=ds_p.id, version_id=1, asset_id=1,
            row_key="S1", material_id=mat1.id, mapping_status="matched"))
        # Mat2: variant only
        db_session.add(BreedingVariantSampleMap(
            dataset_id=ds_v.id, version_id=1, asset_id=1,
            vcf_sample_name="S2", material_id=mat2.id, mapping_status="matched"))
        db_session.commit()

        svc = BreedingDomainService()
        result = svc.get_program_analysis_readiness(db=db_session, program_id=program.id)

        assert result["total_materials"] == 3
        assert result["materials_with_variant"] == 2
        assert result["materials_with_phenotype"] == 1
        assert result["materials_with_both"] == 1
        assert result["ready_material_ids"] == [mat1.id]
