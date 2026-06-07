"""Hard filters (signals #1–#3) applied to raw LCA filings.

These are the cheapest, highest-value cuts and run first: a filing must be
certified (sponsorship), in a target state, and from a software employer.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from ..config import Config
from ..models import LcaFiling


def filing_state(filing: LcaFiling) -> str | None:
    """Prefer the employer's state; fall back to the worksite state."""
    return (filing.employer_state or filing.worksite_state or "").upper() or None


def passes_state(filing: LcaFiling, states: Iterable[str]) -> bool:
    st = filing_state(filing)
    return st in {s.upper() for s in states}


def passes_software(filing: LcaFiling, cfg: Config) -> bool:
    return cfg.software.is_software(filing.naics_code, filing.soc_code)


def apply_hard_filters(
    filings: Iterable[LcaFiling],
    cfg: Config,
    states: Iterable[str],
) -> Iterator[LcaFiling]:
    """Yield only filings that pass sponsorship + state + software filters.

    (Sponsorship is enforced upstream by reading certified-only rows, but we
    re-check defensively here.)
    """
    state_set = {s.upper() for s in states}
    for f in filings:
        if f.case_status and f.case_status.upper().startswith("DENIED"):
            continue
        if not passes_state(f, state_set):
            continue
        if not passes_software(f, cfg):
            continue
        yield f
