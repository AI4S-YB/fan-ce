import { requestClient } from '#/api/request';

export interface BreedingListResult<T> {
  items: T[];
  total: number;
}

export interface BreedingProgramItem {
  id: number;
  code: string;
  name: string;
  species_name?: string | null;
  breeding_goal?: string | null;
  start_year?: number | null;
  status?: string | null;
  owner_name?: string | null;
  meta_json?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  summary_counts?: {
    materials: number;
    trials: number;
    plots: number;
    observations: number;
    biosamples: number;
    assays: number;
    data_files: number;
  };
  preview_summary?: {
    materials: Array<{
      material_code: string;
      material_name: string;
      is_check: number;
    }>;
    traits: Array<{
      trait_code: string;
      trait_name: string;
      count: number;
    }>;
    assay_types: Array<{
      assay_type: string;
      count: number;
    }>;
  };
}

export interface BreedingProgramListParams {
  page?: number;
  size?: number;
  keyword?: string;
  status?: string;
  species_name?: string;
}

export interface BreedingProgramOverview {
  program: BreedingProgramItem;
  counts: {
    materials: number;
    trials: number;
    plots: number;
    observations: number;
    biosamples: number;
    assays: number;
    data_files: number;
    dataset_subject_links: number;
    dataset_assay_links: number;
    dataset_links: number;
  };
}

export interface BreedingMaterialItem {
  id: number;
  program_id: number;
  material_code: string;
  material_name: string;
  material_type: string;
  generation_code?: string | null;
  origin?: string | null;
  germplasm_accession?: string | null;
  germplasm_name?: string | null;
  germplasm_source_file?: string | null;
  status?: string | null;
  is_check?: number | null;
  meta_json?: string | null;
  remarks?: string | null;
}

export interface BreedingTrialItem {
  id: number;
  program_id: number;
  trial_code: string;
  trial_name: string;
  trial_type: string;
  location_name?: string | null;
  season_label?: string | null;
  design_type?: string | null;
  replicate_count?: number | null;
  status?: string | null;
  objective?: string | null;
  sowing_date?: string | null;
  harvest_date?: string | null;
}

export interface BreedingPlotItem {
  id: number;
  trial_id: number;
  material_id: number;
  plot_code: string;
  replicate_no?: number | null;
  block_no?: number | null;
  row_no?: number | null;
  col_no?: number | null;
  treatment_code?: string | null;
  status?: string | null;
}

export interface BreedingBioSampleItem {
  id: number;
  sample_code: string;
  material_id: number;
  plot_id?: number | null;
  sample_type?: string | null;
  tissue_type?: string | null;
  timepoint?: string | null;
  collection_date?: string | null;
  status?: string | null;
  collector?: string | null;
  storage_location?: string | null;
}

export interface BreedingObservationItem {
  id: number;
  trial_id: number;
  plot_id?: number | null;
  material_id?: number | null;
  observation_level: string;
  trait_code: string;
  trait_name?: string | null;
  protocol_name?: string | null;
  obs_value_num?: number | null;
  obs_value_text?: string | null;
  obs_value_score?: string | null;
  obs_date?: string | null;
  observer?: string | null;
  qc_status?: string | null;
  source_dataset_id?: number | null;
  source_version_id?: number | null;
  source_asset_id?: number | null;
  source_row_key?: string | null;
}

export interface BreedingAssayItem {
  id: number;
  assay_code: string;
  biosample_id: number;
  assay_type: string;
  platform?: string | null;
  vendor?: string | null;
  run_date?: string | null;
  status?: string | null;
}

export interface BreedingDataFileItem {
  id: number;
  assay_id: number;
  dataset_id?: number | null;
  version_id?: number | null;
  asset_id?: number | null;
  asset_file_id?: number | null;
  source_mode: string;
  file_role: string;
  file_name?: string | null;
  file_format?: string | null;
  status?: string | null;
}

export async function getBreedingProgramListApi(
  data: BreedingProgramListParams,
) {
  return requestClient.post<BreedingListResult<BreedingProgramItem>>(
    '/breeding/program/list',
    data,
  );
}

export async function getBreedingProgramInfoApi(data: { id: number }) {
  return requestClient.post<BreedingProgramItem>('/breeding/program/info', data);
}

export async function getBreedingProgramOverviewApi(data: { id: number }) {
  return requestClient.post<BreedingProgramOverview>(
    '/breeding/program/overview',
    data,
  );
}

export async function getBreedingMaterialListApi(data: Record<string, any>) {
  return requestClient.post<BreedingListResult<BreedingMaterialItem>>(
    '/breeding/material/list',
    data,
  );
}

export async function getBreedingTrialListApi(data: Record<string, any>) {
  return requestClient.post<BreedingListResult<BreedingTrialItem>>(
    '/breeding/trial/list',
    data,
  );
}

export async function getBreedingPlotListApi(data: Record<string, any>) {
  return requestClient.post<BreedingListResult<BreedingPlotItem>>(
    '/breeding/plot/list',
    data,
  );
}

export async function getBreedingBioSampleListApi(data: Record<string, any>) {
  return requestClient.post<BreedingListResult<BreedingBioSampleItem>>(
    '/breeding/biosample/list',
    data,
  );
}

export async function getBreedingObservationListApi(data: Record<string, any>) {
  return requestClient.post<BreedingListResult<BreedingObservationItem>>(
    '/breeding/observation/list',
    data,
  );
}

export async function getBreedingAssayListApi(data: Record<string, any>) {
  return requestClient.post<BreedingListResult<BreedingAssayItem>>(
    '/breeding/assay/list',
    data,
  );
}

export async function getBreedingDataFileListApi(data: Record<string, any>) {
  return requestClient.post<BreedingListResult<BreedingDataFileItem>>(
    '/breeding/data-file/list',
    data,
  );
}
