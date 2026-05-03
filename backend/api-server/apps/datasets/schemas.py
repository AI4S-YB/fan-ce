from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class DatasetContext(BaseModel):
    project_id: Optional[int] = 0


class DatasetListRequest(DatasetContext):
    page: Optional[int] = 1
    size: Optional[int] = 10
    dataset_id: Optional[int] = None
    name: Optional[str] = None
    dataset_type: Optional[str] = None
    lifecycle_state: Optional[str] = None
    visibility: Optional[str] = None
    keyword: Optional[str] = None


class DatasetInfoRequest(BaseModel):
    id: int


class DatasetUpdateRequest(BaseModel):
    id: int
    title: Optional[str] = None
    dataset_type: Optional[str] = None
    version: Optional[str] = None
    organism: Optional[str] = None
    file_format: Optional[str] = None
    query_engine: Optional[str] = None
    validation_summary: Optional[str] = None
    index_summary: Optional[str] = None
    extra_json: Optional[str] = None
    description_md: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetDeleteRequest(BaseModel):
    id: int

    model_config = ConfigDict(extra="forbid")


class DatasetStateTransitionRequest(BaseModel):
    id: int
    target_state: str
    task_type: Optional[str] = None
    task_status: Optional[str] = "success"
    detail: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetPublishRequest(BaseModel):
    id: int
    note: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetTaskListRequest(BaseModel):
    id: int
    limit: Optional[int] = 20


class DatasetPublishRecordListRequest(BaseModel):
    id: int
    limit: Optional[int] = 20


class DatasetOptionsRequest(DatasetListRequest):
    page: Optional[int] = 0
    size: Optional[int] = 0


class DatasetQueryCapabilitiesRequest(BaseModel):
    id: int
    asset_code: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class DatasetQueryRequest(BaseModel):
    id: int
    operation: str
    asset_code: Optional[str] = None
    params: Optional[dict] = None

    model_config = ConfigDict(extra="allow")


class DatasetRegisterRequest(DatasetContext):
    file_path: str
    name: Optional[str] = None
    dataset_type: Optional[str] = None
    remark: Optional[str] = None
    is_public: Optional[bool] = False
    dry_run: Optional[bool] = False

    model_config = ConfigDict(extra="forbid")


class DatasetIngestActionRequest(BaseModel):
    id: Optional[int] = None
    file_path: Optional[str] = None
    dataset_type: Optional[str] = None
    detail: Optional[str] = None
    output_file_path: Optional[str] = None
    persist_result: Optional[bool] = True

    model_config = ConfigDict(extra="forbid")


class DatasetIngestPipelineRequest(DatasetIngestActionRequest):
    run_validate: Optional[bool] = True
    run_index: Optional[bool] = True


class DatasetIngestTaskSubmitRequest(DatasetIngestActionRequest):
    action: str
    run_validate: Optional[bool] = True
    run_index: Optional[bool] = True

    model_config = ConfigDict(extra="forbid")


class DatasetWorkflowTaskInfoRequest(BaseModel):
    id: int


class DatasetWorkflowTaskRetryRequest(BaseModel):
    id: int


class DatasetVersionListRequest(BaseModel):
    dataset_id: int


class DatasetVersionInfoRequest(BaseModel):
    id: int


class DatasetVersionQueryCapabilitiesRequest(BaseModel):
    id: int
    asset_code: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class DatasetVersionQueryRequest(BaseModel):
    id: int
    operation: str
    asset_code: Optional[str] = None
    params: Optional[dict] = None

    model_config = ConfigDict(extra="allow")


class DatasetVersionCreateRequest(BaseModel):
    dataset_id: int
    version: str
    title: Optional[str] = None
    file_path: Optional[str] = None
    extra_json: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetVersionActivateRequest(BaseModel):
    id: int
    note: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetVersionReleaseRequest(BaseModel):
    id: int
    note: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetVersionWithdrawRequest(BaseModel):
    id: int
    note: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetVersionSetDefaultPublicRequest(BaseModel):
    id: int
    note: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetVersionPublishRecordListRequest(BaseModel):
    dataset_id: Optional[int] = None
    version_id: Optional[int] = None
    limit: Optional[int] = 20

    model_config = ConfigDict(extra="forbid")


class DatasetAssetListRequest(BaseModel):
    version_id: int


class DatasetAssetInfoRequest(BaseModel):
    id: int


