"""Cross-dataset sample alignment validation."""
from sqlalchemy.orm import Session


class AssemblyConsistencyValidator:
    """Cross-dataset sample alignment validation."""

    @staticmethod
    def check_sample_alignment(db: Session, variant_dataset_id: int, phenotype_dataset_id: int) -> dict:
        """Check how many materials are paired between variant and phenotype datasets."""
        from modules.breeding.models import BreedingVariantSampleMap, BreedingPhenotypeSubjectMap

        variant_materials = set(
            r[0] for r in
            db.query(BreedingVariantSampleMap.material_id)
            .filter(
                BreedingVariantSampleMap.dataset_id == variant_dataset_id,
                BreedingVariantSampleMap.material_id.isnot(None),
            )
            .distinct()
            .all()
        )

        pheno_materials = set(
            r[0] for r in
            db.query(BreedingPhenotypeSubjectMap.material_id)
            .filter(
                BreedingPhenotypeSubjectMap.dataset_id == phenotype_dataset_id,
                BreedingPhenotypeSubjectMap.material_id.isnot(None),
            )
            .distinct()
            .all()
        )

        paired = variant_materials & pheno_materials
        variant_only = variant_materials - pheno_materials
        pheno_only = pheno_materials - variant_materials
        total = len(variant_materials | pheno_materials)

        return {
            "paired_count": len(paired),
            "paired_material_ids": sorted(paired),
            "variant_only_count": len(variant_only),
            "variant_only_material_ids": sorted(variant_only),
            "phenotype_only_count": len(pheno_only),
            "phenotype_only_material_ids": sorted(pheno_only),
            "coverage": len(paired) / total if total > 0 else 0.0,
        }
