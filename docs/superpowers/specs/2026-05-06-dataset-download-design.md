# Dataset File Download System Design

> **Date:** 2026-05-06 | **Status:** Approved

## Goal

Allow administrators to mark dataset files as downloadable, and public users to download them via the public portal.

## Data Model

Add `is_downloadable` column to `asset_file` table:

| Column | Type | Default |
|--------|------|---------|
| `is_downloadable` | Boolean | false |

## Backend API

### 1. Admin: Toggle download flag

Reuse existing `POST /admin/dataset/asset/file/update` — add `is_downloadable` to the update schema.

### 2. Public: List downloadable files

`GET /public/dataset/{dataset_code}/downloads` — returns:
```json
{
  "dataset_code": "ds-17",
  "files": [
    {"id": 57, "file_name": "genome.fa.gz", "file_format": "fa.gz", "file_size": 494981933, "is_downloadable": true}
  ]
}
```

### 3. Public: Download file

`GET /public/dataset/{dataset_code}/download/{file_id}` — returns `FileResponse` with appropriate `Content-Disposition` header.

## Admin-Web Changes

- `AssetPanel.vue`: Add download toggle switch in each file row + in file edit modal
- `api/apps/dataset.ts`: Add `is_downloadable` to types

## Public-Web Changes

- `Tools.vue` Download tab: Show downloadable files with size, format, download button
- `genome/Home.vue`: Add quick download links for key files
