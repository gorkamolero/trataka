"""Filtered CSV export — the usable deliverable.

The default export is the "leads" view: companies in the target states with at
least one filing, ordered to surface the best small-software-LLC candidates
first. A separate export dumps the manual-review queue.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from .sources.centroids import centroid_for
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


def export_geojson(
    store: Store,
    out_path: str | Path,
    states: list[str] | None = None,
    llc_only: bool = False,
    min_filings: int = 1,
    use_centroids: bool = True,
    sample: bool = False,
) -> int:
    """Export leads as GeoJSON for the map viewer.

    Companies with precise lat/lon use them (``geocode_precision="address"``);
    otherwise, when ``use_centroids`` is set, they fall back to their city
    centroid (``geocode_precision="city"``). Companies that can't be placed at
    all are omitted from the map (but remain in the CSV and store).
    """
    conditions = [f"lca_filing_count >= {int(min_filings)}"]
    if states:
        joined = ", ".join(f"'{s.upper()}'" for s in states)
        conditions.append(f"state IN ({joined})")
    if llc_only:
        conditions.append("entity_type = 'LLC'")
    where = "WHERE " + " AND ".join(conditions)
    sql = f"""
        SELECT name, entity_type, naics_code, address, city, state, zip,
               latitude, longitude, lca_filing_count, approval_count,
               building_score, building_flags, in_target_band, size_confidence,
               job_titles, review_status
        FROM companies {where}
    """
    rel = store.query(sql)
    cols = [d[0] for d in rel.description]
    features = []
    for row in rel.fetchall():
        rec = dict(zip(cols, row, strict=False))
        lat, lon = rec.get("latitude"), rec.get("longitude")
        precision = "address"
        if lat is None or lon is None:
            if not use_centroids:
                continue
            c = centroid_for(rec.get("city"), rec.get("state"))
            if c is None:
                continue
            lat, lon, precision = c[0], c[1], "city"
        props = {
            "name": rec["name"],
            "entity_type": rec["entity_type"],
            "naics_code": rec["naics_code"],
            "address": rec["address"],
            "city": rec["city"],
            "state": rec["state"],
            "lca_filing_count": rec["lca_filing_count"],
            "approval_count": rec["approval_count"],
            "building_score": rec["building_score"],
            "in_target_band": rec["in_target_band"],
            "size_confidence": rec["size_confidence"],
            "review_status": rec["review_status"],
            "job_titles": json.loads(rec["job_titles"]) if rec["job_titles"] else [],
            "geocode_precision": precision,
            "sample": sample,
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": props,
            }
        )

    fc = {
        "type": "FeatureCollection",
        "metadata": {
            "generated_by": "visa-finder",
            "sample": sample,
            "states": states or [],
            "count": len(features),
        },
        "features": features,
    }
    Path(out_path).write_text(json.dumps(fc))
    return len(features)


def _maps_link(rec: dict) -> str:
    """A Google Maps search link for a company.

    Uses the precise address when known, otherwise name + city + state, with a
    lat/lon fallback so the pin lands somewhere useful even for city-level data.
    """
    parts = [rec.get("name")]
    if rec.get("address"):
        parts.append(rec["address"])
    parts += [rec.get("city"), rec.get("state")]
    query = ", ".join(p for p in parts if p)
    if not query and rec.get("latitude") is not None:
        query = f"{rec['latitude']},{rec['longitude']}"
    return f"https://www.google.com/maps/search/?api=1&query={quote(query)}"


def _md_cell(value: object) -> str:
    if value is None:
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def export_markdown(
    store: Store,
    out_path: str | Path,
    states: list[str] | None = None,
    llc_only: bool = False,
    min_filings: int = 1,
    sample: bool = False,
) -> int:
    """Write a human-readable Markdown report: a sorted leads table with a
    Google Maps link per company, plus a short review-queue section."""
    conditions = [f"lca_filing_count >= {int(min_filings)}"]
    if states:
        joined = ", ".join(f"'{s.upper()}'" for s in states)
        conditions.append(f"state IN ({joined})")
    if llc_only:
        conditions.append("entity_type = 'LLC'")
    where = "WHERE " + " AND ".join(conditions)
    sql = f"""
        SELECT name, entity_type, naics_code, address, city, state, zip,
               latitude, longitude, lca_filing_count, approval_count,
               building_score, in_target_band, size_confidence, job_titles,
               review_status
        FROM companies {where}
        ORDER BY (entity_type = 'LLC') DESC,
                 COALESCE(in_target_band, FALSE) DESC,
                 COALESCE(building_score, 0) DESC,
                 lca_filing_count ASC
    """
    rel = store.query(sql)
    cols = [d[0] for d in rel.description]
    rows = [dict(zip(cols, r, strict=False)) for r in rel.fetchall()]

    states_label = ", ".join(states) if states else "all"
    lines: list[str] = []
    lines.append("# H1B Small-Software-Sponsor Finder — Findings")
    lines.append("")
    if sample:
        lines.append(
            "> ⚠️ **SAMPLE DATA** — synthetic companies placed at city centroids, "
            "for demonstration only. Run the pipeline with real DOL data for live leads."
        )
        lines.append("")
    lines.append(
        f"States: **{states_label}** · Companies: **{len(rows)}** · "
        f"LLC: **{sum(1 for r in rows if r['entity_type'] == 'LLC')}** · "
        f"In target band (2–10): **{sum(1 for r in rows if r['in_target_band'])}**"
    )
    lines.append("")
    lines.append("> Leads to verify, not ground truth. Headcount is never fabricated — "
                 "it is always *unknown*, with a confidence band derived from filing "
                 "volume and building size.")
    lines.append("")
    lines.append(
        "| # | Company | Type | Location | NAICS | Filings | Approvals | "
        "In band | Confidence | Review | Map |"
    )
    lines.append("|---|---------|------|----------|-------|--------:|----------:|"
                 "---------|------------|--------|-----|")
    for i, r in enumerate(rows, 1):
        loc = ", ".join(p for p in [r.get("city"), r.get("state")] if p) or "—"
        band_val = r["in_target_band"]
        band = "✅" if band_val is True else ("—" if band_val is None else "✗")
        review = "🔎 review" if r["review_status"] == "needs_review" else "auto"
        maps = f"[📍 Maps]({_maps_link(r)})"
        lines.append(
            f"| {i} | {_md_cell(r['name'])} | {_md_cell(r['entity_type'])} | "
            f"{_md_cell(loc)} | {_md_cell(r['naics_code'])} | {r['lca_filing_count']} | "
            f"{_md_cell(r['approval_count'])} | {band} | {_md_cell(r['size_confidence'])} | "
            f"{review} | {maps} |"
        )
    lines.append("")

    # Per-company detail with job titles (kept out of the table for width).
    lines.append("## Detail")
    lines.append("")
    for i, r in enumerate(rows, 1):
        titles = json.loads(r["job_titles"]) if r["job_titles"] else []
        lines.append(f"**{i}. {r['name']}** — {r['entity_type']}, "
                     f"{', '.join(p for p in [r.get('city'), r.get('state')] if p)}")
        detail = [f"{r['lca_filing_count']} LCA filing(s)"]
        if r["approval_count"] is not None:
            detail.append(f"{r['approval_count']} USCIS approval(s)")
        if titles:
            detail.append("titles: " + ", ".join(titles))
        detail.append(f"[Google Maps]({_maps_link(r)})")
        lines.append("  - " + " · ".join(detail))
        lines.append("")

    Path(out_path).write_text("\n".join(lines))
    return len(rows)


def export_review_queue(store: Store, out_path: str | Path) -> int:
    sql = (
        "SELECT name, aliases, entity_type, state, lca_filing_count, "
        "match_confidence, review_status FROM companies "
        "WHERE review_status = 'needs_review' ORDER BY match_confidence DESC"
    )
    out_path = Path(out_path)
    store.con.execute(f"COPY ({sql}) TO '{out_path}' (HEADER, DELIMITER ',')")
    return store.con.execute(f"SELECT COUNT(*) FROM ({sql})").fetchone()[0]
