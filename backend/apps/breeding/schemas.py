from typing import Optional, List

from pydantic import BaseModel, ConfigDict


class BreedingPageRequest(BaseModel):
    page: Optional[int] = 1
    size: Optional[int] = 10
    keyword: Optional[str] = None
    status: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class BreedingInfoRequest(BaseModel):
    id: int


class BreedingGermplasmImportCommitRequest(BaseModel):
    validation_token: str


class BreedingGermplasmImportBatchDeleteRequest(BaseModel):
    id: int


class BreedingGermplasmTaxonomySearchRequest(BaseModel):
    keyword: Optional[str] = None
    limit: Optional[int] = 20
    active_only: Optional[int] = 1
    with_germplasm_only: Optional[int] = 0


class BreedingGermplasmTaxonomySyncRequest(BaseModel):
    tax_id: Optional[int] = None
    keyword: Optional[str] = None
    limit: Optional[int] = 20
    active_only: Optional[int] = 1
    force_refresh: Optional[int] = 0


class BreedingGermplasmTaxonomyAuditRequest(BaseModel):
    tax_id: Optional[int] = None
    keyword: Optional[str] = None
    limit: Optional[int] = 20
    active_only: Optional[int] = 1


class BreedingGermplasmListRequest(BreedingPageRequest):
    taxonomy_tax_id: Optional[int] = None
    batch_id: Optional[int] = None


class BreedingGermplasmInfoRequest(BaseModel):
    accession_id: str
    taxonomy_tax_id: int


class BreedingGermplasmStatisticsRequest(BaseModel):
    taxonomy_tax_id: int
    batch_id: Optional[int] = None
    status: Optional[str] = "active"
    model_config = ConfigDict(extra="allow")


class BreedingGermplasmRelationshipRequest(BaseModel):
    taxonomy_tax_id: int
    accession_id_1: str
    accession_id_2: str
    batch_id: Optional[int] = None
    model_config = ConfigDict(extra="allow")


class BreedingGermplasmBatchRelationshipRequest(BaseModel):
    taxonomy_tax_id: int
    selected_nodes: list[str]
    include_internal: Optional[bool] = True
    include_external: Optional[bool] = True
    max_connections_per_node: Optional[int] = 30
    batch_id: Optional[int] = None
    model_config = ConfigDict(extra="allow")


class BreedingGermplasmImportBatchListRequest(BreedingPageRequest):
    taxonomy_tax_id: Optional[int] = None


class BreedingGermplasmSetPublicRequest(BaseModel):
    accession_id: str
    taxonomy_tax_id: int
    is_public: bool


class BreedingGermplasmBatchSetPublicRequest(BaseModel):
    id: int
    is_public: bool


class BreedingProgramListRequest(BreedingPageRequest):
    species_name: Optional[str] = None


class BreedingProgramCreateRequest(BaseModel):
    code: str
    name: str
    species_name: Optional[str] = None
    breeding_goal: Optional[str] = None
    start_year: Optional[int] = None
    status: Optional[str] = "active"
    owner_name: Optional[str] = None
    meta_json: Optional[str] = None


class BreedingProgramUpdateRequest(BreedingProgramCreateRequest):
    id: int


class BreedingMaterialListRequest(BreedingPageRequest):
    program_id: Optional[int] = None
    material_type: Optional[str] = None


class BreedingMaterialCreateRequest(BaseModel):
    program_id: int
    material_code: str
    material_name: str
    material_type: str
    generation_code: Optional[str] = None
    origin: Optional[str] = None
    germplasm_accession: Optional[str] = None
    germplasm_name: Optional[str] = None
    germplasm_source_file: Optional[str] = None
    status: Optional[str] = "active"
    is_check: Optional[int] = 0
    meta_json: Optional[str] = None
    remarks: Optional[str] = None


class BreedingMaterialUpdateRequest(BreedingMaterialCreateRequest):
    id: int


class BreedingTrialListRequest(BreedingPageRequest):
    program_id: Optional[int] = None
    trial_type: Optional[str] = None
    location_name: Optional[str] = None
    season_label: Optional[str] = None


class BreedingTrialCreateRequest(BaseModel):
    program_id: int
    trial_code: str
    trial_name: str
    trial_type: str
    objective: Optional[str] = None
    location_name: Optional[str] = None
    season_label: Optional[str] = None
    design_type: Optional[str] = None
    replicate_count: Optional[int] = None
    status: Optional[str] = "active"
    sowing_date: Optional[str] = None
    harvest_date: Optional[str] = None
    meta_json: Optional[str] = None
    remarks: Optional[str] = None


class BreedingTrialUpdateRequest(BreedingTrialCreateRequest):
    id: int


class BreedingPlotListRequest(BreedingPageRequest):
    program_id: Optional[int] = None
    trial_id: Optional[int] = None
    material_id: Optional[int] = None
    replicate_no: Optional[int] = None
    block_no: Optional[int] = None


