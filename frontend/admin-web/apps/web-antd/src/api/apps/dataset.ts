import type { AxiosProgressEvent } from 'axios';

import { requestClient } from '#/api/request';

export interface DatasetKindOption {
  id: number;
  code: string;
  base_code?: string;
  name: string;
  description?: string;
  is_active?: boolean;
  is_system?: boolean;
  sort_order?: number;
  meta_json?: string | null;
  label: string;
  value: string;
}

export interface AssetTypeOption {
  id: number;
  code: string;
  name: string;
  base_code?: string;
  description?: string;
  allowed_dataset_types?: string[];
  is_active?: boolean;
  is_system?: boolean;
  sort_order?: number;
  meta_json?: string | null;
  label: string;
  value: string;
}

export interface AssetFileTypeOption {
  id: number;
  code: string;
  name: string;
  base_code?: string;
  description?: string;
  supported_file_formats?: string[];
  file_role?: string;
  allowed_asset_types?: string[];
  is_active?: boolean;
  is_system?: boolean;
  sort_order?: number;
  meta_json?: string | null;
  label: string;
  value: string;
}

export interface DatasetOptionItem {
  id: number;
  name?: string;
  title?: string;
  dataset_code?: string;
  dataset_type?: string;
  lifecycle_state?: string;
  visibility?: string;
  version?: string;
  file_path?: string | null;
  file_format?: string;
}

export interface DatasetQueryAdapter {
  adapter?: string;
  display_name?: string;
  supported_operations?: string[];
  examples?: Record<string, { operation?: string; params?: Record<string, any> }>;
}

export interface DatasetFileInfo {
  id?: number;
  name?: string;
  path?: string;
  type?: string;
  data_type?: string;
  size?: number;
  meta_json?: string | null;
}

export interface DatasetWorkflowTaskItem {
  id: number;
  dataset_id?: number | null;
  task_type?: string;
  task_status?: string;
  from_state?: string;
  to_state?: string;
  operator_id?: number;
  detail?: string | null;
  detail_json?: Record<string, any> | null;
  is_async?: boolean;
  create_time?: number;
  finish_time?: number | null;
}

export interface DatasetPublishRecordItem {
  id: number;
  action?: string;
  visibility_before?: string;
  visibility_after?: string;
  lifecycle_before?: string;
  lifecycle_after?: string;
  operator_id?: number;
  note?: string | null;
  create_time?: number;
}

export interface AssetFileItem {
  id: number;
  dataset_asset_id: number;
  file_role?: string;
  file_name?: string;
  storage_uri?: string;
  local_path?: string | null;
  file_format?: string;
  mime_type?: string | null;
  checksum_type?: string | null;
  checksum_value?: string | null;
  file_size?: number | null;
  compress_type?: string | null;
  index_of_file_id?: number | null;
  status?: string;
  meta_json?: string | null;
  create_time?: number;
  update_time?: number;
}

export interface DatasetAssetItem {
  id: number;
  dataset_id: number;
  version_id: number;
  asset_code?: string;
  asset_name?: string;
  asset_type?: string;
  file_format?: string;
  query_engine?: string;
  storage_backend?: string;
  workflow_state?: string;
  status?: string;
  is_required?: boolean;
  is_query_entry?: boolean;
  display_order?: number;
  meta_json?: string | null;
  files: AssetFileItem[];
  create_time?: number;
  update_time?: number;
}

export interface DatasetVersionItem {
  id: number;
  dataset_id: number;
  version?: string;
  title?: string;
  dataset_type?: string;
  lifecycle_state?: string;
  visibility?: string;
  release_state?: string;
  file_path?: string | null;
  file_format?: string;
  query_engine?: string;
  validation_summary?: string | null;
  index_summary?: string | null;
  extra_json?: string | null;
  is_current?: boolean;
  is_published?: boolean;
  is_default_public?: boolean;
  create_time?: number;
  update_time?: number;
}

export interface DatasetVersionPublishRecordItem {
  id: number;
  dataset_id: number;
  version_id: number;
  version?: string;
  action?: string;
  visibility_before?: string;
  visibility_after?: string;
  lifecycle_before?: string;
  lifecycle_after?: string;
  operator_id?: number;
  note?: string | null;
  create_time?: number;
}

