from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlencode
from xml.etree import ElementTree

import requests


class NcbiTaxonomyClient:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, *, tool: str = "fan-ce", email: str | None = None, timeout: int = 20):
        self.tool = tool
        self.email = email
        self.timeout = timeout

    def _build_params(self, **params):
        payload = {"tool": self.tool, **params}
        if self.email:
            payload["email"] = self.email
        return payload

    def _get_json(self, endpoint: str, **params):
        response = requests.get(
            f"{self.BASE_URL}/{endpoint}",
            params=self._build_params(**params),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def _get_text(self, endpoint: str, **params):
        response = requests.get(
            f"{self.BASE_URL}/{endpoint}",
            params=self._build_params(**params),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.text

    def search_taxonomy_ids(self, keyword: str, *, limit: int = 20) -> list[int]:
        text = str(keyword or "").strip()
        if not text:
            return []
        payload = self._get_json(
            "esearch.fcgi",
            db="taxonomy",
            term=text,
            retmode="json",
            retmax=max(1, min(int(limit or 20), 100)),
        )
        id_list = payload.get("esearchresult", {}).get("idlist", [])
        return [int(item) for item in id_list if str(item).isdigit()]

    def fetch_taxa(self, tax_ids: list[int]) -> list[dict[str, Any]]:
        tax_ids = [int(item) for item in tax_ids if item]
        if not tax_ids:
            return []

        xml_text = self._get_text(
            "efetch.fcgi",
            db="taxonomy",
            id=",".join(str(item) for item in tax_ids),
        )
        root = ElementTree.fromstring(xml_text)
        records: list[dict[str, Any]] = []
        for taxon in root.findall("./Taxon"):
            tax_id_text = taxon.findtext("TaxId")
            if not tax_id_text:
                continue
            lineage_nodes = taxon.findall("./LineageEx/Taxon")
            common_name = taxon.findtext("./OtherNames/CommonName")
            lineage_names = [item.findtext("ScientificName") for item in lineage_nodes if item.findtext("ScientificName")]
            records.append(
                {
                    "tax_id": int(tax_id_text),
                    "scientific_name": taxon.findtext("ScientificName"),
                    "common_name": common_name,
                    "rank": taxon.findtext("Rank"),
                    "parent_tax_id": int(taxon.findtext("ParentTaxId") or 0) or None,
                    "lineage": taxon.findtext("Lineage"),
                    "lineage_names": lineage_names,
                    "source": "ncbi_sync",
                    "is_active": 1,
                    "last_sync_time": datetime.utcnow(),
                }
            )
        return records

    def fetch_taxon(self, tax_id: int) -> dict[str, Any] | None:
        records = self.fetch_taxa([tax_id])
        return records[0] if records else None

    def search_taxa(self, keyword: str, *, limit: int = 20) -> list[dict[str, Any]]:
        tax_ids = self.search_taxonomy_ids(keyword, limit=limit)
        return self.fetch_taxa(tax_ids)


ncbi_taxonomy_client = NcbiTaxonomyClient()
