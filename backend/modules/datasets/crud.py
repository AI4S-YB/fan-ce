from typing import TypeVar

from shared.crud_base import CRUDBase
from shared.database import Base

from .models import (
    AssetFile,
    AssetFileTypeRegistry,
    AssetTypeRegistry,
    DatasetAsset,
    DatasetKindRegistry,
    DatasetLineageEdge,
    DatasetPublishRecord,
    DatasetRegistrationCandidate,
    DatasetRegistrationCandidateFile,
    DatasetRegistry,
    DatasetScanJob,
    DatasetScanRoot,
    DatasetStagingFile,
    DatasetVersion,
    DatasetVersionPublishRecord,
    DatasetWorkflowTask,
    FunctionalGene,
    FunctionalTerm,
    FunctionalTermAssignment,
)

ModelType = TypeVar("ModelType", bound=Base)


class CRUDDatasetRegistry(CRUDBase[DatasetRegistry, DatasetRegistry, DatasetRegistry]):
    pass


class CRUDDatasetWorkflowTask(CRUDBase[DatasetWorkflowTask, DatasetWorkflowTask, DatasetWorkflowTask]):
    pass


class CRUDDatasetPublishRecord(CRUDBase[DatasetPublishRecord, DatasetPublishRecord, DatasetPublishRecord]):
    pass


class CRUDDatasetVersion(CRUDBase[DatasetVersion, DatasetVersion, DatasetVersion]):
    pass


class CRUDDatasetAsset(CRUDBase[DatasetAsset, DatasetAsset, DatasetAsset]):
    pass


class CRUDAssetFile(CRUDBase[AssetFile, AssetFile, AssetFile]):
    pass


class CRUDDatasetLineageEdge(CRUDBase[DatasetLineageEdge, DatasetLineageEdge, DatasetLineageEdge]):
    pass


class CRUDDatasetVersionPublishRecord(CRUDBase[DatasetVersionPublishRecord, DatasetVersionPublishRecord, DatasetVersionPublishRecord]):
    pass


class CRUDDatasetKindRegistry(CRUDBase[DatasetKindRegistry, DatasetKindRegistry, DatasetKindRegistry]):
    pass


class CRUDAssetTypeRegistry(CRUDBase[AssetTypeRegistry, AssetTypeRegistry, AssetTypeRegistry]):
    pass


class CRUDAssetFileTypeRegistry(CRUDBase[AssetFileTypeRegistry, AssetFileTypeRegistry, AssetFileTypeRegistry]):
    pass


class CRUDDatasetStagingFile(CRUDBase[DatasetStagingFile, DatasetStagingFile, DatasetStagingFile]):
    pass


class CRUDDatasetScanRoot(CRUDBase[DatasetScanRoot, DatasetScanRoot, DatasetScanRoot]):
    pass


class CRUDDatasetScanJob(CRUDBase[DatasetScanJob, DatasetScanJob, DatasetScanJob]):
    pass


class CRUDDatasetRegistrationCandidate(CRUDBase[DatasetRegistrationCandidate, DatasetRegistrationCandidate, DatasetRegistrationCandidate]):
    pass


class CRUDDatasetRegistrationCandidateFile(CRUDBase[DatasetRegistrationCandidateFile, DatasetRegistrationCandidateFile, DatasetRegistrationCandidateFile]):
    pass


class CRUDFunctionalGene(CRUDBase[FunctionalGene, FunctionalGene, FunctionalGene]):
    pass


class CRUDFunctionalTerm(CRUDBase[FunctionalTerm, FunctionalTerm, FunctionalTerm]):
    pass


class CRUDFunctionalTermAssignment(CRUDBase[FunctionalTermAssignment, FunctionalTermAssignment, FunctionalTermAssignment]):
    pass


dataset_registry_db = CRUDDatasetRegistry(DatasetRegistry)
dataset_workflow_task_db = CRUDDatasetWorkflowTask(DatasetWorkflowTask)
dataset_publish_record_db = CRUDDatasetPublishRecord(DatasetPublishRecord)
dataset_version_db = CRUDDatasetVersion(DatasetVersion)
dataset_asset_db = CRUDDatasetAsset(DatasetAsset)
asset_file_db = CRUDAssetFile(AssetFile)
dataset_lineage_edge_db = CRUDDatasetLineageEdge(DatasetLineageEdge)
dataset_version_publish_record_db = CRUDDatasetVersionPublishRecord(DatasetVersionPublishRecord)
dataset_kind_registry_db = CRUDDatasetKindRegistry(DatasetKindRegistry)
asset_type_registry_db = CRUDAssetTypeRegistry(AssetTypeRegistry)
asset_file_type_registry_db = CRUDAssetFileTypeRegistry(AssetFileTypeRegistry)
dataset_staging_file_db = CRUDDatasetStagingFile(DatasetStagingFile)
dataset_scan_root_db = CRUDDatasetScanRoot(DatasetScanRoot)
dataset_scan_job_db = CRUDDatasetScanJob(DatasetScanJob)
dataset_registration_candidate_db = CRUDDatasetRegistrationCandidate(DatasetRegistrationCandidate)
dataset_registration_candidate_file_db = CRUDDatasetRegistrationCandidateFile(DatasetRegistrationCandidateFile)
functional_gene_db = CRUDFunctionalGene(FunctionalGene)
functional_term_db = CRUDFunctionalTerm(FunctionalTerm)
functional_term_assignment_db = CRUDFunctionalTermAssignment(FunctionalTermAssignment)
