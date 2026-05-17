import pytest


class TestCrossDomainVisibility:
    def test_cross_domain_lookup_filters_out_private_datasets(self, db_session):
        from modules.datasets.cross_domain import CrossDomainDatasetLookup
        from modules.datasets.dataset_model import Dataset
        from modules.datasets.models import DatasetVersion
        from modules.breeding.models import (
            BreedingProgram, BreedingMaterial, BreedingDatasetSubjectLink,
            BreedingDatasetAssayLink, BreedingBioSample, BreedingAssay,
        )
        from shared.database import Base

        # Ensure all link tables queried by get_datasets_for_material exist
        Base.metadata.create_all(
            bind=db_session.get_bind(),
            tables=[
                BreedingDatasetSubjectLink.__table__,
                BreedingDatasetAssayLink.__table__,
                BreedingBioSample.__table__,
                BreedingAssay.__table__,
            ],
            checkfirst=True,
        )

        program = BreedingProgram(code="P_VIS1", name="Visibility Test", status="active")
        db_session.add(program)
        db_session.commit()

        mat = BreedingMaterial(program_id=program.id, material_code="M_VIS1",
                               material_name="Test Material", material_type="line")
        db_session.add(mat)
        db_session.commit()

        ds_public = Dataset(dataset_code="DS_PUB_V", dataset_type="variome",
                           visibility="public", assembly="IRGSP-1.0")
        ds_private = Dataset(dataset_code="DS_PRIV_V", dataset_type="variome",
                            visibility="private", assembly="IRGSP-1.0")
        db_session.add_all([ds_public, ds_private])
        db_session.commit()

        ver_public = DatasetVersion(dataset_id=ds_public.id, version="1.0")
        ver_private = DatasetVersion(dataset_id=ds_private.id, version="1.0")
        db_session.add_all([ver_public, ver_private])
        db_session.commit()

        # Link both datasets to same material
        link1 = BreedingDatasetSubjectLink(dataset_id=ds_public.id, version_id=ver_public.id,
                                           material_id=mat.id, role="source")
        link2 = BreedingDatasetSubjectLink(dataset_id=ds_private.id, version_id=ver_private.id,
                                           material_id=mat.id, role="source")
        db_session.add_all([link1, link2])
        db_session.commit()

        lookup = CrossDomainDatasetLookup()
        result = lookup.get_datasets_for_material(db=db_session, material_id=mat.id)
        ds_ids = [d["dataset_id"] for d in result]
        assert ds_public.id in ds_ids
        assert ds_private.id not in ds_ids

    def test_public_datasets_always_visible(self, db_session):
        from modules.datasets.cross_domain import CrossDomainDatasetLookup
        from modules.datasets.dataset_model import Dataset
        from modules.datasets.models import DatasetVersion
        from modules.breeding.models import (
            BreedingProgram, BreedingMaterial, BreedingDatasetSubjectLink,
            BreedingDatasetAssayLink, BreedingBioSample, BreedingAssay,
        )
        from shared.database import Base

        # Ensure all link tables queried by get_datasets_for_material exist
        Base.metadata.create_all(
            bind=db_session.get_bind(),
            tables=[
                BreedingDatasetSubjectLink.__table__,
                BreedingDatasetAssayLink.__table__,
                BreedingBioSample.__table__,
                BreedingAssay.__table__,
            ],
            checkfirst=True,
        )

        program = BreedingProgram(code="P_VISPUB", name="Public Test", status="active")
        db_session.add(program)
        db_session.commit()

        mat = BreedingMaterial(program_id=program.id, material_code="M_VISPUB",
                               material_name="Public Material", material_type="line")
        db_session.add(mat)
        db_session.commit()

        ds_public = Dataset(dataset_code="DS_ALWAYSVIS", dataset_type="variome",
                           visibility="public", assembly="IRGSP-1.0")
        db_session.add(ds_public)
        db_session.commit()

        ver = DatasetVersion(dataset_id=ds_public.id, version="1.0")
        db_session.add(ver)
        db_session.commit()

        link = BreedingDatasetSubjectLink(dataset_id=ds_public.id, version_id=ver.id,
                                          material_id=mat.id, role="source")
        db_session.add(link)
        db_session.commit()

        lookup = CrossDomainDatasetLookup()
        result = lookup.get_datasets_for_material(db=db_session, material_id=mat.id)
        assert len(result) == 1
        assert result[0]["dataset_id"] == ds_public.id