class DatasetAssetCreateRequest(BaseModel):
    version_id: int
    asset_code: Optional[str] = None
    asset_name: str
    asset_type: str
    file_format: Optional[str] = None
    query_engine: Optional[str] = None
    storage_backend: Optional[str] = "local"
    workflow_state: Optional[str] = "draft"
    status: Optional[str] = "active"
    is_required: Optional[bool] = True
    is_query_entry: Optional[bool] = False
    display_order: Optional[int] = 0
    meta_json: Optional[str] = None
    local_path: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetAssetUpdateRequest(BaseModel):
    id: int
    asset_name: Optional[str] = None
    asset_type: Optional[str] = None
    file_format: Optional[str] = None
    query_engine: Optional[str] = None
    storage_backend: Optional[str] = None
    workflow_state: Optional[str] = None
    status: Optional[str] = None
    is_required: Optional[bool] = None
    is_query_entry: Optional[bool] = None
    display_order: Optional[int] = None
    meta_json: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetAssetDeleteRequest(BaseModel):
    id: int

    model_config = ConfigDict(extra="forbid")


class AssetFileListRequest(BaseModel):
    asset_id: int


class AssetFileInfoRequest(BaseModel):
    id: int


class AssetFileRegisterRequest(BaseModel):
    asset_id: int
    file_role: str
    local_path: str
    asset_file_type_code: Optional[str] = None
    file_name: Optional[str] = None
    storage_uri: Optional[str] = None
    file_format: Optional[str] = None
    mime_type: Optional[str] = None
    checksum_type: Optional[str] = None
    checksum_value: Optional[str] = None
    compress_type: Optional[str] = None
    index_of_file_id: Optional[int] = None
    status: Optional[str] = "active"
    meta_json: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class AssetFileUpdateRequest(BaseModel):
    id: int
    file_role: Optional[str] = None
    local_path: Optional[str] = None
    asset_file_type_code: Optional[str] = None
    storage_uri: Optional[str] = None
    file_format: Optional[str] = None
    mime_type: Optional[str] = None
    checksum_type: Optional[str] = None
    checksum_value: Optional[str] = None
    compress_type: Optional[str] = None
    index_of_file_id: Optional[int] = None
    status: Optional[str] = None
    meta_json: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class AssetFileDeleteRequest(BaseModel):
    id: int

    model_config = ConfigDict(extra="forbid")


class DatasetLineageListRequest(BaseModel):
    dataset_id: Optional[int] = None
    version_id: Optional[int] = None
    limit: Optional[int] = 50


class DatasetLineageCreateRequest(BaseModel):
    src_version_id: int
    dst_version_id: int
    relation_type: str
    src_asset_id: Optional[int] = None
    dst_asset_id: Optional[int] = None
    direction: Optional[str] = "forward"
    detail_json: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetLineageDeleteRequest(BaseModel):
    id: int

    model_config = ConfigDict(extra="forbid")


class PublicDatasetListRequest(BaseModel):
    page: Optional[int] = 1
    size: Optional[int] = 10
    dataset_id: Optional[int] = None
    name: Optional[str] = None
    dataset_type: Optional[str] = None


class PublicDatasetInfoRequest(BaseModel):
    id: int


class PublicDatasetVersionListRequest(BaseModel):
    id: int
    keyword: Optional[str] = None
    is_default_public: Optional[bool] = None
    is_current: Optional[bool] = None
    release_state: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class PublicDatasetVersionInfoRequest(BaseModel):
    id: int
    version_id: int


class PublicDatasetQueryCapabilitiesRequest(BaseModel):
    id: int
    asset_code: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class PublicDatasetQueryRequest(BaseModel):
    id: int
    operation: str
    asset_code: Optional[str] = None
    params: Optional[dict] = None

    model_config = ConfigDict(extra="allow")


class PublicDatasetVersionQueryCapabilitiesRequest(BaseModel):
    id: int
    version_id: int
    asset_code: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class PublicDatasetVersionQueryRequest(BaseModel):
    id: int
    version_id: int
    operation: str
    asset_code: Optional[str] = None
    params: Optional[dict] = None

    model_config = ConfigDict(extra="allow")


class DatasetKindRegistryOptionsRequest(DatasetContext):
    active_only: Optional[bool] = True

    model_config = ConfigDict(extra="forbid")


