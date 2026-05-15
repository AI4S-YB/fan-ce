import { requestClient } from '#/api/request';

export interface PlatformSetupLock {
  lock_code: string;
  is_locked: number;
  reason?: string;
  required_action?: string;
  payload_json?: null | string;
  updated_at?: null | string;
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
  node_count: number;
  latest_job: null | PlatformSetupJob;
  lock: PlatformSetupLock;
}

export interface PlatformSetupJobStatusResponse extends PlatformSetupJob {
  setup_state: {
    lock: PlatformSetupLock;
    status: string;
    ready: boolean;
    node_count: number;
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

export async function startPlatformTaxonomyImportApi(data: {
  force_reinstall?: boolean;
  dump_path?: string | null;
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
