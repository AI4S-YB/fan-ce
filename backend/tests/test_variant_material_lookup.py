import pytest


class TestVariantMaterialLookup:
    def test_lookup_returns_materials_for_samples(self, db_session):
        from modules.datasets.variant_material_lookup import VariantMaterialLookup
        from modules.breeding.models import (
            BreedingProgram, BreedingMaterial, BreedingVariantSampleMap,
        )
        from modules.datasets.dataset_model import Dataset

        program = BreedingProgram(code="P_VML", name="Variant Lookup", status="active")
        db_session.add(program)
        db_session.commit()

        mat1 = BreedingMaterial(program_id=program.id, material_code="M_VML1",
                                material_name="Rice Line A", material_type="line")
        mat2 = BreedingMaterial(program_id=program.id, material_code="M_VML2",
                                material_name="Rice Line B", material_type="line")
        db_session.add_all([mat1, mat2])
        db_session.commit()

        ds = Dataset(dataset_code="DS_VML", dataset_type="variome",
                     visibility="public", assembly="IRGSP-1.0")
        db_session.add(ds)
        db_session.commit()

        map1 = BreedingVariantSampleMap(
            dataset_id=ds.id, version_id=1, asset_id=1,
            vcf_sample_name="SAM001", material_id=mat1.id,
            mapping_status="matched", mapping_method="manual",
        )
        map2 = BreedingVariantSampleMap(
            dataset_id=ds.id, version_id=1, asset_id=1,
            vcf_sample_name="SAM002", material_id=mat2.id,
            mapping_status="matched", mapping_method="manual",
        )
        db_session.add_all([map1, map2])
        db_session.commit()

        result = VariantMaterialLookup.lookup_materials_for_samples(
            db=db_session, dataset_id=ds.id,
            sample_names=["SAM001", "SAM002", "SAM_UNKNOWN"],
        )
        assert result["matched_count"] == 2
        assert result["unmatched"] == ["SAM_UNKNOWN"]
        materials = {m["material_code"] for m in result["materials"]}
        assert "M_VML1" in materials
        assert "M_VML2" in materials

    def test_lookup_returns_empty_for_no_matches(self, db_session):
        from modules.datasets.variant_material_lookup import VariantMaterialLookup

        result = VariantMaterialLookup.lookup_materials_for_samples(
            db=db_session, dataset_id=999, sample_names=["NOBODY"],
        )
        assert result["matched_count"] == 0
        assert len(result["materials"]) == 0
