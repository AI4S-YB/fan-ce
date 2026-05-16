import { requestClient } from '#/api/request';

export interface SiteItem {
  site_code: string;
  site_name: string;
  site_title: string;
  domain: string;
  test_port: string;
  logo_text?: string;
  contact_email?: string;
  footer_copyright?: string;
  extra_json?: string;
  dataset_count?: number;
}

export interface SiteListResponse {
  items: SiteItem[];
}

export interface SiteDatasetsResponse {
  items: Array<{
    id: number;
    dataset_code?: string;
    dataset_name?: string;
    species_name?: string;
  }>;
}

export interface DatasetSitesResponse {
  items: SiteItem[];
}

export function createSiteApi(data: Partial<SiteItem>) {
  return requestClient.post<SiteItem>('/admin/sites', data);
}

export function listSitesApi() {
  return requestClient.get<SiteListResponse>('/admin/sites');
}

export function updateSiteApi(siteCode: string, data: Partial<SiteItem>) {
  return requestClient.put<SiteItem>(`/admin/sites/${siteCode}`, data);
}

export function deleteSiteApi(siteCode: string) {
  return requestClient.delete(`/admin/sites/${siteCode}`);
}

export function bindDatasetApi(siteCode: string, datasetId: number) {
  return requestClient.post(`/admin/sites/${siteCode}/datasets`, {
    dataset_id: datasetId,
  });
}

export function unbindDatasetApi(siteCode: string, datasetId: number) {
  return requestClient.delete(`/admin/sites/${siteCode}/datasets/${datasetId}`);
}

export function listSiteDatasetsApi(siteCode: string) {
  return requestClient.get<SiteDatasetsResponse>(
    `/admin/sites/${siteCode}/datasets`,
  );
}

export function listDatasetSitesApi(datasetId: number) {
  return requestClient.get<DatasetSitesResponse>(
    `/admin/datasets/${datasetId}/sites`,
  );
}