class DatasetKindRegistryListRequest(DatasetContext):
    page: Optional[int] = 1
    size: Optional[int] = 10
    keyword: Optional[str] = None
    code: Optional[str] = None
    base_code: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class DatasetKindRegistryInfoRequest(DatasetContext):
    id: int


class DatasetKindRegistryCreateRequest(DatasetContext):
    code: str
    base_code: str
    name: str
    description: Optional[str] = None
    is_active: Optional[bool] = True
    sort_order: Optional[int] = 0
    meta_json: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetKindRegistryUpdateRequest(DatasetContext):
    id: int
    code: Optional[str] = None
    base_code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    meta_json: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetKindRegistryDeleteRequest(DatasetContext):
    id: int


class AssetTypeRegistryOptionsRequest(DatasetContext):
    dataset_type: Optional[str] = None
    active_only: Optional[bool] = True

    model_config = ConfigDict(extra="forbid")


class AssetTypeRegistryListRequest(DatasetContext):
    page: Optional[int] = 1
    size: Optional[int] = 10
    keyword: Optional[str] = None
    code: Optional[str] = None
    base_code: Optional[str] = None
    dataset_type: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class AssetTypeRegistryInfoRequest(DatasetContext):
    id: int


class AssetTypeRegistryCreateRequest(DatasetContext):
    code: str
    base_code: str
    name: str
    description: Optional[str] = None
    allowed_dataset_types: Optional[List[str]] = None
    is_active: Optional[bool] = True
    sort_order: Optional[int] = 0
    meta_json: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class AssetTypeRegistryUpdateRequest(DatasetContext):
    id: int
    code: Optional[str] = None
    base_code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    allowed_dataset_types: Optional[List[str]] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    meta_json: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class AssetTypeRegistryDeleteRequest(DatasetContext):
    id: int


class AssetFileTypeRegistryOptionsRequest(DatasetContext):
    asset_type: Optional[str] = None
    active_only: Optional[bool] = True

    model_config = ConfigDict(extra="forbid")


class AssetFileTypeRegistryListRequest(DatasetContext):
    page: Optional[int] = 1
    size: Optional[int] = 10
    keyword: Optional[str] = None
    code: Optional[str] = None
    base_code: Optional[str] = None
    asset_type: Optional[str] = None
    file_format: Optional[str] = None
    file_role: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class AssetFileTypeRegistryInfoRequest(DatasetContext):
    id: int


class AssetFileTypeRegistryCreateRequest(DatasetContext):
    code: str
    base_code: str
    name: str
    description: Optional[str] = None
    supported_file_formats: List[str]
    file_role: str
    allowed_asset_types: Optional[List[str]] = None
    is_active: Optional[bool] = True
    sort_order: Optional[int] = 0
    meta_json: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class AssetFileTypeRegistryUpdateRequest(DatasetContext):
    id: int
    code: Optional[str] = None
    base_code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    supported_file_formats: Optional[List[str]] = None
    file_role: Optional[str] = None
    allowed_asset_types: Optional[List[str]] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    meta_json: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class AssetFileTypeRegistryDeleteRequest(DatasetContext):
    id: int


class DatasetStagingListRequest(DatasetContext):
    page: Optional[int] = 1
    size: Optional[int] = 10
    keyword: Optional[str] = None
    stage_status: Optional[str] = None
    dataset_type: Optional[str] = None
    source_mode: Optional[str] = None
    scan_root_id: Optional[int] = None
    view_mode: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetStagingInfoRequest(BaseModel):
    id: int


class DatasetStagingDeleteRequest(DatasetContext):
    id: int

    model_config = ConfigDict(extra="forbid")


class DatasetStagingRegisterRequest(DatasetContext):
    id: int
    name: Optional[str] = None
    dataset_type: Optional[str] = None
    remark: Optional[str] = None
    is_public: Optional[bool] = False
    dry_run: Optional[bool] = False
    keep_staging_file: Optional[bool] = True

    model_config = ConfigDict(extra="forbid")


class DatasetScanRootListRequest(DatasetContext):
    page: Optional[int] = 1
    size: Optional[int] = 20
    keyword: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class DatasetScanRootInfoRequest(DatasetContext):
    id: int

    model_config = ConfigDict(extra="forbid")


