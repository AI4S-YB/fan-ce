import { requestClient } from '#/api/request';

export interface BreedingDatasetSubjectLinkCreateParams {
  dataset_id: number;
  version_id: number;
  asset_id?: number | null;
  program_id?: number | null;
  material_id?: number | null;
  trial_id?: number | null;
  plot_id?: number | null;
  biosample_id?: number | null;
  role: string;
  mapping_status?: string;
  mapping_method?: string;
  confidence?: string | null;
  is_primary?: number;
  note?: string | null;
}

export async function createBrdDatasetSubjectLinkApi(
  data: BreedingDatasetSubjectLinkCreateParams,
) {
  return requestClient.post('/breeding/dataset-subject-link/create', data);
}