class BreedingPlotCreateRequest(BaseModel):
    trial_id: int
    material_id: int
    plot_code: str
    replicate_no: Optional[int] = None
    block_no: Optional[int] = None
    row_no: Optional[int] = None
    col_no: Optional[int] = None
    treatment_code: Optional[str] = None
    area: Optional[float] = None
    plant_count_planned: Optional[int] = None
    plant_count_actual: Optional[int] = None
    status: Optional[str] = "active"
    meta_json: Optional[str] = None
    remarks: Optional[str] = None


class BreedingPlotUpdateRequest(BreedingPlotCreateRequest):
    id: int


class BreedingObservationListRequest(BreedingPageRequest):
    program_id: Optional[int] = None
    trial_id: Optional[int] = None
    plot_id: Optional[int] = None
    material_id: Optional[int] = None
    trait_code: Optional[str] = None
    qc_status: Optional[str] = None


class BreedingObservationCreateRequest(BaseModel):
    trial_id: int
    plot_id: Optional[int] = None
    material_id: Optional[int] = None
    observation_level: str
    trait_code: str
    trait_name: Optional[str] = None
    protocol_name: Optional[str] = None
    obs_value_num: Optional[float] = None
    obs_value_text: Optional[str] = None
    obs_value_score: Optional[str] = None
    obs_date: Optional[str] = None
    observer: Optional[str] = None
    qc_status: Optional[str] = "draft"
    source_dataset_id: Optional[int] = None
    source_version_id: Optional[int] = None
    source_asset_id: Optional[int] = None
    source_row_key: Optional[str] = None
    meta_json: Optional[str] = None
    remarks: Optional[str] = None


class BreedingObservationUpdateRequest(BreedingObservationCreateRequest):
    id: int


class BreedingBioSampleListRequest(BreedingPageRequest):
    program_id: Optional[int] = None
    material_id: Optional[int] = None
    plot_id: Optional[int] = None
    sample_type: Optional[str] = None
    organism: Optional[str] = None


class BreedingBioSampleCreateRequest(BaseModel):
    sample_code: str
    material_id: int
    plot_id: Optional[int] = None
    sample_type: Optional[str] = None
    organism: Optional[str] = None
    tissue_type: Optional[str] = None
    timepoint: Optional[str] = None
    treatment_label: Optional[str] = None
    collection_date: Optional[str] = None
    collector: Optional[str] = None
    storage_location: Optional[str] = None
    status: Optional[str] = "active"
    meta_json: Optional[str] = None
    remarks: Optional[str] = None


class BreedingBioSampleUpdateRequest(BreedingBioSampleCreateRequest):
    id: int


class BreedingAssayListRequest(BreedingPageRequest):
    program_id: Optional[int] = None
    biosample_id: Optional[int] = None
    assay_type: Optional[str] = None
    platform: Optional[str] = None
    library_strategy: Optional[str] = None
    instrument_model: Optional[str] = None


class BreedingAssayCreateRequest(BaseModel):
    assay_code: str
    biosample_id: int
    assay_type: str
    platform: Optional[str] = None
    vendor: Optional[str] = None
    library_strategy: Optional[str] = None
    library_source: Optional[str] = None
    library_selection: Optional[str] = None
    library_layout: Optional[str] = None
    instrument_model: Optional[str] = None
    read_length: Optional[int] = None
    run_date: Optional[str] = None
    status: Optional[str] = "active"
    meta_json: Optional[str] = None
    remarks: Optional[str] = None


class BreedingAssayUpdateRequest(BreedingAssayCreateRequest):
    id: int


class BreedingDataFileListRequest(BreedingPageRequest):
    program_id: Optional[int] = None
    assay_id: Optional[int] = None
    dataset_id: Optional[int] = None
    version_id: Optional[int] = None
    asset_id: Optional[int] = None
    source_mode: Optional[str] = None
    file_role: Optional[str] = None


class BreedingDataFileCreateRequest(BaseModel):
    assay_id: int
    source_mode: str
    dataset_id: Optional[int] = None
    version_id: Optional[int] = None
    asset_id: Optional[int] = None
    asset_file_id: Optional[int] = None
    file_role: str
    file_name: Optional[str] = None
    file_format: Optional[str] = None
    uri_snapshot: Optional[str] = None
    checksum_value: Optional[str] = None
    file_size: Optional[int] = None
    status: Optional[str] = "active"
    meta_json: Optional[str] = None
    remarks: Optional[str] = None


class BreedingDataFileUpdateRequest(BreedingDataFileCreateRequest):
    id: int


class BreedingDatasetSubjectLinkListRequest(BreedingPageRequest):
    dataset_id: Optional[int] = None
    version_id: Optional[int] = None
    asset_id: Optional[int] = None
    material_id: Optional[int] = None
    plot_id: Optional[int] = None
    biosample_id: Optional[int] = None
    role: Optional[str] = None
    mapping_status: Optional[str] = None


