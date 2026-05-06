/**
 * 种质资源相关类型定义
 */

/**
 * 种质资源列表项接口
 */
export interface GermplasmItem {
  id: string;
  record_id?: number;
  accession_id?: string;
  display_name?: string;
  english_name?: null | string;
  taxonomy_tax_id?: number;
  father_accession?: null | string;
  mother_accession?: null | string;
  status?: string;
  is_public?: boolean;
  batch_id?: number;
  batch_code?: null | string;
  source_filename?: null | string;
  attributes: Record<string, any>;
  field_schema?: GermplasmFieldSchemaItem[];
  taxonomy?: {
    common_name?: null | string;
    lineage?: null | string;
    rank?: null | string;
    scientific_name?: null | string;
    tax_id: number;
  };
  breeding_summary?: {
    breeding_material_codes: string[];
    breeding_material_count: number;
    breeding_material_names: string[];
    breeding_program_count: number;
    breeding_program_ids: number[];
  };
}

/**
 * 种质资源详情接口
 */
export interface GermplasmDetail {
  accession_id?: string;
  attributes: Record<string, any>;
  audit?: {
    batch_code?: null | string;
    batch_id?: number;
    created_at?: null | string;
    source_file_path?: null | string;
    source_filename?: null | string;
    source_row_no?: null | number;
    updated_at?: null | string;
  };
  breeding_usage?: {
    breeding_material_codes: string[];
    breeding_material_count: number;
    breeding_material_names: string[];
    breeding_program_count: number;
    breeding_program_ids: number[];
  };
  english_name?: null | string;
  display_name?: string;
  father_name_snapshot?: null | string;
  father_accession?: null | string;
  field_schema?: GermplasmFieldSchemaItem[];
  id: string;
  lineage_summary?: {
    child_count: number;
    children: Array<{
      child_accession: string;
      parent_role: string;
    }>;
    parent_count: number;
    parents: Array<{
      parent_accession: string;
      parent_role: string;
    }>;
  };
  mother_name_snapshot?: null | string;
  mother_accession?: null | string;
  record_id?: number;
  status?: string;
  taxonomy?: {
    common_name?: null | string;
    lineage?: null | string;
    rank?: null | string;
    scientific_name?: null | string;
    tax_id: number;
  };
}

/**
 * 列表查询参数接口
 */
export interface GermplasmListParams {
  page?: number;
  size?: number;
  taxonomy_tax_id?: number;
  batch_id?: number;
  status?: string;
  keyword?: string;
}

export interface GermplasmTaxonomyOption {
  tax_id: number;
  scientific_name?: null | string;
  common_name?: null | string;
  rank?: null | string;
  lineage?: null | string;
  source?: null | string;
  last_sync_time?: null | string;
  germplasm_count: number;
}

export interface GermplasmTaxonomyAuditItem {
  tax_id: number;
  status: 'error' | 'matched' | 'mismatch' | 'not_found';
  germplasm_count: number;
  local: {
    common_name?: null | string;
    last_sync_time?: null | string;
    lineage?: null | string;
    parent_tax_id?: null | number;
    rank?: null | string;
    scientific_name?: null | string;
    source?: null | string;
  };
  remote?: null | {
    common_name?: null | string;
    last_sync_time?: null | string;
    lineage?: null | string;
    parent_tax_id?: null | number;
    rank?: null | string;
    scientific_name?: null | string;
    source?: null | string;
  };
  mismatches: Array<{
    field: string;
    local_value?: null | number | string;
    remote_value?: null | number | string;
  }>;
  message?: null | string;
}

export interface GermplasmTaxonomyAuditResult {
  items: GermplasmTaxonomyAuditItem[];
  total: number;
  summary: {
    error: number;
    matched: number;
    mismatch: number;
    not_found: number;
  };
  source_mode: 'audit';
}

export interface GermplasmValidationIssue {
  row_no: number;
  column_name: string;
  error_code: string;
  message: string;
}

export interface GermplasmFieldSchemaItem {
  field_key: string;
  field_label: string;
  source_header: string;
  display_order: number;
  data_type: string;
  is_builtin: number;
  is_dynamic: number;
}

