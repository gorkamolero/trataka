"""DOL OFLC LCA / H-1B disclosure data reader — the sponsorship signal.

The DOL publishes quarterly disclosure files (xlsx/csv) with one row per case.
Column names drift slightly year to year, so we map a set of known aliases to our
:class:`LcaFiling` fields and ignore the rest.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pandas as pd

from ..models import LcaFiling

# Map our field -> list of known DOL column aliases (case-insensitive match).
_COLUMN_ALIASES: dict[str, list[str]] = {
    "case_number": ["CASE_NUMBER", "CASE_NO"],
    "employer_name": ["EMPLOYER_NAME", "EMPLOYER_BUSINESS_DBA", "LCA_CASE_EMPLOYER_NAME"],
    "naics_code": ["NAICS_CODE", "EMPLOYER_NAICS_CODE", "LCA_CASE_NAICS_CODE"],
    "soc_code": ["SOC_CODE", "LCA_CASE_SOC_CODE", "OCCUPATIONAL_CODE"],
    "job_title": ["JOB_TITLE", "LCA_CASE_JOB_TITLE", "SOC_TITLE"],
    "worksite_city": ["WORKSITE_CITY", "WORKLOC1_CITY", "LCA_CASE_WORKLOC1_CITY"],
    "worksite_state": ["WORKSITE_STATE", "WORKLOC1_STATE", "LCA_CASE_WORKLOC1_STATE"],
    "worksite_zip": ["WORKSITE_POSTAL_CODE", "WORKLOC1_POSTAL_CODE"],
    "employer_city": ["EMPLOYER_CITY", "LCA_CASE_EMPLOYER_CITY"],
    "employer_state": ["EMPLOYER_STATE", "LCA_CASE_EMPLOYER_STATE"],
    "employer_zip": ["EMPLOYER_POSTAL_CODE", "LCA_CASE_EMPLOYER_POSTAL_CODE"],
    "fiscal_year": ["FISCAL_YEAR", "FY"],
    "case_status": ["CASE_STATUS", "STATUS", "APPROVAL_STATUS"],
}

CERTIFIED_STATUSES = {"CERTIFIED", "CERTIFIED-WITHDRAWN", "CERTIFIED - WITHDRAWN"}


def _resolve_columns(df: pd.DataFrame) -> dict[str, str]:
    """Return mapping of our_field -> actual column name present in df."""
    upper = {c.upper().strip(): c for c in df.columns}
    resolved: dict[str, str] = {}
    for field, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in upper:
                resolved[field] = upper[alias]
                break
    return resolved


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str, low_memory=False)


def _clean(v: object) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s or None


def read_lca_file(
    path: str | Path,
    certified_only: bool = True,
    states: list[str] | None = None,
) -> Iterator[LcaFiling]:
    """Yield :class:`LcaFiling` rows from a single DOL disclosure file (.csv,
    .csv.gz, or .xlsx).

    When ``states`` is given, rows are pre-filtered to those employer/worksite
    states in pandas before building objects — a large speed-up on the full
    national files.
    """
    path = Path(path)
    df = _read_table(path)
    cols = _resolve_columns(df)
    if "employer_name" not in cols:
        raise ValueError(f"{path.name}: could not find an employer-name column")

    # Reduce to just the columns we use, renamed to canonical field names.
    canon = pd.DataFrame({field: df[col] for field, col in cols.items()})
    del df

    # Vectorized certified filter: keep certified statuses (and rows whose status
    # is missing/blank, matching the original per-row behaviour).
    if certified_only and "case_status" in canon.columns:
        status = canon["case_status"].fillna("").astype(str).str.upper().str.strip()
        canon = canon[status.isin(CERTIFIED_STATUSES) | (status == "")]

    # Vectorized state pre-filter on employer OR worksite state.
    if states:
        wanted = {s.upper() for s in states}
        mask = pd.Series(False, index=canon.index)
        for c in ("employer_state", "worksite_state"):
            if c in canon.columns:
                col = canon[c].fillna("").astype(str).str.upper().str.strip()
                mask = mask | col.isin(wanted)
        canon = canon[mask]

    for rec in canon.to_dict("records"):
        name = _clean(rec.get("employer_name"))
        if not name:
            continue
        fy_raw = _clean(rec.get("fiscal_year"))
        try:
            fy = int(float(fy_raw)) if fy_raw else None
        except ValueError:
            fy = None
        status_val = (_clean(rec.get("case_status")) or "").upper() or None
        yield LcaFiling(
            case_number=_clean(rec.get("case_number")),
            employer_name=name,
            naics_code=_clean(rec.get("naics_code")),
            soc_code=_clean(rec.get("soc_code")),
            job_title=_clean(rec.get("job_title")),
            worksite_city=_clean(rec.get("worksite_city")),
            worksite_state=_clean(rec.get("worksite_state")),
            worksite_zip=_clean(rec.get("worksite_zip")),
            employer_city=_clean(rec.get("employer_city")),
            employer_state=_clean(rec.get("employer_state")),
            employer_zip=_clean(rec.get("employer_zip")),
            fiscal_year=fy,
            case_status=status_val,
        )


def read_lca_dir(
    directory: str | Path,
    certified_only: bool = True,
    states: list[str] | None = None,
) -> Iterator[LcaFiling]:
    """Yield filings from every supported file in a directory."""
    directory = Path(directory)
    for path in sorted(directory.glob("*")):
        name = path.name.lower()
        if name.endswith((".xlsx", ".xls", ".csv", ".csv.gz")) or name.endswith(".gz"):
            yield from read_lca_file(path, certified_only=certified_only, states=states)

