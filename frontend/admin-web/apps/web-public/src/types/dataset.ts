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
  query_entry_asset?: { id: number; asset_code?: string; asset_name?: string } | null;
  primary_file?: { id: number; name?: string; size?: number; format?: string } | null;
  assets?: PublicAssetItem[];
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
  src_dataset_code?: string;
  src_version?: string;
  dst_dataset_id?: number;
  dst_dataset_title?: string;
  dst_dataset_type?: string;
  dst_dataset_code?: string;
  dst_version?: string;
}

export interface QueryCapabilities {
  operations?: string[];
  filter_options?: Record<string, string[]>;
  query_adapter?: {
    examples?: Record<string, unknown>;
  };
}

export interface QueryResult {
  rows?: Record<string, unknown>[];
  items?: Record<string, unknown>[];
  total?: number;
  download_url?: string;
  // variant adapter returns wrapped data
  data?: {
    count?: number;
    size?: number;
    preview?: string;
    sample_count?: number;
    samples?: string[];
    download_url?: string;
    [key: string]: unknown;
  };
  // variant adapter top-level fields
  count?: number;
  preview?: string;
  adapter?: string;
  operation?: string;
  [key: string]: unknown;
}