class BreedingDatasetSubjectLinkCreateRequest(BaseModel):
    dataset_id: int
    version_id: int
    asset_id: Optional[int] = None
    program_id: Optional[int] = None
    material_id: Optional[int] = None
    trial_id: Optional[int] = None
    plot_id: Optional[int] = None
    biosample_id: Optional[int] = None
    role: str
    mapping_status: Optional[str] = "draft"
    mapping_method: Optional[str] = "manual"
    confidence: Optional[str] = None
    is_primary: Optional[int] = 0
    note: Optional[str] = None


class BreedingDatasetSubjectLinkUpdateRequest(BreedingDatasetSubjectLinkCreateRequest):
    id: int


class BreedingDatasetAssayLinkListRequest(BreedingPageRequest):
    dataset_id: Optional[int] = None
    version_id: Optional[int] = None
    asset_id: Optional[int] = None
    assay_id: Optional[int] = None
    role: Optional[str] = None
    mapping_status: Optional[str] = None


class BreedingDatasetAssayLinkCreateRequest(BaseModel):
    dataset_id: int
    version_id: int
    asset_id: int
    assay_id: int
    role: str
    mapping_status: Optional[str] = "draft"
    mapping_method: Optional[str] = "manual"
    confidence: Optional[str] = None
    is_primary: Optional[int] = 0
    note: Optional[str] = None


class BreedingDatasetAssayLinkUpdateRequest(BreedingDatasetAssayLinkCreateRequest):
    id: int


class BreedingVariantSampleMapListRequest(BreedingPageRequest):
    dataset_id: Optional[int] = None
    version_id: Optional[int] = None
    asset_id: Optional[int] = None
    material_id: Optional[int] = None
    biosample_id: Optional[int] = None
    plot_id: Optional[int] = None
    mapping_status: Optional[str] = None


class BreedingVariantSampleMapCreateRequest(BaseModel):
    dataset_id: int
    version_id: int
    asset_id: int
    vcf_sample_name: str
    normalized_sample_name: Optional[str] = None
    sample_alias: Optional[str] = None
    material_id: Optional[int] = None
    biosample_id: Optional[int] = None
    plot_id: Optional[int] = None
    mapping_status: Optional[str] = "draft"
    mapping_method: Optional[str] = "manual"
    confidence: Optional[str] = None
    is_primary: Optional[int] = 0
    note: Optional[str] = None


class BreedingVariantSampleMapUpdateRequest(BreedingVariantSampleMapCreateRequest):
    id: int


class BreedingPhenotypeSubjectMapListRequest(BreedingPageRequest):
    dataset_id: Optional[int] = None
    version_id: Optional[int] = None
    asset_id: Optional[int] = None
    trial_id: Optional[int] = None
    plot_id: Optional[int] = None
    material_id: Optional[int] = None
    trait_code: Optional[str] = None
    mapping_status: Optional[str] = None


class BreedingPhenotypeSubjectMapCreateRequest(BaseModel):
    dataset_id: int
    version_id: int
    asset_id: int
    row_key: str
    trial_id: Optional[int] = None
    plot_id: Optional[int] = None
    material_id: Optional[int] = None
    trait_code: Optional[str] = None
    obs_date: Optional[str] = None
    mapping_status: Optional[str] = "draft"
    mapping_method: Optional[str] = "manual"
    confidence: Optional[str] = None
    is_primary: Optional[int] = 0
    note: Optional[str] = None


class BreedingPhenotypeSubjectMapUpdateRequest(BreedingPhenotypeSubjectMapCreateRequest):
    id: int


class MaterialOverviewDataset(BaseModel):
    dataset_id: int
    dataset_code: Optional[str] = None
    dataset_type: Optional[str] = None
    role: Optional[str] = None
    link_type: str  # "variant_sample_map" | "phenotype_subject_map" | "dataset_subject_link" | "dataset_assay_link"


class MaterialOverviewResponse(BaseModel):
    id: int
    material_code: str
    material_name: Optional[str] = None
    program_id: Optional[int] = None
    germplasm_accession: Optional[str] = None
    linked_dataset_count: int = 0
    linked_datasets: List[MaterialOverviewDataset] = []
    trial_count: int = 0
    trials: List[dict] = []
    observation_count: int = 0
    biosample_count: int = 0
    assay_count: int = 0


class ProgramDatasetsRequest(BaseModel):
    program_id: int
    dataset_type: Optional[str] = None


class LinkDatasetRequest(BaseModel):
    program_id: int
    dataset_id: int
    version_id: Optional[int] = None
    link_type: str
    role: Optional[str] = None
    material_id: Optional[int] = None
    note: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class LinkDatasetResponse(BaseModel):
    linked: bool
    dataset_id: int
    link_type: str
    link_id: Optional[int] = None
    message: Optional[str] = None


class VariantSampleSyncRequest(BaseModel):
    dataset_id: int
    version_id: int
    asset_id: int
    sample_names: List[str]


class ExpressionSampleMapRequest(BaseModel):
    dataset_id: int
    version_id: int
    asset_id: int
    sample_names: List[str]
