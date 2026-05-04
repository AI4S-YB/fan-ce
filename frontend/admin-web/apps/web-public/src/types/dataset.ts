export interface PublicDatasetItem {
  id: number;
  dataset_code?: string;
  title?: string;
  name?: string;
  dataset_type?: string;
  organism?: string;
  version?: string;
  lifecycle_state?: string;
  visibility?: string;
  description_md?: string;
  extra_json?: string;
}

export interface PublicDatasetDetail extends PublicDatasetItem {
  query_profile?: { file_format?: string; query_engine?: string };
  query_entry_asset?: { id: number; asset_code?: string; asset_name?: string };
  assets?: PublicAssetItem[];
  current_version?: { id: number; version?: string; title?: string };
  default_public_version?: { id: number; version?: string; title?: string };
  version_count?: number;
  file?: { id: number; name?: string; path?: string; size?: number; type?: string };
}

export interface PublicAssetItem {
  id: number;
  asset_code?: string;
  asset_name?: string;
  asset_type?: string;
  file_format?: string;
  query_engine?: string;
  is_required?: boolean;
  is_query_entry?: boolean;
  files?: PublicAssetFileItem[];
}

export interface PublicAssetFileItem {
  id: number;
  file_role?: string;
  file_name?: string;
  file_format?: string;
  storage_uri?: string;
  local_path?: string;
  file_size?: number;
}

export interface PublicLineageItem {
  id: number;
  relation_type?: string;
  direction?: string;
  src_dataset_id?: number;
  src_dataset_title?: string;
  src_dataset_type?: string;
  src_version?: string;
  dst_dataset_id?: number;
  dst_dataset_title?: string;
  dst_dataset_type?: string;
  dst_version?: string;
}

export interface QueryCapabilities {
  operations?: string[];
  filter_options?: Record<string, string[]>;
}

export interface QueryResult {
  rows?: Record<string, unknown>[];
  items?: Record<string, unknown>[];
  total?: number;
  download_url?: string;
}