export interface DatasetLineageItem {
  id: number;
  dataset_id: number;
  src_dataset_id?: number | null;
  src_dataset_title?: string | null;
  src_dataset_type?: string | null;
  src_version_id?: number | null;
  src_version?: string | null;
  src_asset_id?: number | null;
  src_asset_code?: string | null;
  dst_dataset_id?: number | null;
  dst_dataset_title?: string | null;
  dst_dataset_type?: string | null;
  dst_version_id?: number | null;
  dst_version?: string | null;
  dst_asset_id?: number | null;
  dst_asset_code?: string | null;
  relation_type?: string;
  direction?: string;
  detail_json?: string | null;
  create_user_id?: number;
  create_time?: number;
}

export interface DatasetItem {
  id: number;
  dataset_code?: string;
  title?: string;
  name?: string;
  dataset_type?: string;
  dataset_kind?: Record<string, any> | null;
  lifecycle_state?: string;
  visibility?: string;
  version?: string;
  organism?: string;
  assembly?: string;
  file_format?: string;
  query_engine?: string;
  version_count?: number;
  query_adapter?: DatasetQueryAdapter | null;
  description_md?: string;
  create_time?: number;
  update_time?: number;
}

export interface DatasetDetailItem extends DatasetItem {
  remark?: string | null;
  file?: DatasetFileInfo | null;
  query_profile?: {
    file_format?: string;
    query_engine?: string;
    validation_summary?: string | null;
    index_summary?: string | null;
  } | null;
  assets: DatasetAssetItem[];
  query_entry_asset?: DatasetAssetItem | null;
  workflow_tasks: DatasetWorkflowTaskItem[];
  publish_records: DatasetPublishRecordItem[];
  current_version?: DatasetVersionItem | null;
  default_public_version?: DatasetVersionItem | null;
  published_version?: DatasetVersionItem | null;
}

export interface DatasetVersionDetail extends DatasetVersionItem {
  assets: DatasetAssetItem[];
  lineage: DatasetLineageItem[];
}

export interface DatasetListResult {
  total: number;
  dataList: DatasetItem[];
}

export interface DatasetVersionListResult {
  dataset_id: number;
  dataset_code?: string;
  dataset_type?: string;
  current_version?: DatasetVersionItem | null;
  default_public_version?: DatasetVersionItem | null;
  published_version?: DatasetVersionItem | null;
  items: DatasetVersionItem[];
}

export interface DatasetVersionPublishRecordListResult {
  dataset_id?: number | null;
  version_id?: number | null;
  items: DatasetVersionPublishRecordItem[];
}

export interface DatasetVersionQueryCapabilitiesResult {
  dataset_id: number;
  version_id: number;
  dataset_code?: string;
  version?: string;
  dataset_type?: string;
  file_path?: string | null;
  file_access?: {
    exists_on_server?: boolean;
    size?: number | null;
  } | null;
  query_entry_asset?: DatasetAssetItem | null;
  assets?: DatasetAssetItem[];
  query_profile?: {
    file_format?: string;
    query_engine?: string;
    validation_summary?: string | null;
    index_summary?: string | null;
  } | null;
  query_adapter?: DatasetQueryAdapter | null;
  available_adapters?: Array<{
    adapter?: string;
    display_name?: string;
    supported_dataset_types?: string[];
    supported_file_formats?: string[];
  }>;
}

export interface DatasetVersionQueryExecuteResult {
  adapter?: string;
  operation?: string;
  dataset_id?: number;
  version?: string;
  query_adapter?: DatasetQueryAdapter | null;
  data?: Record<string, any>;
  [key: string]: any;
}

export interface OmicsGeneSearchResult {
  total?: number;
  page?: number;
  page_size?: number;
  total_pages?: number;
  genes?: Array<Record<string, any>>;
  query_info?: Record<string, any>;
}

export interface OmicsTranscriptListResult {
  total?: number;
  page?: number;
  page_size?: number;
  total_pages?: number;
  transcripts?: Array<Record<string, any>>;
}

export interface OmicsGeneInfoResult {
  gene_info?: Record<string, any>;
  transcript_info?: Record<string, any>;
  sequences?: Record<string, string>;
}

export interface OmicsTranscriptInfoResult {
  transcript_info?: Record<string, any>;
  sequences?: Record<string, string>;
}

export interface DatasetStagingItem {
  id: number;
  staging_code: string;
  source_name?: string;
  file_name?: string;
  storage_uri?: string;
  local_path?: string | null;
  file_format?: string;
  file_size?: number;
  dataset_type?: string;
  stage_status?: string;
  linked_dataset_id?: number | null;
  create_user_id?: number;
  meta_json?: string | null;
  create_time?: number;
  update_time?: number;
}

