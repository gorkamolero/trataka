"""Filtered CSV export — the usable deliverable.

The default export is the "leads" view: companies in the target states with at
least one filing, ordered to surface the best small-software-LLC candidates
first. A separate export dumps the manual-review queue.
"""

from __future__ import annotations

from pathlib import Path

from .store import Store

LEADS_VIEW = """
SELECT
    name,
    entity_type,
    naics_code,
    address, city, state, zip,
    lca_filing_count,
    approval_count,
    building_score,
    building_flags,
    in_target_band,
    size_confidence,
    job_titles,
    review_status,
    first_seen, last_seen
FROM companies
{where}
ORDER BY
    (entity_type = 'LLC') DESC,
    COALESCE(in_target_band, FALSE) DESC,
    COALESCE(building_score, 0) DESC,
    lca_filing_count ASC
"""


def export_leads(
    store: Store,
    out_path: str | Path,
    states: list[str] | None = None,
    llc_only: bool = False,
    min_filings: int = 1,
) -> int:
    conditions = [f"lca_filing_count >= {int(min_filings)}"]
    if states:
        joined = ", ".join(f"'{s.upper()}'" for s in states)
        conditions.append(f"state IN ({joined})")
    if llc_only:
        conditions.append("entity_type = 'LLC'")
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = LEADS_VIEW.format(where=where)

    out_path = Path(out_path)
    # DuckDB writes the CSV directly from the query.
    store.con.execute(
        f"COPY ({sql}) TO '{out_path}' (HEADER, DELIMITER ',')"
    )
    n = store.con.execute(f"SELECT COUNT(*) FROM ({sql})").fetchone()[0]
    return n


def export_review_queue(store: Store, out_path: str | Path) -> int:
    sql = (
        "SELECT name, aliases, entity_type, state, lca_filing_count, "
        "match_confidence, review_status FROM companies "
        "WHERE review_status = 'needs_review' ORDER BY match_confidence DESC"
    )
    out_path = Path(out_path)
    store.con.execute(f"COPY ({sql}) TO '{out_path}' (HEADER, DELIMITER ',')")
    return store.con.execute(f"SELECT COUNT(*) FROM ({sql})").fetchone()[0]
