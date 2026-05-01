#!/usr/bin/env python3
"""
Dataset Query API Test Script

Tests each query operation against available datasets to verify
all query endpoints are working correctly.

Usage:
  # Copy the access_token from browser DevTools → Application → Local Storage → accessToken
  export FAN_TOKEN="<your-access-token>"
  python3 scripts/test_dataset_queries.py

  # Or with a specific dataset ID:
  python3 scripts/test_dataset_queries.py --dataset-id 1
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from typing import Any

BASE_URL = os.environ.get("FAN_API_BASE", "http://127.0.0.1:8001")
API_PREFIX = "/api/v1/admin/dataset"
TOKEN = os.environ.get("FAN_TOKEN", "")

# Default params for each known operation type
DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "genes_list": {"max_records": 10},
    "samples_list": {"max_records": 10},
    "matrix_slice": {"data_type": "count", "genes": [], "samples": []},
    "query": {"regions": []},
    "region_features": {"region": "Chr1:1-10000", "feature_type": "gene", "limit": 5},
    "gene_search": {"keyword": "AT1G01010", "page": 1, "page_size": 5},
    "gene_list": {"page": 1, "page_size": 5},
    "gene_info": {"gene_id": "AT1G01010"},
    "transcript_list": {"page": 1, "page_size": 5},
    "term_lookup": {"term_source": "go", "keyword": "kinase", "limit": 5},
    "term_gene_list": {"term_source": "go", "term_id": "GO:0005524", "page": 1, "size": 5},
    "batch_fetch": {"regions": []},
    "dataset_summary": {},
    "trait_list": {"limit": 5},
    "trait_search": {"keyword": "height", "limit": 5},
    "trait_values": {"trait": "", "timepoint": "", "limit": 5},
    "subject_list": {"limit": 5},
    "subject_detail": {"subject_id": ""},
}


def api_post(path: str, data: dict[str, Any]) -> dict[str, Any]:
    """Make an authenticated POST request to the API."""
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"code": e.code, "msg": str(e), "data": None}
    except urllib.error.URLError as e:
        return {"code": -1, "msg": f"Connection error: {e.reason}", "data": None}


def get_datasets() -> list[dict[str, Any]]:
    """Fetch all datasets."""
    resp = api_post(f"{API_PREFIX}/list", {"page": 1, "page_size": 100})
    data = resp.get("data", resp)
    return data.get("dataList", data.get("items", []))


def get_dataset_detail(dataset_id: int) -> dict[str, Any]:
    """Fetch dataset detail info."""
    resp = api_post(f"{API_PREFIX}/info", {"id": dataset_id})
    return resp.get("data", resp)


def get_version_capabilities(version_id: int, asset_code: str | None = None) -> dict[str, Any]:
    """Fetch query capabilities for a version."""
    body: dict[str, Any] = {"id": version_id}
    if asset_code:
        body["asset_code"] = asset_code
    resp = api_post(f"{API_PREFIX}/version/query/capabilities", body)
    return resp.get("data", resp)


def execute_query(version_id: int, operation: str, params: dict[str, Any], asset_code: str | None = None) -> dict[str, Any]:
    """Execute a query operation."""
    body: dict[str, Any] = {
        "id": version_id,
        "operation": operation,
        "params": params,
    }
    if asset_code:
        body["asset_code"] = asset_code
    resp = api_post(f"{API_PREFIX}/version/query/execute", body)
    return resp


def check_auth() -> bool:
    """Verify the token is valid."""
    if not TOKEN:
        return False
    resp = api_post(f"{API_PREFIX}/list", {"page": 1, "page_size": 1})
    return not isinstance(resp.get("code"), int) or resp.get("code", 0) < 4000


def main():
    if not TOKEN:
        print("ERROR: FAN_TOKEN environment variable not set.")
        print("  export FAN_TOKEN=\"<your-access-token>\"")
        print("  Get the token from browser DevTools → Application → Local Storage → accessToken")
        sys.exit(1)

    if not check_auth():
        print("ERROR: Invalid or expired token. Please get a fresh token from the browser.")
        sys.exit(1)

    print(f"API: {BASE_URL}")
    print(f"Token: {TOKEN[:20]}...{TOKEN[-10:]}" if len(TOKEN) > 40 else f"Token: {TOKEN[:10]}...")

    # Get datasets
    datasets = get_datasets()
    print(f"\n{'='*80}")
    print(f"Found {len(datasets)} datasets")

    # Filter to datasets that have query adapters
    testable = []
    for ds in datasets:
        ds_id = ds.get("id")
        print(f"\n--- Dataset [{ds_id}]: {ds.get('dataset_code', '?')} "
              f"(type={ds.get('dataset_type', '?')}, lifecycle={ds.get('lifecycle_state', '?')})")
        detail = get_dataset_detail(ds_id)
        current_version = detail.get("current_version", {})
        if not current_version:
            print("  SKIP: no current version")
            continue

        version_id = current_version.get("id")
        version_str = current_version.get("version", "?")

        caps = get_version_capabilities(version_id)
        if caps.get("code") and caps.get("code", 0) >= 4000:
            print(f"  SKIP v{version_str}: capabilities error - {caps.get('msg', 'unknown')}")
            continue

        adapter = caps.get("query_adapter", {}) or {}
        operations = adapter.get("supported_operations", [])
        if not operations:
            print(f"  SKIP v{version_str}: no operations available (adapter={adapter.get('adapter', caps.get('query_engine', 'none'))})")
            continue

        query_entry = caps.get("query_entry_asset", {})
        asset_code = query_entry.get("asset_code") if query_entry else None
        file_access = caps.get("file_access", {}) or {}
        file_ok = file_access.get("exists_on_server", False)

        testable.append({
            "dataset_id": ds_id,
            "version_id": version_id,
            "version": version_str,
            "dataset_code": ds.get("dataset_code", "?"),
            "dataset_type": ds.get("dataset_type", "?"),
            "operations": operations,
            "asset_code": asset_code,
            "file_ok": file_ok,
        })
        print(f"  v{version_str}: {len(operations)} operation(s): {', '.join(operations[:8])}{'...' if len(operations) > 8 else ''}")
        print(f"    asset={asset_code or 'N/A'}, file_accessible={file_ok}")

    if not testable:
        print("\nNo datasets with query capabilities found.")
        return

    # Run query tests
    print(f"\n{'='*80}")
    print("Running query tests...")
    print(f"{'='*80}")

    total_tests = 0
    passed = 0
    failed = 0
    skipped = 0

    for entry in testable:
        ds_code = entry["dataset_code"]
        version_str = entry["version"]
        version_id = entry["version_id"]
        asset_code = entry["asset_code"]
        file_ok = entry["file_ok"]

        print(f"\n▶ Dataset [{entry['dataset_id']}]: {ds_code} v{version_str}")

        if not file_ok:
            print("  ⚠ WARNING: File not accessible on server — queries may fail")

        for op in entry["operations"]:
            total_tests += 1
            params = DEFAULT_PARAMS.get(op, {})
            print(f"  [{op}] ", end="", flush=True)

            start = time.time()
            result = execute_query(version_id, op, params, asset_code)
            elapsed = time.time() - start

            code = result.get("code", 2000) if isinstance(result.get("code"), int) else 0
            msg = result.get("msg", "")

            if code >= 4000:
                print(f"✗ FAIL ({elapsed:.1f}s) — {msg}")
                failed += 1
                print(f"        params: {json.dumps(params, ensure_ascii=False)[:120]}")
            elif code == 2000 or "data" in result:
                data_size = len(json.dumps(result.get("data", result)))
                print(f"✓ PASS ({elapsed:.1f}s, {data_size}B)")
                passed += 1
            else:
                print(f"? UNEXPECTED ({elapsed:.1f}s) — code={code}, msg={msg}")
                failed += 1

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Datasets tested:  {len(testable)}")
    print(f"Total tests:      {total_tests}")
    print(f"Passed:           {passed}")
    print(f"Failed:           {failed}")
    print(f"Pass rate:        {passed/total_tests*100:.0f}%" if total_tests else "N/A")

    if failed > 0:
        print("\n⚠ Some queries failed. Possible reasons:")
        print("  1. File not accessible on server (check file path/backend mount)")
        print("  2. Adapter configured but underlying data missing")
        print("  3. Operation requires specific params — try different default params")
        sys.exit(1)


if __name__ == "__main__":
    main()