export interface DatasetStagingListResult {
  total: number;
  dataList: DatasetStagingItem[];
}

// --- Directory Browse ---

export interface BrowseEntryItem {
  name: string;
  path: string;
  is_dir: boolean;
  modified_time?: number;
}

export interface BrowseFileItem {
  name: string;
  path: string;
  is_dir: false;
  size: number;
  format: string;
  modified_time: number;
}

export interface BrowseResult {
  browse_root: string;
  current_path: string;
  parent_path?: string | null;
  entries: BrowseEntryItem[];
  files: BrowseFileItem[];
  warning?: string;
}

// --- Directory View ---

export interface DirectoryTreeNode {
  name: string;
  path: string;
  is_dir: boolean;
  file_count?: number;
  size?: number;
  format?: string;
  staging_id?: number;
  children: DirectoryTreeNode[];
}

export interface ScanRootTree {
  scan_root_id: number;
  root_path: string;
  root_name: string;
  children: DirectoryTreeNode[];
}

export interface StagingDirectoryView {
  trees: ScanRootTree[];
  orphan_files: DatasetStagingItem[];
}

// --- Scan Job ---

export interface ScanJobItem {
  id: number;
  root_id: number;
  job_code: string;
  status: string;
  scanned_dir_count?: number;
  scanned_file_count?: number;
  staged_file_count?: number;
  skipped_file_count?: number;
  changed_file_count?: number;
  missing_file_count?: number;
  skipped_registered_count?: number;
  error_message?: string | null;
  started_at?: number | null;
  finished_at?: number | null;
}

// --- Registration Candidate ---

export interface CandidateCreateItem {
  staging_file_id: number;
  is_primary: boolean;
}

export interface CandidateCreateRequest {
  candidate_name: string;
  dataset_type: string;
  registration_mode: 'prebuilt' | 'hybrid' | 'recipe_build';
  version_name?: string;
  organism?: string;
  assembly?: string;
  scan_root_id?: number;
  items: CandidateCreateItem[];
}

export interface RegisterCandidateRequest {
  dataset_name?: string;
  remark?: string;
  is_public?: boolean;
  project_id?: number;
  activate_version?: boolean;
}

export interface RegistryListResult<T> {
  total: number;
  dataList: T[];
}

const pre = '/admin/dataset';

export async function getDatasetListApi(data: Record<string, any>) {
  return requestClient.post<DatasetListResult>(`${pre}/list`, data);
}

export async function getDatasetOptionsApi(data: Record<string, any>) {
  return requestClient.post<DatasetOptionItem[]>(`${pre}/options`, data);
}

export async function getDatasetInfoApi(data: { id: number }) {
  return requestClient.post<DatasetDetailItem>(`${pre}/info`, data);
}

export async function deleteDatasetApi(data: { id: number }) {
  return requestClient.post(`${pre}/delete`, data);
}

export async function updateDatasetApi(data: { id: number; title?: string; version?: string; description_md?: string }) {
  return requestClient.post<DatasetDetailItem>(`${pre}/update`, data);
}

export async function getDatasetVersionListApi(data: { dataset_id: number }) {
  return requestClient.post<DatasetVersionListResult>(`${pre}/version/list`, data);
}

export async function getDatasetVersionInfoApi(data: { id: number }) {
  return requestClient.post<DatasetVersionDetail>(`${pre}/version/info`, data);
}

export async function getDatasetVersionQueryCapabilitiesApi(data: { id: number; asset_code?: string }) {
  return requestClient.post<DatasetVersionQueryCapabilitiesResult>(`${pre}/version/query/capabilities`, data);
}

export async function executeDatasetVersionQueryApi(data: {
  id: number;
  operation: string;
  asset_code?: string;
  params?: Record<string, any>;
}) {
  return requestClient.post<DatasetVersionQueryExecuteResult>(`${pre}/version/query/execute`, data);
}

export async function createDatasetVersionApi(data: Record<string, any>) {
  return requestClient.post<DatasetVersionItem>(`${pre}/version/create`, data);
}

export async function activateDatasetVersionApi(data: { id: number; note?: string }) {
  return requestClient.post<DatasetVersionItem>(`${pre}/version/activate`, data);
}

export async function releaseDatasetVersionApi(data: { id: number; note?: string }) {
  return requestClient.post<DatasetVersionItem>(`${pre}/version/release`, data);
}

