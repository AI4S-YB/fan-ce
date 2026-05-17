from sqlalchemy.orm import Session


class CrossDomainDatasetLookup:
    """Cross-domain dataset lookup: given a breeding entity, find linked datasets.

    Consumes breeding link tables from modules.breeding.models.
    Returns dataset summaries from modules.datasets.dataset_model.Dataset.
    Placed in datasets app to avoid circular imports.
    """

    @staticmethod
    def _is_visible(ds, user=None) -> bool:
        """Check dataset visibility. If user is None (public context), only public datasets pass."""
        if ds.visibility == "public":
            return True
        if user is None:
            return False
        if ds.visibility == "project":
            return user.team_id == ds.team_id
        if ds.visibility == "private":
            return user.team_id == ds.team_id
        return False

    def get_datasets_for_material(self, db: Session, material_id: int, user=None) -> list[dict]:
        from modules.breeding.models import (
            BreedingVariantSampleMap,
            BreedingPhenotypeSubjectMap,
            BreedingDatasetSubjectLink,
            BreedingDatasetAssayLink,
            BreedingBioSample,
            BreedingAssay,
        )
        from modules.datasets.dataset_model import Dataset

        results: dict[int, dict] = {}

        def add(ds, role, link_type):
            if not CrossDomainDatasetLookup._is_visible(ds, user):
                return
            if ds.id not in results:
                results[ds.id] = {
                    "dataset_id": ds.id,
                    "dataset_code": ds.dataset_code,
                    "dataset_type": ds.dataset_type,
                    "organism": ds.organism,
                    "assembly": ds.assembly,
                    "links": [],
                }
            results[ds.id]["links"].append({"role": role, "link_type": link_type})

        # variant_sample_map
        for vmap, ds in (
            db.query(BreedingVariantSampleMap, Dataset)
            .join(Dataset, Dataset.id == BreedingVariantSampleMap.dataset_id)
            .filter(BreedingVariantSampleMap.material_id == material_id)
            .all()
        ):
            add(ds, "variant", "variant_sample_map")

        # phenotype_subject_map
        for pmap, ds in (
            db.query(BreedingPhenotypeSubjectMap, Dataset)
            .join(Dataset, Dataset.id == BreedingPhenotypeSubjectMap.dataset_id)
            .filter(BreedingPhenotypeSubjectMap.material_id == material_id)
            .all()
        ):
            add(ds, "phenotype", "phenotype_subject_map")

        # dataset_subject_link
        for slink, ds in (
            db.query(BreedingDatasetSubjectLink, Dataset)
            .join(Dataset, Dataset.id == BreedingDatasetSubjectLink.dataset_id)
            .filter(BreedingDatasetSubjectLink.material_id == material_id)
            .all()
        ):
            add(ds, slink.role or "subject", "dataset_subject_link")

        # dataset_assay_link (via biosample -> assay)
        biosample_subq = (
            db.query(BreedingBioSample.id)
            .filter(BreedingBioSample.material_id == material_id)
            .subquery()
        )
        assay_subq = (
            db.query(BreedingAssay.id)
            .filter(BreedingAssay.biosample_id.in_(biosample_subq))
            .subquery()
        )
        for alink, ds in (
            db.query(BreedingDatasetAssayLink, Dataset)
            .join(Dataset, Dataset.id == BreedingDatasetAssayLink.dataset_id)
            .filter(BreedingDatasetAssayLink.assay_id.in_(assay_subq))
            .all()
        ):
            add(ds, alink.role or "expression", "dataset_assay_link")

        return list(results.values())

    def get_datasets_for_program(self, db: Session, program_id: int, dataset_type: str = None, user=None) -> list[dict]:
        from modules.breeding.models import (
            BreedingVariantSampleMap,
            BreedingPhenotypeSubjectMap,
            BreedingDatasetSubjectLink,
            BreedingDatasetAssayLink,
            BreedingBioSample,
            BreedingAssay,
            BreedingMaterial,
        )
        from modules.datasets.dataset_model import Dataset

        results: dict[int, dict] = {}
        material_ids_subq = (
            db.query(BreedingMaterial.id)
            .filter(BreedingMaterial.program_id == program_id)
            .subquery()
        )

        def add(ds, role, link_type):
            if not CrossDomainDatasetLookup._is_visible(ds, user):
                return
            if ds.id not in results:
                results[ds.id] = {
                    "dataset_id": ds.id,
                    "dataset_code": ds.dataset_code,
                    "dataset_type": ds.dataset_type,
                    "organism": ds.organism,
                    "assembly": ds.assembly,
                    "links": [],
                }
            results[ds.id]["links"].append({"role": role, "link_type": link_type})

        # variant_sample_map
        for vmap, ds in (
            db.query(BreedingVariantSampleMap, Dataset)
            .join(Dataset, Dataset.id == BreedingVariantSampleMap.dataset_id)
            .filter(BreedingVariantSampleMap.material_id.in_(material_ids_subq))
            .all()
        ):
            add(ds, "variant", "variant_sample_map")

        # phenotype_subject_map
        for pmap, ds in (
            db.query(BreedingPhenotypeSubjectMap, Dataset)
            .join(Dataset, Dataset.id == BreedingPhenotypeSubjectMap.dataset_id)
            .filter(BreedingPhenotypeSubjectMap.material_id.in_(material_ids_subq))
            .all()
        ):
            add(ds, "phenotype", "phenotype_subject_map")

        # dataset_subject_link via program_id
        for slink, ds in (
            db.query(BreedingDatasetSubjectLink, Dataset)
            .join(Dataset, Dataset.id == BreedingDatasetSubjectLink.dataset_id)
            .filter(BreedingDatasetSubjectLink.program_id == program_id)
            .all()
        ):
            add(ds, slink.role or "subject", "dataset_subject_link")

        # dataset_assay_link (via biosample -> material)
        biosample_subq = (
            db.query(BreedingBioSample.id)
            .filter(BreedingBioSample.material_id.in_(material_ids_subq))
            .subquery()
        )
        assay_subq = (
            db.query(BreedingAssay.id)
            .filter(BreedingAssay.biosample_id.in_(biosample_subq))
            .subquery()
        )
        for alink, ds in (
            db.query(BreedingDatasetAssayLink, Dataset)
            .join(Dataset, Dataset.id == BreedingDatasetAssayLink.dataset_id)
            .filter(BreedingDatasetAssayLink.assay_id.in_(assay_subq))
            .all()
        ):
            add(ds, alink.role or "expression", "dataset_assay_link")

        result_list = list(results.values())
        if dataset_type:
            result_list = [r for r in result_list if r["dataset_type"] == dataset_type]

        return result_list
