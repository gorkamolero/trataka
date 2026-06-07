"""Source adapters for the free/public inputs.

Each source is described by a :class:`SourceInfo` so the CLI can list them and
explain where the data comes from and how to fetch it. We deliberately stick to
official bulk downloads and free APIs and avoid sources whose terms prohibit
scraping.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceInfo:
    key: str
    name: str
    signal: str
    homepage: str
    fetch_hint: str
    terms_ok: bool = True


SOURCES: dict[str, SourceInfo] = {
    "lca": SourceInfo(
        key="lca",
        name="DOL OFLC LCA / H-1B disclosure data",
        signal="Sponsorship (#1) — certified H1B/LCA filings; carries NAICS + SOC + addresses",
        homepage="https://www.dol.gov/agencies/eta/foreign-labor/performance",
        fetch_hint=(
            "Download the quarterly 'LCA Programs (H-1B, H-1B1, E-3)' disclosure "
            "file (xlsx) for the fiscal year, save under data/raw/lca/."
        ),
    ),
    "h1b_hub": SourceInfo(
        key="h1b_hub",
        name="USCIS H-1B Employer Data Hub",
        signal="Corroboration — approval / petition counts per employer",
        homepage="https://www.uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub",
        fetch_hint="Download the Employer Data Hub CSV export, save under data/raw/h1b_hub/.",
    ),
    "registry_mo": SourceInfo(
        key="registry_mo",
        name="Missouri SOS business registry",
        signal="Entity type (#4) + registered address",
        homepage="https://bsd.sos.mo.gov/",
        fetch_hint="Use the MO SOS entity search / bulk extract; save under data/raw/registry/mo/.",
    ),
    "registry_tx": SourceInfo(
        key="registry_tx",
        name="Texas Comptroller Active Franchise Tax Permit Holders",
        signal="Entity type (#4) + registered address",
        homepage="https://comptroller.texas.gov/transparency/open-data/",
        fetch_hint="Download Active Franchise Tax Permit Holders to data/raw/registry/tx/.",
    ),
    "building": SourceInfo(
        key="building",
        name="US Census Geocoder + OpenStreetMap/Overpass",
        signal="Small-building score (#5) — geocoding + building footprints",
        homepage="https://geocoding.geo.census.gov/",
        fetch_hint="Geocoded on demand via the free Census geocoder; building tags via Overpass.",
    ),
    "opencorporates": SourceInfo(
        key="opencorporates",
        name="OpenCorporates API",
        signal="Registry fallback where state bulk data is thin",
        homepage="https://api.opencorporates.com/documentation/API-Reference",
        fetch_hint="Free tier API; set OPENCORPORATES_API_TOKEN for higher limits.",
    ),
}


def list_sources() -> list[SourceInfo]:
    return list(SOURCES.values())