export async function withdrawDatasetVersionApi(data: { id: number; note?: string }) {
  return requestClient.post<DatasetVersionItem>(`${pre}/version/withdraw`, data);
}

export async function setDefaultPublicDatasetVersionApi(data: { id: number; note?: string }) {
  return requestClient.post<DatasetVersionItem>(`${pre}/version/set-default-public`, data);
}

export async function getDatasetVersionPublishRecordsApi(data: Record<string, any>) {
  return requestClient.post<DatasetVersionPublishRecordListResult>(`${pre}/version/publish/records`, data);
}

export async function getDatasetKindOptionsApi() {
  return requestClient.post<DatasetKindOption[]>(`${pre}/registry/kind/options`, {});
}

export async function getDatasetKindRegistryListApi(data: Record<string, any>) {
  return requestClient.post<RegistryListResult<DatasetKindOption>>(`${pre}/registry/kind/list`, data);
}

export async function createDatasetKindRegistryApi(data: Record<string, any>) {
  return requestClient.post<DatasetKindOption>(`${pre}/registry/kind/create`, data);
}

export async function updateDatasetKindRegistryApi(data: Record<string, any>) {
  return requestClient.post<DatasetKindOption>(`${pre}/registry/kind/update`, data);
}

export async function deleteDatasetKindRegistryApi(data: { id: number }) {
  return requestClient.post(`${pre}/registry/kind/delete`, data);
}

export async function getAssetTypeOptionsApi(data: { dataset_type?: string; active_only?: boolean }) {
  return requestClient.post<AssetTypeOption[]>(`${pre}/registry/asset-type/options`, data);
}

export async function getAssetFileTypeOptionsApi(data: { asset_type?: string; active_only?: boolean }) {
  return requestClient.post<AssetFileTypeOption[]>(`${pre}/registry/asset-file-type/options`, data);
}

export async function getAssetTypeRegistryListApi(data: Record<string, any>) {
  return requestClient.post<RegistryListResult<AssetTypeOption>>(`${pre}/registry/asset-type/list`, data);
}

export async function createAssetTypeRegistryApi(data: Record<string, any>) {
  return requestClient.post<AssetTypeOption>(`${pre}/registry/asset-type/create`, data);
}

export async function updateAssetTypeRegistryApi(data: Record<string, any>) {
  return requestClient.post<AssetTypeOption>(`${pre}/registry/asset-type/update`, data);
}

export async function deleteAssetTypeRegistryApi(data: { id: number }) {
  return requestClient.post(`${pre}/registry/asset-type/delete`, data);
}

export async function getAssetFileTypeRegistryListApi(data: Record<string, any>) {
  return requestClient.post<RegistryListResult<AssetFileTypeOption>>(`${pre}/registry/asset-file-type/list`, data);
}

export async function createAssetFileTypeRegistryApi(data: Record<string, any>) {
  return requestClient.post<AssetFileTypeOption>(
    `${pre}/registry/asset-file-type/create`,
    data,
  );
}

export async function updateAssetFileTypeRegistryApi(data: Record<string, any>) {
  return requestClient.post<AssetFileTypeOption>(
    `${pre}/registry/asset-file-type/update`,
    data,
  );
}

export async function deleteAssetFileTypeRegistryApi(data: { id: number }) {
  return requestClient.post(`${pre}/registry/asset-file-type/delete`, data);
}

export async function uploadDatasetStagingApi(
  data: any,
  onUploadProgress?: (progressEvent: AxiosProgressEvent) => void,
) {
  return requestClient.upload(`${pre}/staging/upload`, data, { onUploadProgress });
}

export async function getDatasetStagingListApi(data: Record<string, any>) {
  return requestClient.post<DatasetStagingListResult>(`${pre}/staging/list`, data);
}

export async function registerDatasetFromStagingApi(data: Record<string, any>) {
  return requestClient.post<DatasetItem>(`${pre}/staging/register`, data);
}

export async function deleteDatasetStagingApi(data: { id: number }) {
  return requestClient.post(`${pre}/staging/delete`, data);
}

export async function createDatasetAssetApi(data: Record<string, any>) {
  return requestClient.post<DatasetAssetItem>(`${pre}/asset/create`, data);
}

export async function updateDatasetAssetApi(data: Record<string, any>) {
  return requestClient.post<DatasetAssetItem>(`${pre}/asset/update`, data);
}

