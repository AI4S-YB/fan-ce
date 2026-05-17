from typing import TypeVar

from shared.crud_base import CRUDBase
from shared.database import Base

from .models import (
    BreedingAssay,
    BreedingBioSample,
    BreedingDataFile,
    BreedingDatasetAssayLink,
    BreedingDatasetSubjectLink,
    BreedingMaterial,
    BreedingObservation,
    BreedingPhenotypeSubjectMap,
    BreedingPlot,
    BreedingProgram,
    BreedingTrial,
    BreedingVariantSampleMap,
)

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBreedingProgram(CRUDBase[BreedingProgram, BreedingProgram, BreedingProgram]):
    pass


class CRUDBreedingMaterial(CRUDBase[BreedingMaterial, BreedingMaterial, BreedingMaterial]):
    pass


class CRUDBreedingTrial(CRUDBase[BreedingTrial, BreedingTrial, BreedingTrial]):
    pass


class CRUDBreedingPlot(CRUDBase[BreedingPlot, BreedingPlot, BreedingPlot]):
    pass


class CRUDBreedingObservation(CRUDBase[BreedingObservation, BreedingObservation, BreedingObservation]):
    pass


class CRUDBreedingBioSample(CRUDBase[BreedingBioSample, BreedingBioSample, BreedingBioSample]):
    pass


class CRUDBreedingAssay(CRUDBase[BreedingAssay, BreedingAssay, BreedingAssay]):
    pass


class CRUDBreedingDataFile(CRUDBase[BreedingDataFile, BreedingDataFile, BreedingDataFile]):
    pass


class CRUDBreedingDatasetSubjectLink(
    CRUDBase[BreedingDatasetSubjectLink, BreedingDatasetSubjectLink, BreedingDatasetSubjectLink]
):
    pass


class CRUDBreedingDatasetAssayLink(
    CRUDBase[BreedingDatasetAssayLink, BreedingDatasetAssayLink, BreedingDatasetAssayLink]
):
    pass


class CRUDBreedingVariantSampleMap(
    CRUDBase[BreedingVariantSampleMap, BreedingVariantSampleMap, BreedingVariantSampleMap]
):
    pass


class CRUDBreedingPhenotypeSubjectMap(
    CRUDBase[BreedingPhenotypeSubjectMap, BreedingPhenotypeSubjectMap, BreedingPhenotypeSubjectMap]
):
    pass


breeding_program_db = CRUDBreedingProgram(BreedingProgram)
breeding_material_db = CRUDBreedingMaterial(BreedingMaterial)
breeding_trial_db = CRUDBreedingTrial(BreedingTrial)
breeding_plot_db = CRUDBreedingPlot(BreedingPlot)
breeding_observation_db = CRUDBreedingObservation(BreedingObservation)
breeding_biosample_db = CRUDBreedingBioSample(BreedingBioSample)
breeding_assay_db = CRUDBreedingAssay(BreedingAssay)
breeding_data_file_db = CRUDBreedingDataFile(BreedingDataFile)
breeding_dataset_subject_link_db = CRUDBreedingDatasetSubjectLink(BreedingDatasetSubjectLink)
breeding_dataset_assay_link_db = CRUDBreedingDatasetAssayLink(BreedingDatasetAssayLink)
breeding_variant_sample_map_db = CRUDBreedingVariantSampleMap(BreedingVariantSampleMap)
breeding_phenotype_subject_map_db = CRUDBreedingPhenotypeSubjectMap(BreedingPhenotypeSubjectMap)
