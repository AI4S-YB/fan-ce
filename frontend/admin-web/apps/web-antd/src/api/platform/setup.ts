import { requestClient } from '#/api/request';

export interface PlatformSetupLock {
  lock_code: string;
  is_locked: number;
  reason?: string;
  required_action?: string;
  payload_json?: null | string;
  updated_at?: null | string;
}

export interface PlatformSetupPackage {
  id: number;
  package_code: string;
  package_type: string;
  package_name: string;
  source: string;
  source_version?: null | string;
  storage_path: string;
  file_size?: null | number;
  sha256?: null | string;
  manifest_json?: null | string;
  status: string;
  created_by?: null | number;
  created_at?: null | string;
  updated_at?: null | string;
}

export interface PlatformSetupSnapshot {
  id: number;
  source_name: string;
  source_version?: null | string;
  archive_path?: null | string;
  extracted_path?: null | string;
  node_count?: number;
  name_count?: number;
  notes?: null | string;
  loaded_at?: null | string;
}

export interface PlatformSetupJob {
  id: number;
  job_type: string;
  package_id?: null | number;
  status: string;
  stage?: null | string;
  progress_percent?: number;
  processed_count?: null | number;
  total_count?: null | number;
  message?: null | string;
  error_message?: null | string;
  result_json?: null | string;
  created_by?: null | number;
  started_at?: null | string;
  finished_at?: null | string;
  created_at?: null | string;
  updated_at?: null | string;
}

export interface PlatformSetupStatusResponse {
  taxonomy_ready: boolean;
  taxonomy_status: string;
  locks: PlatformSetupLock[];
}

export interface PlatformSetupCurrentResponse {
  ready: boolean;
  status: string;
  current_package: null | PlatformSetupPackage;
  current_snapshot: null | PlatformSetupSnapshot;
  latest_job: null | PlatformSetupJob;
  lock: PlatformSetupLock;
}

export interface PlatformSetupPackagesResponse {
  items: PlatformSetupPackage[];
  recommended_package: null | PlatformSetupPackage;
}

export interface PlatformSetupJobStatusResponse extends PlatformSetupJob {
  setup_state: {
    lock: PlatformSetupLock;
    status: string;
    ready: boolean;
    package: null | PlatformSetupPackage;
    job: null | PlatformSetupJob;
    snapshot: null | PlatformSetupSnapshot;
  };
}

function normalizeJobStatusResponse(
  data: PlatformSetupJobStatusResponse | Record<string, any> | null | undefined,
) {
  if (!data || typeof data !== 'object' || !('id' in data)) {
    return null;
  }
  return data as PlatformSetupJobStatusResponse;
}

export async function getPlatformSetupStatusApi() {
  return requestClient.get<PlatformSetupStatusResponse>(
    '/platform/setup/status',
  );
}

export async function getPlatformTaxonomyCurrentApi() {
  return requestClient.get<PlatformSetupCurrentResponse>(
    '/platform/setup/taxonomy/current',
  );
}

export async function getPlatformTaxonomyPackagesApi() {
  return requestClient.get<PlatformSetupPackagesResponse>(
    '/platform/setup/taxonomy/packages',
  );
}

export async function registerPlatformTaxonomyBuiltinPackageApi(data: {
  package_code: string;
  package_name: string;
  package_type: string;
  storage_path: string;
  source?: string;
  source_version?: string;
  sha256?: string;
  manifest_json?: string;
  file_size?: number;
  status?: string;
}) {
  return requestClient.post<PlatformSetupPackage>(
    '/platform/setup/taxonomy/package/register-builtin',
    data,
  );
}

export async function startPlatformTaxonomyImportApi(data: {
  package_id: number;
  force_reinstall?: boolean;
}) {
  return requestClient.post<PlatformSetupJob>(
    '/platform/setup/taxonomy/import/start',
    data,
  );
}

export async function getPlatformTaxonomyImportStatusApi(jobId?: number) {
  const data = await requestClient.get<
    PlatformSetupJobStatusResponse | Record<string, any>
  >('/platform/setup/taxonomy/import/status', {
    params: jobId ? { job_id: jobId } : {},
  });
  return normalizeJobStatusResponse(data);
}
