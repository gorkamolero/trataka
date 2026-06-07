"""OpenCorporates API fallback for entity type + address where state bulk data
is thin. Free tier works without a token but is rate-limited; set
``OPENCORPORATES_API_TOKEN`` for higher limits.
"""

from __future__ import annotations

import os

import requests

from ..models import EntityType
from ..sources.registry import RegistryRecord, classify_entity_type

SEARCH_URL = "https://api.opencorporates.com/v0.4/companies/search"


def lookup_company(
    name: str, jurisdiction: str, timeout: float = 20.0
) -> RegistryRecord | None:
    """Best-effort single-company lookup. Returns None on any failure so the
    pipeline degrades gracefully rather than fabricating a record."""
    params = {
        "q": name,
        "jurisdiction_code": jurisdiction,
        "per_page": 1,
    }
    token = os.environ.get("OPENCORPORATES_API_TOKEN")
    if token:
        params["api_token"] = token

    try:
        resp = requests.get(SEARCH_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        companies = resp.json().get("results", {}).get("companies", [])
    except (requests.RequestException, ValueError):
        return None

    if not companies:
        return None

    c = companies[0]["company"]
    addr = c.get("registered_address") or {}
    etype = classify_entity_type(c.get("company_type") or c.get("name"))
    return RegistryRecord(
        normalized_name=name,
        raw_name=c.get("name", name),
        entity_type=etype or EntityType.UNKNOWN,
        address=addr.get("street_address"),
        city=addr.get("locality"),
        state=(addr.get("region") or "").upper() or None,
        zip=addr.get("postal_code"),
    )
