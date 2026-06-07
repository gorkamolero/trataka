"""DuckDB-backed queryable store for company records.

DuckDB gives us a single-file, SQL-queryable store that handles the dedup-heavy
joins well and exports to CSV trivially. Records are upserted by ``company_id``
so quarterly re-runs accumulate rather than duplicate, and ``first_seen`` /
``last_seen`` track appearance over time.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import duckdb

from .models import Company

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    company_id        VARCHAR PRIMARY KEY,
    name              VARCHAR,
    normalized_name   VARCHAR,
    aliases           VARCHAR,      -- json array
    naics_code        VARCHAR,
    naics_description VARCHAR,
    entity_type       VARCHAR,
    entity_type_source VARCHAR,
    is_staffing       BOOLEAN,
    address           VARCHAR,
    city              VARCHAR,
    state             VARCHAR,
    zip               VARCHAR,
    latitude          DOUBLE,
    longitude         DOUBLE,
    building_score    DOUBLE,
    building_flags    VARCHAR,      -- json array
    lca_filing_count  INTEGER,
    job_titles        VARCHAR,      -- json array
    soc_codes         VARCHAR,      -- json array
    approval_count    INTEGER,
    headcount         VARCHAR,
    size_confidence   VARCHAR,
    in_target_band    BOOLEAN,
    match_confidence  DOUBLE,
    review_status     VARCHAR,
    source_links      VARCHAR,      -- json object
    first_seen        DATE,
    last_seen         DATE
);
"""

_COLUMNS = [
    "company_id", "name", "normalized_name", "aliases", "naics_code",
    "naics_description", "entity_type", "entity_type_source", "is_staffing",
    "address", "city",
    "state", "zip", "latitude", "longitude", "building_score", "building_flags",
    "lca_filing_count", "job_titles", "soc_codes", "approval_count", "headcount",
    "size_confidence", "in_target_band", "match_confidence", "review_status",
    "source_links", "first_seen", "last_seen",
]


class Store:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self.con = duckdb.connect(self.path)
        self.con.execute(SCHEMA)

    def close(self) -> None:
        self.con.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _row(self, c: Company, today: date) -> list:
        def enum_val(v: object) -> object:
            return getattr(v, "value", v)

        return [
            c.company_id, c.name, c.normalized_name, json.dumps(c.aliases),
            c.naics_code, c.naics_description, enum_val(c.entity_type),
            c.entity_type_source, c.is_staffing, c.address, c.city, c.state, c.zip,
            c.latitude, c.longitude, c.building_score, json.dumps(c.building_flags),
            c.lca_filing_count, json.dumps(c.job_titles), json.dumps(c.soc_codes),
            c.approval_count, c.headcount, enum_val(c.size_confidence),
            c.in_target_band, c.match_confidence, enum_val(c.review_status),
            json.dumps(c.source_links), c.first_seen or today, c.last_seen or today,
        ]

    def upsert(self, companies: list[Company], seen_date: date | None = None) -> int:
        """Insert or update companies by company_id, preserving first_seen."""
        today = seen_date or date.today()
        placeholders = ", ".join(["?"] * len(_COLUMNS))
        cols = ", ".join(_COLUMNS)
        # Preserve the earliest first_seen across runs; always advance last_seen.
        update_cols = [c for c in _COLUMNS if c not in ("company_id", "first_seen")]
        set_clause = ", ".join(f"{c}=excluded.{c}" for c in update_cols)
        sql = (
            f"INSERT INTO companies ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT (company_id) DO UPDATE SET {set_clause}, "
            f"first_seen=LEAST(companies.first_seen, excluded.first_seen)"
        )
        for c in companies:
            self.con.execute(sql, self._row(c, today))
        return len(companies)

    def query(self, sql: str):
        """Run an arbitrary read query; returns a DuckDB relation."""
        return self.con.execute(sql)

    def count(self) -> int:
        return self.con.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
