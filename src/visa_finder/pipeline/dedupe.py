"""Dedupe filings into one :class:`Company` per real employer.

Two stages:
  1. Exact collapse on (normalized_name, state) -> a candidate company with
     aggregated filing counts, job titles, and SOC codes.
  2. Fuzzy merge of candidates whose normalized names are very similar within the
     same state (handles "Acme Software" vs "Acme Software Solutions"). Merges
     below a confidence threshold are flagged for the manual-review queue rather
     than merged silently.
"""

from __future__ import annotations

from collections.abc import Iterable

from rapidfuzz import fuzz

from ..models import Company, LcaFiling, ReviewStatus
from ..normalize import company_id, normalize_name
from ..sources.registry import classify_entity_type
from .filters import filing_state

# Above this similarity we merge automatically; between review/auto we merge but
# flag for review; below review we keep separate.
AUTO_MERGE = 92.0
REVIEW_MERGE = 85.0
# A near-total token-set match (one name is the other plus extra descriptor
# words, e.g. "Acme Software" vs "Acme Software Solutions") is a merge candidate,
# but only when the names share enough tokens to avoid a single common word
# (e.g. "Apps") swallowing unrelated companies.
SET_MERGE = 95.0
MIN_SHARED_TOKENS = 2


def match(a: str, b: str) -> tuple[bool, float, bool]:
    """Compare two normalized names.

    Returns (should_merge, confidence_0_1, needs_review).
    """
    sort_score = fuzz.token_sort_ratio(a, b)
    if sort_score >= AUTO_MERGE:
        return True, round(sort_score / 100.0, 3), False
    if sort_score >= REVIEW_MERGE:
        return True, round(sort_score / 100.0, 3), True

    set_score = fuzz.token_set_ratio(a, b)
    shared = len(set(a.split()) & set(b.split()))
    if set_score >= SET_MERGE and shared >= MIN_SHARED_TOKENS:
        return True, round(set_score / 100.0, 3), True
    return False, round(max(sort_score, set_score) / 100.0, 3), False


def _employer_address(filing: LcaFiling) -> tuple[str | None, str | None, str | None]:
    return filing.employer_city, filing.employer_state, filing.employer_zip


def _employer_street(filing: LcaFiling) -> str | None:
    parts = [filing.employer_address1, filing.employer_address2]
    street = " ".join(p for p in parts if p).strip()
    return street or None


def collapse_exact(filings: Iterable[LcaFiling]) -> dict[str, Company]:
    """Stage 1: exact collapse on (normalized_name, state).

    Filings are de-duplicated by case number first, so overlapping cumulative
    quarterly files (DOL's Q-files repeat earlier cases) don't inflate counts.
    """
    companies: dict[str, Company] = {}
    seen_cases: set[str] = set()
    for f in filings:
        if f.case_number:
            if f.case_number in seen_cases:
                continue
            seen_cases.add(f.case_number)
        state = filing_state(f)
        norm = normalize_name(f.employer_name)
        if not norm:
            continue
        cid = company_id(norm, state)
        comp = companies.get(cid)
        if comp is None:
            city, st, zp = _employer_address(f)
            comp = Company(
                company_id=cid,
                name=f.employer_name,
                normalized_name=norm,
                naics_code=f.naics_code,
                address=_employer_street(f),
                city=city,
                state=st or state,
                zip=zp,
                # Low-confidence entity type inferred from the name. The LLC gate
                # overrides this with authoritative registry data when available.
                entity_type=classify_entity_type(f.employer_name),
                entity_type_source="name_inference",
            )
            companies[cid] = comp

        comp.lca_filing_count += 1
        if f.employer_name not in comp.aliases and f.employer_name != comp.name:
            comp.aliases.append(f.employer_name)
        if f.job_title and f.job_title not in comp.job_titles:
            comp.job_titles.append(f.job_title)
        if f.soc_code and f.soc_code not in comp.soc_codes:
            comp.soc_codes.append(f.soc_code)
        if not comp.naics_code and f.naics_code:
            comp.naics_code = f.naics_code
    return companies


def fuzzy_merge(companies: dict[str, Company]) -> list[Company]:
    """Stage 2: merge near-duplicate names within the same state."""
    by_state: dict[str, list[Company]] = {}
    for comp in companies.values():
        by_state.setdefault(comp.state or "", []).append(comp)

    merged: list[Company] = []
    for _state, group in by_state.items():
        # Sort by filing count desc so the larger record becomes the survivor.
        group.sort(key=lambda c: c.lca_filing_count, reverse=True)
        consumed: set[str] = set()
        for i, primary in enumerate(group):
            if primary.company_id in consumed:
                continue
            for other in group[i + 1 :]:
                if other.company_id in consumed:
                    continue
                should_merge, confidence, needs_review = match(
                    primary.normalized_name, other.normalized_name
                )
                if should_merge:
                    _absorb(primary, other)
                    consumed.add(other.company_id)
                    primary.match_confidence = confidence
                    if needs_review:
                        primary.review_status = ReviewStatus.NEEDS_REVIEW
            merged.append(primary)
    return merged


def _absorb(primary: Company, other: Company) -> None:
    primary.lca_filing_count += other.lca_filing_count
    for alias in [other.name, *other.aliases]:
        if alias != primary.name and alias not in primary.aliases:
            primary.aliases.append(alias)
    for jt in other.job_titles:
        if jt not in primary.job_titles:
            primary.job_titles.append(jt)
    for soc in other.soc_codes:
        if soc not in primary.soc_codes:
            primary.soc_codes.append(soc)
    if not primary.naics_code and other.naics_code:
        primary.naics_code = other.naics_code


def dedupe(filings: Iterable[LcaFiling]) -> list[Company]:
    """Full dedupe: exact collapse then fuzzy merge."""
    return fuzzy_merge(collapse_exact(filings))