class DatasetScanRootCreateRequest(DatasetContext):
    name: str
    root_path: str
    description: Optional[str] = None
    scan_recursive: Optional[bool] = True
    include_hidden: Optional[bool] = False
    is_active: Optional[bool] = True
    auto_scan_enabled: Optional[bool] = False
    scan_interval_minutes: Optional[int] = 1440

    model_config = ConfigDict(extra="forbid")


class DatasetScanRootUpdateRequest(DatasetContext):
    id: int
    name: Optional[str] = None
    root_path: Optional[str] = None
    description: Optional[str] = None
    scan_recursive: Optional[bool] = None
    include_hidden: Optional[bool] = None
    is_active: Optional[bool] = None
    auto_scan_enabled: Optional[bool] = None
    scan_interval_minutes: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


class DatasetScanRootDeleteRequest(DatasetContext):
    id: int

    model_config = ConfigDict(extra="forbid")


class DatasetScanBrowseRequest(DatasetContext):
    path: Optional[str] = None
    show_hidden: Optional[bool] = False

    model_config = ConfigDict(extra="forbid")


class DatasetScanJobListRequest(DatasetContext):
    page: Optional[int] = 1
    size: Optional[int] = 20
    root_id: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


class DatasetScanRunRequest(DatasetContext):
    root_id: int

    model_config = ConfigDict(extra="forbid")


class DatasetRegistrationCandidateSourceFileRequest(BaseModel):
    staging_file_id: int
    source_role: Optional[str] = None
    asset_type: Optional[str] = None
    asset_file_type_code: Optional[str] = None
    file_role: Optional[str] = None
    is_primary: Optional[bool] = False
    is_required: Optional[bool] = True
    confidence: Optional[float] = None
    origin_type: Optional[str] = "user_supplied"
    sort_order: Optional[int] = 0
    meta_json: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetRegistrationCandidateListRequest(DatasetContext):
    page: Optional[int] = 1
    size: Optional[int] = 20
    keyword: Optional[str] = None
    dataset_type: Optional[str] = None
    registration_mode: Optional[str] = None
    source_kind: Optional[str] = None
    status: Optional[str] = None
    scan_root_id: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


class DatasetRegistrationCandidateInfoRequest(DatasetContext):
    id: int

    model_config = ConfigDict(extra="forbid")


class DatasetRegistrationCandidateFileListRequest(DatasetContext):
    candidate_id: int

    model_config = ConfigDict(extra="forbid")


class DatasetRegistrationCandidateFileUpdateRequest(DatasetContext):
    id: int
    source_role: Optional[str] = None
    asset_type: Optional[str] = None
    asset_file_type_code: Optional[str] = None
    file_role: Optional[str] = None
    is_primary: Optional[bool] = None
    is_required: Optional[bool] = None
    confidence: Optional[float] = None
    origin_type: Optional[str] = None
    sort_order: Optional[int] = None
    validation_status: Optional[str] = None
    meta_json: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetRegistrationCandidateCreateRequest(DatasetContext):
    candidate_name: str
    dataset_type: Optional[str] = None
    recipe_code: Optional[str] = None
    registration_mode: Optional[str] = "recipe_build"
    version_name: Optional[str] = None
    organism: Optional[str] = None
    reference_dataset_id: Optional[int] = None
    reference_version_id: Optional[int] = None
    source_kind: Optional[str] = None
    scan_root_id: Optional[int] = None
    items: List[DatasetRegistrationCandidateSourceFileRequest]
    meta_json: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetRegistrationCandidateUpdateRequest(DatasetContext):
    id: int
    candidate_name: Optional[str] = None
    dataset_type: Optional[str] = None
    recipe_code: Optional[str] = None
    registration_mode: Optional[str] = None
    version_name: Optional[str] = None
    organism: Optional[str] = None
    reference_dataset_id: Optional[int] = None
    reference_version_id: Optional[int] = None
    source_kind: Optional[str] = None
    scan_root_id: Optional[int] = None
    status: Optional[str] = None
    validation_status: Optional[str] = None
    build_status: Optional[str] = None
    registration_status: Optional[str] = None
    meta_json: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetRegistrationCandidateDeleteRequest(DatasetContext):
    id: int

    model_config = ConfigDict(extra="forbid")


class DatasetRegistrationCandidateRegisterRequest(DatasetContext):
    id: int
    dataset_name: Optional[str] = None
    remark: Optional[str] = None
    is_public: Optional[bool] = False
    activate_version: Optional[bool] = True

    model_config = ConfigDict(extra="forbid")
