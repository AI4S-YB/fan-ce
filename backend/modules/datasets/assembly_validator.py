"""Cross-dataset assembly consistency and sample alignment validation."""
from sqlalchemy.orm import Session


class AssemblyConsistencyValidator:
    """Cross-dataset assembly and sample alignment validation."""

    @staticmethod
    def validate_assembly_consistency(db: Session, dataset_ids: list[int]) -> dict:
        """Check that all given datasets share the same assembly."""
        from modules.datasets.dataset_model import Dataset

        datasets = db.query(Dataset).filter(Dataset.id.in_(dataset_ids)).all()
        if not datasets:
            return {"consistent": True, "assembly": None, "datasets": [], "mismatches": []}

        assemblies: dict[str, list[dict]] = {}
        for ds in datasets:
            asm = (ds.assembly or "").strip()
            assemblies.setdefault(asm, []).append({
                "dataset_id": ds.id,
                "dataset_code": ds.dataset_code,
                "assembly": ds.assembly,
            })

        if len(assemblies) == 1:
            asm_key = list(assemblies.keys())[0]
            return {
                "consistent": True,
                "assembly": asm_key or None,
                "datasets": assemblies[asm_key],
                "mismatches": [],
            }

        majority_key = max(assemblies, key=lambda k: len(assemblies[k]))
        mismatches = []
        for asm_key, items in assemblies.items():
            if asm_key != majority_key:
                mismatches.extend(items)

        return {
            "consistent": False,
            "assembly": majority_key,
            "datasets": assemblies[majority_key],
            "mismatches": mismatches,
        }

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