export async function deleteDatasetAssetApi(data: { id: number }) {
  return requestClient.post(`${pre}/asset/delete`, data);
}

export async function registerAssetFileApi(data: Record<string, any>) {
  return requestClient.post<AssetFileItem>(`${pre}/asset/file/register`, data);
}

export async function updateAssetFileApi(data: Record<string, any>) {
  return requestClient.post<AssetFileItem>(`${pre}/asset/file/update`, data);
}

export async function deleteAssetFileApi(data: { id: number }) {
  return requestClient.post(`${pre}/asset/file/delete`, data);
}

export async function getDatasetLineageListApi(data: Record<string, any>) {
  return requestClient.post<{ dataset_id?: number; version_id?: number; items: DatasetLineageItem[] }>(
    `${pre}/lineage/list`,
    data,
  );
}

export async function createDatasetLineageApi(data: Record<string, any>) {
  return requestClient.post<DatasetLineageItem>(`${pre}/lineage/create`, data);
}

export async function deleteDatasetLineageApi(data: { id: number }) {
  return requestClient.post(`${pre}/lineage/delete`, data);
}

export async function validateDatasetApi(data: { id: number; detail?: string }) {
  return requestClient.post(`${pre}/ingest/validate`, data);
}

export async function indexDatasetApi(data: { id: number; detail?: string }) {
  return requestClient.post(`${pre}/ingest/index`, data);
}

export async function runDatasetPipelineApi(data: { id: number; detail?: string }) {
  return requestClient.post(`${pre}/ingest/pipeline`, data);
}

export async function submitDatasetIngestTaskApi(data: {
  action: 'index' | 'pipeline' | 'validate';
  id?: number;
  file_path?: string;
  dataset_type?: string;
  detail?: string;
  output_file_path?: string;
  persist_result?: boolean;
  run_validate?: boolean;
  run_index?: boolean;
}) {
  return requestClient.post<DatasetWorkflowTaskItem>(`${pre}/ingest/task/submit`, data);
}

export async function getDatasetWorkflowTaskInfoApi(data: { id: number }) {
  return requestClient.post<DatasetWorkflowTaskItem>(`${pre}/ingest/task/info`, data);
}

export async function retryDatasetIngestTaskApi(data: { id: number }) {
  return requestClient.post<DatasetWorkflowTaskItem>(`${pre}/ingest/task/retry`, data);
}

export async function publishDatasetApi(data: { id: number; note?: string }) {
  return requestClient.post<DatasetItem>(`${pre}/publish`, data);
}

export async function unpublishDatasetApi(data: { id: number; note?: string }) {
  return requestClient.post<DatasetItem>(`${pre}/unpublish`, data);
}

export async function searchOmicsGenomeGenesApi(data: Record<string, any>) {
  return requestClient.post<OmicsGeneSearchResult>('/omics/gene/search', data);
}

export async function listOmicsGenomeGenesApi(data: Record<string, any>) {
  return requestClient.post<OmicsGeneSearchResult>('/omics/gene/list', data);
}

export async function listOmicsGenomeTranscriptsApi(data: Record<string, any>) {
  return requestClient.post<OmicsTranscriptListResult>('/omics/gene/transcript/list', data);
}

export async function getOmicsGenomeGeneInfoApi(data: Record<string, any>) {
  return requestClient.post<OmicsGeneInfoResult>('/omics/gene/info', data);
}

export async function getOmicsGenomeTranscriptInfoApi(data: Record<string, any>) {
  return requestClient.post<OmicsTranscriptInfoResult>('/omics/gene/transcript/info', data);
}

// --- Browse ---
export async function browseScanRootPathApi(data: { path?: string }) {
  return requestClient.post<BrowseResult>(`${pre}/staging/scan-root/browse`, data);
}

// --- Directory View ---
export async function getStagingDirectoryViewApi(data: {
  scan_root_id?: number;
  dataset_type?: string;
  source_mode?: string;
  keyword?: string;
}) {
  return requestClient.post<StagingDirectoryView>(`${pre}/staging/list`, {
    ...data,
    view_mode: 'directory',
  });
}

// --- Candidate ---
export async function createRegistrationCandidateApi(data: CandidateCreateRequest) {
  return requestClient.post(`${pre}/candidate/create`, data);
}

export async function registerCandidateApi(candidateId: number, data: RegisterCandidateRequest) {
  return requestClient.post(`${pre}/candidate/register`, { id: candidateId, ...data });
}