export interface GermplasmImportValidationResult {
  validation_token: string;
  status: string;
  template_profile: string;
  taxonomy: GermplasmTaxonomyOption & {
    lineages?: null | string;
  };
  source_filename: string;
  summary: {
    error_rows: number;
    passed: boolean;
    taxonomy_tax_id: number;
    template_profile: string;
    total_rows: number;
    valid_rows: number;
    warning_rows: number;
  };
  errors: GermplasmValidationIssue[];
  warnings: GermplasmValidationIssue[];
  preview_rows: Array<Record<string, any>>;
  builtin_fields?: GermplasmFieldSchemaItem[];
  dynamic_fields?: GermplasmFieldSchemaItem[];
  field_schema_preview?: GermplasmFieldSchemaItem[];
}

export interface GermplasmImportCommitResult {
  batch_id: number;
  batch_code: string;
  imported_count: number;
  lineage_edge_count?: number;
  validation_token: string;
  status: string;
}

export interface GermplasmImportBatchDeleteResult {
  batch_id: number;
  batch_code: string;
  deleted_germplasm_count: number;
  deleted_lineage_count: number;
  status: string;
}

export interface GermplasmImportBatchItem {
  id: number;
  batch_code: string;
  template_profile: string;
  taxonomy_tax_id: number;
  taxonomy?: GermplasmTaxonomyOption;
  source_filename?: null | string;
  source_file_path?: null | string;
  status: string;
  total_rows: number;
  valid_rows: number;
  error_rows: number;
  warning_rows: number;
  is_public?: boolean;
  created_by?: null | number;
  updated_by?: null | number;
  created_at?: null | string;
  updated_at?: null | string;
}

export interface GermplasmImportBatchDetail extends GermplasmImportBatchItem {
  field_schema?: GermplasmFieldSchemaItem[];
  validation_report?: {
    errors?: GermplasmValidationIssue[];
    summary?: Record<string, any>;
    warnings?: GermplasmValidationIssue[];
  };
}

export interface GermplasmGraphNode {
  id: string;
  label?: string;
  degree?: number;
  selected?: boolean;
  attributes?: Record<string, any>;
}

export interface GermplasmGraphEdge {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  weight?: number;
  created_at?: null | string;
}

export interface GermplasmStatisticsResult {
  taxonomy_tax_id: number;
  batch_id?: null | number;
  node_count: number;
  edge_count: number;
  germplasm_record_count: number;
  connected_components: number;
  is_connected: boolean;
  average_degree: number;
  max_degree: number;
  min_degree: number;
  role_counts?: Record<string, number>;
  top_hubs?: Array<{
    accession_id: string;
    degree: number;
    display_name?: null | string;
  }>;
  metadata?: {
    batch?: null | {
      batch_code?: null | string;
      created_at?: null | string;
      id: number;
      source_filename?: null | string;
      updated_at?: null | string;
    };
    generated_at?: string;
    source_model?: string;
    taxonomy?: {
      common_name?: null | string;
      rank?: null | string;
      scientific_name?: null | string;
      tax_id: number;
    };
  };
}

export interface GermplasmRelationshipResult {
  node1: string;
  node2: string;
  exists: boolean;
  relationship_type: string;
  relationship_direction?: null | string;
  weight: number;
  path_nodes?: null | string[];
  shared_parents?: Array<{
    parent_accession: string;
    roles: string[];
  }>;
  shared_children?: Array<{
    child_accession: string;
  }>;
  direct_edges?: Array<{
    child_accession: string;
    created_at?: null | string;
    parent_accession: string;
    parent_role: string;
  }>;
  node_snapshots?: Record<
    string,
    {
      display_name?: null | string;
      english_name?: null | string;
    }
  >;
  generated_at?: string;
}

export interface GermplasmBatchRelationshipResult {
  nodes: GermplasmGraphNode[];
  edges: GermplasmGraphEdge[];
  summary?: {
    edge_count: number;
    include_external: boolean;
    include_internal: boolean;
    max_connections_per_node: number;
    node_count: number;
    selected_node_count: number;
    selected_nodes: string[];
  };
}

/**
 * 列表响应接口
 */
export interface GermplasmListResponse {
  code: number;
  msg: string;
  data: {
    items: GermplasmItem[];
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

/**
 * 详情响应接口
 */
export interface GermplasmDetailResponse {
  code: number;
  msg: string;
  data: GermplasmDetail;
}

/**
 * 动态列配置接口
 */
export interface DynamicColumnConfig {
  dataIndex: string;
  title: string;
  type?: 'date' | 'number' | 'text';
  width?: number;
}
